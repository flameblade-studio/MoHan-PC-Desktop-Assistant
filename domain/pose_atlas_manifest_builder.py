from __future__ import annotations

lazy import hashlib
lazy import json
lazy import struct
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.full_body_asset_evidence import (
    FullBodyAssetEvidenceResult,
    FullBodyAssetManifestView,
    build_full_body_asset_evidence,
)
lazy from domain.hand_asset_evidence import (
    HandAssetEvidenceResult,
    HandAssetManifestEvidence,
    build_hand_asset_evidence,
)
lazy from domain.pose_atlas_release_gate import PoseReleaseViewInput
lazy from domain.pose_runtime_loader import PoseAtlasManifest, PoseViewSpec

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_PNG_HEADER_LENGTH = 33
PNG_BIT_DEPTH = 8
PNG_COLOR_TYPE_RGBA = 6
REQUIRED_CORRECTIONS = frozenset(
    {
        "left-leg-correction",
        "right-leg-correction",
        "left-foot-correction",
        "right-foot-correction",
        "left-sole-correction",
        "right-sole-correction",
    }
)


@dataclass(frozen=True, slots=True)
class PoseAtlasBuildConfig:
    pack_id: str
    source_evidence: str
    identity_evidence: str
    body_profile_id: str = MOHAN_BODY_PROFILE.profile_id
    body_profile_version_range: tuple[int, int] = (MOHAN_BODY_PROFILE.version, MOHAN_BODY_PROFILE.version + 1)
    rig_id: str = "mohan-full-body-v1"
    rig_version_range: tuple[int, int] = (1, 2)


@dataclass(frozen=True, slots=True)
class PoseAtlasAssetRecord:
    view_id: str
    yaw_degrees: int
    rgba_path: str
    sidecar_path: str
    hands_path: str
    width: int
    height: int
    rgba_sha256: str
    sidecar_sha256: str
    hands_sha256: str


@dataclass(frozen=True, slots=True)
class PoseAtlasBuildIssue:
    code: str
    view_id: str | None = None


@dataclass(frozen=True, slots=True)
class _ViewFiles:
    png_path: Path
    body_path: Path
    hands_path: Path
    png: bytes
    body: bytes
    hands: bytes
    width: int
    height: int
    relative_png: str
    relative_body: str
    relative_hands: str


@dataclass(frozen=True, slots=True)
class PoseAtlasManifestBuildResult:
    manifest: PoseAtlasManifest | None
    records: tuple[PoseAtlasAssetRecord, ...]
    asset_evidence: tuple[tuple[str, FullBodyAssetEvidenceResult], ...]
    hand_evidence: tuple[tuple[str, HandAssetEvidenceResult], ...]
    issues: tuple[PoseAtlasBuildIssue, ...]

    @property
    def passed(self) -> bool:
        return self.manifest is not None and not self.issues

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_version": 1,
            "status": "complete" if self.passed else "blocked",
            "records": [
                {
                    "view_id": record.view_id,
                    "yaw_degrees": record.yaw_degrees,
                    "rgba_path": record.rgba_path,
                    "sidecar_path": record.sidecar_path,
                    "hands_path": record.hands_path,
                    "width": record.width,
                    "height": record.height,
                    "rgba_sha256": record.rgba_sha256,
                    "sidecar_sha256": record.sidecar_sha256,
                    "hands_sha256": record.hands_sha256,
                }
                for record in self.records
            ],
            "issues": [
                {"code": issue.code, "view_id": issue.view_id}
                for issue in self.issues
            ],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def release_views(self) -> tuple[PoseReleaseViewInput, ...]:
        if not self.passed:
            return ()
        evidence = dict(self.asset_evidence)
        hands = dict(self.hand_evidence)
        expected = {record.view_id for record in self.records}
        if set(hands) != expected or set(evidence) != expected:
            return ()
        if any(not hands[view_id].passed for view_id in expected):
            return ()
        visible_sides = frozenset(
            side
            for item in hands.values()
            for side in item.visible_sides
        )
        if visible_sides != frozenset({"left", "right"}):
            return ()
        return tuple(
            PoseReleaseViewInput(
                record.view_id,
                record.yaw_degrees,
                record.rgba_sha256,
                record.sidecar_sha256,
                record.hands_sha256,
                evidence[record.view_id],
                hands[record.view_id],
            )
            for record in self.records
        )


def build_pose_atlas_manifest(
    asset_root: Path,
    config: PoseAtlasBuildConfig,
) -> PoseAtlasManifestBuildResult:
    """Build a deterministic v4 manifest from 24 real PNG/sidecar pairs."""

    root = asset_root.resolve()
    issues = _validate_config(config)
    records: list[PoseAtlasAssetRecord] = []
    evidence: list[tuple[str, FullBodyAssetEvidenceResult]] = []
    hands: list[tuple[str, HandAssetEvidenceResult]] = []
    specs: list[PoseViewSpec] = []
    for yaw in CANONICAL_YAWS:
        built, issue = _build_view(root, yaw, config)
        if issue is not None:
            issues.append(issue)
            continue
        if built is None:
            issues.append(PoseAtlasBuildIssue("asset_pair_invalid", canonical_view_id(yaw)))
            continue
        record, asset_evidence, hand_evidence, spec = built
        records.append(record)
        evidence.append((record.view_id, asset_evidence))
        hands.append((record.view_id, hand_evidence))
        specs.append(spec)
    if len(records) != len(CANONICAL_YAWS):
        issues.append(PoseAtlasBuildIssue("canonical_ring_incomplete"))
    unique_issues = tuple(dict.fromkeys(issues))
    if unique_issues:
        return PoseAtlasManifestBuildResult(None, (), (), (), unique_issues)
    manifest = PoseAtlasManifest(
        config.pack_id,
        config.source_evidence,
        tuple(specs),
        "full-body-v4",
        2,
        config.body_profile_id,
        config.body_profile_version_range,
        config.rig_id,
        config.rig_version_range,
    )
    return PoseAtlasManifestBuildResult(
        manifest,
        tuple(records),
        tuple(evidence),
        tuple(hands),
        (),
    )


