"""Uniform display placement for the 24-view size comparison sheet.

The pose-atlas views do not share a sole line or a visible height: each view
draws the figure at its own position on a 1024x1536 canvas. Comparing them, or
comparing a bare view with its dressed counterpart, is only meaningful when the
display transform is explicit.

The standard comes from the formal ``yaw+000`` native PNG: the alpha-visible
bounding box height and the sole row. Two placement modes are supported.

``sole_aligned``
    One global uniform scale for the whole sheet (``standard_height`` divided by
    the reference view's visible height) plus a per-view translation that puts
    the sole on the common baseline row. Visible height differences between
    views stay visible, so the sheet never hides them.

``height_normalised``
    Each view gets its own uniform scale so that every visible height equals the
    standard height. This unifies displayed size; it does not claim the
    anatomical heights are equal.

Both modes are strictly uniform: one scale for x and y, so face and neck
proportions are never stretched. Images are resized in premultiplied space so
semi-transparent garment edges do not bleed.
"""

from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass

lazy import numpy as np

SCHEMA = "mohan.pose-atlas-visible-scale-placement.v1"
SOLE_ALIGNED = "sole_aligned"
HEIGHT_NORMALISED = "height_normalised"
MODES = (SOLE_ALIGNED, HEIGHT_NORMALISED)
DEFAULT_ALPHA_THRESHOLD = 128
ALPHA_THRESHOLD = DEFAULT_ALPHA_THRESHOLD
MIN_SCALE = 0.1
MAX_SCALE = 10.0
RGBA_CHANNELS = 4
RGB_CHANNELS = 3
MASK_DIMENSIONS = 2


class PlacementError(ValueError):
    """The alpha evidence cannot support a placement."""


@dataclass(frozen=True, slots=True)
class VisibleBounds:
    top: int
    bottom: int
    left: int
    right: int

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def centre_x(self) -> float:
        return (self.left + self.right) / 2.0

    def to_dict(self) -> dict[str, int]:
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
            "height": self.height,
            "width": self.width,
        }


@dataclass(frozen=True, slots=True)
class DisplayStandard:
    """The reference scale and sole line taken from the formal +000 native."""

    width: int
    height: int
    reference_height: int
    baseline_row: int
    reference_view: str
    reference_sha256: str
    alpha_threshold: int = DEFAULT_ALPHA_THRESHOLD

    def to_dict(self) -> dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "reference_height": self.reference_height,
            "baseline_row": self.baseline_row,
            "reference_view": self.reference_view,
            "reference_sha256": self.reference_sha256,
            "alpha_threshold": self.alpha_threshold,
        }


@dataclass(frozen=True, slots=True)
class UniformPlacement:
    """One uniform scale plus a translation, applied after composition."""

    view_id: str
    mode: str
    scale: float
    offset_x: float
    offset_y: float
    visible_bounds: VisibleBounds
    canvas: tuple[int, int]

    @property
    def placed_height(self) -> float:
        return self.visible_bounds.height * self.scale

    @property
    def sole_row(self) -> float:
        return self.visible_bounds.bottom * self.scale + self.offset_y

    def to_dict(self) -> dict[str, object]:
        return {
            "view_id": self.view_id,
            "mode": self.mode,
            "scale": round(self.scale, 6),
            "offset_x": round(self.offset_x, 3),
            "offset_y": round(self.offset_y, 3),
            "placed_visible_height": round(self.placed_height, 3),
            "placed_sole_row": round(self.sole_row, 3),
            "uniform_scale_x_equals_y": True,
            "visible_bounds": self.visible_bounds.to_dict(),
        }


def visible_bounds(
    alpha: np.ndarray,
) -> VisibleBounds:
    """Bounding box of the alpha-visible subject, or a fail-closed error.

    One threshold (``ALPHA_THRESHOLD``) governs the reference standard, every
    input frame, and every placed check, so a comparison never mixes visibility
    definitions.
    """

    if alpha.ndim != MASK_DIMENSIONS:
        raise PlacementError("alpha must be a two-dimensional mask")
    mask = alpha >= ALPHA_THRESHOLD
    rows = np.flatnonzero(mask.any(axis=1))
    if not len(rows):
        raise PlacementError("empty_alpha_above_threshold")
    cols = np.flatnonzero(mask.any(axis=0))
    top, bottom = int(rows[0]), int(rows[-1])
    if (top == 0 or bottom == alpha.shape[0] - 1
            or cols[0] == 0 or cols[-1] == alpha.shape[1] - 1):
        raise PlacementError("visible_subject_touches_canvas_edge")
    return VisibleBounds(top, bottom, int(cols[0]), int(cols[-1]))


