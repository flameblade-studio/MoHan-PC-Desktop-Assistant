"""Measure visible hair and headwear defects in the sealed official outfit pack.

The audit deliberately reads the same sealed archive and composed portrait that
users receive.  It therefore catches losses introduced by extraction, assembly,
or runtime composition instead of trusting an intermediate layer report.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import cv2
lazy import numpy as np

lazy from tools.art_pipeline.constants import (
    HEADWEAR_CHAIN_LINK_RADIUS,
    HEADWEAR_COMPONENT_ALPHA_THRESHOLD,
    HEADWEAR_DETACHED_DISTANCE,
    SMALL_COMPONENT_ALPHA_THRESHOLD,
    SMALL_COMPONENT_ANCHOR_MIN_AREA,
    SMALL_COMPONENT_DIRECT_DISTANCE,
    SMALL_COMPONENT_LINK_DISTANCE,
    SMALL_COMPONENT_MAX_AREA,
)
lazy from tools.art_pipeline.speck_cleanup import (
    owner_judge_metrics_for_stored_layer,
    speck_roi_for_shape,
)
lazy from domain.outfit_pack import REQUIRED_SILHOUETTES

DEFAULT_PACK: Final = (
    ROOT / "assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit"
)
DEFAULT_PORTRAIT: Final = ROOT / "docs/media/portraits/idle_front.png"
DEFAULT_BASE_HAIR: Final = ROOT / "assets/expressions/layered/front_hair_back.png"
FRONT_SILHOUETTE: Final = "front-crossed"
HEAD_ROI: Final = (360, 150, 900, 470)
SPECK_HEAD_ROI: Final = (300, 100, 1000, 520)
SPECK_FULL_BODY_ROI: Final = (250, 30, 800, 420)
# The original alpha>30 rule remains part of the report's contract, but a
# sealed composite must not hide any residual pixel below that threshold.
SPECK_ALPHA_THRESHOLD: Final = 0
SPECK_OWNER_ALPHA_THRESHOLD: Final = SMALL_COMPONENT_ALPHA_THRESHOLD
SPECK_SMALL_COMPONENT_MAX_AREA: Final = SMALL_COMPONENT_MAX_AREA
SPECK_LARGE_COMPONENT_MIN_AREA: Final = SMALL_COMPONENT_ANCHOR_MIN_AREA
SPECK_DIRECT_DISTANCE_PX: Final = SMALL_COMPONENT_DIRECT_DISTANCE
FINE_CHAIN_ROI: Final = (735, 280, 800, 430)
FINE_CHAIN_MIN_COMPONENT_AREA: Final = 10
FINE_CHAIN_ENDPOINT_AREAS: Final = (386, 89)
BROWN_BRIGHTNESS_MIN: Final = 70
BROWN_BRIGHTNESS_MAX: Final = 150
BROWN_RED_BLUE_MARGIN: Final = 18
DETACHED_DISTANCE_PX: Final = float(HEADWEAR_DETACHED_DISTANCE)
IMAGE_DIMENSIONS: Final = 3
RGBA_CHANNELS: Final = 4
OPAQUE: Final = 255
ANCHOR_COORDINATE_COUNT: Final = 2
OWNER_JUDGE_CANVAS: Final = (1254, 1254)
MAX_COMPOSITE_ISOLATED_COUNT: Final = 9
# These two detached blue bead assemblies are intentional: the design hangs
# them from the right side of the hairpiece rather than touching the crown.
# The whitelist is keyed by measured source-pixel area so an unexpected change
# in either assembly fails the gate instead of being silently accepted.
DETACHED_HEADWEAR_WHITELIST: Final = {
    "front-eureka": frozenset({319}),
    "front-mock-scold": frozenset({84}),
}
DETACHED_HEADWEAR_WHITELIST_REASONS: Final = {
    ("front-eureka", 319): "右側懸掛藍色珠飾，設計上與冠體分離。",
    ("front-mock-scold", 84): "右側懸掛藍色珠飾，設計上與冠體分離。",
}


def _decode_png(encoded: bytes, label: str) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_UNCHANGED)
    if (
        image is None
        or image.ndim != IMAGE_DIMENSIONS
        or image.shape[2] != RGBA_CHANNELS
    ):
        raise ValueError(f"Expected RGBA PNG: {label}")
    return image


def _read_png(path: Path) -> np.ndarray:
    return _decode_png(path.read_bytes(), str(path))


def _owner_judge_layer_metrics(image: np.ndarray) -> dict[str, object]:
    """Measure the sealed member with the supplied judge's exact geometry."""

    alpha = image[:, :, 3]
    height, width = alpha.shape
    measured = owner_judge_metrics_for_stored_layer(alpha)
    if (height, width) == OWNER_JUDGE_CANVAS:
        judge_shape = [height, width]
    elif height <= OWNER_JUDGE_CANVAS[0] and width <= OWNER_JUDGE_CANVAS[1]:
        judge_shape = list(OWNER_JUDGE_CANVAS)
    else:
        judge_shape = [height, width]
    return {
        **measured,
        "source_shape": [height, width],
        "judge_canvas_shape": judge_shape,
    }


