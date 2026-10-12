"""Pure manifest contracts for mohan.body-pack.v1."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import unicodedata
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from typing import Protocol


SCHEMA = "mohan.body-pack.v1"
MAX_VERSION_LENGTH = 128
MAX_LICENSE_LENGTH = 512
MAX_PATH_LENGTH = 512
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FILE_FIELDS = frozenset({"path", "sha256"})
REFERENCE_FIELDS = frozenset({"id", "version", "fingerprint"})
MANIFEST_FIELDS = frozenset({
    "schema", "id", "version", "license", "full_body", "half_body", "fingerprint",
})
OPTIONAL_MANIFEST_FIELDS = frozenset({"face_core_masks", "missing_body_poses"})


class BodyPackError(ValueError):
    """A body-pack manifest violates its domain contract."""


class BodyPackMismatchError(BodyPackError):
    """A declared fingerprint or an expected body-pack reference differs."""

    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.path = path


@dataclass(frozen=True, slots=True)
class BodyPackFile:
    """One hash-bound image file referenced by the body pack."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class BodyPackView:
    """Frame files belonging to one view, in manifest declaration order."""

    view_id: str
    frames: tuple[tuple[str, BodyPackFile], ...]


@dataclass(frozen=True, slots=True)
class BodyPackReference:
    """Stable body-pack identity expected by a consumer."""

    id: str
    version: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class BodyPackManifest:
    """Validated body-pack metadata and immutable view/frame mappings."""

    schema: str
    id: str
    version: str
    license: str
    full_body: tuple[BodyPackView, ...]
    half_body: tuple[BodyPackView, ...]
    face_core_masks: tuple[tuple[str, BodyPackFile], ...]
    fingerprint: str
    missing_body_poses: tuple[str, ...] = ()


class BodyPackSource(Protocol):
    """Read-only frame source required by body-pack renderers."""

    @property
    def manifest(self) -> BodyPackManifest: ...

    def frame_keys(self, view: str, *, halfbody: bool = False) -> tuple[str, ...]: ...

    def load_frame(self, view: str, key: str, *, halfbody: bool = False) -> bytes: ...

    def load_face_core(self, view: str) -> bytes | None: ...


def parse_body_pack_reference(value: object) -> BodyPackReference:
    """Validate and parse an id/version/fingerprint reference."""
    if isinstance(value, BodyPackReference):
        _identifier(value.id, "reference.id")
        _text(value.version, "reference.version", MAX_VERSION_LENGTH)
        _sha256(value.fingerprint, "reference.fingerprint")
        return value
    reference = _exact_mapping(value, REFERENCE_FIELDS, frozenset(), "reference")
    return BodyPackReference(
        _identifier(reference["id"], "reference.id"),
        _text(reference["version"], "reference.version", MAX_VERSION_LENGTH),
        _sha256(reference["fingerprint"], "reference.fingerprint"),
    )


def parse_body_pack(
    value: object,
    reference: BodyPackReference | Mapping[str, object] | None = None,
) -> BodyPackManifest:
    """Parse a body-pack manifest and verify its logical fingerprint.

    full_body and half_body map view IDs to either one file (treated as the
    rest frame) or nested frame-state mappings. Nested state keys are joined
    with slash characters, so pose/family/eye entries remain distinguishable.
    """
    manifest = _exact_mapping(
        value,
        MANIFEST_FIELDS,
        OPTIONAL_MANIFEST_FIELDS,
        "body pack",
    )
    if manifest["schema"] != SCHEMA:
        raise BodyPackError(f"Only {SCHEMA} is supported.")

    pack_id = _identifier(manifest["id"], "id")
    version = _text(manifest["version"], "version", MAX_VERSION_LENGTH)
    license_name = _text(manifest["license"], "license", MAX_LICENSE_LENGTH)
    full_body = _parse_views(manifest["full_body"], "full_body")
    half_body = _parse_views(manifest["half_body"], "half_body")
    masks = _parse_face_core_masks(manifest.get("face_core_masks", {}))
    missing = _mapping(manifest.get("missing_body_poses", {}), "missing_body_poses")
    missing_ids = []
    available_ids = {view.view_id for view in half_body}
    for pose, entry in missing.items():
        pose_id = _key(pose, "missing_body_poses pose")
        metadata = _exact_mapping(entry, frozenset({"status"}), frozenset(), "missing body pose")
        if metadata["status"] != "missing_body_pose" or pose_id in available_ids:
            raise BodyPackError("Missing body poses require missing_body_pose status and no half-body frames.")
        missing_ids.append(pose_id)
    declared_fingerprint = _sha256(manifest["fingerprint"], "fingerprint")

    parsed = BodyPackManifest(
        schema=SCHEMA,
        id=pack_id,
        version=version,
        license=license_name,
        full_body=full_body,
        half_body=half_body,
        face_core_masks=masks,
        fingerprint=declared_fingerprint,
        missing_body_poses=tuple(sorted(missing_ids)),
    )
    actual_fingerprint = compute_body_pack_fingerprint(parsed)
    if declared_fingerprint != actual_fingerprint:
        raise BodyPackMismatchError(
            "fingerprint_mismatch",
            "The declared body-pack fingerprint does not match its distinct file hashes.",
        )

    if reference is not None:
        expected = parse_body_pack_reference(reference)
        if expected.id != parsed.id:
            raise BodyPackMismatchError(
                "id_mismatch",
                "The body pack ID does not match the expected reference.",
            )
        if expected.version != parsed.version:
            raise BodyPackMismatchError(
                "version_mismatch",
                "The body-pack version does not match the expected reference.",
            )
        if expected.fingerprint != parsed.fingerprint:
            raise BodyPackMismatchError(
                "fingerprint_mismatch",
                "The body-pack fingerprint does not match the expected reference.",
            )
    return parsed


