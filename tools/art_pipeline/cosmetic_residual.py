"""Reuse the approved full-body pigment separation on a native RGBA source.

The numerical method is preserved from native-front-v4-makeup-10/
pigment-residual-review-04/recipe.py. It expresses a desired color difference
as an independent pigment layer; it neither transfers donor facial pixels nor
registers geometry. Callers provide already aligned native artwork and support.
"""
from __future__ import annotations

lazy import numpy as np
lazy from numpy.typing import NDArray

Rgba = NDArray[np.uint8]
IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4


def _validate_pair(base: Rgba, layer: Rgba) -> None:
    if (
        base.dtype != np.uint8 or layer.dtype != np.uint8
        or base.ndim != IMAGE_DIMENSIONS or base.shape[-1] != RGBA_CHANNELS
        or base.shape != layer.shape
    ):
        raise ValueError("Cosmetic residuals require matching uint8 RGBA arrays.")


def source_atop(base: Rgba, layer: Rgba) -> Rgba:
    """Paint pigment on existing source coverage without changing its alpha."""
    _validate_pair(base, layer)
    alpha = layer[:, :, 3:4].astype(float) / 255
    result = base.copy()
    result[:, :, :3] = np.rint(
        base[:, :, :3] * (1 - alpha) + layer[:, :, :3] * alpha
    ).astype(np.uint8)
    return result


def residual_layer(base: Rgba, target_layer: Rgba) -> Rgba:
    """Encode the target pigment without baking underlying brightening into it.

    As in the accepted full-body recipe, the minimal representable alpha is
    computed per pixel from the positive and negative RGB differences. The
    returned layer retains the caller's support and reconstructs the desired
    composite within eight-bit rounding precision.
    """
    target = source_atop(base, target_layer)
    original = base[:, :, :3].astype(float)
    delta = target[:, :, :3].astype(float) - original
    ratios = np.where(
        delta >= 0,
        delta / np.maximum(255 - original, 1),
        -delta / np.maximum(original, 1),
    )
    alpha = np.ceil(np.max(ratios, axis=2) * 255).astype(np.uint8)
    alpha[target_layer[:, :, 3] == 0] = 0
    rgb = original + delta / np.maximum(alpha[:, :, None] / 255, 1 / 255)
    result = np.zeros_like(target_layer)
    result[:, :, :3] = np.rint(np.clip(rgb, 0, 255)).astype(np.uint8)
    result[:, :, 3] = alpha
    result[alpha == 0] = 0
    return result
