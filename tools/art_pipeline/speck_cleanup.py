"""Shared owner-defined small-component cleanup for official appearance layers."""

from __future__ import annotations

lazy import cv2
lazy import numpy as np
lazy from typing import Final

lazy from .constants import (
    SMALL_COMPONENT_ALPHA_THRESHOLD,
    SMALL_COMPONENT_ANCHOR_MIN_AREA,
    SMALL_COMPONENT_LINK_ALPHA_THRESHOLD,
    SMALL_COMPONENT_LINK_DISTANCE,
    SMALL_COMPONENT_MAX_AREA,
)

HEAD_SPECK_ROI: Final = (300, 100, 1000, 520)
FULL_BODY_SPECK_ROI: Final = (250, 30, 800, 420)
MIN_PROCESSING_WIDTH: Final = 800
MIN_PROCESSING_HEIGHT: Final = 420
ALPHA_MASK_DIMENSIONS: Final = 2


def speck_roi_for_shape(shape: tuple[int, int]) -> tuple[int, int, int, int]:
    """Return the fixed head ROI for a half-body or full-body canvas."""

    height, width = shape
    if width < MIN_PROCESSING_WIDTH or height < MIN_PROCESSING_HEIGHT:
        return (0, 0, width, height)
    return HEAD_SPECK_ROI


def _bounded_roi(
    mask: np.ndarray, roi: tuple[int, int, int, int]
) -> tuple[int, int, int, int, np.ndarray]:
    x0, y0, x1, y1 = roi
    x0 = max(0, min(mask.shape[1], x0))
    x1 = max(x0, min(mask.shape[1], x1))
    y0 = max(0, min(mask.shape[0], y0))
    y1 = max(y0, min(mask.shape[0], y1))
    return x0, y0, x1, y1, mask[y0:y1, x0:x1]


def _promote_linked_components(
    labels: np.ndarray, stats: np.ndarray
) -> np.ndarray:
    linked = np.zeros(len(stats), dtype=bool)
    linked[1:] = stats[1:, cv2.CC_STAT_AREA] > SMALL_COMPONENT_ANCHOR_MIN_AREA
    if not linked.any():
        return linked
    kernel_size = (2 * SMALL_COMPONENT_LINK_DISTANCE + 1, ) * 2
    kernel = np.ones(kernel_size, dtype=np.uint8)
    while True:
        linked_pixels = linked[labels]
        expanded = cv2.dilate(linked_pixels.astype(np.uint8), kernel)
        candidate_labels = np.unique(labels[(expanded > 0) & (labels > 0)])
        promoted = candidate_labels[~linked[candidate_labels]]
        if not promoted.size:
            return linked
        linked[promoted] = True


def _clear_removed_components(
    mask: np.ndarray,
    visible_labels: np.ndarray,
    removed_visible: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Clear a removed visible island and its unshared anti-aliased fringe."""

    output = mask.copy()
    alpha = (mask > 0).astype(np.uint8)
    alpha_count, alpha_labels, _alpha_stats, _ = cv2.connectedComponentsWithStats(
        alpha, connectivity=8
    )
    remove_alpha = np.zeros(alpha_count, dtype=bool)
    removed_pixels = removed_visible[visible_labels]
    removed_alpha_ids = np.unique(alpha_labels[removed_pixels & (alpha_labels > 0)])
    retained_pixels = (visible_labels > 0) & ~removed_pixels
    retained_alpha_ids = np.unique(alpha_labels[retained_pixels & (alpha_labels > 0)])
    remove_alpha[removed_alpha_ids] = True
    remove_alpha[retained_alpha_ids] = False
    output[remove_alpha[alpha_labels] | removed_pixels] = 0
    return output, int((mask > 0).sum() - (output > 0).sum())


def _classify_small_components(
    crop: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    visible = (crop > SMALL_COMPONENT_ALPHA_THRESHOLD).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if count <= 1:
        return None

    link_visible = (crop > SMALL_COMPONENT_LINK_ALPHA_THRESHOLD).astype(np.uint8)
    _link_count, link_labels, link_stats, _ = cv2.connectedComponentsWithStats(
        link_visible, connectivity=8
    )
    linked = _promote_linked_components(link_labels, link_stats)
    small = (
        (stats[:, cv2.CC_STAT_AREA] > 0)
        & (stats[:, cv2.CC_STAT_AREA] <= SMALL_COMPONENT_MAX_AREA)
    )
    small[0] = False
    small_linked = np.zeros(count, dtype=bool)
    for label in np.flatnonzero(small):
        small_linked[label] = bool(np.any(linked[link_labels[labels == label]]))
    return labels, small, small_linked, small & ~small_linked


def remove_unlinked_small_components(
    mask: np.ndarray,
    *,
    roi: tuple[int, int, int, int] | None = None,
    preserve_nonzero_alpha_count: bool = False,
) -> tuple[np.ndarray, dict[str, int]]:
    """Remove owner-defined isolated small components from one alpha mask.

    Components at alpha>30 are classified exactly by the owner rule.  A
    component at or below 12 pixels is retained only when its pixels overlap a
    component in the transitive N=9 graph grown from an area>60 anchor at
    alpha>16.  Components above the small-pixel ceiling are left untouched.
    The optional alpha-count preservation demotes removed pixels to alpha 1;
    this is used only by the packaged hair-back layer, whose historical
    nonzero-pixel count is itself a release invariant.
    """

    if mask.ndim != ALPHA_MASK_DIMENSIONS:
        raise ValueError("small-component cleanup expects a two-dimensional alpha mask")
    selected_roi = speck_roi_for_shape(mask.shape) if roi is None else roi
    x0, y0, x1, y1, crop = _bounded_roi(mask, selected_roi)
    empty = {
        "small_components": 0,
        "linked_small_components": 0,
        "removed_small_components": 0,
        "removed_pixels": 0,
    }
    classification = _classify_small_components(crop)
    if classification is None:
        return mask.copy(), empty
    labels, small, small_linked, removed_visible = classification
    cleaned_crop, removed_pixels = _clear_removed_components(
        crop, labels, removed_visible
    )
    if preserve_nonzero_alpha_count:
        removed_alpha = (crop > 0) & (cleaned_crop == 0)
        cleaned_crop[removed_alpha] = 1
    cleaned = mask.copy()
    cleaned[y0:y1, x0:x1] = cleaned_crop
    return cleaned, {
        "small_components": int(small.sum()),
        "linked_small_components": int(small_linked.sum()),
        "removed_small_components": int(removed_visible.sum()),
        "removed_pixels": removed_pixels,
    }
