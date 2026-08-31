#!/usr/bin/env python3
"""Transfer only approved thumbnail plates from a same-canvas authority image."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


def existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def nail_metrics(rgb: np.ndarray, coordinates: list[tuple[int, int]]) -> dict[str, float | int]:
    pixels = np.array([rgb[y, x] for x, y in coordinates], dtype=np.float32)
    luminance = pixels @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return {
        "pixel_count": int(len(coordinates)),
        "luminance_min": float(luminance.min()),
        "luminance_median": float(np.median(luminance)),
        "dark_pixel_count_lt_60": int(np.count_nonzero(luminance < 60.0)),
        "near_black_pixel_count_lt_35": int(np.count_nonzero(luminance < 35.0)),
    }


def crop_fit(image: Image.Image, box: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image.crop(box).convert("RGB"), size, Image.Resampling.NEAREST)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=existing_file)
    parser.add_argument("--expected-input-sha256", required=True)
    parser.add_argument("--authority", required=True, type=existing_file)
    parser.add_argument("--expected-authority-sha256", required=True)
    parser.add_argument("--mask-manifest", required=True, type=existing_file)
    parser.add_argument("--output-dir", required=True, type=Path)
    parsed = parser.parse_args()

    input_sha = sha256(parsed.input)
    authority_sha = sha256(parsed.authority)
    if input_sha != parsed.expected_input_sha256.upper():
        raise ValueError(f"FAIL_CLOSED_INPUT_SHA256:{input_sha}")
    if authority_sha != parsed.expected_authority_sha256.upper():
        raise ValueError(f"FAIL_CLOSED_AUTHORITY_SHA256:{authority_sha}")
    if parsed.output_dir.exists():
        raise FileExistsError(parsed.output_dir)

    target = Image.open(parsed.input).convert("RGBA")
    authority = Image.open(parsed.authority).convert("RGBA")
    if target.size != (1024, 1536) or authority.size != target.size:
        raise ValueError(f"expected same-canvas 1024x1536 RGBA: {target.size}, {authority.size}")

    manifest = json.loads(parsed.mask_manifest.read_text(encoding="utf-8"))
    regions = manifest.get("regions")
    if not isinstance(regions, list) or len(regions) != 2:
        raise ValueError("mask manifest must contain exactly two thumbnail regions")

    hard_mask = Image.new("L", target.size, 0)
    coordinates_by_side: dict[str, list[tuple[int, int]]] = {}
    for region in regions:
        side = str(region["side"])
        coordinates = [(int(x), int(y)) for x, y in region["coordinates"]]
        coordinates_by_side[side] = coordinates
        for x, y in coordinates:
            hard_mask.putpixel((x, y), 255)

    feather = hard_mask.filter(ImageFilter.GaussianBlur(radius=0.65))
    support = hard_mask.filter(ImageFilter.MaxFilter(size=3))
    feather_array = np.minimum(np.asarray(feather), np.asarray(support)).astype(np.uint8)
    feather = Image.fromarray(feather_array, mode="L")

    target_rgb = target.convert("RGB")
    authority_rgb = authority.convert("RGB")
    transferred_rgb = Image.composite(authority_rgb, target_rgb, feather)
    transferred = Image.merge("RGBA", (*transferred_rgb.split(), target.getchannel("A")))

    target_array = np.asarray(target)
    output_array = np.asarray(transferred)
    diff_rgb = np.any(target_array[:, :, :3] != output_array[:, :, :3], axis=2)
    support_array = np.asarray(support) > 0
    outside_diff = int(np.count_nonzero(diff_rgb & ~support_array))
    alpha_diff = int(np.count_nonzero(target_array[:, :, 3] != output_array[:, :, 3]))
    if outside_diff or alpha_diff:
        raise RuntimeError(f"thumb transfer escaped mask: outside_rgb={outside_diff}, alpha={alpha_diff}")

    parsed.output_dir.mkdir(parents=True, exist_ok=False)
    output_path = parsed.output_dir / "yaw+000-pitch+00.face-identity-filmgrain-thumb-nails-rgba.png"
    mask_path = parsed.output_dir / "yaw+000-pitch+00.thumb-nails-feather-mask.png"
    detail_path = parsed.output_dir / "yaw+000-pitch+00.thumb-nails-before-after-40x.png"
    fullbody_path = parsed.output_dir / "yaw+000-pitch+00.v8-vs-v9-fullbody.png"
    qa_path = parsed.output_dir / "yaw+000-pitch+00.thumb-nails-transfer-qa.json"
    transferred.save(output_path)
    feather.save(mask_path)

    detail = Image.new("RGB", (1760, 1120), (24, 27, 31))
    detail_draw = ImageDraw.Draw(detail)
    panels = (
        ("left BEFORE", target_rgb, (250, 785, 272, 813)),
        ("left AFTER", transferred_rgb, (250, 785, 272, 813)),
        ("right BEFORE", target_rgb, (758, 784, 780, 812)),
        ("right AFTER", transferred_rgb, (758, 784, 780, 812)),
    )
    for index, (label, image, box) in enumerate(panels):
        x = (index % 2) * 880
        y = (index // 2) * 560
        detail_draw.text((x + 12, y + 12), label, fill=(150, 255, 175) if "AFTER" in label else (240, 240, 240))
        detail.paste(crop_fit(image, box, (880, 520)), (x, y + 40))
    detail.save(detail_path)

    fullbody = Image.new("RGB", (2048, 1584), (18, 18, 18))
    for index, (label, image) in enumerate((("V8 FACE ONLY", target), ("V9 + V5 THUMB NAILS", transferred))):
        panel = Image.new("RGB", target.size, (18, 18, 18))
        panel.paste(image, mask=image.getchannel("A"))
        panel.thumbnail((1024, 1536), Image.Resampling.LANCZOS)
        fullbody.paste(panel, (index * 1024, 48))
        ImageDraw.Draw(fullbody).text((index * 1024 + 16, 16), label, fill=(150, 255, 175) if index else (240, 240, 240))
    fullbody.save(fullbody_path)

    target_rgb_array = np.asarray(target_rgb)
    output_rgb_array = np.asarray(transferred_rgb)
    qa = {
        "status": "GENERATED_STAGING_THUMBNAIL_PLATE_TRANSFER",
        "formal_art_pass": False,
        "input": {"path": str(parsed.input), "sha256": input_sha},
        "authority": {"path": str(parsed.authority), "sha256": authority_sha},
        "mask_manifest": str(parsed.mask_manifest),
        "method": "V5_IRREGULAR_MASK_GAUSSIAN_FEATHER_RADIUS_0.65_CLIPPED_TO_1PX_DILATION",
        "changed_rgb_pixels": int(np.count_nonzero(diff_rgb)),
        "outside_support_rgb_diff_pixels": outside_diff,
        "alpha_diff_pixels": alpha_diff,
        "nail_roi_metrics": {
            side: {
                "before": nail_metrics(target_rgb_array, coordinates),
                "after": nail_metrics(output_rgb_array, coordinates),
            }
            for side, coordinates in coordinates_by_side.items()
        },
        "outputs": {
            "rgba": {"path": str(output_path), "sha256": sha256(output_path)},
            "mask": str(mask_path),
            "detail_40x": str(detail_path),
            "fullbody": str(fullbody_path),
        },
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
