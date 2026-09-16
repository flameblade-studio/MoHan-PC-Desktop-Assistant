"""Source-bound material replacements may change only authored mask pixels."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from tools.art_pipeline.source_bound_material_guard import (
    MaterialGuardError,
    verify_material_change,
)


def png_bytes(pixels: np.ndarray, mode: str) -> bytes:
    stream = BytesIO()
    Image.fromarray(pixels, mode).save(stream, format="PNG")
    return stream.getvalue()


def rgba() -> np.ndarray:
    pixels = np.zeros((3, 4, 4), dtype=np.uint8)
    pixels[1, 1:3] = [31, 47, 73, 192]
    return pixels


def binary_mask(*points: tuple[int, int]) -> np.ndarray:
    mask = np.zeros((3, 4), dtype=np.uint8)
    for x, y in points:
        mask[y, x] = 255
    return mask


def test_reports_jsonable_changed_count_and_half_open_bbox() -> None:
    original = rgba()
    candidate = original.copy()
    candidate[1, 2, 0] += 1

    report = verify_material_change(
        png_bytes(original, "RGBA"),
        png_bytes(candidate, "RGBA"),
        png_bytes(binary_mask((2, 1)), "L"),
    )

    assert report == {"changed_pixels": 1, "changed_bbox_xyxy": [2, 1, 3, 2]}


def test_transparent_rgb_change_still_requires_mask_ownership() -> None:
    original = rgba()
    candidate = original.copy()
    candidate[0, 0, 0] = 1

    with pytest.raises(MaterialGuardError, match="1 pixels outside"):
        verify_material_change(
            png_bytes(original, "RGBA"),
            png_bytes(candidate, "RGBA"),
            png_bytes(binary_mask((2, 1)), "L"),
        )


def test_unchanged_candidate_returns_zero_and_no_bbox() -> None:
    original = png_bytes(rgba(), "RGBA")

    report = verify_material_change(
        original,
        original,
        png_bytes(binary_mask((2, 1)), "L"),
    )

    assert report == {"changed_pixels": 0, "changed_bbox_xyxy": None}


@pytest.mark.parametrize(
    ("original", "candidate", "mask", "message"),
    [
        (
            png_bytes(rgba()[..., :3], "RGB"),
            png_bytes(rgba(), "RGBA"),
            png_bytes(binary_mask((2, 1)), "L"),
            "original member must be an 8-bit RGBA PNG",
        ),
        (
            png_bytes(rgba(), "RGBA"),
            png_bytes(np.zeros((2, 4, 4), dtype=np.uint8), "RGBA"),
            png_bytes(binary_mask((2, 1)), "L"),
            "dimensions differ",
        ),
        (
            png_bytes(rgba(), "RGBA"),
            png_bytes(rgba(), "RGBA"),
            png_bytes(np.zeros((2, 4), dtype=np.uint8), "L"),
            "mask dimensions differ",
        ),
        (
            png_bytes(rgba(), "RGBA"),
            png_bytes(rgba(), "RGBA"),
            png_bytes(np.zeros((3, 4), dtype=np.uint8), "L"),
            "select at least one pixel",
        ),
        (
            png_bytes(rgba(), "RGBA"),
            png_bytes(rgba(), "RGBA"),
            png_bytes(np.full((3, 4), 127, dtype=np.uint8), "L"),
            "contain only 0 and 255",
        ),
    ],
)
def test_rejects_invalid_images_and_masks(
    original: bytes,
    candidate: bytes,
    mask: bytes,
    message: str,
) -> None:
    with pytest.raises(MaterialGuardError, match=message):
        verify_material_change(original, candidate, mask)
