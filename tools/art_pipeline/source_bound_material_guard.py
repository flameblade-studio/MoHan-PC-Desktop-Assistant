"""Fail closed when a source-bound material changes pixels outside its mask."""

from __future__ import annotations

lazy from io import BytesIO
lazy from typing import TypedDict

lazy import numpy as np
lazy from PIL import Image

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_HEADER_LENGTH = 26
PNG_BIT_DEPTH_OFFSET = 24
PNG_COLOR_TYPE_OFFSET = 25
PNG_8_BIT = 8
PNG_GRAYSCALE_COLOR_TYPE = 0
PNG_RGBA_COLOR_TYPE = 6
MASK_BACKGROUND = 0
MASK_FOREGROUND = 255


class MaterialGuardError(ValueError):
    """Raised when material bytes or their allowed-change mask are invalid."""


class MaterialChangeReport(TypedDict):
    """JSON-serializable evidence for one guarded material replacement."""

    changed_pixels: int
    changed_bbox_xyxy: list[int] | None


def verify_material_change(
    original_member: bytes,
    candidate_member: bytes,
    allowed_mask: bytes,
) -> MaterialChangeReport:
    """Require every changed RGBA pixel to lie inside a pinned binary mask.

    The bounding box uses half-open ``[x0, y0, x1, y1]`` coordinates. Fully
    transparent RGB differences still count, preserving exact source pixels.
    """

    original = _decode_rgba_png(original_member, "original member")
    candidate = _decode_rgba_png(candidate_member, "candidate member")
    if candidate.shape != original.shape:
        raise MaterialGuardError("Candidate member dimensions differ from the original member.")
    mask = _decode_binary_mask_png(allowed_mask)
    if mask.shape != original.shape[:2]:
        raise MaterialGuardError("Allowed-change mask dimensions differ from the pack member.")
    if not np.any(mask):
        raise MaterialGuardError("Allowed-change mask must select at least one pixel.")

    changed = np.any(original != candidate, axis=2)
    outside = changed & ~mask
    if np.any(outside):
        count = int(np.count_nonzero(outside))
        bbox = _bounding_box(outside)
        raise MaterialGuardError(
            f"Candidate changes {count} pixels outside the allowed-change mask; bbox={bbox}."
        )
    return {
        "changed_pixels": int(np.count_nonzero(changed)),
        "changed_bbox_xyxy": _bounding_box(changed),
    }


def _decode_rgba_png(payload: bytes, label: str) -> np.ndarray:
    _require_png_header(payload, label, PNG_RGBA_COLOR_TYPE)
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG" or image.mode != "RGBA":
                raise MaterialGuardError(f"{label} must be an 8-bit RGBA PNG.")
            image.load()
            pixels = np.asarray(image, dtype=np.uint8)
    except MaterialGuardError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise MaterialGuardError(f"Cannot decode {label} as PNG.") from error
    return pixels


def _decode_binary_mask_png(payload: bytes) -> np.ndarray:
    label = "allowed-change mask"
    _require_png_header(payload, label, PNG_GRAYSCALE_COLOR_TYPE)
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG" or image.mode != "L":
                raise MaterialGuardError("Allowed-change mask must be an 8-bit grayscale PNG.")
            image.load()
            pixels = np.asarray(image, dtype=np.uint8)
    except MaterialGuardError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise MaterialGuardError("Cannot decode allowed-change mask as PNG.") from error
    if not np.isin(pixels, (MASK_BACKGROUND, MASK_FOREGROUND)).all():
        raise MaterialGuardError("Allowed-change mask must contain only 0 and 255.")
    mask = pixels == MASK_FOREGROUND
    return mask


def _require_png_header(payload: bytes, label: str, color_type: int) -> None:
    if (
        not isinstance(payload, bytes)
        or len(payload) < PNG_HEADER_LENGTH
        or payload[: len(PNG_SIGNATURE)] != PNG_SIGNATURE
        or payload[PNG_BIT_DEPTH_OFFSET] != PNG_8_BIT
        or payload[PNG_COLOR_TYPE_OFFSET] != color_type
    ):
        kind = "RGBA" if color_type == PNG_RGBA_COLOR_TYPE else "grayscale"
        raise MaterialGuardError(f"{label} must be an 8-bit {kind} PNG.")


def _bounding_box(mask: np.ndarray) -> list[int] | None:
    rows, columns = np.nonzero(mask)
    if not len(columns):
        return None
    return [
        int(columns.min()),
        int(rows.min()),
        int(columns.max()) + 1,
        int(rows.max()) + 1,
    ]
