"""Approved source extraction remains reversible across independent controls."""
lazy import numpy as np
lazy import pytest

lazy from tools.art_pipeline.approved_cosmetics import MAX_RECONSTRUCTION_ERROR, extract_cosmetics
lazy from tools.art_pipeline.cosmetic_residual import source_atop


def test_overlapping_pigments_reconstruct_without_double_painting_or_alpha_drift():
    bare = np.full((3, 5, 4), [120, 130, 140, 127], dtype=np.uint8)
    target = np.full_like(bare, [80, 150, 100, 255])
    supports = {slot: np.ones((3, 5)) for slot in ("eyes", "cheeks", "lips")}
    protected = np.zeros((3, 5), bool)
    protected[1, 2] = True
    result = extract_cosmetics(bare, target, np.ones((3, 5)), supports, protected=protected)
    assert result.max_reconstruction_error <= MAX_RECONSTRUCTION_ERROR
    assert np.array_equal(result.composite[protected], bare[protected])
    assert np.array_equal(result.composite[:, :, 3], bare[:, :, 3])
    assert np.max(np.abs(result.composite[:, :, :3][~protected].astype(int) - target[:, :, :3][~protected])) <= MAX_RECONSTRUCTION_ERROR
    for layer in result.layers.values():
        assert not layer[protected].any()
    assert np.array_equal(source_atop(bare, np.zeros_like(bare)), bare)


def test_foundation_can_be_removed_without_a_white_patch_in_dark_pigment():
    bare = np.full((1, 2, 4), [130, 120, 110, 255], dtype=np.uint8)
    target = np.full_like(bare, [175, 100, 90, 255])
    supports = {slot: np.ones((1, 2)) if slot == "eyes" else np.zeros((1, 2))
                for slot in ("eyes", "cheeks", "lips")}
    result = extract_cosmetics(bare, target, np.ones((1, 2)), supports)
    pigment_only = source_atop(bare, result.layers["eyes"])
    assert np.all(pigment_only[:, :, :3] <= result.composite[:, :, :3] + 1)
    assert result.layers["foundation"][:, :, 3].any()
    assert not result.layers["cheeks"].any()
    assert not result.layers["lips"].any()


@pytest.mark.parametrize("bad", [np.full((2, 2), np.nan), np.ones((1, 2)), np.full((2, 2), 2)])
def test_invalid_coverage_fails_before_creating_layers(bad):
    source = np.zeros((2, 2, 4), np.uint8)
    supports = {slot: np.ones((2, 2)) for slot in ("eyes", "cheeks", "lips")}
    with pytest.raises(ValueError, match="coverage"):
        extract_cosmetics(source, source, bad, supports)
