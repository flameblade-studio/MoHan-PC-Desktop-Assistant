"""Validate complete, source-bound half-body expression families before rendering."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath, PureWindowsPath

lazy from PySide6.QtGui import QImage

lazy from infrastructure.detachable_halfbody_assets import DIMENSION, POSES

SCHEMA = "mohan.complete-halfbody-expressions.v1"
FAMILIES = frozenset({"neutral", "small", "a", "o"})
EYES = frozenset({"rest", "half", "closed"})
PNG_HEADER_LENGTH = 26


@dataclass(frozen=True)
class CompleteHalfbodyFrames:
    """Immutable source bytes, grouped by pose, mouth and discrete eye state."""

    frames: frozendict[str, frozendict[str, frozendict[str, bytes]]]
    expressions: frozendict[str, tuple[str, str]]


def _read_frame(root: Path, record: object) -> bytes:
    if not isinstance(record, dict):
        raise ValueError("Complete half-body frame requires a path and SHA-256")
    value, expected = record.get("path"), record.get("sha256")
    if not isinstance(value, str) or not value:
        raise ValueError("Complete half-body frame path is missing")
    portable, windows = PurePosixPath(value), PureWindowsPath(value)
    if (
        "\\" in value or windows.drive or portable.is_absolute()
        or portable.as_posix() != value or ".." in portable.parts
    ):
        raise ValueError("Complete half-body frame path must remain in its root")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Complete half-body frame path escapes its root")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Complete half-body frame digest mismatch: {value}")
    if len(data) < PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[24:26] != b"\x08\x06":
        raise ValueError(f"Complete half-body frame must be 8-bit RGBA PNG: {value}")
    image = QImage.fromData(data, "PNG")
    if image.isNull() or image.size().toTuple() != (DIMENSION, DIMENSION):
        raise ValueError(f"Complete half-body frame canvas must be 1254x1254: {value}")
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    alpha = bytes(rgba.constBits())[3::4]
    if 0 not in alpha or not any(alpha):
        raise ValueError(f"Complete half-body frame must contain body and transparency: {value}")
    return data


def _read_pose(root: Path, record: object) -> frozendict[str, frozendict[str, bytes]]:
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
    return frozendict(result)


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
    if not isinstance(poses, dict) or not poses or not set(poses) <= POSES:
        raise ValueError("Invalid complete half-body pose inventory")
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("Complete half-body expressions require explicit bindings")
    frames = frozendict((pose, _read_pose(root, record)) for pose, record in poses.items())
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
    return CompleteHalfbodyFrames(frames, frozendict(expressions))
