#!/usr/bin/env python3
"""Build mutually-exclusive 2.5D semantic shells for one canonical view."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


CANVAS = (1024, 1536)


def load_rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    if image.size != CANVAS:
        raise ValueError(f"expected {CANVAS}, got {image.size}: {path}")
    return np.asarray(image, dtype=np.uint8)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def masked_rgba(source: np.ndarray, mask: np.ndarray) -> np.ndarray:
    output = np.zeros_like(source)
    output[mask] = source[mask]
    output[:, :, 3] = np.where(mask, source[:, :, 3], 0)
    return output


def save_rgba(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array, "RGBA").save(path)


def save_depth(depth: np.ndarray, mask: np.ndarray, path: Path) -> None:
    output = np.zeros_like(depth)
    output[mask] = depth[mask]
    Image.fromarray(output, "L").save(path)


def composite_on(image: np.ndarray, background: tuple[int, int, int]) -> Image.Image:
    rgba = Image.fromarray(image, "RGBA")
    base = Image.new("RGBA", CANVAS, (*background, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anatomy", type=Path, required=True)
    parser.add_argument("--outfit", type=Path, required=True)
    parser.add_argument("--hair", type=Path, required=True)
    parser.add_argument("--ornament", type=Path, required=True)
    parser.add_argument("--depth", type=Path, required=True)
    parser.add_argument("--missing-mask", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=False)
    anatomy = load_rgba(args.anatomy)
    outfit = load_rgba(args.outfit)
    hair = load_rgba(args.hair)
    ornament = load_rgba(args.ornament)
    depth = np.asarray(Image.open(args.depth).convert("L"), dtype=np.uint8)
    if depth.shape != (CANVAS[1], CANVAS[0]):
        raise ValueError(f"depth shape mismatch: {depth.shape}")

    outfit_visible = outfit[:, :, 3] > 0
    rgb = outfit[:, :, :3].astype(np.int16)
    high = rgb.max(axis=2)
    low = rgb.min(axis=2)
    chroma = high - low
    # The clean semantic control has explicit blue outer robe and neutral-white
    # inner dress.  Partition only existing outfit pixels; never invent cloth.
    inner = outfit_visible & (low > 145) & (chroma < 70)
    outer = outfit_visible & ~inner

    hair_visible = hair[:, :, 3] > 0
    yy, xx = np.indices(hair_visible.shape)
    # Upper/central mass is the back shell; the two long side curtains stay
    # individually addressable for yaw interpolation and DLC occlusion.
    back = hair_visible & ((yy < 360) | ((xx >= 465) & (xx <= 560)))
    remaining = hair_visible & ~back
    hair_left = remaining & (xx < 512)
    hair_right = remaining & ~hair_left

    masks = {
        "body": anatomy[:, :, 3] > 0,
        "outer_robe_wide_sleeves": outer,
        "inner_white_dress_skirt": inner,
        "hair_back": back,
        "hair_left": hair_left,
        "hair_right": hair_right,
        "ornament": ornament[:, :, 3] > 0,
    }
    sources = {
        "body": anatomy,
        "outer_robe_wide_sleeves": outfit,
        "inner_white_dress_skirt": outfit,
        "hair_back": hair,
        "hair_left": hair,
        "hair_right": hair,
        "ornament": ornament,
    }

    occupied = np.zeros_like(hair_visible)
    overlap_pixels = 0
    output_paths: dict[str, str] = {}
    shell_images: list[tuple[str, np.ndarray]] = []
    for name, mask in masks.items():
        overlap_pixels += int((occupied & mask).sum())
        occupied |= mask
        shell = masked_rgba(sources[name], mask)
        rgba_path = args.output_dir / f"{args.view_id}_{name}-shell-rgba.png"
        depth_path = args.output_dir / f"{args.view_id}_{name}-shell-depth.png"
        save_rgba(shell, rgba_path)
        save_depth(depth, mask, depth_path)
        output_paths[f"{name}_rgba"] = str(rgba_path.resolve())
        output_paths[f"{name}_depth"] = str(depth_path.resolve())
        shell_images.append((name, shell))
    if overlap_pixels:
        raise ValueError(f"shell ownership overlap: {overlap_pixels}")

    combined = np.zeros_like(anatomy)
    for name, shell in shell_images:
        take = shell[:, :, 3] > 0
        combined[take] = shell[take]
    combined_path = args.output_dir / f"{args.view_id}_separated-shells-combined-rgba.png"
    save_rgba(combined, combined_path)
    output_paths["combined_rgba"] = str(combined_path.resolve())

    missing = load_rgba(args.missing_mask)
    panels: list[tuple[str, Image.Image]] = []
    for name, shell in shell_images:
        panels.append((name, composite_on(shell, (96, 96, 96))))
    panels.append(("combined", composite_on(combined, (96, 96, 96))))
    panels.append(("missing", composite_on(missing, (32, 32, 32))))
    thumb_size = (256, 384)
    contact = Image.new("RGB", (thumb_size[0] * 3, (thumb_size[1] + 28) * 3), (24, 27, 31))
    draw = ImageDraw.Draw(contact)
    for index, (name, panel) in enumerate(panels):
        x = (index % 3) * thumb_size[0]
        y = (index // 3) * (thumb_size[1] + 28)
        contact.paste(panel.resize(thumb_size, Image.Resampling.LANCZOS), (x, y + 28))
        draw.text((x + 6, y + 7), name, fill=(240, 240, 240))
    contact_path = args.output_dir / f"{args.view_id}_separated-25d-shells-contact.png"
    contact.save(contact_path)
    output_paths["contact"] = str(contact_path.resolve())

    manifest_path = args.output_dir / f"{args.view_id}.separated-25d-shells.json"
    manifest = {
        "schema": "mohan.separated-25d-shells.v1",
        "view_id": args.view_id,
        "accepted": False,
        "formal": False,
        "canvas": [1024, 1536],
        "ownership_overlap_pixels": overlap_pixels,
        "shells": output_paths,
        "missing_mask": str(args.missing_mask.resolve()),
        "policy": {
            "outfit_is_not_part_of_body": True,
            "hair_is_not_part_of_outfit": True,
            "ornament_is_not_part_of_hair": True,
            "missing_pixels_are_not_extrapolated": True,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    hashes = {path: sha256(Path(path)) for path in output_paths.values()}
    hashes[str(manifest_path.resolve())] = sha256(manifest_path)
    (args.output_dir / "sha256.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"manifest": str(manifest_path.resolve()), "contact": str(contact_path.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