def _asset_path(manifest: dict[str, object], category: str, slot: str) -> str:
    collection = manifest[category]
    if not isinstance(collection, list) or len(collection) != 1:
        raise ValueError(f"Expected one official {category} item.")
    variants = collection[0]["variants"]
    poses = variants[0]["poses"]
    declarations = poses[FRONT_SILHOUETTE]
    return next(item["path"] for item in declarations if item["slot"] == slot)


def _expand_declared_layer(
    image: np.ndarray,
    declaration: dict[str, object],
    canvas_shape: tuple[int, int],
) -> np.ndarray:
    """Restore a cropped asset to its declared canvas at its declared anchor."""

    canvas_height, canvas_width = canvas_shape
    anchor = declaration.get("anchor", [0, 0])
    if not isinstance(anchor, list) or len(anchor) != ANCHOR_COORDINATE_COUNT:
        raise ValueError("Layer anchor must contain x and y.")
    x, y = (int(anchor[0]), int(anchor[1]))
    height, width = image.shape[:2]
    if (
        x < 0
        or y < 0
        or x + width > canvas_width
        or y + height > canvas_height
    ):
        raise ValueError("Layer anchor escaped the declared canvas.")
    if (height, width) == canvas_shape and (x, y) == (0, 0):
        return image
    expanded = np.zeros((canvas_height, canvas_width, RGBA_CHANNELS), dtype=image.dtype)
    expanded[y : y + height, x : x + width] = image
    return expanded


def brown_hair_metrics(
    portrait: np.ndarray,
    front_hair: np.ndarray,
    back_hair: np.ndarray,
    base_hair: np.ndarray,
) -> dict[str, int | float]:
    """Measure the owner's forehead criterion and attribute every suspect pixel."""

    x0, y0, x1, y1 = HEAD_ROI
    rgb = portrait[y0:y1, x0:x1, :3][:, :, ::-1].astype(np.int16)
    brightness = rgb.mean(axis=2)
    brown = (
        (brightness > BROWN_BRIGHTNESS_MIN)
        & (brightness < BROWN_BRIGHTNESS_MAX)
        & ((rgb[:, :, 0] - rgb[:, :, 2]) > BROWN_RED_BLUE_MARGIN)
    )
    front_alpha = front_hair[y0:y1, x0:x1, 3]
    back_alpha = back_hair[y0:y1, x0:x1, 3]
    base_alpha = base_hair[y0:y1, x0:x1, 3]
    outfit_alpha = np.maximum(front_alpha, back_alpha)
    total = int(brown.sum())
    solid = int((brown & (outfit_alpha == OPAQUE)).sum())
    outfit_empty = brown & (outfit_alpha == 0)
    holes = int((outfit_empty & (base_alpha == 0)).sum())
    return {
        "roi_pixels": int(brown.size),
        "brown_pixels": total,
        "brown_share_percent": round(100.0 * total / brown.size, 4),
        "brown_outfit_alpha_255": solid,
        "brown_outfit_alpha_255_percent": round(100.0 * solid / max(total, 1), 4),
        "brown_outfit_alpha_0": int(outfit_empty.sum()),
        "brown_outfit_alpha_0_percent": round(
            100.0 * outfit_empty.sum() / max(total, 1), 4
        ),
        "brown_both_outfit_and_base_hair_alpha_0": holes,
        "brown_hole_share_percent": round(100.0 * holes / max(total, 1), 4),
    }


