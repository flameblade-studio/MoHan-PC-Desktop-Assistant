"""Build 24 staging outfit ownership templates from 3D anatomy controls.

The neutral renderer has no hair or ornament geometry.  This tool therefore
does not invent those masks.  Its output is an outfit search/ownership
template that must later be intersected with an accepted RGBA master.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


SIZE = (1024, 1536)
VIEWS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15))
GARMENT_IDS = (2, 3, 4, 6, 7, 9, 10, 12, 13)
EXPOSED_IDS = (1, 5, 8, 11, 14)


def bbox(mask: np.ndarray, label: str) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError(f"empty {label}")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def dilate(mask: np.ndarray, size: int) -> np.ndarray:
    kernel = np.ones((size, size), dtype=np.uint8)
    return cv2.dilate(mask.astype(np.uint8), kernel, iterations=1) > 0


def load_l(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "L" or image.size != SIZE:
            raise ValueError(f"expected L {SIZE}: {path} mode={image.mode} size={image.size}")
        return np.asarray(image, dtype=np.uint8).copy()


def outfit_template(part_id: np.ndarray, silhouette: np.ndarray) -> np.ndarray:
    garment_seed = np.isin(part_id, GARMENT_IDS)
    exposed = np.isin(part_id, EXPOSED_IDS)
    tx0, ty0, tx1, ty1 = bbox(part_id == 2, "torso part-ID")
    lx0, _, lx1, _ = bbox(np.isin(part_id, (9, 10, 12, 13)), "leg part-ID")
    fx0, fy0, fx1, _ = bbox(np.isin(part_id, (11, 14)), "feet part-ID")

    cx = (tx0 + tx1) // 2
    shoulder_half = max((tx1 - tx0) // 2 + 36, 96)
    hip_half = max((lx1 - lx0) // 2 + 38, 104)
    hem_half = max((fx1 - fx0) // 2 + 54, hip_half + 34)
    y_top = max(0, ty0 - 28)
    y_hip = min(SIZE[1] - 1, ty1 + 20)
    y_hem = min(SIZE[1] - 1, fy0 + 22)

    envelope_image = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(envelope_image)
    draw.polygon(
        [
            (cx - shoulder_half, y_top),
            (cx + shoulder_half, y_top),
            (cx + hip_half, y_hip),
            (cx + hem_half, y_hem),
            (cx - hem_half, y_hem),
            (cx - hip_half, y_hip),
        ],
        fill=255,
    )
    envelope = np.asarray(envelope_image, dtype=np.uint8) > 0

    # The arms/torso/legs come from projected 3D part IDs.  The robe polygon is
    # parameterized only by their bboxes, so it remains traceable to geometry.
    outfit = dilate(garment_seed, 31) | envelope
    outfit &= ~dilate(exposed, 17)
    outfit |= (part_id == 255) & dilate(outfit, 9)
    outfit &= dilate(silhouette > 0, 41) | envelope
    return outfit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundles-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.bundles_root.is_dir():
        raise FileNotFoundError(args.bundles_root)
    args.output_root.mkdir(parents=True, exist_ok=True)

    written = 0
    pixel_counts: list[int] = []
    for view in VIEWS:
        bundle = args.bundles_root / view
        part_id = load_l(bundle / f"{view}_part-id.png")
        silhouette = load_l(bundle / f"{view}_silhouette.png")
        outfit = outfit_template(part_id, silhouette)
        if not np.any(outfit):
            raise ValueError(f"empty outfit ownership template: {view}")
        exposed_overlap = outfit & np.isin(part_id, EXPOSED_IDS)
        if np.any(exposed_overlap):
            raise ValueError(f"outfit template overlaps exposed body ownership: {view}")
        Image.fromarray(outfit.astype(np.uint8) * 255, mode="L").save(
            args.output_root / f"{view}_default_outfit_mask.png"
        )
        written += 1
        pixel_counts.append(int(np.count_nonzero(outfit)))

    if written != 24:
        raise RuntimeError(f"expected 24 outfit masks, wrote {written}")
    print(
        "PASS_CANONICAL24_OUTFIT_STAGING "
        f"masks={written} views=24 min_pixels={min(pixel_counts)} "
        f"max_pixels={max(pixel_counts)} exposed_body_overlap=0 "
        "ornament=BLOCKED_NO_GEOMETRY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
