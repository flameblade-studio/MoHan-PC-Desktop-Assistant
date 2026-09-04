"""Shared owner-defined small-component cleanup for official appearance layers."""

from __future__ import annotations

lazy import cv2
lazy import numpy as np
lazy from typing import Final

lazy from .constants import (
    SMALL_COMPONENT_ANCHOR_MIN_AREA,
    SMALL_COMPONENT_LINK_DISTANCE,
    SMALL_COMPONENT_MAX_AREA,
)

HEAD_SPECK_ROI: Final = (300, 100, 1000, 520)
FULL_BODY_SPECK_ROI: Final = (250, 30, 800, 420)
OWNER_JUDGE_CANVAS_SHAPE: Final = (1254, 1254)
MIN_PROCESSING_WIDTH: Final = 800
MIN_PROCESSING_HEIGHT: Final = 420
ALPHA_MASK_DIMENSIONS: Final = 2
# This is the owner-provided sealed-pack criterion.  Keep it separate from the
# older transitive-chain cleanup below: the latter is useful diagnostics, but
# it is not allowed to decide the release gate.
OWNER_ALPHA_THRESHOLD: Final = 30
OWNER_SMALL_COMPONENT_MAX_AREA: Final = 12
OWNER_LARGE_COMPONENT_MIN_AREA: Final = 60
OWNER_DILATION_KERNEL_SIZE: Final = 7


def speck_roi_for_shape(shape: tuple[int, int]) -> tuple[int, int, int, int]:
    """Return the owner speck ROI for a half-body or full-body canvas."""

    height, width = shape
    if width < MIN_PROCESSING_WIDTH or height < MIN_PROCESSING_HEIGHT:
        return (0, 0, width, height)
    if height > width:
        return FULL_BODY_SPECK_ROI
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


def owner_judge_metrics(
    alpha: np.ndarray,
    *,
    roi: tuple[int, int, int, int] | None = None,
) -> dict[str, int | list[int]]:
    """Apply the supplied sealed-pack speck rule to one alpha mask.

    The owner rule intentionally has no transitive chain promotion.  It counts
    all alpha 1--30 pixels over the complete stored asset, then measures small
    alpha>30 components inside the selected ROI after one 7x7 dilation of
    components larger than 60 pixels.
    """

    if alpha.ndim != ALPHA_MASK_DIMENSIONS:
        raise ValueError("owner speck metrics expects a two-dimensional alpha mask")
    selected_roi = speck_roi_for_shape(alpha.shape) if roi is None else roi
    x0, y0, x1, y1, crop = _bounded_roi(alpha, selected_roi)
    visible = (crop > OWNER_ALPHA_THRESHOLD).astype(np.uint8)
    isolated_count = 0
    if crop.size and visible.any():
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            visible, connectivity=8
        )
        large = np.zeros_like(visible)
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] > OWNER_LARGE_COMPONENT_MIN_AREA:
                large[labels == label] = 1
        far = (
            cv2.dilate(
                large,
                np.ones(
                    (OWNER_DILATION_KERNEL_SIZE, OWNER_DILATION_KERNEL_SIZE),
                    dtype=np.uint8,
                ),
            )
            == 0
        )
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] > OWNER_SMALL_COMPONENT_MAX_AREA:
                continue
            ys, xs = np.nonzero(labels == label)
            if far[ys, xs].all():
                isolated_count += 1
    return {
        "roi_xyxy": [x0, y0, x1, y1],
        "alpha_1_30": int(
            ((alpha > 0) & (alpha <= OWNER_ALPHA_THRESHOLD)).sum()
        ),
        "isolated_count": isolated_count,
        "nontransparent": int((alpha > 0).sum()),
        "alpha_threshold": OWNER_ALPHA_THRESHOLD,
        "small_component_max_area": OWNER_SMALL_COMPONENT_MAX_AREA,
        "large_component_min_area": OWNER_LARGE_COMPONENT_MIN_AREA,
        "dilation_kernel_size": OWNER_DILATION_KERNEL_SIZE,
    }


