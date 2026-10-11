"""Validate complete, source-bound half-body expression families before rendering."""
from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath, PureWindowsPath

lazy from PIL import Image

lazy from domain.character_runtime import CHARACTER_EXPRESSION_ROLES
lazy from domain.character_source import active_expression_catalog
lazy from domain.python315_concurrency import ThreadPoolExecutor
lazy from infrastructure.detachable_halfbody_assets import DIMENSION, POSES

SCHEMA = "mohan.complete-halfbody-expressions.v1"
FAMILIES = frozenset({"neutral", "small", "a", "o"})
EYES = frozenset({"rest", "half", "closed"})
MOUTH_SHAPES = frozenset({"small", "a", "o"})
GLANCE_COMPLETE_POSE = f"cheek-{CHARACTER_EXPRESSION_ROLES['side_gaze']}"
COMPLETE_CHEEK_POSES = frozenset({
    GLANCE_COMPLETE_POSE,
    f"cheek-{CHARACTER_EXPRESSION_ROLES['noticed']}",
    f"cheek-{CHARACTER_EXPRESSION_ROLES['happiness']}",
    f"cheek-{CHARACTER_EXPRESSION_ROLES['worry']}",
    f"cheek-{CHARACTER_EXPRESSION_ROLES['reminder']}",
})
COMPLETE_FRONT_POSES = frozenset(
    f"front-{expression}"
    for expression, pose in active_expression_catalog().state_to_pose.items()
    if pose == "front"
)
COMPLETE_POSES = POSES | COMPLETE_CHEEK_POSES | COMPLETE_FRONT_POSES
PNG_HEADER_LENGTH = 26
# Pillow releases the GIL while decoding, so canvas checks run in parallel;
# Qt's decoder holds it and made startup grow linearly with the frame count.
IMAGE_CHECK_WORKERS = 8


@dataclass(frozen=True)
class CompleteHalfbodyFrames:
    """Immutable source bytes, grouped by pose, mouth and discrete eye state."""

    frames: frozendict[str, frozendict[str, frozendict[str, bytes]]]
    expressions: frozendict[str, tuple[str, str]]
    oral_masks: frozendict[str, frozendict[str, bytes]]
    whole_frame_blinks: frozenset[str]


def _read_image_record(
    root: Path, record: object, label: str, pending: list[tuple[bytes, str, str]],
) -> bytes:
    if not isinstance(record, dict):
        raise ValueError(f"Complete half-body {label} requires a path and SHA-256")
    value, expected = record.get("path"), record.get("sha256")
    if not isinstance(value, str) or not value:
        raise ValueError(f"Complete half-body {label} path is missing")
    portable, windows = PurePosixPath(value), PureWindowsPath(value)
    if (
        "\\" in value or windows.drive or portable.is_absolute()
        or portable.as_posix() != value or ".." in portable.parts
    ):
        raise ValueError(f"Complete half-body {label} path must remain in its root")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Complete half-body {label} path escapes its root")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Complete half-body {label} digest mismatch: {value}")
    if len(data) < PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[24:26] != b"\x08\x06":
        raise ValueError(f"Complete half-body {label} must be 8-bit RGBA PNG: {value}")
    pending.append((data, label, value))
    return data


def _check_image(data: bytes, label: str, value: str) -> None:
    """Require the full canvas plus both transparent and visible pixels."""

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            size, mode = image.size, image.mode
            low, high = image.getchannel("A").getextrema() if mode == "RGBA" else (0, 0)
    except (OSError, ValueError) as error:
        raise ValueError(f"Complete half-body {label} is not a readable PNG: {value}") from error
    if size != (DIMENSION, DIMENSION):
        raise ValueError(
            f"Complete half-body {label} canvas must be "
            f"{DIMENSION}x{DIMENSION}: {value}"
        )
    if mode != "RGBA" or low != 0 or high == 0:
        raise ValueError(f"Complete half-body {label} must contain content and transparency: {value}")


def _check_images(pending: list[tuple[bytes, str, str]]) -> None:
    with ThreadPoolExecutor(max_workers=IMAGE_CHECK_WORKERS) as executor:
        for check in [executor.submit(_check_image, *item) for item in pending]:
            check.result()


