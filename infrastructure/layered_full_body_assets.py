"""Load and validate the 24-view × 25-layer full-body parametric assets.

Each PoseAtlas generation ships 600 transparent PNG layers (24 yaw views × 25
layers) under ``assets/pose-atlas/<generation>-layered/`` (the current root is
``domain.constants.POSE_ATLAS_LAYERED_ROOT_NAME``). This module loads them into an immutable,
Qt-independent manifest so the full-body renderer can compose a continuously
controlled full-body portrait and replace the legacy PoseAtlas static photo +
procedural mouth.

Back-facing views may omit invisible facial-feature layers. Front and side
views must retain all 25 layer files, including transparent placeholders for
individual features hidden by the viewing angle.
"""

from __future__ import annotations

lazy from collections.abc import Mapping
lazy import hashlib
lazy import struct
lazy import json
lazy import zlib
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath, PureWindowsPath

lazy import cv2
lazy import numpy as np

lazy from domain.constants import FULL_BODY_LAYER_Z_ORDER
lazy from domain.face_rig import EyeState, Viseme

FULL_BODY_DIMENSION_WIDTH = 1024
FULL_BODY_DIMENSION_HEIGHT = 1536
PNG_HEADER_LENGTH = 33
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
COLOR_IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4
SHA256_HEX_LENGTH = 64
SIDE_VIEW_YAW_LIMIT = 90
COMPLETE_EXPRESSION_MANIFEST_NAME = "complete_expression_manifest.json"
COMPLETE_EXPRESSION_SCHEMA = "mohan.complete-expression-manifest.v1"
COMPLETE_EXPRESSION_VERSION = 1
COMPLETE_EXPRESSION_MOTION_POLICY = "neutral_body_only"
COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY = "preserve_body_layers"
COMPLETE_EXPRESSION_MOTION_POLICIES = frozenset(
    {COMPLETE_EXPRESSION_MOTION_POLICY, COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY}
)

# The 24 authored yaw views, in canonical ascending order.
VIEW_IDS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)

# Layers that must be present on every view (body + clothing). Facial-feature
# layers may be absent on back-facing views.
REQUIRED_LAYERS = frozenset(
    {
        "body",
        "hair_back",
        "hair_left",
        "hair_right",
        "sleeve_left",
        "sleeve_right",
        "ornament",
    }
)

COMPLETE_EXPRESSION_STATES = (EyeState.REST, EyeState.HALF, EyeState.CLOSED)
SPOKEN_VISEMES = tuple(
    viseme for viseme in Viseme if viseme is not Viseme.CLOSED
)


@dataclass(frozen=True, slots=True)
class CompleteExpressionFrameSet:
    """One source-bound full-body expression group across three eye states.

    A complete frame is an atomic full-body snapshot.  Version 1 therefore
    supports either a neutral-body atomic route or a source-bound replacement
    region that preserves the current body's pose, hands, and sleeves.
    """

    source_group_id: str
    source_lineage: str
    frames: frozendict[Viseme, frozendict[EyeState, Path]]
    oral_masks: frozendict[Viseme, frozendict[EyeState, Path]] = frozendict()
    neutral_frames: frozendict[EyeState, Path] = frozendict()
    motion_policy: str = COMPLETE_EXPRESSION_MOTION_POLICY
    replacement_mask: Path | None = None

    def frame(self, viseme: Viseme, eye_state: EyeState) -> Path:
        return self.frames[viseme][eye_state]

    def oral_mask(self, viseme: Viseme, eye_state: EyeState) -> Path | None:
        if not self.oral_masks:
            return None
        return self.oral_masks[viseme][eye_state]


@dataclass(frozen=True, slots=True)
class LayeredFullBodyView:
    """One view's complete set of 25 transparent layers."""

    view_id: str
    layers: frozendict[str, Path]
    mouth_center_x: float | None = None
    blink_frames: frozendict[EyeState, Path] = frozendict()
    speech_frames: frozendict[Viseme, Path] = frozendict()
    speech_oral_masks: frozendict[Viseme, Path] = frozendict()
    complete_expression_frames: CompleteExpressionFrameSet | None = None

    def path(self, layer: str) -> Path | None:
        return self.layers.get(layer)


@dataclass(frozen=True, slots=True)
class LayeredFullBodyManifest:
    """The complete 24-view full-body layered asset set."""

    views: frozendict[str, LayeredFullBodyView]

    def view(self, view_id: str) -> LayeredFullBodyView:
        return self.views[view_id]