def subthreshold_report(alpha: np.ndarray) -> dict[str, object]:
    """Pixels between 0 and the threshold, reported instead of ignored.

    A thin alpha tail below the display threshold is not part of the measured
    subject. It is reported with its own bounding box so a reviewer can see
    whether it was separated from the body and whether it reached an edge.
    """

    if alpha.ndim != MASK_DIMENSIONS:
        raise PlacementError("alpha must be a two-dimensional mask")
    tail = (alpha > 0) & (alpha < ALPHA_THRESHOLD)
    rows = np.flatnonzero(tail.any(axis=1))
    if not len(rows):
        return {"tail_pixels": 0, "tail_bbox": None, "tail_touches_edge": False}
    cols = np.flatnonzero(tail.any(axis=0))
    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(cols[0]), int(cols[-1])
    return {
        "tail_pixels": int(tail.sum()),
        "tail_bbox": {"top": top, "bottom": bottom, "left": left, "right": right},
        "tail_touches_edge": bool(
            top == 0 or bottom == alpha.shape[0] - 1
            or left == 0 or right == alpha.shape[1] - 1
        ),
    }


def crop_report(
    placed: UniformPlacement,
    originals: dict[str, np.ndarray],
    normalised: dict[str, np.ndarray],
) -> dict[str, object]:
    """Fail-closed record of whether any visible pixel was lost.

    The visible subject (alpha above the threshold) must stay strictly inside
    every canvas edge in both the original composition and the placed result.
    """

    entry: dict[str, object] = {"visible_cropped": False, "details": {}}
    for kind, frames in (("original", originals), ("normalised", normalised)):
        for state, frame in frames.items():
            alpha = frame[..., 3]
            mask = alpha >= ALPHA_THRESHOLD
            rows = np.flatnonzero(mask.any(axis=1))
            cols = np.flatnonzero(mask.any(axis=0))
            detail = {
                "tail": subthreshold_report(alpha),
                "visible_pixels": int(mask.sum()),
            }
            if len(rows) and len(cols):
                top, bottom = int(rows[0]), int(rows[-1])
                left, right = int(cols[0]), int(cols[-1])
                detail["visible_bbox"] = {
                    "top": top, "bottom": bottom, "left": left, "right": right,
                }
                cropped = (
                    top == 0 or bottom == alpha.shape[0] - 1
                    or left == 0 or right == alpha.shape[1] - 1
                )
                if cropped:
                    entry["visible_cropped"] = True
            entry["details"][f"{kind}_{state}"] = detail
    entry["placement"] = placed.to_dict()
    return entry


def _mask_bounds(alpha: np.ndarray) -> VisibleBounds | None:
    mask = alpha >= ALPHA_THRESHOLD
    rows = np.flatnonzero(mask.any(axis=1))
    if not len(rows):
        return None
    cols = np.flatnonzero(mask.any(axis=0))
    return VisibleBounds(int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1]))


def refine_placement(
    source: np.ndarray,
    placement_in: UniformPlacement,
    standard: DisplayStandard,
    *,
    tolerance_px: float = 1.0,
    max_passes: int = 4,
) -> UniformPlacement:
    """Correct the translation so the placed contour lands on the standard.

    Bilinear resampling rounds the thresholded alpha contour by up to a pixel, so
    the affine is solved once from the source bounds and then its translation is
    corrected against the resampled result. The scale never changes, so this
    stays one uniform affine per view.
    """

    current = placement_in
    for _ in range(max_passes):
        placed = place_image(source, current)
        bounds = _mask_bounds(placed[..., 3])
        if bounds is None:
            raise PlacementError("placed_subject_below_threshold")
        dy = standard.baseline_row - bounds.bottom
        dx = standard.width / 2.0 - bounds.centre_x
        if abs(dy) <= tolerance_px and abs(dx) <= tolerance_px:
            break
        current = UniformPlacement(
            view_id=current.view_id,
            mode=current.mode,
            scale=current.scale,
            offset_x=current.offset_x + dx,
            offset_y=current.offset_y + dy,
            visible_bounds=current.visible_bounds,
            canvas=current.canvas,
        )
    return current


