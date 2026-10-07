"""Validate complete, source-bound half-body expression families before rendering."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath, PureWindowsPath

lazy from PySide6.QtGui import QImage

lazy from domain.qt_image_io import image_from_png
lazy from domain.constants import CHARACTER_EXPRESSION_ROLES
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
COMPLETE_POSES = POSES | COMPLETE_CHEEK_POSES
PNG_HEADER_LENGTH = 26


@dataclass(frozen=True)
class CompleteHalfbodyFrames:
    """Immutable source bytes, grouped by pose, mouth and discrete eye state."""

    frames: frozendict[str, frozendict[str, frozendict[str, bytes]]]
    expressions: frozendict[str, tuple[str, str]]
    oral_masks: frozendict[str, frozendict[str, bytes]]
    whole_frame_blinks: frozenset[str]


def _read_image_record(root: Path, record: object, label: str) -> bytes:
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
    image = image_from_png(data)
    if image.isNull() or image.size().toTuple() != (DIMENSION, DIMENSION):
        raise ValueError(
            f"Complete half-body {label} canvas must be "
            f"{DIMENSION}x{DIMENSION}: {value}"
        )
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    alpha = bytes(rgba.constBits())[3::4]
    if 0 not in alpha or not any(alpha):
        raise ValueError(f"Complete half-body {label} must contain content and transparency: {value}")
    return data


def _read_frame(root: Path, record: object) -> bytes:
    return _read_image_record(root, record, "frame")


def _read_pose(
    root: Path, record: object,
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
            (eye, _read_frame(root, frame)) for eye, frame in states.items()
        )
    oral_payload = record.get("oral_masks", {})
    if oral_payload:
        if not isinstance(oral_payload, dict) or set(oral_payload) != MOUTH_SHAPES:
            raise ValueError("Complete half-body oral masks require small/a/o shapes")
        oral_masks = frozendict(
            (shape, _read_image_record(root, mask, "oral mask"))
            for shape, mask in oral_payload.items()
        )
    else:
        oral_masks = frozendict()
    blink_composition = record.get("blink_composition", "eye-patch")
    if blink_composition not in {"eye-patch", "whole-frame"}:
        raise ValueError("Unsupported complete half-body blink composition")
    return frozendict(result), oral_masks, blink_composition == "whole-frame"


def load_complete_halfbody_frames(root: Path) -> CompleteHalfbodyFrames | None:
    """Absent installation keeps legacy behavior; corrupt installed data raises."""

    root = Path(root).resolve()
    if not root.exists():
        return None
    path = root / "manifest.json"
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
    for pose, record in poses.items():
        frame_group, oral_group, whole_frame_blink = _read_pose(root, record)
        pose_frames[pose] = frame_group
        if oral_group:
            oral_masks[pose] = oral_group
        if whole_frame_blink:
            whole_frame_blinks.add(pose)
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
    return CompleteHalfbodyFrames(
        frames,
        frozendict(expressions),
        frozendict(oral_masks),
        frozenset(whole_frame_blinks),
    )
