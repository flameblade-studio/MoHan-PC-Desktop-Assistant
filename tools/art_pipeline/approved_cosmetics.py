"""Separate aligned, approved cosmetics into reversible native pigment controls.

Callers own registration and authored skin/feature support. This module does not
infer anatomy, synthesize artwork, or select a source from another view.
"""
from __future__ import annotations

lazy from dataclasses import dataclass

lazy import numpy as np
lazy from numpy.typing import NDArray

lazy from tools.art_pipeline.cosmetic_residual import Rgba, residual_layer, source_atop

PIGMENT_SLOTS = ("eyes", "cheeks", "lips")
SLOTS = ("foundation", *PIGMENT_SLOTS)
MAX_RECONSTRUCTION_ERROR = 2


@dataclass(frozen=True)
class ExtractedCosmetics:
    """Native layers with the measured reconstruction and protected-area result."""

    layers: dict[str, Rgba]
    composite: Rgba
    max_reconstruction_error: int


def _support(value: NDArray, shape: tuple[int, int], name: str) -> NDArray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != shape or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite native-canvas support.")
    if np.any((array < 0) | (array > 1)):
        raise ValueError(f"{name} must contain coverage in [0, 1].")
    return array


def extract_cosmetics(
    bare: Rgba,
    approved: Rgba,
    coverage: NDArray,
    pigment_supports: dict[str, NDArray],
    *,
    protected: NDArray | None = None,
) -> ExtractedCosmetics:
    """Extract four controls without changing source alpha or protected pixels.

    Positive color/brightening residuals belong to foundation. Dark pigment is
    allocated to the authored eye, cheek and lip supports. Overlapping supports
    share their pigment instead of applying the same difference twice.
    """
    # Validate both image arrays using the shared native RGBA contract.
    source_atop(bare, approved)
    shape = bare.shape[:2]
    skin = _support(coverage, shape, "coverage").copy()
    if set(pigment_supports) != set(PIGMENT_SLOTS):
        raise ValueError("Exactly eyes, cheeks and lips supports are required.")
    weights = {slot: _support(pigment_supports[slot], shape, slot)
               for slot in PIGMENT_SLOTS}
    if protected is not None:
        aperture = np.asarray(protected)
        if aperture.shape != shape or aperture.dtype != np.bool_:
            raise ValueError("Protected pixels require a native-canvas boolean mask.")
        skin[aperture] = 0
    skin[(bare[:, :, 3] == 0) | (approved[:, :, 3] == 0)] = 0
    total = sum(weights.values())
    denominator = np.maximum(total, 1)
    weights = {slot: weight / denominator for slot, weight in weights.items()}
    difference = (approved[:, :, :3].astype(float) - bare[:, :, :3]) * skin[:, :, None]
    dark = np.minimum(difference, 0)
    deltas = {"foundation": difference - dark * np.minimum(total, 1)[:, :, None]}
    deltas.update({slot: dark * weight[:, :, None] for slot, weight in weights.items()})
    composite = bare.copy()
    layers = {}
    cumulative = np.zeros_like(difference)
    for slot in SLOTS:
        if not np.any(deltas[slot]):
            layers[slot] = np.zeros_like(bare)
            continue
        cumulative += deltas[slot]
        target = bare.copy()
        target[:, :, :3] = np.rint(np.clip(bare[:, :, :3] + cumulative, 0, 255)).astype(np.uint8)
        target[:, :, 3] = np.where(skin > 0, 255, 0)
        layer = residual_layer(composite, target)
        composite = source_atop(composite, layer)
        layers[slot] = layer
    expected = np.rint(np.clip(bare[:, :, :3] + difference, 0, 255)).astype(np.uint8)
    error = int(np.abs(composite[:, :, :3].astype(int) - expected).max())
    if error > MAX_RECONSTRUCTION_ERROR:
        raise ValueError(f"Approved target reconstruction error: {error}")
    if not np.array_equal(composite[:, :, 3], bare[:, :, 3]):
        raise ValueError("Cosmetics changed native alpha.")
    if not np.array_equal(composite[skin == 0], bare[skin == 0]):
        raise ValueError("Cosmetics changed protected or unowned pixels.")
    return ExtractedCosmetics(layers, composite, error)