def display_standard(
    reference_alpha: np.ndarray,
    *,
    view_id: str,
    sha256: str,
) -> DisplayStandard:
    """Pin the reference visible height and the common sole row."""

    bounds = visible_bounds(reference_alpha)
    return DisplayStandard(
        width=reference_alpha.shape[1],
        height=reference_alpha.shape[0],
        reference_height=bounds.height,
        baseline_row=bounds.bottom,
        reference_view=view_id,
        reference_sha256=sha256,
        alpha_threshold=ALPHA_THRESHOLD,
    )


def compute_placement(
    bounds: VisibleBounds,
    standard: DisplayStandard,
    *,
    view_id: str,
    mode: str = SOLE_ALIGNED,
) -> UniformPlacement:
    """One uniform scale and one translation for the whole view."""

    if mode not in MODES:
        raise PlacementError(f"unsupported placement mode: {mode}")
    if standard.reference_height <= 0 or bounds.height <= 0:
        raise PlacementError("degenerate_visible_height")
    # SOLE_ALIGNED keeps the reference magnification (1.0) for every view and only
    # translates it, so genuinely shorter views stay visually shorter. Only
    # HEIGHT_NORMALISED rescales each view to the reference height.
    scale = (
        standard.reference_height / bounds.height if mode == HEIGHT_NORMALISED else 1.0
    )
    if not MIN_SCALE <= scale <= MAX_SCALE or not math.isfinite(scale):
        raise PlacementError(f"scale_out_of_range:{scale}")
    offset_x = standard.width / 2.0 - bounds.centre_x * scale
    offset_y = standard.baseline_row - bounds.bottom * scale
    return UniformPlacement(
        view_id=view_id,
        mode=mode,
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        visible_bounds=bounds,
        canvas=(standard.width, standard.height),
    )


def _premultiply(image: np.ndarray) -> np.ndarray:
    if image.ndim != MASK_DIMENSIONS + 1 or image.shape[2] != RGBA_CHANNELS:
        raise PlacementError("image must be RGBA")
    values = image.astype(np.float64, copy=True)
    alpha = values[..., 3:4] / 255.0
    values[..., :RGB_CHANNELS] *= alpha
    return values


def resize_premultiplied(image: np.ndarray, scale: float) -> np.ndarray:
    """Resize RGBA in premultiplied space so edges keep their colour."""

    if scale <= 0.0 or not math.isfinite(scale):
        raise PlacementError(f"invalid_scale:{scale}")
    source = _premultiply(image)
    height = max(1, round(image.shape[0] * scale))
    width = max(1, round(image.shape[1] * scale))
    rows = np.clip((np.arange(height) + 0.5) / scale - 0.5, 0, image.shape[0] - 1)
    cols = np.clip((np.arange(width) + 0.5) / scale - 0.5, 0, image.shape[1] - 1)
    row_index = np.floor(rows).astype(int)
    col_index = np.floor(cols).astype(int)
    row_next = np.clip(row_index + 1, 0, image.shape[0] - 1)
    col_next = np.clip(col_index + 1, 0, image.shape[1] - 1)
    row_weight = (rows - row_index)[:, None, None]
    col_weight = (cols - col_index)[None, :, None]
    top = source[row_index][:, col_index] * (1 - col_weight) + (
        source[row_index][:, col_next] * col_weight
    )
    bottom = source[row_next][:, col_index] * (1 - col_weight) + (
        source[row_next][:, col_next] * col_weight
    )
    scaled = top * (1 - row_weight) + bottom * row_weight
    alpha = np.clip(scaled[..., 3:4], 0.0, 255.0)
    colour = np.divide(
        scaled[..., :RGB_CHANNELS],
        alpha / 255.0,
        out=np.zeros_like(scaled[..., :RGB_CHANNELS]),
        where=alpha > 0,
    )
    result = np.concatenate([np.clip(colour, 0, 255), alpha], axis=2)
    return np.clip(np.round(result), 0, 255).astype(np.uint8)