def remove_owner_specks(  # noqa: PLR0914 - mirrors the supplied judge step by step
    alpha: np.ndarray,
    *,
    roi: tuple[int, int, int, int] | None = None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Clear the owner rule's low-alpha residue and isolated components."""

    before = owner_judge_metrics(alpha, roi=roi)
    cleaned = alpha.copy()
    low_alpha = (cleaned > 0) & (cleaned <= OWNER_ALPHA_THRESHOLD)
    low_alpha_removed = int(low_alpha.sum())
    cleaned[low_alpha] = 0

    selected_roi = speck_roi_for_shape(cleaned.shape) if roi is None else roi
    x0, y0, x1, y1, crop = _bounded_roi(cleaned, selected_roi)
    visible = (crop > OWNER_ALPHA_THRESHOLD).astype(np.uint8)
    isolated_components_removed = 0
    isolated_pixels_removed = 0
    if crop.size and visible.any():
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            visible, connectivity=8
        )
        large = np.zeros_like(visible)
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] > OWNER_LARGE_COMPONENT_MIN_AREA:
                large[labels == label] = 1
        far = (
            cv2.dilate(
                large,
                np.ones(
                    (OWNER_DILATION_KERNEL_SIZE, OWNER_DILATION_KERNEL_SIZE),
                    dtype=np.uint8,
                ),
            )
            == 0
        )
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] > OWNER_SMALL_COMPONENT_MAX_AREA:
                continue
            ys, xs = np.nonzero(labels == label)
            if not far[ys, xs].all():
                continue
            cleaned[y0 + ys, x0 + xs] = 0
            isolated_components_removed += 1
            isolated_pixels_removed += len(xs)

    after = owner_judge_metrics(cleaned, roi=roi)
    return cleaned, {
        "owner_alpha_1_30_removed": low_alpha_removed,
        "owner_isolated_components_removed": isolated_components_removed,
        "owner_isolated_pixels_removed": isolated_pixels_removed,
        "owner_isolated_count_before": int(before["isolated_count"]),
        "owner_isolated_count_after": int(after["isolated_count"]),
    }


def owner_judge_metrics_for_stored_layer(
    alpha: np.ndarray,
) -> dict[str, int | list[int]]:
    """Measure a layer using the sealed-pack judge's stored-image geometry."""

    height, width = alpha.shape
    if (height, width) == OWNER_JUDGE_CANVAS_SHAPE:
        judge_alpha = alpha
        roi = HEAD_SPECK_ROI
    elif (
        height <= OWNER_JUDGE_CANVAS_SHAPE[0]
        and width <= OWNER_JUDGE_CANVAS_SHAPE[1]
    ):
        judge_alpha = np.zeros(OWNER_JUDGE_CANVAS_SHAPE, dtype=alpha.dtype)
        judge_alpha[:height, :width] = alpha
        roi = HEAD_SPECK_ROI
    else:
        judge_alpha = alpha
        roi = speck_roi_for_shape(alpha.shape)
    return owner_judge_metrics(judge_alpha, roi=roi)


def remove_owner_specks_for_stored_layer(
    alpha: np.ndarray,
) -> tuple[np.ndarray, dict[str, int]]:
    """Clean a layer with the same canvas padding used by the sealed judge."""

    height, width = alpha.shape
    cropped = (
        (height, width) != OWNER_JUDGE_CANVAS_SHAPE
        and height <= OWNER_JUDGE_CANVAS_SHAPE[0]
        and width <= OWNER_JUDGE_CANVAS_SHAPE[1]
    )
    if cropped:
        judge_alpha = np.zeros(OWNER_JUDGE_CANVAS_SHAPE, dtype=alpha.dtype)
        judge_alpha[:height, :width] = alpha
        cleaned, metrics = remove_owner_specks(judge_alpha, roi=HEAD_SPECK_ROI)
        return cleaned[:height, :width], metrics
    return remove_owner_specks(alpha, roi=speck_roi_for_shape(alpha.shape))


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
    visible = (crop > 0).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if count <= 1:
        return None

    link_labels, link_stats = labels, stats
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
) -> tuple[np.ndarray, dict[str, int]]:
    """Remove legacy chain-unlinked small components from one alpha mask.

    Every nonzero-alpha component participates in the cleanup.  A component at
    or below 12 pixels is retained only when its pixels belong to the
    transitive N=9 graph grown from an area>60 anchor.  Components above the
    small-pixel ceiling are left untouched.  Removing a component always writes
    alpha zero; no historical pixel-count preservation is allowed to leave a
    residual pixel behind.
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
    cleaned = mask.copy()
    cleaned[y0:y1, x0:x1] = cleaned_crop
    return cleaned, {
        "small_components": int(small.sum()),
        "linked_small_components": int(small_linked.sum()),
        "removed_small_components": int(removed_visible.sum()),
        "removed_pixels": removed_pixels,
    }