def _png_dimensions(path: Path, *, rgba_layer: bool = False) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(PNG_HEADER_LENGTH)
        if len(header) != PNG_HEADER_LENGTH or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"invalid full-body PNG: {path.name}")
        source.seek(-len(PNG_IEND), 2)
        ending = source.read()
    if (
        header[8:16] != b"\x00\x00\x00\x0dIHDR"
        or zlib.crc32(header[12:29]) != int.from_bytes(header[29:33], "big")
        or ending != PNG_IEND
    ):
        raise ValueError(f"invalid full-body PNG structure: {path.name}")
    if rgba_layer and header[24:26] != b"\x08\x06":
        raise ValueError(f"full-body layer must be 8-bit RGBA: {path.name}")
    return struct.unpack(">II", header[16:24])


def load_layered_full_body_assets(root: Path) -> LayeredFullBodyManifest:
    """Load and validate all 600 full-body layers, failing closed on gaps."""

    authority_centers = _load_authority_mouth_centers(root)
    complete_expressions = _load_complete_expression_manifest(root)
    views: dict[str, LayeredFullBodyView] = {}
    for view_id in VIEW_IDS:
        required_layers = (
            FULL_BODY_LAYER_Z_ORDER
            if abs(int(view_id[3:7])) <= SIDE_VIEW_YAW_LIMIT
            else REQUIRED_LAYERS
        )
        layers: dict[str, Path] = {}
        for layer in FULL_BODY_LAYER_Z_ORDER:
            path = root / f"{view_id}_{layer}.png"
            if not path.is_file():
                if layer in required_layers:
                    raise FileNotFoundError(
                        f"missing full-body asset: {view_id}_{layer}.png"
                    )
                continue
            if _png_dimensions(path, rgba_layer=True) != (
                FULL_BODY_DIMENSION_WIDTH,
                FULL_BODY_DIMENSION_HEIGHT,
            ):
                raise ValueError(
                    f"unexpected full-body dimensions: {view_id}_{layer}.png"
                )
            layers[layer] = path
        views[view_id] = LayeredFullBodyView(
            view_id,
            frozendict(layers),
            authority_centers.get(view_id),
            _load_blink_frames(root, view_id),
            _load_speech_frames(root, view_id),
            _load_speech_frames(root, view_id, oral_masks=True),
            complete_expressions.get(view_id),
        )
    return LayeredFullBodyManifest(frozendict(views))


def _load_blink_frames(root: Path, view_id: str) -> frozendict[EyeState, Path]:
    """Optional authored eyelids must form a complete, same-canvas pair."""
    frames = {
        state: root / f"{view_id}_blink_{state.value}.png"
        for state in (EyeState.HALF, EyeState.CLOSED)
    }
    if not any(path.exists() for path in frames.values()):
        return frozendict()
    for path in frames.values():
        if not path.is_file():
            raise FileNotFoundError(f"incomplete full-body blink pair: {path.name}")
        if _png_dimensions(path) != (FULL_BODY_DIMENSION_WIDTH, FULL_BODY_DIMENSION_HEIGHT):
            raise ValueError(f"unexpected full-body blink dimensions: {path.name}")
        _validate_blink_transparency(path)
    return frozendict(frames)


def _validate_blink_transparency(path: Path) -> None:
    """Validate full-canvas RGB replacements before composition so the character remains covered by its authority."""
    pixels = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if (
        pixels is None
        or pixels.dtype != np.uint8
        or pixels.ndim != COLOR_IMAGE_DIMENSIONS
        or pixels.shape[2] != RGBA_CHANNELS
        or not np.any(pixels[:, :, 3] == 0)
    ):
        raise ValueError(f"full-body blink must be an 8-bit transparent RGBA overlay: {path.name}")


def _load_speech_frames(
    root: Path, view_id: str, *, oral_masks: bool = False,
) -> frozendict[Viseme, Path]:
    """Optional native speech assets must cover every spoken viseme."""
    suffix = "_oral" if oral_masks else ""
    frames = {
        viseme: root / f"{view_id}_speech_{viseme.value}{suffix}.png"
        for viseme in Viseme if viseme is not Viseme.CLOSED
    }
    if not any(path.exists() for path in frames.values()):
        return frozendict()
    for path in frames.values():
        if not path.is_file():
            raise FileNotFoundError(f"incomplete full-body speech set: {path.name}")
        if _png_dimensions(path, rgba_layer=True) != (
            FULL_BODY_DIMENSION_WIDTH, FULL_BODY_DIMENSION_HEIGHT,
        ):
            raise ValueError(f"unexpected full-body speech dimensions: {path.name}")
    return frozendict(frames)