def _unlinked_component_entry(
    binary: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    main_bounds: tuple[int, int, int, int],
    label: int,
) -> dict[str, object] | None:
    main_x, main_y, main_width, main_height = main_bounds
    x, y, width, height = (int(value) for value in stats[label, :4])
    dx = max(main_x - (x + width), x - (main_x + main_width), 0)
    dy = max(main_y - (y + height), y - (main_y + main_height), 0)
    distance = float(np.hypot(dx, dy))
    if distance <= DETACHED_DISTANCE_PX:
        return None
    pixels = (labels == label) & (binary > 0)
    ys, xs = np.nonzero(pixels)
    if not len(xs):
        return None
    return {
        "area": int(len(xs)),
        "bbox": [
            int(xs.min()),
            int(ys.min()),
            int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
        ],
        "distance_from_main_px": round(distance, 3),
    }


def _linked_unattached_components(binary: np.ndarray) -> list[dict[str, object]]:
    binary = (binary > 0).astype(np.uint8)
    radius = HEADWEAR_CHAIN_LINK_RADIUS
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1)
    )
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        cv2.dilate(binary, kernel), connectivity=8
    )
    if count <= 1:
        return []
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    main_bounds = tuple(int(value) for value in stats[main, :4])
    unattached = []
    for label in range(1, count):
        if label == main:
            continue
        entry = _unlinked_component_entry(
            binary, labels, stats, main_bounds, label
        )
        if entry is not None:
            unattached.append(entry)
    return unattached


def _linked_unattached_count(binary: np.ndarray) -> int:
    return len(_linked_unattached_components(binary))


def component_metrics(image: np.ndarray) -> dict[str, object]:
    """Measure raw components and components linked by visible chain spacing."""

    binary = (image[:, :, 3] > 0).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    if count == 1:
        return {
            "component_count": 0,
            "main_component_area": 0,
            "detached_over_100px": 0,
            "unlinked_over_100px": 0,
            "unlinked_components": [],
            "components": [],
        }
    main_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    distance_to_main = cv2.distanceTransform(
        (labels != main_label).astype(np.uint8),
        cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE,
    )
    components = []
    for label in range(1, count):
        distance = 0.0
        if label != main_label:
            distance = float(distance_to_main[labels == label].min())
        components.append(
            {
                "area": int(stats[label, cv2.CC_STAT_AREA]),
                "distance_from_main_px": round(distance, 3),
            }
        )
    components.sort(key=lambda item: (-item["area"], item["distance_from_main_px"]))
    unlinked_components = _linked_unattached_components(binary)
    return {
        "component_count": len(components),
        "main_component_area": int(stats[main_label, cv2.CC_STAT_AREA]),
        "detached_over_100px": sum(
            item["distance_from_main_px"] > DETACHED_DISTANCE_PX
            for item in components
        ),
        "unlinked_over_100px": len(unlinked_components),
        "unlinked_components": unlinked_components,
        "components": components,
    }


def _bounded_roi(
    image: np.ndarray, roi: tuple[int, int, int, int]
) -> tuple[int, int, int, int, np.ndarray]:
    x0, y0, x1, y1 = roi
    x0 = max(0, min(image.shape[1], x0))
    x1 = max(x0, min(image.shape[1], x1))
    y0 = max(0, min(image.shape[0], y0))
    y1 = max(y0, min(image.shape[0], y1))
    return x0, y0, x1, y1, image[y0:y1, x0:x1]


