#!/usr/bin/env python3
"""Build a clean palette-only Hanfu control from a true 3D semantic render.

No source RGB texture is projected.  The 3D part-ID/depth silhouette supplies
pose and occlusion; deterministic polygons/dilations supply separate outfit,
hair, and ornament control domains for the image model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SIZE = (1024, 1536)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("required semantic part is empty")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic-root", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--b00", type=Path, required=True)
    parser.add_argument("--step16", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    yaw_match = re.fullmatch(r"yaw([+-]\d{3})-pitch\+00", args.view_id)
    if yaw_match is None:
        raise ValueError(f"invalid canonical view id: {args.view_id}")
    yaw_degrees = int(yaw_match.group(1))

    part_path = args.semantic_root / f"{args.view_id}_part-id.png"
    rgba_path = args.semantic_root / f"{args.view_id}_rgba.png"
    depth_path = args.semantic_root / f"{args.view_id}_depth.png"
    part = np.asarray(Image.open(part_path).convert("L"), dtype=np.uint8)
    source = np.asarray(Image.open(rgba_path).convert("RGBA"), dtype=np.uint8)
    depth = np.asarray(Image.open(depth_path).convert("L"), dtype=np.float32) / 255.0
    if Image.open(part_path).size != SIZE or Image.open(rgba_path).size != SIZE:
        raise ValueError("semantic inputs must be 1024x1536")

    visible3d = source[..., 3] > 0
    head = part == 1
    torso = part == 2
    left_arm = np.isin(part, [3, 4])
    left_hand = part == 5
    right_arm = np.isin(part, [6, 7])
    right_hand = part == 8
    legs_feet = np.isin(part, [9, 10, 11, 12, 13, 14])
    shoes = np.isin(part, [11, 14])
    hx0, hy0, hx1, hy1 = bbox(head)
    tx0, ty0, tx1, ty1 = bbox(torso)
    cx = int(round((tx0 + tx1) / 2))

    # Replace the generic mesh head silhouette with the actual checkpoint-16
    # face contour.  Only its binary contour is used; no Step16 RGB is copied.
    step16_rgb = np.asarray(Image.open(args.step16).convert("RGB"), dtype=np.uint8)
    red, green, blue_channel = [step16_rgb[..., index] for index in range(3)]
    authority_skin = (
        (red > 125)
        & (green > 85)
        & (blue_channel > 75)
        & (red > green * 1.025)
        & (green > blue_channel * 0.93)
    ).astype(np.uint8)
    authority_skin[:280] = 0
    authority_skin[900:] = 0
    authority_skin[:, :150] = 0
    authority_skin[:, 720:] = 0
    authority_skin = cv2.morphologyEx(authority_skin, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(authority_skin, 8)
    if count < 2:
        raise ValueError("Step16 authority face contour missing")
    authority_face = labels == (1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])))
    ax0, ay0, ax1, ay1 = bbox(authority_face)
    face_crop = authority_face[ay0 : ay1 + 1, ax0 : ax1 + 1].astype(np.uint8)
    target_face_w = max(4, int((hx1 - hx0 + 1) * 0.78))
    target_face_h = max(4, int((hy1 - hy0 + 1) * 0.90))
    face_resized = cv2.resize(face_crop, (target_face_w, target_face_h), interpolation=cv2.INTER_NEAREST) > 0
    face = np.zeros_like(head)
    face_x0 = int(round((hx0 + hx1 + 1 - target_face_w) / 2 + 0.05 * (hx1 - hx0 + 1)))
    face_y0 = hy0 + int(0.07 * (hy1 - hy0 + 1))
    face_y1 = min(face.shape[0], face_y0 + target_face_h)
    face_x1 = min(face.shape[1], face_x0 + target_face_w)
    face[face_y0:face_y1, face_x0:face_x1] = face_resized[: face_y1 - face_y0, : face_x1 - face_x0]
    # The Step16 crop is a front/near-profile identity contour.  Applying it
    # past profile would paint a second face on the back of the head, so back
    # views deliberately expose no face-skin control.
    is_back_view = abs(yaw_degrees) > 90
    if is_back_view:
        face.fill(False)

    # Wide Hanfu sleeves are pose-driven dilations of the actual 3D arms.
    sleeve_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (59, 59))
    sleeves = cv2.dilate((left_arm | right_arm).astype(np.uint8), sleeve_kernel) > 0
    sleeves &= cv2.dilate(visible3d.astype(np.uint8), np.ones((71, 71), np.uint8)) > 0

    # Long robe/skirt uses the projected torso center and feet height.  This is
    # a semantic silhouette, not a painted B00 texture warp.
    waist_y = int(round(ty0 + 0.70 * (ty1 - ty0)))
    foot_y = bbox(legs_feet)[3]
    skirt = np.zeros_like(part, dtype=np.uint8)
    skirt_points = np.asarray(
        [
            [cx - 115, waist_y - 15],
            [cx + 115, waist_y - 15],
            [cx + 215, foot_y - 58],
            [cx - 230, foot_y - 58],
        ],
        dtype=np.int32,
    )
    cv2.fillConvexPoly(skirt, skirt_points, 1)
    skirt = skirt.astype(bool)
    torso_robe = cv2.dilate(torso.astype(np.uint8), np.ones((37, 37), np.uint8)) > 0
    outfit = torso_robe | sleeves | skirt | legs_feet | left_arm | right_arm

    # White inner layer runs continuously from collar to hem; blue outer robe
    # remains a distinct color region inside the same DLC ownership domain.
    inner = np.zeros_like(part, dtype=np.uint8)
    inner_points = np.asarray(
        [
            [cx - 58, ty0 - 8],
            [cx + 45, ty0 - 8],
            [cx + 92, foot_y + 2],
            [cx - 105, foot_y + 2],
        ],
        dtype=np.int32,
    )
    cv2.fillConvexPoly(inner, inner_points, 1)
    inner = inner.astype(bool) & outfit
    if is_back_view:
        # B00's white inner crossing is a front-side garment opening.  It must
        # not be painted through the blue outer robe on rear controls.
        inner.fill(False)

    # Step16 supplies style direction, but only a deterministic black control
    # silhouette is emitted here.  Hair remains its own ownership domain.
    hair = np.zeros_like(part, dtype=np.uint8)
    head_w = hx1 - hx0 + 1
    head_h = hy1 - hy0 + 1
    cv2.ellipse(
        hair,
        (int(hx0 + head_w * 0.48), int(hy0 + head_h * 0.42)),
        (max(1, int(head_w * 0.55)), max(1, int(head_h * 0.48))),
        0,
        180,
        360,
        1,
        -1,
    )
    lock_y = min(foot_y - 80, int(hy1 + head_h * 3.4))
    left_lock = np.asarray(
        [[hx0 - 10, hy0 + head_h // 3], [hx0 + 35, hy1], [cx - 45, lock_y], [cx - 92, lock_y]],
        dtype=np.int32,
    )
    right_lock = np.asarray(
        [[hx1 - 28, hy0 + head_h // 3], [hx1 + 15, hy1], [cx + 68, lock_y], [cx + 26, lock_y]],
        dtype=np.int32,
    )
    cv2.fillPoly(hair, [left_lock, right_lock], 1)
    if is_back_view:
        cv2.ellipse(
            hair,
            (int(hx0 + head_w * 0.48), int(hy0 + head_h * 0.48)),
            (max(1, int(head_w * 0.58)), max(1, int(head_h * 0.54))),
            0,
            0,
            360,
            1,
            -1,
        )
    hair = hair.astype(bool)

    # Physical-side anchor: B00's ornament is fixed on the character, so its
    # projected horizontal offset crosses the head centre around profile and
    # reaches image-left at the back.  This rotates one physical anchor; it
    # never mirrors ornament pixels from another view.
    ornament = np.zeros_like(part, dtype=np.uint8)
    head_cx = (hx0 + hx1) / 2.0
    projected_offset = (head_w * 0.68 + 22.0) * math.cos(math.radians(yaw_degrees))
    anchor_x = int(np.clip(round(head_cx + projected_offset), 24, SIZE[0] - 32))
    anchor_y = hy0 + max(18, head_h // 5)
    cv2.line(ornament, (anchor_x, anchor_y), (anchor_x + 8, anchor_y + 112), 1, 5, cv2.LINE_AA)
    cv2.circle(ornament, (anchor_x + 3, anchor_y + 48), 9, 1, -1, cv2.LINE_AA)
    cv2.circle(ornament, (anchor_x + 8, anchor_y + 112), 8, 1, -1, cv2.LINE_AA)
    ornament = ornament.astype(bool)

    # Enforce exclusive ownership.  Visible anatomy is only face/head skin and
    # hands; clothing, hair, and ornament are not welded into it.
    outfit &= ~hair & ~ornament
    anatomy = (face | left_hand | right_hand) & ~hair & ~ornament & ~outfit
    hair &= ~ornament
    domains = {"anatomy": anatomy, "outfit": outfit, "hair": hair, "ornament": ornament}

    # Uniformly fit the complete registered control into a safe canvas margin.
    # Every ownership domain receives the exact same affine transform.
    scale = 0.94
    matrix = np.asarray(
        [[scale, 0.0, SIZE[0] * (1.0 - scale) / 2.0], [0.0, scale, SIZE[1] * (1.0 - scale) / 2.0]],
        dtype=np.float32,
    )
    domains = {
        name: cv2.warpAffine(current.astype(np.uint8), matrix, SIZE, flags=cv2.INTER_NEAREST) > 0
        for name, current in domains.items()
    }
    anatomy, outfit, hair, ornament = [domains[name] for name in ("anatomy", "outfit", "hair", "ornament")]
    inner = cv2.warpAffine(inner.astype(np.uint8), matrix, SIZE, flags=cv2.INTER_NEAREST) > 0
    shoes = cv2.warpAffine(shoes.astype(np.uint8), matrix, SIZE, flags=cv2.INTER_NEAREST) > 0
    shoes &= outfit

    b00 = np.asarray(Image.open(args.b00).convert("RGBA"), dtype=np.uint8)
    opaque = b00[..., 3] > 0
    rgb = b00[..., :3]
    blue_set = opaque & (rgb[..., 2] > rgb[..., 0] * 1.15) & (rgb[..., 2] > 75)
    white_set = opaque & (rgb.mean(axis=2) > 175)
    skin_set = opaque & (rgb[..., 0] > rgb[..., 1] * 1.03) & (rgb[..., 1] > rgb[..., 2] * 0.95) & (rgb.mean(axis=2) > 120)
    blue = np.median(rgb[blue_set], axis=0) if np.any(blue_set) else np.array([31, 68, 120])
    white = np.median(rgb[white_set], axis=0) if np.any(white_set) else np.array([222, 224, 230])
    skin = np.median(rgb[skin_set], axis=0) if np.any(skin_set) else np.array([220, 182, 170])

    # Smooth depth-derived lighting, never source texture RGB.
    depth_fitted = cv2.warpAffine(depth, matrix, SIZE, flags=cv2.INTER_LINEAR)
    light = cv2.GaussianBlur(0.72 + 0.38 * depth_fitted, (0, 0), 5)[..., None]
    canvas = np.zeros((*part.shape, 4), dtype=np.uint8)
    for current_mask, color in (
        (anatomy, skin),
        (outfit & ~inner, blue),
        (inner, white),
        (shoes, white),
        (hair, np.array([14, 18, 26])),
        (ornament, np.array([174, 205, 229])),
    ):
        shaded = np.clip(color * light, 0, 255).astype(np.uint8)
        canvas[current_mask, :3] = shaded[current_mask]
        canvas[current_mask, 3] = 255

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, Path] = {}
    for name, current_mask in domains.items():
        layer = np.zeros_like(canvas)
        layer[current_mask] = canvas[current_mask]
        path = args.output_dir / f"{args.view_id}_{name}-control-rgba.png"
        Image.fromarray(layer, "RGBA").save(path)
        output_paths[name] = path
    combined_path = args.output_dir / f"{args.view_id}_clean-semantic-hanfu-control-rgba.png"
    Image.fromarray(canvas, "RGBA").save(combined_path)

    overlap = sum(
        int(np.count_nonzero(first & second))
        for index, first in enumerate(domains.values())
        for second in list(domains.values())[index + 1 :]
    )
    evidence = {
        "formal": False,
        "accepted": False,
        "view_id": args.view_id,
        "canvas": [1024, 1536],
        "source_rgb_texture_projected": False,
        "identity_checkpoint_contract": "checkpoint-16",
        "step16_sha256": sha(args.step16),
        "ownership_overlap_pixels": overlap,
        "ownership_pixels": {key: int(value.sum()) for key, value in domains.items()},
        "palettes_rgb": {"blue": blue.astype(int).tolist(), "white": white.astype(int).tolist(), "skin": skin.astype(int).tolist()},
        "combined": {"path": str(combined_path.resolve()), "sha256": sha(combined_path)},
        "inputs": {
            "part_id": {"path": str(part_path.resolve()), "sha256": sha(part_path)},
            "depth": {"path": str(depth_path.resolve()), "sha256": sha(depth_path)},
            "semantic_rgba": {"path": str(rgba_path.resolve()), "sha256": sha(rgba_path)},
            "b00": {"path": str(args.b00.resolve()), "sha256": sha(args.b00)},
            "step16": {"path": str(args.step16.resolve()), "sha256": sha(args.step16)},
        },
        "outputs": {key: {"path": str(path.resolve()), "sha256": sha(path)} for key, path in output_paths.items()},
    }
    evidence_path = args.output_dir / f"{args.view_id}_clean-semantic-hanfu-control.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0 if overlap == 0 and all(mask.any() for mask in domains.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