def _shift(source: np.ndarray, dy: int, dx: int, shape: tuple[int, int]) -> np.ndarray:
    target = np.zeros((shape[0], shape[1], RGBA_CHANNELS), dtype=np.float64)
    height, width = source.shape[0], source.shape[1]
    y0, x0 = max(0, dy), max(0, dx)
    y1, x1 = min(shape[0], dy + height), min(shape[1], dx + width)
    # Check before clipping: a disconnected island can disappear completely
    # without leaving any pixels on the output edge. Include faint alpha too.
    kept = np.zeros((height, width), dtype=bool)
    if y1 > y0 and x1 > x0:
        kept[y0 - dy:y1 - dy, x0 - dx:x1 - dx] = True
    if np.any((source[..., 3] > 0) & ~kept):
        raise PlacementError("placement_would_crop_nonzero_alpha")
    if y1 <= y0 or x1 <= x0:
        return target
    target[y0:y1, x0:x1] = source[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    return target


def place_image(image: np.ndarray, placement: UniformPlacement) -> np.ndarray:
    """Apply one uniform scale and translation onto the display canvas."""

    scaled = _premultiply(resize_premultiplied(image, placement.scale))
    dy = round(placement.offset_y)
    dx = round(placement.offset_x)
    placed = _shift(scaled, dy, dx, (placement.canvas[1], placement.canvas[0]))
    alpha = placed[..., 3:4]
    colour = np.divide(
        placed[..., :RGB_CHANNELS],
        alpha / 255.0,
        out=np.zeros_like(placed[..., :RGB_CHANNELS]),
        where=alpha > 0,
    )
    result = np.concatenate([np.clip(colour, 0, 255), np.clip(alpha, 0, 255)], axis=2)
    return np.clip(np.round(result), 0, 255).astype(np.uint8)


def placed_bounds_delta(
    placement: UniformPlacement, placed_alpha: np.ndarray
) -> dict[str, float]:
    """Where the placed image actually lands versus the transform's intention.

    For the frame the transform was derived from, both deltas are zero. For a
    dressed or expression frame the same transform is still applied exactly, so a
    non-zero delta is the composition's own extent beyond the reference
    silhouette (for example a robe hem below the bare sole line), not a
    transform error.
    """

    mask = placed_alpha >= ALPHA_THRESHOLD
    rows = np.flatnonzero(mask.any(axis=1))
    if not len(rows):
        raise PlacementError("placed_subject_below_threshold")
    bounds = VisibleBounds(
        int(rows[0]), int(rows[-1]),
        int(np.flatnonzero(mask.any(axis=0))[0]),
        int(np.flatnonzero(mask.any(axis=0))[-1]),
    )
    return {
        "height_delta_px": float(bounds.height - placement.placed_height),
        "sole_delta_px": float(bounds.bottom - placement.sole_row),
        "placed_height_px": float(bounds.height),
        "placed_sole_row": float(bounds.bottom),
    }


def transform_is_exact(
    placement: UniformPlacement,
    source_alpha: np.ndarray,
    placed_alpha: np.ndarray,
    *,
    tolerance_px: float = 1.0,
    lateral_tolerance_px: float = 2.0,
) -> dict[str, object]:
    """Whether the placed subject is exactly the source subject under the affine.

    Compare each contour edge against the actual pixel-centred resampling and
    integer translation used by place_image. Top and bottom can round in opposite
    directions, so their span is diagnostic, not a second single-edge error.
    The preview separately requires the bare subject's final height and baseline
    to match the display standard within one pixel.
    """

    source = visible_bounds(source_alpha)
    placed = visible_bounds(placed_alpha)
    centre_offset = (placement.scale - 1.0) / 2.0
    applied_x = round(placement.offset_x) + centre_offset
    applied_y = round(placement.offset_y) + centre_offset
    expected_sole = source.bottom * placement.scale + applied_y
    expected_left = source.left * placement.scale + applied_x
    expected_right = source.right * placement.scale + applied_x
    deltas = {
        "height": float(placed.height - source.height * placement.scale),
        "sole": float(placed.bottom - expected_sole),
        "left": float(placed.left - expected_left),
        "right": float(placed.right - expected_right),
        "top_contour": float(placed.top - (source.top * placement.scale + applied_y)),
    }
    vertical_exact = (
        abs(deltas["top_contour"]) <= tolerance_px
        and abs(deltas["sole"]) <= tolerance_px
    )
    horizontal_exact = (
        abs(deltas["left"]) <= lateral_tolerance_px
        and abs(deltas["right"]) <= lateral_tolerance_px
    )
    return {
        "exact": vertical_exact and horizontal_exact,
        "vertical_exact": vertical_exact,
        "horizontal_exact": horizontal_exact,
        "edge_deltas_px": {key: round(value, 3) for key, value in deltas.items()},
        "tolerance_px": tolerance_px,
        "lateral_tolerance_px": lateral_tolerance_px,
    }
