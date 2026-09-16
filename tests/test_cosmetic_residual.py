"""Pigment controls preserve native coverage and reconstruct bounded colors."""
import numpy as np
import pytest

from tools.art_pipeline.cosmetic_residual import residual_layer, source_atop


def test_dark_pigment_does_not_carry_the_foundation_when_it_is_removed():
    bare = np.array([[[140, 110, 90, 255]]], dtype=np.uint8)
    foundation = np.array([[[190, 168, 150, 255]]], dtype=np.uint8)
    target = np.array([[[118, 68, 72, 255]]], dtype=np.uint8)
    made_up_skin = source_atop(bare, foundation)
    pigment = residual_layer(made_up_skin, target)
    full = source_atop(made_up_skin, pigment)
    no_foundation = source_atop(bare, pigment)
    assert np.max(np.abs(full.astype(int) - target.astype(int))) <= 1
    assert np.all(no_foundation[:, :, :3] <= full[:, :, :3])
    assert np.array_equal(no_foundation[:, :, 3], bare[:, :, 3])


def test_residual_preserves_shape_and_handles_both_color_directions():
    base = np.array([[[0, 255, 95, 255], [180, 90, 150, 128], [30, 40, 50, 0]]], dtype=np.uint8)
    target = np.array([[[255, 0, 180, 255], [120, 150, 165, 90], [0, 0, 0, 0]]], dtype=np.uint8)
    expected = source_atop(base, target)
    pigment = residual_layer(base, target)
    reconstructed = source_atop(base, pigment)
    assert np.max(np.abs(reconstructed.astype(int) - expected.astype(int))) <= 1
    assert np.array_equal(reconstructed[:, :, 3], base[:, :, 3])
    assert not pigment[0, 2].any()
    assert np.array_equal(base, source_atop(base, np.zeros_like(base)))


def test_residual_rejects_mismatched_canvas_before_painting():
    with pytest.raises(ValueError, match="matching uint8 RGBA"):
        residual_layer(np.zeros((2, 2, 4), np.uint8), np.zeros((3, 2, 4), np.uint8))