def _source_alpha_roi(
    source_alpha: np.ndarray | None,
    crop: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> np.ndarray | None:
    if source_alpha is None:
        return None
    source_crop = source_alpha[y0:y1, x0:x1]
    if source_crop.ndim == IMAGE_DIMENSIONS:
        source_crop = source_crop[:, :, 3]
    if source_crop.shape != crop.shape[:2]:
        raise ValueError("source_alpha must share the composite canvas shape")
    return source_crop


def _restrict_to_source(
    small: np.ndarray, labels: np.ndarray, source_crop: np.ndarray
) -> np.ndarray:
    source_pixels = source_crop > 0
    source_small = np.zeros(small.size, dtype=bool)
    for label in np.flatnonzero(small):
        source_small[label] = bool(np.any(source_pixels[labels == label]))
    return small & source_small


def _minimum_distance_to_components(
    labels: np.ndarray, retained: np.ndarray
) -> np.ndarray:
    minimum_distance = np.full(retained.size, np.inf, dtype=np.float32)
    source = np.ones(labels.shape, dtype=np.uint8)
    source[retained[labels]] = 0
    distance = cv2.distanceTransform(source, cv2.DIST_C, 3)
    pixels = labels > 0
    np.minimum.at(minimum_distance, labels[pixels], distance[pixels])
    return minimum_distance


def _promote_linked_components(
    labels: np.ndarray, stats: np.ndarray, anchor_area: int
) -> np.ndarray:
    linked = np.zeros(len(stats), dtype=bool)
    linked[1:] = stats[1:, cv2.CC_STAT_AREA] > anchor_area
    while True:
        minimum_distance = _minimum_distance_to_components(labels, linked)
        promoted = (minimum_distance <= SMALL_COMPONENT_LINK_DISTANCE) & ~linked
        if not promoted.any():
            return linked
        linked |= promoted


def _direct_speck_masks(
    labels: np.ndarray,
    stats: np.ndarray,
    source_crop: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, int]:
    large = stats[:, cv2.CC_STAT_AREA] > SPECK_LARGE_COMPONENT_MIN_AREA
    large[0] = False
    small = (
        (stats[:, cv2.CC_STAT_AREA] > 0)
        & (stats[:, cv2.CC_STAT_AREA] <= SPECK_SMALL_COMPONENT_MAX_AREA)
    )
    small[0] = False
    if source_crop is not None:
        small = _restrict_to_source(small, labels, source_crop)
    distance = _minimum_distance_to_components(labels, large)
    direct = small & (distance > SPECK_DIRECT_DISTANCE_PX)
    return small, direct, int(large.sum())


def _linked_mask_for_crop(
    crop: np.ndarray, source_crop: np.ndarray | None
) -> tuple[np.ndarray, np.ndarray]:
    # The composite gate must see even alpha=1 remnants.  The separate
    # fine-chain gate intentionally keeps its historical alpha>16 contract.
    link_visible = (crop[:, :, 3] > 0).astype(np.uint8)
    _link_count, link_labels, link_stats, _ = cv2.connectedComponentsWithStats(
        link_visible, connectivity=8
    )
    return link_labels, _promote_linked_components(
        link_labels, link_stats, SMALL_COMPONENT_ANCHOR_MIN_AREA
    )


def _empty_speck_metrics(roi: tuple[int, int, int, int]) -> dict[str, object]:
    x0, y0, x1, y1 = roi
    return {
        "roi_xyxy": [x0, y0, x1, y1],
        "component_count": 0,
        "large_component_count": 0,
        "small_component_count": 0,
        "direct_definition_count": 0,
        "isolated_count": 0,
        "alpha_threshold": SPECK_ALPHA_THRESHOLD,
        "owner_alpha_threshold": SPECK_OWNER_ALPHA_THRESHOLD,
        "small_component_max_area": SPECK_SMALL_COMPONENT_MAX_AREA,
        "large_component_min_area": SPECK_LARGE_COMPONENT_MIN_AREA,
        "direct_distance_px": SPECK_DIRECT_DISTANCE_PX,
        "link_distance_px": SMALL_COMPONENT_LINK_DISTANCE,
    }


def isolated_speck_metrics(
    image: np.ndarray,
    *,
    roi: tuple[int, int, int, int] | None = None,
    source_alpha: np.ndarray | None = None,
) -> dict[str, object]:
    """Measure small composite specks and the N-linked chain-aware remainder.

    The release gate counts every alpha>0 component, while retaining the
    owner's alpha>30 value in ``owner_alpha_threshold`` as a diagnostic.  The
    isolated definition is area<=12 and Chebyshev distance>3 from every
    area>60 component; the N=9 chain rule then removes only links that reach an
    area>60 anchor.  When ``source_alpha`` is supplied, only pixels painted by
    that source layer are attributed to this gate.
    """

    selected_roi = speck_roi_for_shape(image.shape[:2]) if roi is None else roi
    x0, y0, x1, y1, crop = _bounded_roi(image, selected_roi)
    source_crop = _source_alpha_roi(source_alpha, crop, x0, y0, x1, y1)
    visible = (crop[:, :, 3] > SPECK_ALPHA_THRESHOLD).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        visible, connectivity=8
    )
    if count <= 1:
        return _empty_speck_metrics((x0, y0, x1, y1))

    small, direct, large_count = _direct_speck_masks(labels, stats, source_crop)

    link_labels, linked = _linked_mask_for_crop(crop, source_crop)

    small_linked = np.zeros(count, dtype=bool)
    for label in np.flatnonzero(small):
        small_linked[label] = bool(np.any(linked[link_labels[labels == label]]))

    return {
        "roi_xyxy": [x0, y0, x1, y1],
        "component_count": int(count - 1),
        "large_component_count": large_count,
        "small_component_count": int(small.sum()),
        "direct_definition_count": int(direct.sum()),
        "isolated_count": int((direct & ~small_linked).sum()),
        "alpha_threshold": SPECK_ALPHA_THRESHOLD,
        "owner_alpha_threshold": SPECK_OWNER_ALPHA_THRESHOLD,
        "small_component_max_area": SPECK_SMALL_COMPONENT_MAX_AREA,
        "large_component_min_area": SPECK_LARGE_COMPONENT_MIN_AREA,
        "direct_distance_px": SPECK_DIRECT_DISTANCE_PX,
        "link_distance_px": SMALL_COMPONENT_LINK_DISTANCE,
    }


