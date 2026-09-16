"""Apply the approved pigment recipe to native supports without moving source pixels."""

from __future__ import annotations

from typing import Literal

import cv2
import numpy as np

Slot = Literal["eyes", "cheeks", "lips"]
PALETTE_ID = "owner-approved-muted-rose-20260912"
LIGHT_OPACITY = 0.55
IMAGE_AXES = 3
RGBA_CHANNELS = 4
# Shared material adjustments; each source retains its native texture and lighting.
LAB_ADJUSTMENTS = {
    "eyes": (-3.0, 0.0, 0.0),
    "cheeks": (0.0, 2.0, -0.5),
    "lips": (-5.0, 4.0, -1.0),
}


def native_pigment(
    source: np.ndarray, support: np.ndarray, slot: Slot,
    *, excluded: np.ndarray | None = None,
) -> np.ndarray:
    """Return an RGBA pigment layer on the unchanged native source canvas."""
    if source.dtype != np.uint8 or source.ndim != IMAGE_AXES or source.shape[2] not in (3, RGBA_CHANNELS):
        raise ValueError("A native RGB or RGBA uint8 source is required.")
    if support.dtype != np.uint8 or support.shape != source.shape[:2]:
        raise ValueError("Support must be a native uint8 alpha plane.")
    if slot not in LAB_ADJUSTMENTS:
        raise ValueError("Unknown cosmetic slot.")
    if excluded is not None and excluded.shape != support.shape:
        raise ValueError("Exclusion must match the native canvas.")
    alpha = support.copy()
    if source.shape[2] == RGBA_CHANNELS:
        alpha[source[:, :, 3] == 0] = 0
    if excluded is not None:
        alpha[excluded != 0] = 0
    rgb = source[:, :, :3].astype(np.float32) / 255
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)
    lab += np.array(LAB_ADJUSTMENTS[slot], dtype=np.float32)
    color = np.rint(np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB), 0, 1) * 255).astype(np.uint8)
    result = np.dstack((color, alpha))
    result[alpha == 0] = 0
    return result