def _build_view(
    root: Path,
    yaw: int,
    config: PoseAtlasBuildConfig,
) -> tuple[
    tuple[
        PoseAtlasAssetRecord,
        FullBodyAssetEvidenceResult,
        HandAssetEvidenceResult,
        PoseViewSpec,
    ] | None,
    PoseAtlasBuildIssue | None,
]:
    view_id = canonical_view_id(yaw)
    try:
        files = _view_files(root, view_id, yaw)
    except _BuildFailure as error:
        return None, PoseAtlasBuildIssue(error.code, view_id)
    asset_evidence = build_full_body_asset_evidence(
        files.png_path,
        files.body_path,
        FullBodyAssetManifestView(view_id, yaw, files.width, files.height),
    )
    if not asset_evidence.passed:
        return None, PoseAtlasBuildIssue("full_body_evidence_failed", view_id)
    rgba_sha256 = hashlib.sha256(files.png).hexdigest()
    sidecar_sha256 = hashlib.sha256(files.body).hexdigest()
    hands_sha256 = hashlib.sha256(files.hands).hexdigest()
    hand_evidence = build_hand_asset_evidence(
        root,
        HandAssetManifestEvidence(
            view_id,
            yaw,
            files.relative_png,
            files.relative_hands,
            files.width,
            files.height,
            rgba_sha256,
            hands_sha256,
        ),
    )
    if not hand_evidence.passed:
        return None, PoseAtlasBuildIssue("hand_evidence_failed", view_id)
    record = PoseAtlasAssetRecord(
        view_id,
        yaw,
        files.relative_png,
        files.relative_body,
        files.relative_hands,
        files.width,
        files.height,
        rgba_sha256,
        sidecar_sha256,
        hands_sha256,
    )
    spec = PoseViewSpec(
        view_id,
        yaw,
        files.relative_png,
        rgba_sha256,
        files.width,
        files.height,
        config.identity_evidence,
        config.source_evidence,
        config.body_profile_id,
        config.rig_id,
        config.rig_version_range,
        REQUIRED_CORRECTIONS,
    )
    return (record, asset_evidence, hand_evidence, spec), None


class _BuildFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _view_files(root: Path, view_id: str, yaw: int) -> _ViewFiles:
    paths = (
        root / f"{view_id}.png",
        root / f"{view_id}.landmarks.json",
        root / f"{view_id}.hands.json",
    )
    for path, code in zip(
        paths,
        ("rgba_missing", "sidecar_missing", "hands_sidecar_missing"),
        strict=True,
    ):
        if not path.is_file():
            raise _BuildFailure(code)
    try:
        png, body, hands = (path.read_bytes() for path in paths)
        width, height = _png_dimensions(png)
        _validate_sidecar(body, view_id, yaw)
        relative = tuple(_relative_posix(path, root) for path in paths)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise _BuildFailure("asset_pair_invalid") from error
    return _ViewFiles(*paths, png, body, hands, width, height, *relative)


def _validate_config(config: PoseAtlasBuildConfig) -> list[PoseAtlasBuildIssue]:
    issues = []
    if not config.pack_id.strip():
        issues.append(PoseAtlasBuildIssue("pack_id_missing"))
    if not config.source_evidence.strip():
        issues.append(PoseAtlasBuildIssue("source_evidence_missing"))
    if not config.identity_evidence.strip():
        issues.append(PoseAtlasBuildIssue("identity_evidence_missing"))
    return issues


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if (
        len(data) < MIN_PNG_HEADER_LENGTH
        or data[:8] != PNG_SIGNATURE
        or data[12:16] != b"IHDR"
    ):
        raise ValueError("invalid_png")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", data[16:29]
    )
    if (
        width <= 0
        or height <= 0
        or depth != PNG_BIT_DEPTH
        or color != PNG_COLOR_TYPE_RGBA
        or compression
        or filtering
        or interlace
    ):
        raise ValueError("invalid_rgba_png")
    return width, height


def _validate_sidecar(data: bytes, view_id: str, yaw: int) -> None:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("invalid_sidecar")
    if (
        payload.get("schema_version") not in {1, 2}
        or payload.get("view_id") != view_id
        or payload.get("yaw_degrees") != yaw
        or not isinstance(payload.get("landmarks"), dict)
    ):
        raise ValueError("sidecar_identity_mismatch")


def _relative_posix(path: Path, root: Path) -> str:
    relative = path.resolve().relative_to(root)
    value = PurePosixPath(*relative.parts).as_posix()
    if not value or value.startswith("/") or ".." in PurePosixPath(value).parts:
        raise ValueError("unsafe_relative_path")
    return value
