#!/usr/bin/env python3
"""Build a geometry-faithful B00-palette control while keeping ownership separate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--hair-mask", type=Path)
    parser.add_argument("--jaw13-json", type=Path, required=True)
    parser.add_argument("--jaw-authority", type=Path, required=True)
    parser.add_argument("--b00", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prefix = args.view_id
    silhouette = np.asarray(Image.open(args.bundle / f"{prefix}_silhouette.png").convert("L")) > 0
    outfit_raw = np.asarray(Image.open(args.bundle / f"{prefix}_ownership-outfit.png").convert("L")) > 0
    ornament_raw = np.asarray(Image.open(args.bundle / f"{prefix}_ownership-ornament.png").convert("L")) > 16
    shaded = np.asarray(Image.open(args.bundle / f"{prefix}_shaded-render.png").convert("L"), dtype=np.float32) / 255.0
    hair = (
        np.asarray(Image.open(args.hair_mask).convert("L")) > 0
        if args.hair_mask
        else np.zeros_like(silhouette)
    )
    # Do not reuse the failed B00 texture warp as a hair shape. The 3D bundle
    # has no hair geometry, so hair remains an independent (possibly empty)
    # domain and checkpoint-16 supplies the actual style reference.
    ornament = ornament_raw & ~hair
    hair &= ~ornament
    yy, xx = np.indices(silhouette.shape)
    near_body = cv2.dilate(silhouette.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))) > 0
    outfit = outfit_raw & ((yy >= 650) | near_body) & ~hair & ~ornament
    anatomy = silhouette & ~outfit & ~hair & ~ornament

    # Jaw13 is only the target mesh correspondence. Its generic shape is never
    # treated as MoHan identity. Extract a lower-face curve from checkpoint-16,
    # normalize that authority curve, then map it to the 13 target x positions.
    jaw_payload = json.loads(args.jaw13_json.read_text(encoding="utf-8"))
    target_points = np.asarray([item["screen_xy"] for item in jaw_payload["candidates"]], dtype=np.float32)
    authority = np.asarray(Image.open(args.jaw_authority).convert("RGB"))
    red, green, blue_channel = [authority[:, :, index] for index in range(3)]
    skin_mask = (
        (red > 125)
        & (green > 85)
        & (blue_channel > 75)
        & (red > green * 1.025)
        & (green > blue_channel * 0.93)
    ).astype(np.uint8)
    skin_mask[:280] = 0
    skin_mask[900:] = 0
    skin_mask[:, :150] = 0
    skin_mask[:, 720:] = 0
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(skin_mask, 8)
    if count < 2:
        raise ValueError("checkpoint-16 jaw authority skin component missing")
    authority_face = labels == (1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])))
    contour_set, _ = cv2.findContours(authority_face.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contour_set, key=cv2.contourArea)[:, 0, :].astype(np.float32)
    lower = contour[contour[:, 1] >= np.percentile(contour[:, 1], 58)]
    order = np.argsort(lower[:, 0])
    lower = lower[order]
    source_x = np.linspace(lower[:, 0].min(), lower[:, 0].max(), 13)
    source_y = np.asarray([np.max(lower[np.abs(lower[:, 0] - value) < 5, 1]) for value in source_x])
    normalized_y = (source_y - source_y.min()) / max(1.0, float(source_y.max() - source_y.min()))
    target_curve = target_points.copy()
    generic_min, generic_max = float(target_points[:, 1].min()), float(target_points[:, 1].max())
    target_curve[:, 1] = generic_min + normalized_y * (generic_max - generic_min)
    target_curve = target_curve[np.argsort(target_curve[:, 0])]
    # Persist a machine-only jaw geometry channel. The full-body RGB remains
    # label-free and the generic mesh curve is never painted as identity.
    jaw_geometry_mask = np.zeros_like(silhouette, dtype=np.uint8)
    cv2.polylines(
        jaw_geometry_mask,
        [np.rint(target_curve).astype(np.int32)],
        False,
        255,
        3,
        cv2.LINE_AA,
    )

    b00 = np.asarray(Image.open(args.b00).convert("RGBA"))
    # B00-derived robust palettes, not a second identity texture projection.
    opaque = b00[:, :, 3] > 0
    rgb = b00[:, :, :3]
    blue_candidates = opaque & (rgb[:, :, 2] > rgb[:, :, 0] * 1.15) & (rgb[:, :, 2] > 75)
    white_candidates = opaque & (rgb.mean(axis=2) > 175)
    skin_candidates = opaque & (rgb[:, :, 0] > rgb[:, :, 1] * 1.03) & (rgb[:, :, 1] > rgb[:, :, 2] * 0.95) & (rgb.mean(axis=2) > 120)
    blue = np.median(rgb[blue_candidates], axis=0) if np.any(blue_candidates) else np.array([24, 66, 119])
    white = np.median(rgb[white_candidates], axis=0) if np.any(white_candidates) else np.array([225, 226, 225])
    skin = np.median(rgb[skin_candidates], axis=0) if np.any(skin_candidates) else np.array([222, 184, 169])

    center_x = 512.0
    inner_white = outfit & (np.abs(xx - center_x) < np.maximum(42.0, (yy - 250.0) * 0.075))
    outer_blue = outfit & ~inner_white
    lighting = (0.60 + 0.65 * shaded)[..., None]
    canvas = np.zeros((*silhouette.shape, 4), dtype=np.uint8)
    domain_masks = {"anatomy": anatomy, "outfit": outfit, "hair": hair, "ornament": ornament}
    anatomy_rgb = np.clip(skin * lighting, 0, 255).astype(np.uint8)
    blue_rgb = np.clip(blue * lighting, 0, 255).astype(np.uint8)
    white_rgb = np.clip(white * lighting, 0, 255).astype(np.uint8)
    canvas[anatomy, :3] = anatomy_rgb[anatomy]
    canvas[outer_blue, :3] = blue_rgb[outer_blue]
    canvas[inner_white, :3] = white_rgb[inner_white]
    canvas[hair, :3] = np.array([15, 19, 27], dtype=np.uint8)
    canvas[ornament, :3] = np.array([184, 205, 224], dtype=np.uint8)
    visible = anatomy | outfit | hair | ornament
    canvas[visible, 3] = 255
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, mask in domain_masks.items():
        layer = np.zeros_like(canvas)
        layer[mask] = canvas[mask]
        path = args.output_dir / f"{prefix}_{name}-control-rgba.png"
        Image.fromarray(layer, "RGBA").save(path)
        paths[name] = path
    combined = args.output_dir / f"{prefix}_b00-palette-3d-control-rgba.png"
    Image.fromarray(canvas, "RGBA").save(combined)
    jaw_geometry_path = args.output_dir / f"{prefix}_step16-authority-jaw13-geometry.png"
    Image.fromarray(jaw_geometry_mask, "L").save(jaw_geometry_path)
    overlap = sum(int(np.count_nonzero(a & b)) for i, a in enumerate(domain_masks.values()) for b in list(domain_masks.values())[i + 1 :])
    evidence = {
        "schema": "mohan.b00-palette-3d-control.v1",
        "formal": False,
        "accepted": False,
        "identity_checkpoint_contract": "checkpoint-16",
        "jaw_identity_contract": {
            "mesh_correspondence": str(args.jaw13_json.resolve()),
            "authority": str(args.jaw_authority.resolve()),
            "authority_sha256": digest(args.jaw_authority),
            "generic_mesh_shape_used_as_identity": False,
            "labels_or_overlay_in_control": False,
            "mapped_curve_xy": target_curve.round(3).tolist(),
            "geometry_channel": {
                "path": str(jaw_geometry_path.resolve()),
                "sha256": digest(jaw_geometry_path),
            },
        },
        "view_id": prefix,
        "canvas": [1024, 1536],
        "ownership_overlap_pixels": overlap,
        "ownership_pixels": {name: int(mask.sum()) for name, mask in domain_masks.items()},
        "b00_sha256": digest(args.b00),
        "palettes_rgb": {"blue": blue.astype(int).tolist(), "white": white.astype(int).tolist(), "skin": skin.astype(int).tolist()},
        "combined": {"path": str(combined.resolve()), "sha256": digest(combined)},
        "outputs": {name: {"path": str(path.resolve()), "sha256": digest(path)} for name, path in paths.items()},
    }
    (args.output_dir / f"{prefix}_b00-palette-3d-control.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0 if overlap == 0 and int(visible.sum()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