def snapshot_speech_frames(view: LayeredFullBodyView) -> frozendict[str, bytes]:
    """Freeze registered mouth pixels and validate them before the frame loop."""
    if view.speech_oral_masks and set(view.speech_oral_masks) != set(view.speech_frames):
        raise ValueError("Native oral masks must match the authored speech visemes")
    if not view.speech_frames:
        return frozendict()
    body_path = view.path("body")
    if body_path is None:
        raise ValueError("Native speech requires a body canvas")
    canvas = _png_dimensions(body_path)
    snapshots: dict[str, bytes] = {}
    for viseme, path in (*view.speech_frames.items(), *view.speech_oral_masks.items()):
        if viseme not in Viseme or viseme == Viseme.CLOSED:
            raise ValueError("Native speech requires a spoken viseme")
        data = path.read_bytes()
        pixels = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if (pixels is None or pixels.dtype != np.uint8
                or pixels.ndim != COLOR_IMAGE_DIMENSIONS or pixels.shape[2] != RGBA_CHANNELS
                or (pixels.shape[1], pixels.shape[0]) != canvas
                or not np.any(pixels[:, :, 3] == 0)
                or not np.any(pixels[:, :, 3] > 0)):
            raise ValueError(f"Native speech requires a nonempty same-canvas transparent RGBA overlay: {path.name}")
        snapshots[str(path)] = data
    return frozendict(snapshots)


def _load_complete_expression_manifest(
    root: Path,
) -> frozendict[str, CompleteExpressionFrameSet]:
    """Load an optional, versioned full-body expression sidecar."""

    path = root / COMPLETE_EXPRESSION_MANIFEST_NAME
    if not path.is_file():
        return frozendict()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid complete expression manifest: {path.name}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != COMPLETE_EXPRESSION_SCHEMA
        or isinstance(payload.get("version"), bool)
        or not isinstance(payload.get("version"), int)
        or payload.get("version") != COMPLETE_EXPRESSION_VERSION
        or not isinstance(payload.get("views"), dict)
    ):
        raise ValueError("Provide a supported complete expression manifest schema/version")
    result: dict[str, CompleteExpressionFrameSet] = {}
    for view_id, record in payload["views"].items():
        if view_id not in VIEW_IDS:
            raise ValueError(f"Unknown complete expression view: {view_id}")
        result[view_id] = _parse_complete_expression_view(root, view_id, record)
    return frozendict(result)


def _parse_complete_expression_view(
    root: Path,
    view_id: str,
    record: object,
) -> CompleteExpressionFrameSet:
    if not isinstance(record, dict):
        raise ValueError(f"Invalid complete expression view: {view_id}")
    source_group_id = record.get("source_group_id")
    if not isinstance(source_group_id, str) or not source_group_id.strip():
        raise ValueError(f"Complete expression requires source_group_id: {view_id}")
    source_lineage = _source_lineage_token(record.get("source_lineage"), view_id)
    motion_policy = record.get("motion_policy", COMPLETE_EXPRESSION_MOTION_POLICY)
    if (
        not isinstance(motion_policy, str)
        or motion_policy not in COMPLETE_EXPRESSION_MOTION_POLICIES
    ):
        raise ValueError(
            "Complete expression motion_policy must be neutral_body_only or "
            "preserve_body_layers: "
            f"{view_id}"
        )
    frames = _parse_complete_expression_states(
        root, view_id, record.get("frames"), "frames",
    )
    oral_payload = record.get("oral_masks", {})
    oral_masks = (
        frozendict()
        if oral_payload in ({}, None)
        else _parse_complete_expression_states(root, view_id, oral_payload, "oral_masks")
    )
    neutral_payload = record.get("neutral_frames", {})
    neutral_frames = (
        frozendict()
        if neutral_payload in ({}, None)
        else _parse_complete_expression_neutral_states(root, view_id, neutral_payload)
    )
    replacement_payload = record.get("replacement_mask")
    replacement_mask = (
        None
        if replacement_payload in ({}, None)
        else _resolve_complete_expression_asset(
            root, replacement_payload, f"{view_id}/replacement_mask",
        )
    )
    return CompleteExpressionFrameSet(
        source_group_id.strip(), source_lineage, frames, oral_masks, neutral_frames,
        motion_policy, replacement_mask,
    )


