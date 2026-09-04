"""Measure visible hair and headwear defects in the sealed official outfit pack.

The audit deliberately reads the same sealed archive and composed portrait that
users receive.  It therefore catches losses introduced by extraction, assembly,
or runtime composition instead of trusting an intermediate layer report.
"""

from __future__ import annotations

lazy import argparse
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
    HEADWEAR_COMPONENT_LINK_DISTANCE,
    HEADWEAR_DETACHED_DISTANCE,
    HEADWEAR_CHAIN_ANCHOR_MIN_AREA,
)

DEFAULT_PACK: Final = (
    ROOT / "assets/official-packs/mohan.official.blue-white-hanfu.mohan-outfit"
)
DEFAULT_PORTRAIT: Final = ROOT / "docs/media/portraits/idle_front.png"
DEFAULT_BASE_HAIR: Final = ROOT / "assets/expressions/layered/front_hair_back.png"
FRONT_SILHOUETTE: Final = "front-crossed"
HEAD_ROI: Final = (360, 150, 900, 470)
SPECK_HEAD_ROI: Final = (300, 100, 1000, 520)
SPECK_FULL_BODY_ROI: Final = (250, 30, 800, 420)
SPECK_ALPHA_THRESHOLD: Final = 30
SPECK_SMALL_COMPONENT_MAX_AREA: Final = 12
SPECK_LARGE_COMPONENT_MIN_AREA: Final = 60
SPECK_DIRECT_DISTANCE_PX: Final = 3
BROWN_BRIGHTNESS_MIN: Final = 70
BROWN_BRIGHTNESS_MAX: Final = 150
BROWN_RED_BLUE_MARGIN: Final = 18
DETACHED_DISTANCE_PX: Final = float(HEADWEAR_DETACHED_DISTANCE)
IMAGE_DIMENSIONS: Final = 3
RGBA_CHANNELS: Final = 4
OPAQUE: Final = 255


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


def _asset_path(manifest: dict[str, object], category: str, slot: str) -> str:
    collection = manifest[category]
    if not isinstance(collection, list) or len(collection) != 1:
        raise ValueError(f"Expected one official {category} item.")
    variants = collection[0]["variants"]
    poses = variants[0]["poses"]
    declarations = poses[FRONT_SILHOUETTE]
    return next(item["path"] for item in declarations if item["slot"] == slot)


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


def _linked_unattached_count(binary: np.ndarray) -> int:
    radius = HEADWEAR_CHAIN_LINK_RADIUS
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1)
    )
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        cv2.dilate(binary, kernel), connectivity=8
    )
    if count <= 1:
        return 0
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    main_x, main_y, main_width, main_height = stats[main, :4]
    unattached = 0
    for label in range(1, count):
        if label == main:
            continue
        x, y, width, height = stats[label, :4]
        dx = max(main_x - (x + width), x - (main_x + main_width), 0)
        dy = max(main_y - (y + height), y - (main_y + main_height), 0)
        if float(np.hypot(dx, dy)) > DETACHED_DISTANCE_PX:
            unattached += 1
    return unattached


def component_metrics(image: np.ndarray) -> dict[str, object]:
    """Measure raw components and components linked by visible chain spacing."""

    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (image[:, :, 3] > 0).astype(np.uint8), connectivity=8
    )
    if count == 1:
        return {
            "component_count": 0,
            "main_component_area": 0,
            "detached_over_100px": 0,
            "unlinked_over_100px": 0,
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
    return {
        "component_count": len(components),
        "main_component_area": int(stats[main_label, cv2.CC_STAT_AREA]),
        "detached_over_100px": sum(
            item["distance_from_main_px"] > DETACHED_DISTANCE_PX
            for item in components
        ),
        "unlinked_over_100px": _linked_unattached_count(
            (image[:, :, 3] > 0).astype(np.uint8)
        ),
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
    linked[1:] = stats[1:, cv2.CC_STAT_AREA] >= anchor_area
    while True:
        minimum_distance = _minimum_distance_to_components(labels, linked)
        promoted = (minimum_distance <= HEADWEAR_COMPONENT_LINK_DISTANCE) & ~linked
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
    link_visible = (
        crop[:, :, 3] > HEADWEAR_COMPONENT_ALPHA_THRESHOLD
    ).astype(np.uint8)
    _link_count, link_labels, link_stats, _ = cv2.connectedComponentsWithStats(
        link_visible, connectivity=8
    )
    anchor_area = (
        HEADWEAR_CHAIN_ANCHOR_MIN_AREA
        if source_crop is not None
        else SPECK_LARGE_COMPONENT_MIN_AREA
    )
    return link_labels, _promote_linked_components(link_labels, link_stats, anchor_area)


def _empty_speck_metrics(roi: tuple[int, int, int, int]) -> dict[str, object]:
    x0, y0, x1, y1 = roi
    return {
        "roi_xyxy": [x0, y0, x1, y1],
        "component_count": 0,
        "large_component_count": 0,
        "small_component_count": 0,
        "direct_definition_count": 0,
        "isolated_count": 0,
    }


def isolated_speck_metrics(
    image: np.ndarray,
    *,
    roi: tuple[int, int, int, int] = SPECK_HEAD_ROI,
    source_alpha: np.ndarray | None = None,
) -> dict[str, object]:
    """Measure small composite specks and the N-linked chain-aware remainder.

    ``direct_definition_count`` is the owner's original diagnostic: alpha>30,
    area<=12, and Chebyshev distance>3 from every area>60 component.  The
    release gate's ``isolated_count`` additionally treats a fine-chain section
    as non-isolated when it reaches an area>60 anchor through the measured
    transitive N-neighbour rule.  This keeps the gate aligned with the cleanup
    rule rather than mistaking a chain's individual links for specks.  When
    ``source_alpha`` is supplied, only pixels painted by that source layer are
    attributed to this gate; this prevents an unrelated base-hair fragment from
    being blamed on headwear.
    """

    x0, y0, x1, y1, crop = _bounded_roi(image, roi)
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
        "isolated_count": int((small & ~small_linked).sum()),
        "link_distance_px": HEADWEAR_COMPONENT_LINK_DISTANCE,
    }


def audit(pack_path: Path, portrait_path: Path, base_hair_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(pack_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        front_path = _asset_path(manifest, "hairstyles", "front")
        back_path = _asset_path(manifest, "hairstyles", "back")
        front_hair = _decode_png(archive.read(front_path), front_path)
        back_hair = _decode_png(archive.read(back_path), back_path)

        headwear_by_silhouette = {}
        headwear_poses = manifest["headwear"][0]["variants"][0]["poses"]
        for silhouette, declarations in sorted(headwear_poses.items()):
            path = declarations[0]["path"]
            headwear_by_silhouette[silhouette] = component_metrics(
                _decode_png(archive.read(path), path)
            )

        hair_poses = manifest["hairstyles"][0]["variants"][0]["poses"]
        empty_back = 0
        nonempty_back = 0
        for declarations in hair_poses.values():
            path = next(item["path"] for item in declarations if item["slot"] == "back")
            alpha = _decode_png(archive.read(path), path)[:, :, 3]
            if np.any(alpha):
                nonempty_back += 1
            else:
                empty_back += 1

    detached = sum(
        item["unlinked_over_100px"] for item in headwear_by_silhouette.values()
    )
    return {
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
        "composite_specks": isolated_speck_metrics(_read_png(portrait_path)),
        "headwear": {
            "detached_over_100px_total": detached,
            "front_crossed": headwear_by_silhouette[FRONT_SILHOUETTE],
            "by_silhouette": headwear_by_silhouette,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