def _alpha_component_stats(
    alpha: np.ndarray,
    roi: tuple[int, int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    x0, y0, x1, y1 = roi
    _count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (alpha[y0:y1, x0:x1] > HEADWEAR_COMPONENT_ALPHA_THRESHOLD).astype(
            np.uint8
        ),
        connectivity=8,
    )
    return labels, stats


def _maximum_link_distance(labels: np.ndarray, stats: np.ndarray) -> float:
    linked = np.zeros(len(stats), dtype=bool)
    linked[1:] = stats[1:, cv2.CC_STAT_AREA] > SMALL_COMPONENT_ANCHOR_MIN_AREA
    maximum_link_distance = 0.0
    while True:
        source = np.ones(labels.shape, dtype=np.uint8)
        source[linked[labels]] = 0
        distance = cv2.distanceTransform(source, cv2.DIST_C, 3)
        minimum_distance = np.full(len(stats), np.inf, dtype=np.float32)
        component_pixels = labels > 0
        np.minimum.at(
            minimum_distance,
            labels[component_pixels],
            distance[component_pixels],
        )
        promoted = (minimum_distance <= SMALL_COMPONENT_LINK_DISTANCE) & ~linked
        if not promoted.any():
            break
        maximum_link_distance = max(
            maximum_link_distance, float(minimum_distance[promoted].max())
        )
        linked |= promoted
    return maximum_link_distance


def fine_chain_metrics(image: np.ndarray) -> dict[str, object]:
    """Measure the preserved front-crossed silver chain contract."""

    labels, stats = _alpha_component_stats(image[:, :, 3], FINE_CHAIN_ROI)
    maximum_link_distance = _maximum_link_distance(labels, stats)

    _head_labels, head_stats = _alpha_component_stats(
        image[:, :, 3], SPECK_HEAD_ROI
    )
    head_areas = set(head_stats[1:, cv2.CC_STAT_AREA].tolist())
    endpoint_areas = tuple(
        area for area in FINE_CHAIN_ENDPOINT_AREAS if area in head_areas
    )
    return {
        "roi_xyxy": list(FINE_CHAIN_ROI),
        "link_count": int(
            (stats[1:, cv2.CC_STAT_AREA] >= FINE_CHAIN_MIN_COMPONENT_AREA).sum()
        ),
        "endpoint_areas": list(endpoint_areas),
        "maximum_link_distance_px": round(maximum_link_distance, 3),
        "alpha_threshold": HEADWEAR_COMPONENT_ALPHA_THRESHOLD,
        "minimum_link_area": FINE_CHAIN_MIN_COMPONENT_AREA,
        "link_distance_px": SMALL_COMPONENT_LINK_DISTANCE,
    }


def audit(  # noqa: PLR0914 - the report intentionally keeps all gate sections together
    pack_path: Path, portrait_path: Path, base_hair_path: Path
) -> dict[str, object]:
    pack_path = pack_path.resolve(strict=True)
    portrait_path = portrait_path.resolve(strict=True)
    base_hair_path = base_hair_path.resolve(strict=True)
    portrait = _read_png(portrait_path)
    sealed_pack_sha256 = hashlib.sha256(pack_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(pack_path) as archive:
        sealed_member_count = len(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        hair_poses = manifest["hairstyles"][0]["variants"][0]["poses"]
        front_crossed_front_declaration = next(
            item
            for item in hair_poses[FRONT_SILHOUETTE]
            if item["slot"] == "front"
        )
        front_crossed_back_declaration = next(
            item
            for item in hair_poses[FRONT_SILHOUETTE]
            if item["slot"] == "back"
        )
        front_crossed_front_raw = _decode_png(
            archive.read(front_crossed_front_declaration["path"]),
            front_crossed_front_declaration["path"],
        )
        front_crossed_back_raw = _decode_png(
            archive.read(front_crossed_back_declaration["path"]),
            front_crossed_back_declaration["path"],
        )
        front_hair = _expand_declared_layer(
            front_crossed_front_raw,
            front_crossed_front_declaration,
            portrait.shape[:2],
        )
        back_hair = _expand_declared_layer(
            front_crossed_back_raw,
            front_crossed_back_declaration,
            portrait.shape[:2],
        )

        headwear_by_silhouette = {}
        small_component_specks = {}
        front_crossed_headwear = None
        headwear_poses = manifest["headwear"][0]["variants"][0]["poses"]
        missing_hair_back_silhouettes = [
            silhouette
            for silhouette in REQUIRED_SILHOUETTES
            if silhouette not in hair_poses
        ]
        if missing_hair_back_silhouettes:
            raise ValueError(
                "Official pack is missing hair poses: "
                + ", ".join(missing_hair_back_silhouettes)
            )
        for silhouette, declarations in sorted(headwear_poses.items()):
            path = declarations[0]["path"]
            headwear = _decode_png(archive.read(path), path)
            headwear_by_silhouette[silhouette] = component_metrics(headwear)
            if silhouette == FRONT_SILHOUETTE:
                front_crossed_headwear = headwear
            hair_declarations = hair_poses[silhouette]
            silhouette_front_declaration = next(
                item for item in hair_declarations if item["slot"] == "front"
            )
            silhouette_back_declaration = next(
                item for item in hair_declarations if item["slot"] == "back"
            )
            front_raw = _decode_png(
                archive.read(silhouette_front_declaration["path"]),
                silhouette_front_declaration["path"],
            )
            back_raw = _decode_png(
                archive.read(silhouette_back_declaration["path"]),
                silhouette_back_declaration["path"],
            )
            small_component_specks[silhouette] = {
                "front": _owner_judge_layer_metrics(front_raw),
                "back": _owner_judge_layer_metrics(back_raw),
                "headwear": _owner_judge_layer_metrics(headwear),
            }

        empty_back = 0
        nonempty_back = 0
        for silhouette in REQUIRED_SILHOUETTES:
            declarations = hair_poses[silhouette]
            path = next(item["path"] for item in declarations if item["slot"] == "back")
            alpha = _decode_png(archive.read(path), path)[:, :, 3]
            if np.any(alpha):
                nonempty_back += 1
            else:
                empty_back += 1

    detached_components = {
        silhouette: metrics["unlinked_components"]
        for silhouette, metrics in headwear_by_silhouette.items()
    }
    detached = sum(len(components) for components in detached_components.values())
    detached_whitelist = []
    detached_unexpected = []
    for silhouette, components in detached_components.items():
        allowed_areas = DETACHED_HEADWEAR_WHITELIST.get(silhouette, frozenset())
        for component in components:
            area = int(component["area"])
            entry = {
                "silhouette": silhouette,
                "area": area,
                "bbox": component["bbox"],
                "distance_from_main_px": component["distance_from_main_px"],
            }
            if area in allowed_areas:
                entry["reason"] = DETACHED_HEADWEAR_WHITELIST_REASONS.get(
                    (silhouette, area), "明列的設計性分離珠飾。"
                )
                detached_whitelist.append(entry)
            else:
                detached_unexpected.append(entry)
    isolated_small_points = sum(
        int(metrics["isolated_count"])
        for silhouette_metrics in small_component_specks.values()
        for metrics in silhouette_metrics.values()
    )
    alpha_1_30_residuals = sum(
        int(metrics["alpha_1_30"])
        for silhouette_metrics in small_component_specks.values()
        for metrics in silhouette_metrics.values()
    )
    if front_crossed_headwear is None:
        raise ValueError("Official pack is missing the front-crossed headwear layer.")
    composite_specks = _owner_judge_layer_metrics(portrait)
    return {
        "sealed_source": {
            "path": str(pack_path),
            "sha256": sealed_pack_sha256,
            "member_count": sealed_member_count,
            "layer_source": "zip members",
        },
        "contract": {
            "head_roi_xyxy": list(HEAD_ROI),
            "brown_brightness_strict_range": [
                BROWN_BRIGHTNESS_MIN,
                BROWN_BRIGHTNESS_MAX,
            ],
            "brown_red_minus_blue_strict_min": BROWN_RED_BLUE_MARGIN,
            "detached_distance_strict_min_px": DETACHED_DISTANCE_PX,
            "chain_link_radius_px": HEADWEAR_CHAIN_LINK_RADIUS,
        },
        "hair": brown_hair_metrics(
            _read_png(portrait_path),
            front_hair,
            back_hair,
            _read_png(base_hair_path),
        ),
        "hair_back_slots": {
            "empty": empty_back,
            "nonempty": nonempty_back,
        },
        "composite_specks": composite_specks,
        "fine_chain": fine_chain_metrics(front_crossed_headwear),
        "headwear": {
            "detached_over_100px_total": detached,
            "non_whitelisted_detached_over_100px": len(detached_unexpected),
            "detached_whitelist": detached_whitelist,
            "detached_unexpected": detached_unexpected,
            "front_crossed": headwear_by_silhouette[FRONT_SILHOUETTE],
            "by_silhouette": headwear_by_silhouette,
        },
        "small_component_specks": small_component_specks,
        "quality_gate": {
            "empty_back": empty_back,
            "non_whitelisted_detached_over_100px": len(detached_unexpected),
            "isolated_small_points": isolated_small_points,
            "alpha_1_30_residuals": alpha_1_30_residuals,
            "composite_isolated_count": int(composite_specks["isolated_count"]),
            "passed": (
                not empty_back
                and not detached_unexpected
                and isolated_small_points == 0
                and alpha_1_30_residuals == 0
                and int(composite_specks["isolated_count"])
                <= MAX_COMPOSITE_ISOLATED_COUNT
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--portrait", type=Path, default=DEFAULT_PORTRAIT)
    parser.add_argument("--base-hair", type=Path, default=DEFAULT_BASE_HAIR)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = audit(arguments.pack, arguments.portrait, arguments.base_hair)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["quality_gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
