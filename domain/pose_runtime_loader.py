from __future__ import annotations

lazy import hashlib
lazy import threading
lazy from dataclasses import dataclass
lazy from pathlib import PurePosixPath
lazy from typing import Literal, Protocol

lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_full_body_rig import FULL_BODY_RIG_SCHEMA_VERSION
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id

type LoadStatus = Literal["activated", "rejected", "cancelled", "stale"]
type RigContract = Literal["full-body-v4", "legacy-v3"]
FULL_BODY_RIG_ID = "mohan-full-body-v1"
LEGACY_YAWS = (-30, 0, 30)
FULL_BODY_CORRECTIONS = frozenset({
    "left-leg-correction", "right-leg-correction", "left-foot-correction",
    "right-foot-correction", "left-sole-correction", "right-sole-correction",
})


@dataclass(frozen=True, slots=True)
class PoseViewSpec:
    view_id: str
    yaw_degrees: int
    path: str
    sha256: str
    width: int
    height: int
    identity_evidence: str
    source_evidence: str
    body_profile_id: str
    rig_id: str | None
    rig_version_range: tuple[int, int] | None
    correction_layers: frozenset[str]


@dataclass(frozen=True, slots=True)
class PoseAtlasManifest:
    pack_id: str
    source_evidence: str
    views: tuple[PoseViewSpec, ...]
    contract: RigContract
    schema_version: int
    body_profile_id: str
    body_profile_version_range: tuple[int, int]
    rig_id: str | None
    rig_version_range: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class DecodedRgba:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True, slots=True)
class PoseRuntimeAtlas:
    pack_id: str
    source_evidence: str
    audit_evidence: str
    views: tuple[tuple[int, DecodedRgba], ...]
    contract: RigContract
    body_profile_id: str
    rig_id: str | None

    @property
    def complete_360(self) -> bool:
        return bool(
            self.contract == "full-body-v4"
            and self.rig_id == FULL_BODY_RIG_ID
            and tuple(yaw for yaw, _image in self.views) == CANONICAL_YAWS
        )

    @property
    def full_body(self) -> bool:
        return self.complete_360

    @property
    def legacy_fallback(self) -> bool:
        return self.contract == "legacy-v3"


@dataclass(frozen=True, slots=True)
class AtlasApproval:
    passed: bool
    evidence: str
    problems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PoseLoadResult:
    status: LoadStatus
    active_atlas: PoseRuntimeAtlas
    problems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PoseRuntimeLimits:
    max_asset_bytes: int = 32 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_width: int = 8192
    max_height: int = 8192


DEFAULT_RUNTIME_LIMITS = PoseRuntimeLimits()


class PoseAssetSource(Protocol):
    def revision(self) -> str: ...

    def read(self, path: str) -> bytes: ...


class PoseAssetDecoder(Protocol):
    def decode(self, data: bytes) -> DecodedRgba: ...


class PoseAtlasAuditor(Protocol):
    def audit(self, atlas: PoseRuntimeAtlas) -> AtlasApproval: ...


class PoseAtlasActivator(Protocol):
    def activate(self, atlas: PoseRuntimeAtlas) -> None: ...


