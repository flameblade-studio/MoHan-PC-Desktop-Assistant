#!/usr/bin/env python3
"""Face-only local identity transfer for yaw+000 staging artwork."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

SOURCE_POINTS = np.float32([
    (474, 415), (739, 415), (550, 405), (665, 405),
    (550, 447), (666, 447), (608, 523), (560, 570),
    (655, 570), (608, 645), (505, 535), (710, 535), (608, 350),
])
TARGET_POINTS = np.float32([
    (468, 192), (560, 192), (493, 195), (535, 195),
    (492, 211), (536, 211), (514, 239), (495, 256),
    (535, 256), (514, 286), (477, 243), (551, 243), (514, 167),
])
REJECTED_AUTHORITY_SHA256 = {
    # Original B00 contains the bilateral thumb/nail contamination confirmed
    # in the owner 2048px contact.  It must never seed another view.
    "220BD1D466666719BB3CEA4246DC2F8309430CFEECE742313B93C59C188A48D5",
    # First 12-pixel thumbnail repair still failed the owner's 20x inspection.
    "1B4C8B69BC8FFBB2D0C5A2AC5F9352A107E2CFA177E24CFFD1ABE540011E17F2",
}
TRIANGLES = (
    (12, 0, 2), (12, 2, 3), (12, 3, 1),
    (0, 10, 4), (0, 4, 2), (2, 4, 6), (2, 6, 3),
    (3, 6, 5), (3, 5, 1), (1, 5, 11), (4, 10, 6),
    (5, 6, 11), (10, 7, 6), (6, 8, 11), (10, 9, 7),
    (7, 9, 8), (8, 9, 11),
)


def existing(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=existing)
    parser.add_argument("--authority", required=True, type=existing)
    parser.add_argument("--expected-authority-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--view-id", default="yaw+000-pitch+00")
    parser.add_argument("--grain-seed", type=int, default=20260826)
    parser.add_argument("--grain-sigma", type=float, default=0.85)
    parser.add_argument("--identity-strength", type=float, default=0.24)
    parser.add_argument("--repair-thumb-black-specks", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def audit_thumb_black_specks(rgb: np.ndarray, alpha: np.ndarray | None = None) -> dict[str, object]:
    """Find tiny dark islands surrounded by skin in the two yaw+000 hand ROIs."""
    rois = {
        "viewer_left_hand": (210, 725, 320, 880),
        "viewer_right_hand": (705, 725, 815, 880),
    }
    findings: list[dict[str, object]] = []
    for label, (x0, y0, x1, y1) in rois.items():
        crop = rgb[y0:y1, x0:x1]
        red = crop[..., 0].astype(np.int16)
        green = crop[..., 1].astype(np.int16)
        blue = crop[..., 2].astype(np.int16)
        opaque = np.ones(red.shape, dtype=bool) if alpha is None else alpha[y0:y1, x0:x1] >= 128
        skin = (
            (red > 82) & (green > 52) & (blue > 42)
            & (red > green + 4) & (green >= blue - 5)
            & opaque
        ).astype(np.uint8)
        dark = ((red < 58) & (green < 58) & (blue < 58) & opaque).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
        for component in range(1, count):
            area = int(stats[component, cv2.CC_STAT_AREA])
            if not 1 <= area <= 20:
                continue
            component_mask = (labels == component).astype(np.uint8)
            ring = cv2.dilate(component_mask, np.ones((5, 5), np.uint8)) - component_mask
            ring_pixels = int(ring.sum())
            skin_ratio = float((ring.astype(bool) & skin.astype(bool)).sum() / max(ring_pixels, 1))
            if skin_ratio >= 0.30:
                cx = int(stats[component, cv2.CC_STAT_LEFT] + stats[component, cv2.CC_STAT_WIDTH] // 2 + x0)
                cy = int(stats[component, cv2.CC_STAT_TOP] + stats[component, cv2.CC_STAT_HEIGHT] // 2 + y0)
                local_y, local_x = np.where(component_mask != 0)
                findings.append({
                    "roi": label,
                    "area": area,
                    "center": [cx, cy],
                    "skin_ring_ratio": skin_ratio,
                    "pixels": [[int(x + x0), int(y + y0)] for x, y in zip(local_x, local_y, strict=True)],
                })
    return {
        "detected": bool(findings),
        "component_count": len(findings),
        "pixel_count": sum(int(item["area"]) for item in findings),
        "components": findings,
    }


def repair_thumb_black_specks(rgb: np.ndarray, audit: dict[str, object]) -> tuple[np.ndarray, int]:
    repaired = rgb.copy()
    changed = 0
    for component in audit["components"]:
        for x, y in component["pixels"]:
            local = rgb[max(0, y - 4): y + 5, max(0, x - 4): x + 5]
            red = local[..., 0].astype(np.int16)
            green = local[..., 1].astype(np.int16)
            blue = local[..., 2].astype(np.int16)
            skin = (
                (red > 82) & (green > 52) & (blue > 42)
                & (red > green + 4) & (green >= blue - 5)
            )
            candidates = local[skin]
            if len(candidates) < 5:
                raise RuntimeError(f"insufficient local thumb skin samples at {(x, y)}")
            repaired[y, x] = np.median(candidates, axis=0).astype(np.uint8)
            changed += 1
    return repaired, changed


def warp_triangle(
    source: np.ndarray, canvas: np.ndarray,
    source_triangle: np.ndarray, target_triangle: np.ndarray,
) -> None:
    sx, sy, sw, sh = cv2.boundingRect(source_triangle)
    tx, ty, tw, th = cv2.boundingRect(target_triangle)
    source_rect = source[sy:sy + sh, sx:sx + sw]
    source_local = source_triangle - np.float32((sx, sy))
    target_local = target_triangle - np.float32((tx, ty))
    transform = cv2.getAffineTransform(source_local, target_local)
    warped = cv2.warpAffine(
        source_rect, transform, (tw, th), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    triangle_mask = np.zeros((th, tw), dtype=np.uint8)
    cv2.fillConvexPoly(
        triangle_mask, np.rint(target_local).astype(np.int32), 255,
        lineType=cv2.LINE_AA,
    )
    region = canvas[ty:ty + th, tx:tx + tw]
    alpha = triangle_mask.astype(np.float32)[..., None] / 255.0
    region[:] = np.clip(warped * alpha + region * (1.0 - alpha), 0, 255).astype(np.uint8)


def main() -> int:
    parsed = args()
    if re.fullmatch(r"yaw[+-]\d{3}-pitch[+-]\d{2}", parsed.view_id) is None:
        raise ValueError("invalid canonical view id")
    if not parsed.output_dir.is_absolute() or parsed.output_dir.drive.upper() != "D:":
        raise ValueError("output directory must be absolute on D drive")
    if parsed.output_dir.exists() and any(parsed.output_dir.iterdir()):
        raise FileExistsError("output directory must be absent or empty")

    expected_authority_sha256 = parsed.expected_authority_sha256.upper()
    if re.fullmatch(r"[0-9A-F]{64}", expected_authority_sha256) is None:
        raise ValueError("expected authority SHA-256 must be 64 hexadecimal characters")
    authority_sha256 = sha256(parsed.authority)
    if authority_sha256 in REJECTED_AUTHORITY_SHA256:
        raise ValueError(f"FAIL_CLOSED_REJECTED_CONTAMINATED_AUTHORITY_SHA256:{authority_sha256}")
    if authority_sha256 != expected_authority_sha256:
        raise ValueError(
            "FAIL_CLOSED_AUTHORITY_SHA256_MISMATCH:"
            f"expected={expected_authority_sha256}:actual={authority_sha256}"
        )

    target_pil = Image.open(parsed.target).convert("RGBA")
    authority_pil = Image.open(parsed.authority).convert("RGBA")
    if target_pil.size != (1024, 1536) or authority_pil.size not in ((1254, 1254), (1024, 1536)):
        raise ValueError("FAIL_CLOSED_EXPECTED_AUTHORITY_AND_TARGET_CANVAS")
    if parsed.preflight_only:
        print(json.dumps({
            "status": "PREFLIGHT_OK",
            "target": str(parsed.target),
            "authority": str(parsed.authority),
            "authority_sha256": authority_sha256,
        }, ensure_ascii=False, indent=2))
        return 0
    target_rgba = np.asarray(target_pil, dtype=np.uint8).copy()
    authority_rgba = np.asarray(authority_pil, dtype=np.uint8).copy()
    thumb_audit_before = audit_thumb_black_specks(target_rgba[..., :3], target_rgba[..., 3])
    thumb_repaired_pixels = 0
    if parsed.repair_thumb_black_specks:
        target_rgba[..., :3], thumb_repaired_pixels = repair_thumb_black_specks(
            target_rgba[..., :3], thumb_audit_before
        )
    thumb_audit_after = audit_thumb_black_specks(target_rgba[..., :3], target_rgba[..., 3])
    target_bgr = cv2.cvtColor(target_rgba[..., :3], cv2.COLOR_RGB2BGR)
    source_bgr = cv2.cvtColor(authority_rgba[..., :3], cv2.COLOR_RGB2BGR)

    source_points = TARGET_POINTS if authority_pil.size == target_pil.size else SOURCE_POINTS
    warped_face = target_bgr.copy()
    for indices in TRIANGLES:
        warp_triangle(
            source_bgr, warped_face,
            source_points[list(indices)], TARGET_POINTS[list(indices)],
        )

    # Transfer only the internal identity features.  The generated target owns
    # the outer facial silhouette, jaw, chin, ears, hairline and neck so a
    # landmark mismatch cannot pinch or replace the head geometry.
    face_mask = np.zeros(target_bgr.shape[:2], dtype=np.uint8)
    for center, axes in (
        ((493, 204), (24, 18)),  # viewer-left eye and brow
        ((535, 204), (24, 18)),  # viewer-right eye and brow
        ((514, 230), (17, 27)),  # nose bridge and tip
        ((514, 257), (31, 16)),  # lips and corners, excludes chin
    ):
        cv2.ellipse(face_mask, center, axes, 0.0, 0.0, 360.0, 255, -1, cv2.LINE_AA)
    face_mask = cv2.GaussianBlur(face_mask, (0, 0), 5.0)
    face_mask[target_rgba[..., 3] == 0] = 0
    if not 0.0 <= parsed.identity_strength <= 1.0:
        raise ValueError("identity strength must be between 0 and 1")
    blend = face_mask.astype(np.float32)[..., None] / 255.0
    blend *= parsed.identity_strength
    cloned = np.clip(
        warped_face.astype(np.float32) * blend
        + target_bgr.astype(np.float32) * (1.0 - blend),
        0,
        255,
    ).astype(np.uint8)

    # A low, deterministic luminance grain removes the overly smooth generated
    # finish without changing alpha, geometry, clothes, hair, ears, or neck.
    rng = np.random.default_rng(parsed.grain_seed)
    grain = rng.normal(0.0, parsed.grain_sigma, cloned.shape[:2]).astype(np.float32)
    foreground = target_rgba[..., 3] > 0
    result_bgr = cloned.astype(np.float32)
    result_bgr[foreground] += grain[foreground, None]
    result_bgr = np.clip(result_bgr, 0, 255).astype(np.uint8)
    result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
    result_rgb[~foreground] = 0
    result = np.dstack((result_rgb, target_rgba[..., 3]))

    parsed.output_dir.mkdir(parents=True, exist_ok=False)
    output_path = parsed.output_dir / f"{parsed.view_id}.face-identity-filmgrain-rgba.png"
    mask_path = parsed.output_dir / f"{parsed.view_id}.face-only-mask.png"
    contact_path = parsed.output_dir / f"{parsed.view_id}.face-identity-ab-contact.png"
    detail_contact_path = parsed.output_dir / f"{parsed.view_id}.face-identity-ab-detail.png"
    Image.fromarray(result, mode="RGBA").save(output_path)
    Image.fromarray(face_mask, mode="L").save(mask_path)

    contact = Image.new("RGB", (2048, 1584), (28, 31, 35))
    before = Image.new("RGB", target_pil.size, (18, 18, 18))
    before.paste(target_pil, mask=target_pil.getchannel("A"))
    after_pil = Image.fromarray(result, mode="RGBA")
    after = Image.new("RGB", after_pil.size, (18, 18, 18))
    after.paste(after_pil, mask=after_pil.getchannel("A"))
    contact.paste(before, (0, 48))
    contact.paste(after, (1024, 48))
    draw = ImageDraw.Draw(contact)
    draw.text((16, 14), "A  raw yaw+000 base (not final)", fill=(240, 240, 240))
    draw.text((1040, 14), "B  face-only identity + fixed film grain", fill=(160, 255, 180))
    contact.save(contact_path)

    crop_box = (430, 130, 598, 330)
    before_detail = before.crop(crop_box).resize((672, 800), Image.Resampling.LANCZOS)
    after_detail = after.crop(crop_box).resize((672, 800), Image.Resampling.LANCZOS)
    detail_contact = Image.new("RGB", (1344, 848), (28, 31, 35))
    detail_contact.paste(before_detail, (0, 48))
    detail_contact.paste(after_detail, (672, 48))
    detail_draw = ImageDraw.Draw(detail_contact)
    detail_draw.text((16, 14), "A  raw face detail", fill=(240, 240, 240))
    detail_draw.text((688, 14), "B  B00 internal-feature identity detail", fill=(160, 255, 180))
    detail_contact.save(detail_contact_path)

    thumb_pollution = audit_thumb_black_specks(result_rgb, target_rgba[..., 3])

    evidence = {
        "status": "GENERATED_LOCAL_FACE_ONLY_POSTPROCESS_STAGING",
        "formal_art_pass": False,
        "target": {"path": str(parsed.target), "sha256": sha256(parsed.target)},
        "authority": {"path": str(parsed.authority), "sha256": authority_sha256},
        "method": "13_POINT_PIECEWISE_AFFINE_INTERNAL_FEATURE_FEATHER_BLEND_ONLY",
        "preserved": ["hair", "ears", "neck", "non_thumb_anatomy", "outfit", "ornament", "alpha"],
        "film_grain": {"seed": parsed.grain_seed, "sigma": parsed.grain_sigma},
        "identity_strength": parsed.identity_strength,
        "thumb_black_speck_repair": {
            "enabled": parsed.repair_thumb_black_specks,
            "changed_pixels": thumb_repaired_pixels,
            "before": thumb_audit_before,
            "after_local_repair": thumb_audit_after,
            "after_full_postprocess": thumb_pollution,
        },
        "outputs": {
            "rgba": {"path": str(output_path), "sha256": sha256(output_path)},
            "mask": {"path": str(mask_path), "sha256": sha256(mask_path)},
            "contact": {"path": str(contact_path), "sha256": sha256(contact_path)},
            "detail_contact": {
                "path": str(detail_contact_path),
                "sha256": sha256(detail_contact_path),
            },
        },
    }
    evidence_path = parsed.output_dir / "postprocess-result.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
