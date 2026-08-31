"""Extract traceable hair/ornament ownership from one accepted RGBA master."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SIZE = (1024, 1536)


def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != SIZE:
            raise ValueError(f"expected {SIZE}: {path} size={image.size}")
        return np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()


def binary(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != SIZE:
            raise ValueError(f"expected mask {SIZE}: {path} size={image.size}")
        if image.mode == "RGBA":
            return np.asarray(image, dtype=np.uint8)[:, :, 3] > 0
        return np.asarray(image.convert("L"), dtype=np.uint8) > 0


def parse_numbers(value: str, count: int, label: str) -> tuple[int, ...]:
    values = tuple(int(item) for item in value.split(","))
    if len(values) != count:
        raise ValueError(f"{label} requires {count} comma-separated integers")
    return values


def save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray(mask.astype(np.uint8) * 255, mode="L").save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--outfit-mask", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--face-ellipse", required=True, help="cx,cy,rx,ry")
    parser.add_argument("--ornament-anchor", required=True, help="cx,cy,rx,ry")
    parser.add_argument("--birefnet-alpha", type=Path)
    parser.add_argument("--hair-seed", type=Path, action="append", default=[])
    parser.add_argument("--ornament-seed", type=Path)
    args = parser.parse_args()

    source = rgba(args.master)
    rgb = source[:, :, :3]
    foreground = source[:, :, 3] > 0
    if args.birefnet_alpha is not None:
        foreground &= binary(args.birefnet_alpha)
    outfit = (
        binary(args.outfit_mask) & foreground
        if args.outfit_mask is not None
        else np.zeros(foreground.shape, dtype=bool)
    )
    cx, cy, rx, ry = parse_numbers(args.face_ellipse, 4, "face ellipse")
    ox, oy, orx, ory = parse_numbers(args.ornament_anchor, 4, "ornament anchor")
    yy, xx = np.indices(foreground.shape)
    face = (((xx - cx) / max(1, rx)) ** 2 + ((yy - cy) / max(1, ry)) ** 2) <= 1.0
    ornament_roi = (((xx - ox) / max(1, orx)) ** 2 + ((yy - oy) / max(1, ory)) ** 2) <= 1.0

    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    saturation = maximum.astype(np.int16) - minimum.astype(np.int16)
    # Bright metal only.  A lower threshold misclassifies grey hair highlights
    # as ornament and leaves dark hair welded into the outfit overlay.
    silver = (maximum > 185) & (saturation < 72)
    blue_gem = (
        (rgb[:, :, 2] > 95)
        & (rgb[:, :, 2] > rgb[:, :, 0] * 1.12)
        & (rgb[:, :, 2] > rgb[:, :, 1] * 1.04)
    )
    ornament = ornament_roi & (silver | blue_gem)
    if args.ornament_seed is not None:
        ornament |= binary(args.ornament_seed) & ornament_roi
    ornament &= foreground & ~face & ~outfit

    head_zone = (
        (xx >= cx - int(1.15 * rx)) & (xx <= cx + int(1.15 * rx))
        & (yy >= max(0, cy - int(1.75 * ry))) & (yy <= cy + int(0.75 * ry))
    )
    lock_zone = (
        (xx >= cx - int(1.05 * rx)) & (xx <= cx + int(1.05 * rx))
        & (yy >= cy - int(0.15 * ry)) & (yy <= cy + int(4.2 * ry))
    )
    channel_minimum = rgb.min(axis=2)
    blue_minus_red = rgb[:, :, 2].astype(np.int16) - rgb[:, :, 0].astype(np.int16)
    dark_hair = (
        (maximum < 155)
        & ((maximum - channel_minimum) < 55)
        & (blue_minus_red < 36)
    )
    seed_union = np.zeros(foreground.shape, dtype=bool)
    for seed in args.hair_seed:
        seed_union |= binary(seed) & foreground
    upper_hair_zone = (
        (yy >= cy - int(2.55 * ry))
        & (yy <= cy + int(0.55 * ry))
        & (xx >= cx - int(1.40 * rx))
        & (xx <= cx + int(1.40 * rx))
    )
    left_strand_zone = (
        (yy > cy + int(0.55 * ry))
        & (yy <= cy + int(4.30 * ry))
        & (xx >= cx - int(1.50 * rx))
        & (xx <= cx - int(0.65 * rx))
    )
    right_strand_zone = (
        (yy > cy + int(0.55 * ry))
        & (yy <= cy + int(4.30 * ry))
        & (xx >= cx + int(0.65 * rx))
        & (xx <= cx + int(1.50 * rx))
    )
    # Long hair crosses the white inner robe.  The legacy hair layers are only
    # spatial hints and contain robe pixels in that overlap, so require a dark
    # source pixel below the head.  The upper envelope may retain brighter
    # specular hair because it cannot reach clothing.
    upper_hair_colour = (
        (maximum < 225)
        & ((maximum - channel_minimum) < 110)
        & (blue_minus_red < 75)
    )
    strand_colour = (
        (maximum < 170)
        & ((maximum - channel_minimum) < 85)
        & (blue_minus_red < 55)
    )
    seed_hair = np.zeros(foreground.shape, dtype=bool)
    if np.any(seed_union):
        # Legacy seeds are location hints only.  Their connected components can
        # be split by the face and can also contain robe pixels, so ownership is
        # selected by a tight head/strand envelope plus source colour instead.
        seed_hair = seed_union & (
            (upper_hair_zone & upper_hair_colour)
            | ((left_strand_zone | right_strand_zone) & strand_colour)
        )
    hair = foreground & dark_hair & head_zone
    if np.any(seed_hair):
        hair |= seed_hair
    else:
        hair |= foreground & dark_hair & lock_zone
    # Source-derived recovery for hair pixels omitted by legacy layer hints.
    # The envelope is anchored to the 3D head geometry; it cannot reach the
    # sleeves or skirt, and it keeps all already-visible long hair in core.
    hair |= foreground & upper_hair_zone & upper_hair_colour & ~face & ~ornament
    hair |= foreground & (left_strand_zone | right_strand_zone) & strand_colour
    hair &= ~face & ~outfit & ~ornament
    hair = cv2.morphologyEx(
        hair.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)
    ) > 0
    allowed_hair_colour = (
        (upper_hair_zone & upper_hair_colour)
        | ((left_strand_zone | right_strand_zone) & strand_colour)
    )
    hair &= foreground & allowed_hair_colour & ~face & ~outfit & ~ornament

    checks = {
        "hair_pixels": int(np.count_nonzero(hair)),
        "ornament_pixels": int(np.count_nonzero(ornament)),
        "hair_ornament_overlap": int(np.count_nonzero(hair & ornament)),
        "hair_outfit_overlap": int(np.count_nonzero(hair & outfit)),
        "ornament_outfit_overlap": int(np.count_nonzero(ornament & outfit)),
        "hair_face_overlap": int(np.count_nonzero(hair & face)),
        "ornament_face_overlap": int(np.count_nonzero(ornament & face)),
    }
    if checks["hair_pixels"] == 0 or checks["ornament_pixels"] == 0:
        raise ValueError(f"empty extracted ownership: {checks}")
    if any(value for key, value in checks.items() if key.endswith("overlap")):
        raise ValueError(f"ownership overlap: {checks}")

    args.output_root.mkdir(parents=True, exist_ok=True)
    save_mask(args.output_root / f"{args.view_id}_hair_mask.png", hair)
    save_mask(args.output_root / f"{args.view_id}_ornament_mask.png", ornament)
    print("PASS_HAIR_ORNAMENT_SMOKE " + " ".join(f"{key}={value}" for key, value in checks.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