class PoseRuntimeLoader:
    """Predecode and atomically activate one audited canonical atlas."""

    def __init__(
        self,
        fallback_atlas: PoseRuntimeAtlas,
        source: PoseAssetSource,
        decoder: PoseAssetDecoder,
        *services: object,
        limits: PoseRuntimeLimits = DEFAULT_RUNTIME_LIMITS,
    ) -> None:
        if len(services) == 3 and isinstance(services[-1], PoseRuntimeLimits):
            auditor, activator, limits = services
        elif len(services) == 2:
            auditor, activator = services
        else:
            raise TypeError("Pose runtime requires an auditor and activator.")
        if not callable(getattr(auditor, "audit", None)):
            raise TypeError("Pose runtime auditor is invalid.")
        if not callable(getattr(activator, "activate", None)):
            raise TypeError("Pose runtime activator is invalid.")
        self._active = fallback_atlas
        self._source = source
        self._decoder = decoder
        self._auditor = auditor  # type: ignore[assignment]
        self._activator = activator  # type: ignore[assignment]
        self._limits = limits
        self._lock = threading.Lock()
        self._generation = 0
        self._cancelled_generation: int | None = None

    @property
    def active_atlas(self) -> PoseRuntimeAtlas:
        with self._lock:
            return self._active

    def begin_load(self) -> int:
        with self._lock:
            self._generation += 1
            self._cancelled_generation = None
            return self._generation

    def cancel(self, generation: int) -> None:
        with self._lock:
            if generation == self._generation:
                self._cancelled_generation = generation

    def load(
        self,
        generation: int,
        manifest: PoseAtlasManifest,
    ) -> PoseLoadResult:
        blocked = self._load_preflight(generation, manifest)
        if blocked is not None:
            return blocked
        revision = self._source.revision()
        decoded = self._decode_views(generation, manifest)
        if isinstance(decoded, PoseLoadResult):
            return decoded
        if self._source.revision() != revision:
            return self._rejected("source_changed")
        candidate = self._audited_candidate(manifest, decoded)
        if isinstance(candidate, PoseLoadResult):
            return candidate
        state = self._generation_state(generation)
        if state is not None:
            return PoseLoadResult(state, self.active_atlas)
        return self._activate(generation, candidate)

    def _load_preflight(
        self,
        generation: int,
        manifest: PoseAtlasManifest,
    ) -> PoseLoadResult | None:
        state = self._generation_state(generation)
        if state is not None:
            return PoseLoadResult(state, self.active_atlas)
        problems = self._validate_manifest(manifest)
        if problems:
            return PoseLoadResult("rejected", self.active_atlas, problems)
        return None

    def _decode_views(
        self,
        generation: int,
        manifest: PoseAtlasManifest,
    ) -> tuple[tuple[int, DecodedRgba], ...] | PoseLoadResult:
        decoded: list[tuple[int, DecodedRgba]] = []
        total_bytes = 0
        try:
            for view in sorted(manifest.views, key=lambda item: item.yaw_degrees):
                state = self._generation_state(generation)
                if state is not None:
                    return PoseLoadResult(state, self.active_atlas)
                item = self._decode_view(view, total_bytes)
                if isinstance(item, PoseLoadResult):
                    return item
                image, total_bytes = item
                decoded.append((view.yaw_degrees, image))
        except (KeyError, OSError, ValueError):
            return self._rejected("decode_failed")
        return tuple(decoded)

    def _decode_view(
        self,
        view: PoseViewSpec,
        previous_bytes: int,
    ) -> tuple[DecodedRgba, int] | PoseLoadResult:
        data = self._source.read(view.path)
        if len(data) > self._limits.max_asset_bytes:
            return self._rejected("asset_size_limit")
        total_bytes = previous_bytes + len(data)
        if total_bytes > self._limits.max_total_bytes:
            return self._rejected("total_size_limit")
        if hashlib.sha256(data).hexdigest() != view.sha256:
            return self._rejected("hash_mismatch")
        image = self._decoder.decode(data)
        if not self._decoded_matches(view, image):
            return self._rejected("decoded_image_mismatch")
        return image, total_bytes

    def _audited_candidate(
        self,
        manifest: PoseAtlasManifest,
        decoded: tuple[tuple[int, DecodedRgba], ...],
    ) -> PoseRuntimeAtlas | PoseLoadResult:
        candidate = PoseRuntimeAtlas(
            manifest.pack_id,
            manifest.source_evidence,
            "",
            decoded,
            manifest.contract,
            manifest.body_profile_id,
            manifest.rig_id,
        )
        approval = self._auditor.audit(candidate)
        if not approval.passed or not approval.evidence.strip():
            return PoseLoadResult(
                "rejected",
                self.active_atlas,
                approval.problems or ("atlas_audit_failed",),
            )
        return PoseRuntimeAtlas(
            candidate.pack_id,
            candidate.source_evidence,
            approval.evidence,
            candidate.views,
            candidate.contract,
            candidate.body_profile_id,
            candidate.rig_id,
        )

    def _activate(
        self,
        generation: int,
        candidate: PoseRuntimeAtlas,
    ) -> PoseLoadResult:
        previous = self.active_atlas
        try:
            self._activator.activate(candidate)
        except Exception:
            self._activator.activate(previous)
            raise
        with self._lock:
            if (
                generation != self._generation
                or generation == self._cancelled_generation
            ):
                stale = generation != self._generation
            else:
                self._active = candidate
                return PoseLoadResult("activated", candidate)
        self._activator.activate(previous)
        return PoseLoadResult(
            "stale" if stale else "cancelled",
            previous,
        )

    def _generation_state(self, generation: int) -> LoadStatus | None:
        with self._lock:
            if generation == self._cancelled_generation:
                return "cancelled"
            if generation != self._generation:
                return "stale"
        return None

    def _validate_manifest(
        self,
        manifest: PoseAtlasManifest,
    ) -> tuple[str, ...]:
        problems: list[str] = []
        if not manifest.pack_id.strip() or not manifest.source_evidence.strip():
            problems.append("missing_source_evidence")
        expected_yaws = self._validate_contract(manifest, problems)
        counts: dict[int, int] = {}
        for view in manifest.views:
            counts[view.yaw_degrees] = counts.get(view.yaw_degrees, 0) + 1
            self._validate_view(manifest, view, problems)
        self._validate_ring(manifest.contract, counts, expected_yaws, problems)
        return tuple(dict.fromkeys(problems))

    def _validate_contract(
        self,
        manifest: PoseAtlasManifest,
        problems: list[str],
    ) -> tuple[int, ...]:
        if manifest.contract == "full-body-v4":
            self._validate_full_body_contract(manifest, problems)
            return CANONICAL_YAWS
        if manifest.contract == "legacy-v3":
            if manifest.schema_version != 1 or manifest.rig_id is not None:
                problems.append("invalid_legacy_schema")
            return LEGACY_YAWS
        problems.append("unknown_rig_contract")
        return ()

    def _validate_full_body_contract(
        self,
        manifest: PoseAtlasManifest,
        problems: list[str],
    ) -> None:
        checks = (
            (manifest.schema_version == 2, "invalid_full_body_schema"),
            (manifest.body_profile_id == MOHAN_BODY_PROFILE.profile_id, "body_profile_mismatch"),
            (
                self._range_contains(
                    manifest.body_profile_version_range,
                    MOHAN_BODY_PROFILE.version,
                ),
                "body_profile_version",
            ),
            (manifest.rig_id == FULL_BODY_RIG_ID, "full_body_rig_mismatch"),
            (
                self._range_contains(
                    manifest.rig_version_range,
                    FULL_BODY_RIG_SCHEMA_VERSION,
                ),
                "full_body_rig_version",
            ),
        )
        problems.extend(problem for valid, problem in checks if not valid)

    def _validate_view(
        self,
        manifest: PoseAtlasManifest,
        view: PoseViewSpec,
        problems: list[str],
    ) -> None:
        checks = (
            (view.view_id == canonical_view_id(view.yaw_degrees), "noncanonical_view"),
            (self._safe_path(view.path), "unsafe_path"),
            (
                bool(view.identity_evidence.strip() and view.source_evidence.strip()),
                "missing_view_evidence",
            ),
            (view.source_evidence == manifest.source_evidence, "source_evidence_mismatch"),
            (self._valid_hash(view.sha256), "invalid_hash"),
        )
        problems.extend(problem for valid, problem in checks if not valid)
        if manifest.contract == "full-body-v4":
            self._validate_full_body_view(manifest, view, problems)
        elif view.rig_id is not None or view.rig_version_range is not None or view.correction_layers:
            problems.append("legacy_claims_full_body")

    @staticmethod
    def _validate_full_body_view(
        manifest: PoseAtlasManifest,
        view: PoseViewSpec,
        problems: list[str],
    ) -> None:
        if (
            view.body_profile_id != manifest.body_profile_id
            or view.rig_id != manifest.rig_id
            or view.rig_version_range != manifest.rig_version_range
        ):
            problems.append("view_rig_mismatch")
        if not view.correction_layers >= FULL_BODY_CORRECTIONS:
            problems.append("missing_full_body_corrections")

    @staticmethod
    def _validate_ring(
        contract: RigContract,
        counts: dict[int, int],
        expected_yaws: tuple[int, ...],
        problems: list[str],
    ) -> None:
        if set(counts) != set(expected_yaws):
            problems.append(
                "incomplete_canonical_ring"
                if contract == "full-body-v4"
                else "invalid_legacy_views"
            )
        if any(count != 1 for count in counts.values()):
            problems.append("duplicate_view")

    @staticmethod
    def _valid_hash(value: str) -> bool:
        return len(value) == 64 and all(
            character in "0123456789abcdef" for character in value
        )

    @staticmethod
    def _range_contains(value: tuple[int, int] | None, version: int) -> bool:
        return bool(
            value is not None
            and len(value) == 2
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
            and value[0] <= version < value[1]
        )

    def _decoded_matches(
        self,
        view: PoseViewSpec,
        image: DecodedRgba,
    ) -> bool:
        return bool(
            0 < image.width <= self._limits.max_width
            and 0 < image.height <= self._limits.max_height
            and image.width == view.width
            and image.height == view.height
            and len(image.rgba) == image.width * image.height * 4
        )

    def _rejected(self, problem: str) -> PoseLoadResult:
        return PoseLoadResult("rejected", self.active_atlas, (problem,))

    @staticmethod
    def _safe_path(path: str) -> bool:
        value = PurePosixPath(path)
        return bool(
            path
            and not value.is_absolute()
            and ".." not in value.parts
            and "\\" not in path
            and value.suffix.lower() in {".png", ".webp", ".rgba"}
        )
