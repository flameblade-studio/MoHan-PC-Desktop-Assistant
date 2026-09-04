"""以差分、去溢色、配準與安全區抽出半身分層素材。"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .constants import (
    BARE_SKIN_GREEN_BLUE_MARGIN,
    BARE_SKIN_RED_GREEN_MARGIN,
    CANVAS_SIZE,
    BARE_SKIN_RED_MIN,
    RECTANGLE_FIELDS,
    DESPILL_DARK_GREEN_MAX,
    DESPILL_DARK_SPILL_THRESHOLD,
    DESPILL_EDGE_SPILL_THRESHOLD,
    DESPILL_INNER_EROSION_KERNEL,
    DESPILL_REDUCTION_FACTOR,
    DIFF_ALPHA_THRESHOLD,
    DIFF_FEATHER_PIXELS,
    DIFF_SOFT_BLUR_SIGMA,
    HEAD_FALLBACK_TOP_RATIO,
    HEAD_REGION_BOTTOM_FACE_FACTOR,
    HEAD_REGION_FACE_CUT_BOTTOM_FACTOR,
    HEAD_REGION_FACE_CUT_LEFT_FACTOR,
    HEAD_REGION_FACE_CUT_TOP_FACTOR,
    HEAD_REGION_LEFT_FACE_FACTOR,
    HEAD_REGION_RIGHT_FACE_FACTOR,
    HEADWEAR_DARK_PIXEL_MAX,
    HEADWEAR_COMPONENT_ALPHA_THRESHOLD,
    HEADWEAR_COMPONENT_LINK_DISTANCE,
    HEADWEAR_CHAIN_ANCHOR_MIN_AREA,
    HEADWEAR_CHAIN_BRIDGE_ALPHA,
    HEADWEAR_CHAIN_BRIDGE_DISTANCE,
    HEADWEAR_SKIN_GREEN_BLUE_MARGIN,
    HEADWEAR_SKIN_RED_GREEN_MARGIN,
    HEADWEAR_SKIN_RED_MIN,
    HEADWEAR_TOP_RESIDUE_CHANNEL_SPREAD_MAX,
    HEADWEAR_TOP_RESIDUE_DILATION_KERNEL,
    HEADWEAR_TOP_RESIDUE_MAX_AREA,
    HEADWEAR_TOP_RESIDUE_MIN_AREA,
    HEADWEAR_TOP_RESIDUE_PIXEL_MAX,
    HEADWEAR_TOP_RESIDUE_ROI,
    HAIR_BODY_OPEN_KERNEL,
    HAIR_FINE_REGION_BOTTOM_RATIO,
    HAIR_FRONT_OPEN_KERNEL,
    HAIR_SPILL_BRIGHTNESS_MAX,
    HAIR_SPILL_BRIGHTNESS_MIN,
    HAIR_SPILL_RED_BLUE_MARGIN,
    HALF_SILHOUETTES,
    MAKEUP_CHEEK_CENTER_X_FACTOR,
    MAKEUP_CHEEK_CENTER_Y_FACTOR,
    MAKEUP_CHEEK_RADIUS_X_FACTOR,
    MAKEUP_CHEEK_RADIUS_Y_FACTOR,
    MAKEUP_EYE_CENTER_Y_FACTOR,
    MAKEUP_EYE_RADIUS_X_FACTOR,
    MAKEUP_EYE_RADIUS_Y_FACTOR,
    MAKEUP_LIP_RADIUS_X_FACTOR,
    MAKEUP_LIP_RADIUS_Y_FACTOR,
    MAKEUP_SLOT_PRIORITY,
    REGISTER_HEAD_ROI_BOTTOM_RATIO,
    REGISTER_IGNORE_SHIFT_PIXELS,
    REGISTER_LOWER_ROI_TOP_RATIO,
    REGISTER_MAX_SHIFT_PIXELS,
    REGISTER_MIN_ALPHA_PIXELS,
    RECONSTRUCTION_ERROR_PIXEL_THRESHOLD,
    SMALL_COMPONENT_ALPHA_THRESHOLD,
    SHOE_BLUE_GREEN_MARGIN,
    SHOE_BLUE_RED_MARGIN,
    SHOE_BARE_ALPHA_MIN,
    SHOE_COVERED_ALPHA_MIN,
    SHOE_FOOT_BAND_TOP_RATIO,
    SHOE_FOOT_ZONE_TOP_RATIO,
    SHOE_NEAREST_MAX_DISTANCE,
    SHOE_UPPER_EXCLUSION_RATIO,
    SHEET_BACKGROUND_BGR,
    SHEET_TILE_GAP,
    SHEET_TILE_HEIGHT,
    SHEET_TILE_WIDTH,
    STEP_PARAMETERS,
    STEPS,
    DiffParameters,
)
lazy from .image_ops import (
    composite_over,
    key_file,
    resize_rgba,
    save_png,
    transparent_rgb_zero,
    warp_rgba,
)
lazy from .reference_layers import extract_reference_layers
lazy from .speck_cleanup import (
    remove_owner_specks,
    remove_unlinked_small_components,
    speck_roi_for_shape,
)
lazy from .vision import face_box, face_landmarks


def despill(image: np.ndarray) -> np.ndarray:
    """只在剪影邊緣與暗色洋紅滲色處壓低 R/B，並清空透明 RGB。"""

    output = transparent_rgb_zero(image)
    alpha = output[:, :, 3]
    solid = (alpha > 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (DESPILL_INNER_EROSION_KERNEL, DESPILL_INNER_EROSION_KERNEL),
    )
    inner = cv2.erode(solid, kernel)
    edge = (solid == 1) & (inner == 0)
    blue = output[:, :, 0].astype(np.int16)
    green = output[:, :, 1].astype(np.int16)
    red = output[:, :, 2].astype(np.int16)
    spill = np.minimum(red, blue) - green
    dark_tint = (green < DESPILL_DARK_GREEN_MAX) & (
        spill > DESPILL_DARK_SPILL_THRESHOLD
    )
    fix = (edge & (spill > DESPILL_EDGE_SPILL_THRESHOLD)) | (dark_tint & (solid == 1))
    reduction = (spill[fix] * DESPILL_REDUCTION_FACTOR).astype(np.int16)
    red[fix] -= reduction
    blue[fix] -= reduction
    output[:, :, 0] = np.clip(blue, 0, 255).astype(np.uint8)
    output[:, :, 2] = np.clip(red, 0, 255).astype(np.uint8)
    return transparent_rgb_zero(output)


def key_and_despill(path: Path) -> np.ndarray:
    return despill(key_file(path))


def _diff_mask_with_parameters(
    prev: np.ndarray,
    cur: np.ndarray,
    parameters: DiffParameters,
) -> np.ndarray:
    rgb = np.abs(prev[:, :, :3].astype(np.int16) - cur[:, :, :3].astype(np.int16)).max(
        axis=2
    )
    alpha = np.abs(prev[:, :, 3].astype(np.int16) - cur[:, :, 3].astype(np.int16))
    raw = ((rgb > parameters.rgb_threshold) | (alpha > DIFF_ALPHA_THRESHOLD)).astype(
        np.uint8
    )
    cleaned = raw
    if parameters.open_kernel:
        cleaned = cv2.morphologyEx(
            cleaned,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (parameters.open_kernel, parameters.open_kernel),
            ),
        )
    if parameters.close_kernel:
        cleaned = cv2.morphologyEx(
            cleaned,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (parameters.close_kernel, parameters.close_kernel),
            ),
        )
    cleaned &= (cur[:, :, 3] > 0).astype(np.uint8)
    if parameters.soft_alpha_span:
        graded = (
            np.clip(rgb.astype(np.float32) / parameters.soft_alpha_span, 0.0, 1.0)
            * cleaned
        )
        graded = cv2.GaussianBlur(graded, (0, 0), DIFF_SOFT_BLUR_SIGMA)
        return (np.clip(graded, 0.0, 1.0) * 255).astype(np.uint8)
    distance = cv2.distanceTransform(cleaned, cv2.DIST_L2, 3)
    return (np.clip(distance / DIFF_FEATHER_PIXELS, 0.0, 1.0) * 255).astype(np.uint8)


def diff_mask(prev: np.ndarray, cur: np.ndarray, step: str) -> np.ndarray:
    """產生一個步驟的軟 alpha 差異遮罩。"""

    try:
        parameters = STEP_PARAMETERS[step]
    except KeyError as error:
        raise ValueError(f"未知抽層步驟：{step}") from error
    return _diff_mask_with_parameters(prev, cur, parameters)
def makeup_region(image: np.ndarray, model_path: Path) -> np.ndarray:
    """由 YuNet 五點建立 eyes/cheeks/lips 共用的妝容安全區。"""

    height, width = image.shape[:2]
    try:
        points, _score = face_landmarks(image, model_path)
    except ValueError:
        return np.zeros((height, width), np.uint8)
    eye_left, eye_right, _nose, mouth_left, mouth_right = points
    distance = float(np.hypot(*(eye_right - eye_left)))
    region = np.zeros((height, width), np.uint8)
    for eye in (eye_left, eye_right):
        cv2.ellipse(
            region,
            (int(eye[0]), int(eye[1] + MAKEUP_EYE_CENTER_Y_FACTOR * distance)),
            (
                int(MAKEUP_EYE_RADIUS_X_FACTOR * distance),
                int(MAKEUP_EYE_RADIUS_Y_FACTOR * distance),
            ),
            0,
            0,
            360,
            1,
            -1,
        )
    for eye, sign in ((eye_left, -1), (eye_right, 1)):
        cv2.ellipse(
            region,
            (
                int(eye[0] + sign * MAKEUP_CHEEK_CENTER_X_FACTOR * distance),
                int(eye[1] + MAKEUP_CHEEK_CENTER_Y_FACTOR * distance),
            ),
            (
                int(MAKEUP_CHEEK_RADIUS_X_FACTOR * distance),
                int(MAKEUP_CHEEK_RADIUS_Y_FACTOR * distance),
            ),
            0,
            0,
            360,
            1,
            -1,
        )
    mouth_center = (mouth_left + mouth_right) / 2.0
    cv2.ellipse(
        region,
        (int(mouth_center[0]), int(mouth_center[1])),
        (
            int(MAKEUP_LIP_RADIUS_X_FACTOR * distance),
            int(MAKEUP_LIP_RADIUS_Y_FACTOR * distance),
        ),
        0,
        0,
        360,
        1,
        -1,
    )
    return region


def register(
    prev: np.ndarray, cur: np.ndarray, step: str
) -> tuple[np.ndarray, tuple[float, float]]:
    height = prev.shape[0]
    if step == "L2_garment":
        rows = slice(0, int(height * REGISTER_HEAD_ROI_BOTTOM_RATIO))
    elif step in ("L3_hair", "L4_headwear"):
        rows = slice(int(height * REGISTER_LOWER_ROI_TOP_RATIO), height)
    else:
        rows = slice(0, height)
    previous_alpha = prev[rows, :, 3].astype(np.float32) / 255.0
    current_alpha = cur[rows, :, 3].astype(np.float32) / 255.0
    if (
        previous_alpha.sum() < REGISTER_MIN_ALPHA_PIXELS
        or current_alpha.sum() < REGISTER_MIN_ALPHA_PIXELS
    ):
        return cur, (0.0, 0.0)
    (dx, dy), _response = cv2.phaseCorrelate(previous_alpha, current_alpha)
    if (
        abs(dx) < REGISTER_IGNORE_SHIFT_PIXELS
        and abs(dy) < REGISTER_IGNORE_SHIFT_PIXELS
    ):
        return cur, (0.0, 0.0)
    if abs(dx) > REGISTER_MAX_SHIFT_PIXELS or abs(dy) > REGISTER_MAX_SHIFT_PIXELS:
        return cur, (float(dx), float(dy))
    matrix = np.array([[1, 0, -dx], [0, 1, -dy]], dtype=np.float32)
    return warp_rgba(cur, matrix, (cur.shape[1], cur.shape[0])), (float(dx), float(dy))


def silhouette_id(prefix: str) -> str | None:
    if prefix.startswith("full_"):
        return prefix[len("full_") :]
    for key, silhouette in HALF_SILHOUETTES.items():
        if prefix.startswith(f"halfprod_{key}_") or prefix.startswith(f"half_{key}"):
            return silhouette
    if prefix.startswith("yaw000"):
        return "yaw+000-pitch+00"
    return None


def makeup_slot_masks(
    layer: np.ndarray, regions: dict[str, object]
) -> dict[str, np.ndarray]:
    """以 eyes > lips > cheeks 優先序切槽，保證槽遮罩互斥。"""

    slots = regions.get("slots")
    if not isinstance(slots, dict):
        raise ValueError("safe regions 缺少 slots 物件")
    taken = np.zeros(layer.shape[:2], dtype=bool)
    result: dict[str, np.ndarray] = {}
    for slot in MAKEUP_SLOT_PRIORITY:
        mask = np.zeros(layer.shape[:2], dtype=bool)
        rectangles = slots.get(slot, [])
        if not isinstance(rectangles, list):
            raise ValueError(f"槽位矩形格式錯誤：{slot}")
        for rectangle in rectangles:
            if (
                not isinstance(rectangle, list | tuple)
                or len(rectangle) != RECTANGLE_FIELDS
            ):
                raise ValueError(f"槽位矩形格式錯誤：{slot}")
            x, y, width, height = (int(value) for value in rectangle)
            x0, y0 = max(0, x), max(0, y)
            x1 = min(layer.shape[1], x + width)
            y1 = min(layer.shape[0], y + height)
            if x0 < x1 and y0 < y1:
                mask[y0:y1, x0:x1] = True
        mask &= ~taken
        taken |= mask
        result[slot] = mask
    return result


def write_makeup_slots(
    layer: np.ndarray,
    prefix: str,
    output: Path,
    safe_regions_path: Path | None,
) -> dict[str, int]:
    if safe_regions_path is None or not safe_regions_path.is_file():
        return {}
    silhouette = silhouette_id(prefix)
    if silhouette is None:
        return {}
    document = json.loads(safe_regions_path.read_text(encoding="utf-8"))
    all_regions = document.get("silhouettes", {})
    regions = all_regions.get(silhouette) if isinstance(all_regions, dict) else None
    if not isinstance(regions, dict):
        return {}
    counts: dict[str, int] = {}
    for slot, mask in makeup_slot_masks(layer, regions).items():
        part = layer.copy()
        part[:, :, 3] = part[:, :, 3] * mask
        part[part[:, :, 3] == 0] = 0
        save_png(output / f"L1_makeup.{slot}.png", part)
        counts[slot] = int((part[:, :, 3] > 0).sum())
    return counts


def head_region(image: np.ndarray, model_path: Path) -> np.ndarray:
    height, width = image.shape[:2]
    box = face_box(image, model_path)
    region = np.zeros((height, width), np.uint8)
    if box is None:
        region[: int(height * HEAD_FALLBACK_TOP_RATIO), :] = 1
        return region
    x, y, face_width, face_height = box
    top = 0
    bottom = min(height, int(y + face_height * HEAD_REGION_BOTTOM_FACE_FACTOR))
    left = max(0, int(x - HEAD_REGION_LEFT_FACE_FACTOR * face_width))
    right = min(width, int(x + HEAD_REGION_RIGHT_FACE_FACTOR * face_width))
    region[top:bottom, left:right] = 1
    region[
        int(y + HEAD_REGION_FACE_CUT_TOP_FACTOR * face_height) : bottom,
        int(x + HEAD_REGION_FACE_CUT_LEFT_FACTOR * face_width) : int(
            x + HEAD_REGION_FACE_CUT_BOTTOM_FACTOR * face_width
        ),
    ] = 0
    return region


def _headwear_cleanup(mask: np.ndarray, cur: np.ndarray) -> np.ndarray:
    blue = cur[:, :, 0].astype(np.int16)
    green = cur[:, :, 1].astype(np.int16)
    red = cur[:, :, 2].astype(np.int16)
    skin = (
        (red > HEADWEAR_SKIN_RED_MIN)
        & (red > green + HEADWEAR_SKIN_RED_GREEN_MARGIN)
        & (green > blue + HEADWEAR_SKIN_GREEN_BLUE_MARGIN)
    )
    mask = mask.copy()
    mask[skin] = 0
    dark = np.maximum(np.maximum(red, green), blue) < HEADWEAR_DARK_PIXEL_MAX
    mask[dark] = 0
    brightness = (red + green + blue) / 3.0
    warm_underlayer = (
        (brightness > HAIR_SPILL_BRIGHTNESS_MIN)
        & (brightness < HAIR_SPILL_BRIGHTNESS_MAX)
        & ((red - blue) > HAIR_SPILL_RED_BLUE_MARGIN)
    )
    # The silver/blue ornament has no warm material.  The same measured brown
    # criterion therefore identifies hairline/skin drift, not ornament pixels.
    mask[warm_underlayer] = 0
    mask = _remove_headwear_top_residues(mask, cur)
    return remove_unlinked_headwear_fragments(mask)


def _remove_headwear_top_residues(
    mask: np.ndarray, cur: np.ndarray
) -> np.ndarray:
    """Remove only the measured detached neutral-dark top contamination."""

    if mask.shape[:2] != (CANVAS_SIZE, CANVAS_SIZE):
        return mask.copy()
    visible = (mask > SMALL_COMPONENT_ALPHA_THRESHOLD).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if count <= 1:
        return mask.copy()
    large = np.zeros_like(visible)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] > HEADWEAR_TOP_RESIDUE_MAX_AREA:
            large[labels == label] = 1
    far_from_large = cv2.dilate(
        large,
        np.ones(
            (HEADWEAR_TOP_RESIDUE_DILATION_KERNEL,)
            * 2,
            dtype=np.uint8,
        ),
    ) == 0
    x0, y0, x1, y1 = HEADWEAR_TOP_RESIDUE_ROI
    cleaned = mask.copy()
    for label in range(1, count):
        if not _is_headwear_top_residue(
            label, stats, labels, cur, far_from_large, (x0, y0, x1, y1)
        ):
            continue
        ys, xs = np.nonzero(labels == label)
        cleaned[ys, xs] = 0
    return cleaned


def _is_headwear_top_residue(
    label: int,
    stats: np.ndarray,
    labels: np.ndarray,
    cur: np.ndarray,
    far_from_large: np.ndarray,
    roi: tuple[int, int, int, int],
) -> bool:
    x, y, width, height, area = (int(value) for value in stats[label])
    x0, y0, x1, y1 = roi
    if not (
        HEADWEAR_TOP_RESIDUE_MIN_AREA <= area <= HEADWEAR_TOP_RESIDUE_MAX_AREA
        and x0 <= x
        and x + width <= x1
        and y0 <= y
        and y + height <= y1
    ):
        return False
    ys, xs = np.nonzero(labels == label)
    if not far_from_large[ys, xs].all():
        return False
    colours = cur[ys, xs, :3].astype(np.int16)
    maximum = colours.max(axis=1)
    spread = maximum - colours.min(axis=1)
    return bool(
        maximum.max() <= HEADWEAR_TOP_RESIDUE_PIXEL_MAX
        and spread.max() <= HEADWEAR_TOP_RESIDUE_CHANNEL_SPREAD_MAX
    )


def _closest_component_points(
    first: np.ndarray, second: np.ndarray
) -> tuple[int, tuple[int, int], tuple[int, int]]:
    """Return Chebyshev distance and closest (x, y) points for two components."""

    best: tuple[int, tuple[int, int], tuple[int, int]] | None = None
    for y, x in first:
        distances = np.maximum(np.abs(second[:, 0] - y), np.abs(second[:, 1] - x))
        index = int(distances.argmin())
        candidate = (
            int(distances[index]),
            (int(x), int(y)),
            (int(second[index, 1]), int(second[index, 0])),
        )
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        raise ValueError("headwear components must contain pixels")
    return best


def _bridge_headwear_chain(
    layer: np.ndarray, mask: np.ndarray
) -> tuple[np.ndarray, int]:
    """Bridge a retained fine link to an anchor across only a measured short gap."""

    visible = (mask > HEADWEAR_COMPONENT_ALPHA_THRESHOLD).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if count <= 1:
        return layer.copy(), 0
    points = {
        label: np.column_stack(np.nonzero(labels == label))
        for label in range(1, count)
    }
    anchors = [
        label
        for label in range(1, count)
        if stats[label, cv2.CC_STAT_AREA] >= HEADWEAR_CHAIN_ANCHOR_MIN_AREA
    ]
    if not anchors:
        return layer.copy(), 0
    output = layer.copy()
    bridged_pixels = 0
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= HEADWEAR_CHAIN_ANCHOR_MIN_AREA:
            continue
        candidate_points = points[label]
        closest = min(
            (_closest_component_points(candidate_points, points[anchor]) for anchor in anchors),
            key=lambda candidate: candidate[0],
        )
        if closest[0] > HEADWEAR_CHAIN_BRIDGE_DISTANCE:
            continue
        bridged_pixels += _draw_headwear_chain_bridge(
            output, mask, closest[1], closest[2]
        )
    return output, bridged_pixels


def _draw_headwear_chain_bridge(
    output: np.ndarray,
    mask: np.ndarray,
    first: tuple[int, int],
    second: tuple[int, int],
) -> int:
    bridge = np.zeros(mask.shape, dtype=np.uint8)
    cv2.line(bridge, first, second, 1, 1)
    new_pixels = (bridge > 0) & (output[:, :, 3] == 0)
    if not new_pixels.any():
        return 0
    first_colour = output[first[1], first[0], :3].astype(np.float32)
    second_colour = output[second[1], second[0], :3].astype(np.float32)
    steps = max(abs(second[0] - first[0]), abs(second[1] - first[1]))
    for y, x in zip(*np.nonzero(new_pixels), strict=True):
        progress = (
            0.5
            if not steps
            else max(abs(int(x) - first[0]), abs(int(y) - first[1])) / steps
        )
        output[y, x, :3] = np.rint(
            first_colour * (1.0 - progress) + second_colour * progress
        ).clip(0, 255).astype(np.uint8)
        output[y, x, 3] = HEADWEAR_CHAIN_BRIDGE_ALPHA
    return int(new_pixels.sum())
def remove_unlinked_headwear_fragments(mask: np.ndarray) -> np.ndarray:
    """Keep small headwear components only in a measured transitive chain.

    Component discovery uses alpha>16, matching the release audit's visible
    headwear scan. Components larger than the small-noise ceiling are anchors;
    a smaller component is promoted only when it is within N Chebyshev pixels of
    an already retained component. Repeating the promotion preserves each fine
    chain link without allowing an isolated edge speck to survive. Soft alpha
    pixels belonging to a retained component are kept with it.
    """

    visible = (mask > HEADWEAR_COMPONENT_ALPHA_THRESHOLD).astype(np.uint8)
    visible_count, visible_labels, visible_stats, _ = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if visible_count <= 1:
        return np.zeros_like(mask)

    keep_visible = np.zeros(visible_count, dtype=bool)
    keep_visible[1:] = (
        visible_stats[1:, cv2.CC_STAT_AREA] >= HEADWEAR_CHAIN_ANCHOR_MIN_AREA
    )
    kernel_size = (2 * HEADWEAR_COMPONENT_LINK_DISTANCE + 1, ) * 2
    kernel = np.ones(kernel_size, dtype=np.uint8)
    while True:
        expanded = cv2.dilate(
            keep_visible[visible_labels].astype(np.uint8), kernel
        )
        candidate_labels = np.unique(
            visible_labels[(expanded > 0) & (visible_labels > 0)]
        )
        promoted = candidate_labels[~keep_visible[candidate_labels]]
        if not promoted.size:
            break
        keep_visible[promoted] = True

    # Retain the anti-aliased fringe attached to a kept visible component, but
    # remove a whole low-alpha island that has no visible retained component.
    alpha_count, alpha_labels, _alpha_stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8), connectivity=8
    )
    keep_alpha = np.zeros(alpha_count, dtype=bool)
    overlap = alpha_labels[keep_visible[visible_labels] & (alpha_labels > 0)]
    if overlap.size:
        keep_alpha[np.unique(overlap)] = True
    return np.where(keep_alpha[alpha_labels], mask, 0).astype(mask.dtype)

def _clean_small_components(
    layer: np.ndarray,
) -> tuple[np.ndarray, dict[str, int]]:
    source_alpha = layer[:, :, 3]
    cleaned_alpha, metrics = remove_unlinked_small_components(
        source_alpha,
        roi=speck_roi_for_shape(layer.shape[:2]),
    )
    cleaned_alpha, owner_metrics = remove_owner_specks(
        cleaned_alpha,
        roi=speck_roi_for_shape(layer.shape[:2]),
    )
    output = layer.copy()
    output[:, :, 3] = cleaned_alpha
    output[cleaned_alpha == 0] = 0
    return output, {**metrics, **owner_metrics}


def _remove_hair_underlayer_spill(layer: np.ndarray) -> tuple[np.ndarray, int]:
    """Neutralize measured warm skin colour carried into an opaque hair layer.

    The incremental source is a fully composited portrait, so a differenced
    hair mask can retain the previous skin/hairline RGB.  Only pixels matching
    the release audit's fixed brown criterion are touched.  Replacing their hue
    with the same per-pixel mean luminance preserves texture and alpha while
    removing the under-layer colour cast.
    """

    output = layer.copy()
    blue = output[:, :, 0].astype(np.int16)
    green = output[:, :, 1].astype(np.int16)
    red = output[:, :, 2].astype(np.int16)
    brightness = (red + green + blue) / 3.0
    spill = (
        (output[:, :, 3] > 0)
        & (brightness > HAIR_SPILL_BRIGHTNESS_MIN)
        & (brightness < HAIR_SPILL_BRIGHTNESS_MAX)
        & ((red - blue) > HAIR_SPILL_RED_BLUE_MARGIN)
    )
    neutral = np.rint(brightness[spill]).astype(np.uint8)
    output[spill, 0] = neutral
    output[spill, 1] = neutral
    output[spill, 2] = neutral
    return output, int(spill.sum())


def _hair_masks(
    previous: np.ndarray,
    current: np.ndarray,
    base: np.ndarray,
    model_path: Path,
) -> tuple[np.ndarray, np.ndarray]:
    parameters = STEP_PARAMETERS["L3_hair"]
    fine_parameters = DiffParameters(
        parameters.rgb_threshold,
        HAIR_FRONT_OPEN_KERNEL,
        parameters.close_kernel,
        parameters.soft_alpha_span,
    )
    body_parameters = DiffParameters(
        parameters.rgb_threshold,
        HAIR_BODY_OPEN_KERNEL,
        parameters.close_kernel,
        parameters.soft_alpha_span,
    )
    fine_mask = _diff_mask_with_parameters(previous, current, fine_parameters)
    front_mask = _diff_mask_with_parameters(previous, current, body_parameters)
    fine_bottom = int(current.shape[0] * HAIR_FINE_REGION_BOTTOM_RATIO)
    front_mask[:fine_bottom] = fine_mask[:fine_bottom]
    permissive_mask = diff_mask(previous, current, "L3_hair")
    back_mask = permissive_mask.copy()
    back_mask[front_mask > 0] = 0
    back_mask = (back_mask * head_region(base, model_path)).astype(np.uint8)
    return front_mask, back_mask


def _safe_prefix(prefix: str) -> Path:
    candidate = Path(prefix)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("prefix 必須是相對且不可離開輸出目錄")
    return candidate


NEUTRAL_HALF_BODY_PREFIX = "halfprod_front_A"


def _resolve_reference_layers(
    base: np.ndarray,
    reference_path: Path | None,
    model_path: Path,
    report: dict[str, object],
    source_directory: Path,
    prefix: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]] | None:
    """擁有者 2026-09-05 裁決：頭髮與髮飾以 v4 原圖為準。

    有參考圖且對齊成功時回傳（前髮層, 髮飾層, 報告）；沒有參考圖回傳 None，
    對齊失敗也回傳 None 並在報告寫明，讓呼叫端回退到差分抽層。半身姿勢另傳
    本姿勢與正面中性姿勢的髮層渲染，讓舉起的手掌、手臂遮住 v4 頭髮。
    """
    if reference_path is None:
        return None
    neutral = None
    if prefix.startswith("halfprod_"):
        neutral = source_directory / f"{NEUTRAL_HALF_BODY_PREFIX}.L3_hair.png"
    reference_layers = extract_reference_layers(
        base,
        reference_path,
        model_path,
        pose_render_path=source_directory / f"{prefix}.L3_hair.png",
        neutral_render_path=neutral,
    )
    report["reference"] = (
        reference_layers[2] if reference_layers is not None else "alignment failed"
    )
    return reference_layers


def _reference_layer_for_step(
    step: str,
    reference_layers: tuple[np.ndarray, np.ndarray, dict[str, object]],
    layer_report: dict[str, object],
) -> np.ndarray:
    """L3 前髮與 L4 髮飾整層改取參考圖像素。

    後髮槽維持差分抽出的內側低 Z 髮量（封裝契約要求正面姿勢的後髮層非空），
    它整個藏在前髮之下，不影響外觀。
    """
    if step == "L3_hair":
        hair_entry = layer_report[step]
        if isinstance(hair_entry, dict):
            hair_entry["source"] = "reference"
        return reference_layers[0]
    layer_report[step] = {"source": "reference"}
    return reference_layers[1]


def _extract_steps(
    base: np.ndarray,
    prefix: str,
    source_directory: Path,
    output: Path,
    model_path: Path,
    safe_regions_path: Path | None,
    reference_path: Path | None = None,
) -> tuple[list[np.ndarray], np.ndarray, np.ndarray | None, dict[str, object]]:
    previous = base
    layers: list[np.ndarray] = []
    layer_report: dict[str, object] = {}
    report: dict[str, object] = {"layers": layer_report}
    hair_back: np.ndarray | None = None
    reference_layers = _resolve_reference_layers(
        base, reference_path, model_path, report, source_directory, prefix
    )
    for step in STEPS:
        if not (source_directory / f"{prefix}.{step}.png").is_file():
            layer_report[step] = "missing"
            continue
        current = key_and_despill(source_directory / f"{prefix}.{step}.png")
        save_png(output / f"{step}.keyed.png", current)
        if current.shape != base.shape:
            current = resize_rgba(current, (base.shape[1], base.shape[0]))
        current, shift = register(previous, current, step)
        mask = diff_mask(previous, current, step)
        if step == "L1_makeup":
            mask = (mask * makeup_region(base, model_path)).astype(np.uint8)
        elif step == "L3_hair":
            front_mask, back_mask = _hair_masks(
                previous, current, base, model_path
            )
            # The permissive mask is only an inner, low-Z backing mass.  This
            # anatomical head region excludes the face core and all garment
            # pixels that a direct open=0 foreground mask admitted in QA.
            hair_back = current.copy()
            hair_back[:, :, 3] = (
                current[:, :, 3].astype(np.uint16) * back_mask // 255
            ).astype(np.uint8)
            hair_back[hair_back[:, :, 3] == 0] = 0
            hair_back, back_corrected = _remove_hair_underlayer_spill(hair_back)
            hair_back, back_speck_cleanup = _clean_small_components(hair_back)
            save_png(output / "L3_hair.back.png", hair_back)
            mask = front_mask
            layer_report[step] = {
                "back_opaque_pixels": int((hair_back[:, :, 3] > 0).sum()),
                "back_warm_underlayer_pixels_corrected": back_corrected,
                "back_small_component_cleanup": back_speck_cleanup,
            }
        elif step == "L4_headwear":
            mask = (mask * head_region(base, model_path)).astype(np.uint8)
            mask = _headwear_cleanup(mask, current)
        layer = current.copy()
        layer_alpha = current[:, :, 3].astype(np.uint16) * mask // 255
        if step == "L4_headwear":
            # Keep the extracted headwear mask's measured visibility when a
            # subpixel registration would otherwise attenuate a valid chain.
            layer_alpha = np.maximum(layer_alpha, mask)
        layer[:, :, 3] = layer_alpha.astype(np.uint8)
        layer[layer[:, :, 3] == 0] = 0
        if reference_layers is not None and step in ("L3_hair", "L4_headwear"):
            layer = _reference_layer_for_step(step, reference_layers, layer_report)
        elif step == "L3_hair":
            layer, corrected = _remove_hair_underlayer_spill(layer)
            layer, front_speck_cleanup = _clean_small_components(layer)
            hair_entry = layer_report[step]
            if isinstance(hair_entry, dict):
                hair_entry["warm_underlayer_pixels_corrected"] = corrected
                hair_entry["front_small_component_cleanup"] = front_speck_cleanup
        elif step == "L4_headwear":
            layer, chain_bridged_pixels = _bridge_headwear_chain(layer, mask)
            layer, headwear_speck_cleanup = _clean_small_components(layer)
            layer_report[step] = {
                "chain_bridged_pixels": chain_bridged_pixels,
                "small_component_cleanup": headwear_speck_cleanup,
            }
        save_png(output / f"{step}.png", layer)
        if step == "L1_makeup":
            report["makeup_slots"] = write_makeup_slots(
                layer, prefix, output, safe_regions_path
            )
        layers.append(layer)
        layer_report[step] = {
            **(
                layer_report.get(step, {})
                if isinstance(layer_report.get(step), dict)
                else {}
            ),
            "opaque_pixels": int((layer[:, :, 3] > 0).sum()),
            "share_of_canvas": round(float((layer[:, :, 3] > 0).mean()), 4),
            "registration_shift_px": [round(shift[0], 2), round(shift[1], 2)],
        }
        previous = current
    return layers, previous, hair_back, report


def _find_shoe_source(source_directory: Path, prefix: str) -> Path | None:
    for name in ("L5c_shoes", "L5b_shoes", "L5_shoes"):
        candidate = source_directory / f"{prefix}.{name}.png"
        if candidate.is_file():
            return candidate
    return None


def _foot_mask(shoes: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mask = mask.copy()
    height = shoes.shape[0]
    mask[: int(height * SHOE_UPPER_EXCLUSION_RATIO), :] = 0
    foot_zone = np.zeros_like(mask)
    foot_zone[int(height * SHOE_FOOT_ZONE_TOP_RATIO) :, :] = 255
    foot_zone = (foot_zone * (shoes[:, :, 3] > 0)).astype(np.uint8)
    band = slice(
        int(height * SHOE_FOOT_BAND_TOP_RATIO),
        int(height * SHOE_FOOT_ZONE_TOP_RATIO),
    )
    blue = shoes[band, :, 0].astype(np.int16)
    green = shoes[band, :, 1].astype(np.int16)
    red = shoes[band, :, 2].astype(np.int16)
    not_blue = ~(
        (blue > red + SHOE_BLUE_RED_MARGIN) & (blue > green + SHOE_BLUE_GREEN_MARGIN)
    )
    foot_zone[band, :] = (not_blue & (shoes[band, :, 3] > 0)).astype(np.uint8) * 255
    return np.maximum(mask, foot_zone)


def _patch_bare_feet(base: np.ndarray, shoe_layer: np.ndarray) -> tuple[int, int]:
    zone_top = int(base.shape[0] * SHOE_FOOT_ZONE_TOP_RATIO)
    blue = base[zone_top:, :, 0].astype(np.int16)
    green = base[zone_top:, :, 1].astype(np.int16)
    red = base[zone_top:, :, 2].astype(np.int16)
    bare = (
        (base[zone_top:, :, 3] > SHOE_BARE_ALPHA_MIN)
        & (red > BARE_SKIN_RED_MIN)
        & (red > green + BARE_SKIN_RED_GREEN_MARGIN)
        & (green > blue + BARE_SKIN_GREEN_BLUE_MARGIN)
    )
    region = shoe_layer[zone_top:]
    covered = region[:, :, 3] > SHOE_COVERED_ALPHA_MIN
    uncovered = bare & ~covered
    patched = 0
    for row in np.nonzero(uncovered.any(axis=1))[0]:
        covered_x = np.nonzero(covered[row])[0]
        if covered_x.size == 0:
            continue
        for column in np.nonzero(uncovered[row])[0]:
            nearest = covered_x[np.abs(covered_x - column).argmin()]
            if abs(int(nearest) - int(column)) > SHOE_NEAREST_MAX_DISTANCE:
                continue
            region[row, column, :3] = region[row, nearest, :3]
            region[row, column, 3] = 255
            patched += 1
    shoe_layer[zone_top:] = region
    left = int((bare & ~(shoe_layer[zone_top:, :, 3] > SHOE_COVERED_ALPHA_MIN)).sum())
    return left, patched


def _build_shoe_layer(
    base: np.ndarray,
    final: np.ndarray,
    source_path: Path,
    output_shape: tuple[int, int, int],
    keyed_output: Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    shoes = key_and_despill(source_path)
    save_png(keyed_output, shoes)
    if shoes.shape != output_shape:
        shoes = resize_rgba(shoes, (output_shape[1], output_shape[0]))
    shoes, shoe_shift = register(final, shoes, "L2_garment")
    mask = _foot_mask(shoes, diff_mask(final, shoes, "L2_garment"))
    shoe_layer = shoes.copy()
    shoe_layer[:, :, 3] = (shoes[:, :, 3].astype(np.uint16) * mask // 255).astype(
        np.uint8
    )
    shoe_layer[shoe_layer[:, :, 3] == 0] = 0
    left, patched = _patch_bare_feet(base, shoe_layer)
    shoe_report = {
        "bare_foot_uncovered_px": left,
        "shoes_patched_px": patched,
        "shoes": {
            "opaque_pixels": int((shoe_layer[:, :, 3] > 0).sum()),
            "registration_shift_px": [round(shoe_shift[0], 2), round(shoe_shift[1], 2)],
        },
    }
    return shoe_layer, shoes, shoe_report


def _merge_shoes(
    base: np.ndarray,
    final: np.ndarray,
    layers: list[np.ndarray],
    source_path: Path | None,
    output: Path,
) -> tuple[list[np.ndarray], np.ndarray, dict[str, object]]:
    if source_path is None or len(layers) != len(STEPS):
        return layers, final, {}
    shoe_layer, shoes, report = _build_shoe_layer(
        base, final, source_path, base.shape, output / "L5_shoes.keyed.png"
    )
    merged = composite_over(layers[1], shoe_layer)
    save_png(output / "L2_garment.png", merged)
    layers[1] = merged
    return layers, shoes, report


def _write_final_outputs(
    base: np.ndarray,
    layers: list[np.ndarray],
    hair_back: np.ndarray | None,
    final: np.ndarray,
    output: Path,
    report: dict[str, object],
) -> None:
    reconstruction = base
    for index, layer in enumerate(layers):
        if index == 1 and hair_back is not None:
            reconstruction = composite_over(reconstruction, hair_back)
        reconstruction = composite_over(reconstruction, layer)
    save_png(output / "reconstruction.png", reconstruction)
    save_png(output / "final.png", final)
    both = (final[:, :, 3] > 0) | (reconstruction[:, :, 3] > 0)
    error = np.abs(
        final[:, :, :3].astype(np.int16) - reconstruction[:, :, :3].astype(np.int16)
    )
    report["reconstruction_mean_channel_error"] = round(
        float(error[both].mean()) if both.any() else 0.0,
        3,
    )
    report["reconstruction_pixels_over_24"] = int(
        (error.max(axis=2)[both] > RECONSTRUCTION_ERROR_PIXEL_THRESHOLD).sum()
    )

    def tile(image: np.ndarray) -> np.ndarray:
        background = np.empty(image.shape[:2] + (3,), np.uint8)
        background[:, :] = SHEET_BACKGROUND_BGR
        alpha = image[:, :, 3:4].astype(np.float32) / 255.0
        composed = image[:, :, :3] * alpha + background * (1.0 - alpha)
        return cv2.resize(
            composed.astype(np.uint8), (SHEET_TILE_WIDTH, SHEET_TILE_HEIGHT)
        )

    tiles = [
        tile(base),
        *(
            tile(item)
            for index, layer in enumerate(layers)
            for item in (
                (hair_back, layer)
                if index == 1 and hair_back is not None
                else (layer,)
            )
        ),
        tile(reconstruction),
        tile(final),
    ]
    sheet = np.zeros(
        (SHEET_TILE_HEIGHT, (SHEET_TILE_WIDTH + SHEET_TILE_GAP) * len(tiles)),
        np.uint8,
    )
    sheet = np.dstack((sheet, sheet, sheet))
    for index, item in enumerate(tiles):
        start = index * (SHEET_TILE_WIDTH + SHEET_TILE_GAP)
        sheet[:, start : start + SHEET_TILE_WIDTH] = item
    save_png(output / "sheet.png", sheet)


def extract(  # noqa: PLR0913 - 參考圖與其他輸入路徑一樣由呼叫端提供，屬同一層級的 I/O 參數
    base_magenta: Path,
    prefix: str,
    *,
    source_directory: Path,
    output_root: Path,
    model_path: Path,
    safe_regions_path: Path | None = None,
    output_name: str | None = None,
    reference_path: Path | None = None,
) -> dict[str, object]:
    """執行一批抽層並寫出報告；所有 I/O 根目錄由呼叫端提供。"""

    relative_prefix = _safe_prefix(prefix if output_name is None else output_name)

    output = output_root / relative_prefix
    output.mkdir(parents=True, exist_ok=True)
    base = key_and_despill(base_magenta)
    save_png(output / "base.png", base)
    layers, final, hair_back, report = _extract_steps(
        base,
        prefix,
        source_directory,
        output,
        model_path,
        safe_regions_path,
        reference_path,
    )
    layers, final, shoe_report = _merge_shoes(
        base, final, layers, _find_shoe_source(source_directory, prefix), output
    )
    report.update(shoe_report)
    _write_final_outputs(base, layers, hair_back, final, output, report)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_magenta", type=Path)
    parser.add_argument("prefix")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--safe-regions", type=Path)
    args = parser.parse_args(argv)
    report = extract(
        args.base_magenta,
        args.prefix,
        source_directory=args.source_dir,
        output_root=args.output_root,
        model_path=args.model,
        safe_regions_path=args.safe_regions,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