def _read_pose(
    root: Path, record: object, pending: list[tuple[bytes, str, str]],
) -> tuple[frozendict[str, frozendict[str, bytes]], frozendict[str, bytes], bool]:
    if not isinstance(record, dict) or not isinstance(record.get("source_lineage"), dict):
        raise ValueError("Complete half-body pose requires source lineage")
    if not record["source_lineage"]:
        raise ValueError("Complete half-body source lineage cannot be empty")
    families = record.get("frames")
    if not isinstance(families, dict) or set(families) != FAMILIES:
        raise ValueError("Complete half-body pose requires neutral/small/a/o families")
    result = {}
    for family, states in families.items():
        if not isinstance(states, dict) or set(states) != EYES:
            raise ValueError("Complete half-body family requires rest/half/closed")
        result[family] = frozendict(
            (eye, _read_image_record(root, frame, "frame", pending))
            for eye, frame in states.items()
        )
    oral_payload = record.get("oral_masks", {})
    if oral_payload:
        if not isinstance(oral_payload, dict) or set(oral_payload) != MOUTH_SHAPES:
            raise ValueError("Complete half-body oral masks require small/a/o shapes")
        oral_masks = frozendict(
            (shape, _read_image_record(root, mask, "oral mask", pending))
            for shape, mask in oral_payload.items()
        )
    else:
        oral_masks = frozendict()
    blink_composition = record.get("blink_composition", "eye-patch")
    if blink_composition not in {"eye-patch", "whole-frame"}:
        raise ValueError("Unsupported complete half-body blink composition")
    return frozendict(result), oral_masks, blink_composition == "whole-frame"


def load_complete_halfbody_frames(
    root: Path, *, manifest_path: Path | None = None,
) -> CompleteHalfbodyFrames | None:
    """Absent installation keeps legacy behavior; corrupt installed data raises."""

    root = Path(root).resolve()
    if not root.exists():
        return None
    path = root / "manifest.json" if manifest_path is None else Path(manifest_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Complete half-body manifest escapes its asset root")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Unsupported complete half-body expression schema")
    poses, bindings = data.get("poses"), data.get("expressions")
    if not isinstance(poses, dict) or not poses or not set(poses) <= COMPLETE_POSES:
        raise ValueError("Invalid complete half-body pose inventory")
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("Complete half-body expressions require explicit bindings")
    pose_frames = {}
    oral_masks = {}
    whole_frame_blinks = set()
    pending: list[tuple[bytes, str, str]] = []
    for pose, record in poses.items():
        frame_group, oral_group, whole_frame_blink = _read_pose(root, record, pending)
        if pose in COMPLETE_FRONT_POSES and not whole_frame_blink:
            raise ValueError(
                f"Complete front expression requires whole-frame blinks: {pose}"
            )
        pose_frames[pose] = frame_group
        if oral_group:
            oral_masks[pose] = oral_group
        if whole_frame_blink:
            whole_frame_blinks.add(pose)
    _check_images(pending)
    frames = frozendict(pose_frames)
    expressions = {}
    for expression, binding in bindings.items():
        if not isinstance(expression, str) or not expression or not isinstance(binding, dict):
            raise ValueError("Invalid complete half-body expression binding")
        pose, family = binding.get("pose"), binding.get("family")
        if not isinstance(pose, str) or pose not in frames or not isinstance(family, str) or family not in FAMILIES:
            raise ValueError(f"Invalid complete half-body expression target: {expression}")
        expressions[expression] = (pose, family)
    for pose in frames:
        bound_families = {family for target, family in expressions.values() if target == pose}
        if bound_families != FAMILIES:
            raise ValueError(f"Complete half-body pose requires bindings for every mouth family: {pose}")
        if (
            pose in COMPLETE_FRONT_POSES
            and expressions.get(pose.removeprefix("front-")) != (pose, "neutral")
        ):
            raise ValueError(
                f"Complete front expression requires its own neutral binding: {pose}"
            )
    return CompleteHalfbodyFrames(
        frames,
        frozendict(expressions),
        frozendict(oral_masks),
        frozenset(whole_frame_blinks),
    )
