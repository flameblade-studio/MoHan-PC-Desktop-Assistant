#!/usr/bin/env python3
"""Carve loose clothing shells from registered multi-yaw authority silhouettes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


CANVAS = (1024, 1536)
LOW = (256, 384)
DEPTH_SAMPLES = 128


def load_rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    if image.size != CANVAS:
        raise ValueError(f"expected {CANVAS}, got {image.size}: {path}")
    return np.asarray(image, dtype=np.uint8)


def clean(mask: np.ndarray, close: int = 11) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close, close))
    result = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    return result > 0


def silhouette(mask: np.ndarray, keep: int = 2) -> np.ndarray:
    closed = clean(mask, 25)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(closed.astype(np.uint8), 8)
    ranked = sorted(range(1, count), key=lambda label: stats[label, cv2.CC_STAT_AREA], reverse=True)[:keep]
    kept = np.isin(labels, ranked)
    # Authority art contains embroidery and lighting gaps.  A visual hull uses
    # the alpha contour, so close internal row gaps without extending beyond
    # each retained component's left/right boundary.
    filled = np.zeros_like(kept)
    for label in ranked:
        component = labels == label
        ys = np.flatnonzero(component.any(axis=1))
        for y in ys:
            xs = np.flatnonzero(component[y])
            filled[y, xs[0]:xs[-1] + 1] = True
    return clean(filled, 13)


def segment(image: np.ndarray) -> dict[str, np.ndarray]:
    rgb = image[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    high, low = rgb.max(axis=2), rgb.min(axis=2)
    chroma = high - low
    visible = image[:, :, 3] > 8
    blue = visible & (b > r + 8) & (b >= g - 10)
    neutral = visible & (low > 138) & (chroma < 76)
    outfit = silhouette(blue | neutral, 3)
    ys, xs = np.where(outfit)
    if not len(xs):
        raise ValueError("empty outfit silhouette")
    centre = int(np.median(xs))
    # Sleeves are upper side lobes of the real outfit alpha, not body-mesh arms.
    upper = np.indices(outfit.shape)[0] < int(np.quantile(ys, 0.58))
    left_sleeve = silhouette(outfit & upper & (np.indices(outfit.shape)[1] < centre - 62), 1)
    right_sleeve = silhouette(outfit & upper & (np.indices(outfit.shape)[1] > centre + 62), 1)
    inner = silhouette(neutral & (np.indices(outfit.shape)[0] > int(np.quantile(ys, 0.12))), 1)
    outer = silhouette(blue & ~left_sleeve & ~right_sleeve, 2)
    return {
        "outer_robe": outer,
        "inner_skirt": inner,
        "sleeve_left": left_sleeve,
        "sleeve_right": right_sleeve,
    }


def carve_visual_hull(masks: list[np.ndarray], yaws: list[float], target_yaw: float) -> np.ndarray:
    small = [
        np.asarray(Image.fromarray((mask * 255).astype(np.uint8), "L").resize(LOW, Image.Resampling.NEAREST)) > 0
        for mask in masks
    ]
    x = np.linspace(-1.0, 1.0, LOW[0], dtype=np.float32)
    z = np.linspace(-1.0, 1.0, DEPTH_SAMPLES, dtype=np.float32)
    xx, zz = np.meshgrid(x, z, indexing="ij")
    occupied = np.ones((LOW[1], LOW[0], DEPTH_SAMPLES), dtype=bool)
    for silhouette, yaw in zip(small, yaws, strict=True):
        angle = np.deg2rad(yaw)
        projected = xx * np.cos(angle) + zz * np.sin(angle)
        u = np.clip(np.rint((projected + 1.0) * 0.5 * (LOW[0] - 1)), 0, LOW[0] - 1).astype(np.int32)
        sampled = silhouette[:, u]
        occupied &= sampled
    angle = np.deg2rad(target_yaw)
    projected = xx * np.cos(angle) + zz * np.sin(angle)
    u = np.clip(np.rint((projected + 1.0) * 0.5 * (LOW[0] - 1)), 0, LOW[0] - 1).astype(np.int32)
    output = np.zeros((LOW[1], LOW[0]), dtype=bool)
    flat_u = u.ravel()
    for y in range(LOW[1]):
        active = occupied[y].ravel()
        if np.any(active):
            output[y, np.unique(flat_u[active])] = True
    full = np.asarray(
        Image.fromarray((output * 255).astype(np.uint8), "L").resize(CANVAS, Image.Resampling.BILINEAR)
    ) > 96
    return clean(full, 5)


def rgba_from_mask(mask: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    output = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    output[mask] = (*color, 255)
    return output


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", nargs=2, metavar=("YAW", "RGBA"), required=True)
    parser.add_argument("--target-yaw", type=float, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.source) < 3:
        raise ValueError("at least three calibrated silhouettes are required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    yaws = [float(yaw) for yaw, _ in args.source]
    paths = [Path(path) for _, path in args.source]
    segmented = [segment(load_rgba(path)) for path in paths]
    colors = {
        "outer_robe": (35, 74, 126),
        "inner_skirt": (236, 239, 244),
        "sleeve_left": (46, 90, 145),
        "sleeve_right": (46, 90, 145),
    }
    masks: dict[str, np.ndarray] = {}
    for domain in colors:
        masks[domain] = carve_visual_hull(
            [entry[domain] for entry in segmented], yaws, args.target_yaw
        )
    # Establish exclusive ownership without changing the union silhouette.
    masks["sleeve_left"] &= ~masks["inner_skirt"]
    masks["sleeve_right"] &= ~masks["inner_skirt"] & ~masks["sleeve_left"]
    masks["outer_robe"] &= ~masks["inner_skirt"] & ~masks["sleeve_left"] & ~masks["sleeve_right"]
    occupied = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    overlap = 0
    outputs: dict[str, str] = {}
    rendered: list[tuple[str, np.ndarray]] = []
    for domain in ("outer_robe", "inner_skirt", "sleeve_left", "sleeve_right"):
        overlap += int((occupied & masks[domain]).sum())
        occupied |= masks[domain]
        rgba = rgba_from_mask(masks[domain], colors[domain])
        path = args.output_dir / f"{args.view_id}_{domain}-visual-hull-rgba.png"
        Image.fromarray(rgba, "RGBA").save(path)
        outputs[domain] = str(path.resolve())
        rendered.append((domain, rgba))
    if overlap:
        raise ValueError(f"visual hull ownership overlap: {overlap}")
    combined = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    for _, rgba in rendered:
        take = rgba[:, :, 3] > 0
        combined[take] = rgba[take]
    combined_path = args.output_dir / f"{args.view_id}_clothing-visual-hull-combined-rgba.png"
    Image.fromarray(combined, "RGBA").save(combined_path)
    outputs["combined"] = str(combined_path.resolve())

    panel_size = (256, 384)
    contact = Image.new("RGB", (panel_size[0] * 3, (panel_size[1] + 28) * 2), (32, 35, 40))
    draw = ImageDraw.Draw(contact)
    panels = rendered + [("combined", combined)]
    for index, (name, rgba) in enumerate(panels):
        x = (index % 3) * panel_size[0]
        y = (index // 3) * (panel_size[1] + 28)
        base = Image.new("RGBA", CANVAS, (104, 104, 104, 255))
        base.alpha_composite(Image.fromarray(rgba, "RGBA"))
        contact.paste(base.convert("RGB").resize(panel_size, Image.Resampling.LANCZOS), (x, y + 28))
        draw.text((x + 6, y + 7), name, fill=(245, 245, 245))
    contact_path = args.output_dir / f"{args.view_id}_clothing-visual-hull-contact.png"
    contact.save(contact_path)
    outputs["contact"] = str(contact_path.resolve())

    manifest_path = args.output_dir / f"{args.view_id}.clothing-visual-hull.json"
    manifest = {
        "schema": "mohan.clothing-visual-hull.v1",
        "view_id": args.view_id,
        "target_yaw": args.target_yaw,
        "accepted": False,
        "formal": False,
        "sources": [{"yaw": yaw, "path": str(path.resolve()), "sha256": sha256(path)} for yaw, path in zip(yaws, paths, strict=True)],
        "outputs": outputs,
        "ownership_overlap_pixels": overlap,
        "method": "orthographic_multi_silhouette_voxel_carving",
        "old_body_topology_used_for_clothing_contour": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path.resolve()), "contact": str(contact_path.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