def _source_lineage_token(value: object, view_id: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and value:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    raise ValueError(f"Complete expression requires source_lineage: {view_id}")


def _parse_complete_expression_states(
    root: Path,
    view_id: str,
    payload: object,
    field: str,
) -> frozendict[Viseme, frozendict[EyeState, Path]]:
    expected_visemes = frozenset(viseme.value for viseme in SPOKEN_VISEMES)
    expected_states = frozenset(state.value for state in COMPLETE_EXPRESSION_STATES)
    if not isinstance(payload, dict) or set(payload) != expected_visemes:
        raise ValueError(
            f"Complete expression {field} requires every spoken viseme: {view_id}"
        )
    parsed: dict[Viseme, frozendict[EyeState, Path]] = {}
    for viseme in SPOKEN_VISEMES:
        state_records = payload[viseme.value]
        if not isinstance(state_records, dict) or set(state_records) != expected_states:
            raise ValueError(
                f"Complete expression {field} requires rest/half/closed: "
                f"{view_id}/{viseme.value}"
            )
        parsed[viseme] = frozendict(
            {
                state: _resolve_complete_expression_asset(
                    root, state_records[state.value],
                    f"{view_id}/{viseme.value}/{state.value}",
                )
                for state in COMPLETE_EXPRESSION_STATES
            }
        )
    return frozendict(parsed)


def _parse_complete_expression_neutral_states(
    root: Path,
    view_id: str,
    payload: object,
) -> frozendict[EyeState, Path]:
    expected_states = frozenset(state.value for state in COMPLETE_EXPRESSION_STATES)
    if not isinstance(payload, dict) or set(payload) != expected_states:
        raise ValueError(
            f"Complete expression neutral_frames requires rest/half/closed: {view_id}"
        )
    return frozendict(
        {
            state: _resolve_complete_expression_asset(
                root, payload[state.value], f"{view_id}/neutral/{state.value}",
            )
            for state in COMPLETE_EXPRESSION_STATES
        }
    )


def _resolve_complete_expression_asset(
    root: Path,
    record: object,
    label: str,
) -> Path:
    if not isinstance(record, dict):
        raise ValueError(f"Complete expression requires an asset record: {label}")
    declared = record.get("path")
    if not isinstance(declared, str) or not declared:
        raise ValueError(f"Complete expression requires an asset path: {label}")
    portable = PurePosixPath(declared)
    if (
        portable.is_absolute()
        or PureWindowsPath(declared).drive
        or "\\" in declared
        or ".." in portable.parts
        or portable.as_posix() != declared
    ):
        raise ValueError(f"Complete expression requires a portable relative path: {label}")
    path = (root / portable).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Complete expression asset escapes atlas root: {label}")
    expected_sha = record.get("sha256")
    if (
        not isinstance(expected_sha, str)
        or len(expected_sha) != SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdefABCDEF" for character in expected_sha)
    ):
        raise ValueError(f"Complete expression requires a SHA256: {label}")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise FileNotFoundError(f"Missing complete expression asset: {path.name}") from error
    if hashlib.sha256(data).hexdigest() != expected_sha.lower():
        raise ValueError(f"Complete expression SHA256 mismatch: {path.name}")
    _validate_complete_expression_png(
        data, path, (FULL_BODY_DIMENSION_WIDTH, FULL_BODY_DIMENSION_HEIGHT),
    )
    return path


def _validate_complete_expression_png(
    data: bytes,
    path: Path,
    canvas: tuple[int, int],
) -> None:
    if _png_dimensions(path, rgba_layer=True) != canvas:
        raise ValueError(f"Complete expression canvas mismatch: {path.name}")
    pixels = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if (
        pixels is None
        or pixels.dtype != np.uint8
        or pixels.ndim != COLOR_IMAGE_DIMENSIONS
        or pixels.shape[2] != RGBA_CHANNELS
        or (pixels.shape[1], pixels.shape[0]) != canvas
        or not np.any(pixels[:, :, 3] == 0)
        or not np.any(pixels[:, :, 3] > 0)
    ):
        raise ValueError(
            f"Complete expression requires a nonempty transparent RGBA frame: {path.name}"
        )


def _validate_complete_expression_group(
    group: CompleteExpressionFrameSet,
) -> None:
    if not isinstance(group.source_group_id, str) or not group.source_group_id.strip():
        raise ValueError("Complete expression requires source_group_id")
    if not isinstance(group.source_lineage, str) or not group.source_lineage.strip():
        raise ValueError("Complete expression requires source_lineage")
    if (
        not isinstance(group.motion_policy, str)
        or group.motion_policy not in COMPLETE_EXPRESSION_MOTION_POLICIES
    ):
        raise ValueError(
            "Complete expression motion_policy must be neutral_body_only or "
            "preserve_body_layers"
        )
    expected_visemes = frozenset(SPOKEN_VISEMES)
    expected_states = frozenset(COMPLETE_EXPRESSION_STATES)
    if not isinstance(group.frames, Mapping) or set(group.frames) != expected_visemes:
        raise ValueError("Complete expression frames require every spoken viseme")
    for viseme in SPOKEN_VISEMES:
        states = group.frames[viseme]
        if not isinstance(states, Mapping) or set(states) != expected_states:
            raise ValueError("Complete expression frames require rest/half/closed")
    if not isinstance(group.neutral_frames, Mapping):
        raise ValueError("Complete expression neutral_frames must be a mapping")
    if group.neutral_frames and set(group.neutral_frames) != expected_states:
        raise ValueError("Complete expression neutral_frames require rest/half/closed")
    if not isinstance(group.oral_masks, Mapping):
        raise ValueError("Complete expression oral_masks must be a mapping")
    if group.oral_masks:
        if set(group.oral_masks) != expected_visemes:
            raise ValueError("Complete expression oral masks must match frames")
        for viseme in SPOKEN_VISEMES:
            states = group.oral_masks[viseme]
            if not isinstance(states, Mapping) or set(states) != expected_states:
                raise ValueError("Complete expression oral masks require rest/half/closed")
    _validate_complete_expression_replacement(group)


def _validate_complete_expression_replacement(
    group: CompleteExpressionFrameSet,
) -> None:
    """Validate the optional source-bound region policy independently."""

    if group.replacement_mask is not None and not isinstance(group.replacement_mask, Path):
        raise ValueError("Complete expression replacement_mask must be a filesystem path")
    if (
        group.motion_policy == COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY
        and group.replacement_mask is None
    ):
        raise ValueError(
            "Complete expression preserve_body_layers requires replacement_mask"
        )
    if (
        group.motion_policy == COMPLETE_EXPRESSION_MOTION_POLICY
        and group.replacement_mask is not None
    ):
        raise ValueError(
            "Complete expression replacement_mask requires preserve_body_layers"
        )


def snapshot_complete_expression_frames(
    view: LayeredFullBodyView,
) -> frozendict[str, bytes]:
    """Validate and freeze complete-expression bytes before the frame loop."""

    group = getattr(view, "complete_expression_frames", None)
    if group is None:
        return frozendict()
    _validate_complete_expression_group(group)
    body_path = view.path("body")
    if body_path is None:
        raise ValueError("Complete expression requires a body canvas")
    canvas = _png_dimensions(body_path)
    paths = [*group.frames[viseme].values() for viseme in SPOKEN_VISEMES]
    paths.extend(group.neutral_frames.values())
    if group.replacement_mask is not None:
        paths.append(group.replacement_mask)
    paths.extend(
        path
        for viseme in SPOKEN_VISEMES
        for path in group.oral_masks.get(viseme, {}).values()
    )
    snapshots: dict[str, bytes] = {}
    for path in paths:
        if not isinstance(path, Path):
            raise ValueError("Complete expression assets must use filesystem paths")
        data = path.read_bytes()
        _validate_complete_expression_png(data, path, canvas)
        snapshots[str(path)] = data
    return frozendict(snapshots)


def _load_authority_mouth_centers(root: Path) -> dict[str, float]:
    """Load only explicitly trusted centers; malformed data fails closed."""

    path = root / "mouth_authority_manifest.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    version = payload.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        return {}
    views = payload.get("views", {})
    if not isinstance(views, dict):
        return {}
    centers: dict[str, float] = {}
    for view_id, record in views.items():
        if view_id not in VIEW_IDS or not isinstance(record, dict):
            continue
        if record.get("trusted") is not True:
            continue
        value = record.get("mouth_center_x")
        if (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and 0 <= value < FULL_BODY_DIMENSION_WIDTH
        ):
            centers[view_id] = float(value)
    return centers