def compute_body_pack_fingerprint(
    value: BodyPackManifest | Mapping[str, object],
) -> str:
    """Hash normalized frame-to-file bindings in a stable order.

    Each record contains its section, view, state, path and file SHA-256.
    Text fields use Unicode NFC. Sorted records are encoded as compact JSON
    arrays in UTF-8 before hashing.
    Repeated paths may bind to multiple frames, while one path cannot declare
    conflicting digests.
    """
    if isinstance(value, BodyPackManifest):
        full_body, half_body, masks = (
            value.full_body,
            value.half_body,
            value.face_core_masks,
        )
    elif isinstance(value, Mapping):
        full_body = _parse_views(value.get("full_body"), "full_body")
        half_body = _parse_views(value.get("half_body"), "half_body")
        masks = _parse_face_core_masks(value.get("face_core_masks", {}))
    else:
        raise BodyPackError("Provide a parsed body-pack manifest or mapping.")

    # Validate path collisions and conflicting hashes before hashing bindings.
    _files_from_parsed(full_body, half_body, masks)
    records: list[tuple[str, str, str, str, str]] = []

    def add(
        section: str,
        view_id: str,
        state: str,
        file: BodyPackFile,
    ) -> None:
        records.append(
            (
                section,
                _fingerprint_text(view_id),
                _fingerprint_text(state),
                _fingerprint_text(_safe_path(file.path)),
                _sha256(file.sha256, f"{file.path}.sha256"),
            )
        )

    for view in full_body:
        for state, file in view.frames:
            add("full_body", view.view_id, state, file)
    for view in half_body:
        for state, file in view.frames:
            add("half_body", view.view_id, state, file)
    for view_id, file in masks:
        add("face_core_masks", view_id, "mask", file)

    payload_bytes = json.dumps(
        sorted(records), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()


def _fingerprint_text(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _parse_views(value: object, label: str) -> tuple[BodyPackView, ...]:
    views = _mapping(value, label)
    if not views:
        raise BodyPackError(f"{label} must contain at least one view.")

    parsed: list[BodyPackView] = []
    seen_view_ids: set[str] = set()
    for raw_view_id, frame_spec in views.items():
        view_id = _key(raw_view_id, f"{label} view")
        folded_view_id = view_id.casefold()
        if folded_view_id in seen_view_ids:
            raise BodyPackError(f"{label} view IDs must be unique ignoring case.")
        seen_view_ids.add(folded_view_id)

        frames: list[tuple[str, BodyPackFile]] = []
        if _is_file_mapping(frame_spec):
            frames.append(("rest", _parse_file(frame_spec)))
        else:
            _collect_frames(frame_spec, (), frames, f"{label}.{view_id}")
        if not frames:
            raise BodyPackError(f"{label}.{view_id} must contain a frame.")
        frame_ids = [frame_id for frame_id, _ in frames]
        if len(frame_ids) != len(set(frame_ids)):
            raise BodyPackError(f"{label}.{view_id} has duplicate frame keys.")
        parsed.append(BodyPackView(view_id=view_id, frames=tuple(frames)))
    return tuple(parsed)


def _collect_frames(
    value: object,
    state_path: tuple[str, ...],
    output: list[tuple[str, BodyPackFile]],
    label: str,
) -> None:
    if _is_file_mapping(value):
        frame_id = "/".join(state_path) if state_path else "rest"
        output.append((frame_id, _parse_file(value)))
        return
    states = _mapping(value, label)
    if not states:
        raise BodyPackError(f"{label} must contain a frame or frame-state mapping.")
    for raw_state, child in states.items():
        state = _key(raw_state, f"{label} frame state")
        _collect_frames(child, (*state_path, state), output, f"{label}.{state}")


def _parse_face_core_masks(value: object) -> tuple[tuple[str, BodyPackFile], ...]:
    masks = _mapping(value, "face_core_masks")
    parsed: list[tuple[str, BodyPackFile]] = []
    seen_view_ids: set[str] = set()
    for raw_view_id, file_value in masks.items():
        view_id = _key(raw_view_id, "face_core_masks view")
        if view_id.casefold() in seen_view_ids:
            raise BodyPackError("face_core_masks view IDs must be unique ignoring case.")
        seen_view_ids.add(view_id.casefold())
        if not _is_file_mapping(file_value):
            raise BodyPackError(
                f"face_core_masks.{view_id} must reference one path and SHA-256."
            )
        parsed.append((view_id, _parse_file(file_value)))
    return tuple(parsed)


def _files_from_parsed(
    full_body: tuple[BodyPackView, ...],
    half_body: tuple[BodyPackView, ...],
    masks: tuple[tuple[str, BodyPackFile], ...],
) -> dict[str, str]:
    files: dict[str, str] = {}
    folded_paths: dict[str, str] = {}

    def add(file: BodyPackFile) -> None:
        path = _safe_path(file.path)
        digest = _sha256(file.sha256, f"{path}.sha256")
        folded = path.casefold()
        prior_case_path = folded_paths.get(folded)
        if prior_case_path is not None and prior_case_path != path:
            raise BodyPackError("Body-pack paths must not collide ignoring case.")
        folded_paths[folded] = path
        prior_digest = files.get(path)
        if prior_digest is not None and prior_digest != digest:
            raise BodyPackError(f"Body-pack path {path!r} has conflicting SHA-256 values.")
        files[path] = digest

    for view in (*full_body, *half_body):
        for _, file in view.frames:
            add(file)
    for _, file in masks:
        add(file)
    if not files:
        raise BodyPackError("A body pack must reference at least one file.")
    return files


def _parse_file(value: object) -> BodyPackFile:
    file_value = _exact_mapping(value, FILE_FIELDS, frozenset(), "file")
    return BodyPackFile(
        path=_safe_path(file_value["path"]),
        sha256=_sha256(file_value["sha256"], "file.sha256"),
    )


def _is_file_mapping(value: object) -> bool:
    return isinstance(value, Mapping) and (
        "path" in value or "sha256" in value
    )


def _safe_path(value: object) -> str:
    if not isinstance(value, str):
        raise BodyPackError("A file path must be text.")
    if (
        not value
        or len(value) > MAX_PATH_LENGTH
        or value != value.strip()
        or unicodedata.normalize("NFC", value) != value
        or value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or ":" in value
        or any(unicodedata.category(char) == "Cc" for char in value)
        or any(char in '<>:"|?*' for char in value)
    ):
        raise BodyPackError("File paths must be safe relative POSIX paths.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise BodyPackError("File paths must not contain empty, dot, or parent segments.")
    if any(part.endswith((" ", ".")) for part in parts):
        raise BodyPackError("File path segments must not end in spaces or dots.")
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"COM{index}" for index in range(1, 10))
    reserved.update(f"LPT{index}" for index in range(1, 10))
    if any(part.split(".", 1)[0].upper() in reserved for part in parts):
        raise BodyPackError("File paths must avoid reserved Windows device names.")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise BodyPackError(f"{label} must be a lowercase 64-character SHA-256 digest.")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise BodyPackError(f"{label} must be a portable lowercase identifier.")
    return value


def _text(value: object, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(unicodedata.category(char) == "Cc" for char in value)
    ):
        raise BodyPackError(f"{label} must be bounded, non-empty text without controls.")
    return value


def _key(value: object, label: str) -> str:
    if not isinstance(value, str) or not KEY.fullmatch(value):
        raise BodyPackError(f"{label} must be a portable non-empty key.")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise BodyPackError(f"{label} must be a string-keyed mapping.")
    return value


def _exact_mapping(
    value: object,
    required: frozenset[str],
    optional: frozenset[str],
    label: str,
) -> Mapping[str, object]:
    mapping = _mapping(value, label)
    keys = set(mapping)
    if not required <= keys or keys - required - optional:
        raise BodyPackError(f"{label} has missing or unsupported fields.")
    return mapping
