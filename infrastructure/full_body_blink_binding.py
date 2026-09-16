"""Bind candidate blink PNGs to an explicit authority using immutable bytes.

The receipt declares asset provenance; visual acceptance remains a separate owner decision.
Validation happens once at renderer construction, with the frame loop kept free of validation.
"""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from collections.abc import Mapping
lazy from pathlib import Path, PurePosixPath, PureWindowsPath

lazy import cv2
lazy import numpy as np

lazy from domain.face_rig import EyeState

RECEIPT_SCHEMA = "mohan.candidate-blink-binding.v1"
RECEIPT_VERSION = 1
PORTABLE_RECEIPT_SCHEMA = "mohan.candidate-blink-binding.v2"
PORTABLE_RECEIPT_VERSION = 2
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOR_DIMENSIONS = 3
RGBA_CHANNELS = 4
RGB_CHANNELS = 3
BLINK_STATES = (EyeState.HALF, EyeState.CLOSED)


def _object(value: object, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid blink binding object: {field}")
    return value


def _canvas(receipt: dict) -> tuple[int, int]:
    canvas = _object(receipt.get("canvas"), "canvas")
    values = (canvas.get("width"), canvas.get("height"))
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("Provide a supported blink binding canvas")
    return values


def _declared_path(value: object, expected_path: Path, binding_root: Path | None) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Blink binding requires a path: {expected_path.name}")
    if binding_root is None:
        if not Path(value).is_absolute():
            raise ValueError(f"Blink binding requires an absolute path: {expected_path.name}")
        return Path(value).resolve()
    portable = PurePosixPath(value)
    if (portable.is_absolute() or PureWindowsPath(value).drive
            or "\\" in value or ".." in portable.parts or portable.as_posix() != value):
        raise ValueError(f"Blink binding requires a portable relative path: {expected_path.name}")
    resolved = (binding_root / portable).resolve()
    if not resolved.is_relative_to(binding_root.resolve()):
        raise ValueError(f"Blink binding path escapes atlas root: {expected_path.name}")
    return resolved


def _snapshot(record: object, expected_path: Path, binding_root: Path | None) -> bytes:
    binding = _object(record, expected_path.name)
    declared = binding.get("path")
    if _declared_path(declared, expected_path, binding_root) != expected_path.resolve():
        raise ValueError(f"Blink binding path mismatch: {expected_path.name}")
    expected_sha = binding.get("sha256")
    data = expected_path.read_bytes()
    if not isinstance(expected_sha, str) or hashlib.sha256(data).hexdigest() != expected_sha.lower():
        raise ValueError(f"Blink binding SHA256 mismatch: {expected_path.name}")
    return data


def _validate_png(data: bytes, canvas: tuple[int, int] | None, *, overlay: bool) -> None:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Blink binding requires PNG bytes")
    pixels = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if pixels is None or pixels.dtype != np.uint8 or pixels.ndim != COLOR_DIMENSIONS:
        raise ValueError("Blink binding requires an 8-bit color PNG")
    if canvas is not None and (pixels.shape[1], pixels.shape[0]) != canvas:
        raise ValueError("Blink binding canvas mismatch")
    if pixels.shape[2] not in (RGB_CHANNELS, RGBA_CHANNELS):
        raise ValueError("Blink binding requires RGB or RGBA")
    if overlay and (pixels.shape[2] != RGBA_CHANNELS or not np.any(pixels[:, :, 3] == 0)):
        raise ValueError("Blink binding requires transparent RGBA overlays")


def snapshot_view_authority(authority_root: Path, view_id: str) -> frozendict[str, bytes]:
    """Freeze a source with a base-only blink contract; the blink receipt is omitted."""
    if not view_id or Path(view_id).name != view_id or "/" in view_id or "\\" in view_id:
        raise ValueError("Provide a supported authority view id")
    path = authority_root / f"{view_id}.png"
    try:
        data = path.read_bytes()
        _validate_png(data, None, overlay=False)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Missing or invalid view authority: {path}") from exc
    return frozendict({str(path): data})


def bind_blink_source(
    authority_root: Path,
    view_id: str,
    frames: Mapping[EyeState, Path],
) -> frozendict[str, bytes]:
    """Validate one declared source/pair and freeze the bytes actually drawn.

    Views with authored blink frames receive receipts; base-only views use the established contract. Existing default
    renderers do not call this candidate-only boundary.
    """
    if not frames:
        return frozendict()
    if set(frames) != set(BLINK_STATES):
        raise ValueError(f"Incomplete blink binding pair: {view_id}")
    if Path(view_id).name != view_id or "/" in view_id or "\\" in view_id:
        raise ValueError("Provide a supported blink binding view id")
    receipt_path = authority_root / f"{view_id}.blink-binding.json"
    receipt = _object(json.loads(receipt_path.read_text(encoding="utf-8")), "receipt")
    version = receipt.get("version")
    supported = ((RECEIPT_SCHEMA, RECEIPT_VERSION),
                 (PORTABLE_RECEIPT_SCHEMA, PORTABLE_RECEIPT_VERSION))
    if (isinstance(version, bool) or not isinstance(version, int)
            or (receipt.get("schema"), version) not in supported):
        raise ValueError("Provide a supported blink binding schema/version")
    binding_root = authority_root.parent if version == PORTABLE_RECEIPT_VERSION else None
    if receipt.get("view_id") != view_id:
        raise ValueError("Blink binding view mismatch")
    canvas = _canvas(receipt)
    source_path = authority_root / f"{view_id}.png"
    blink = _object(receipt.get("blink"), "blink")
    records = [(source_path, receipt.get("source"), False)]
    records.extend((frames[state], blink.get(state.value), True) for state in BLINK_STATES)
    if len({path.resolve() for path, _, _ in records}) != len(records):
        raise ValueError("Blink binding source and frames must be distinct")
    snapshots: dict[str, bytes] = {}
    for path, record, overlay in records:
        data = _snapshot(record, path, binding_root)
        _validate_png(data, canvas, overlay=overlay)
        snapshots[str(path)] = data
    return frozendict(snapshots)
