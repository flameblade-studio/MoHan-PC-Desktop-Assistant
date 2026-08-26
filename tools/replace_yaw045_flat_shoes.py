from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFilter


LOCK_Y = 1410
SHIFT_X = -25
SHIFT_Y = 8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def polygon_mask(size: tuple[int, int], polygons: list[list[tuple[int, int]]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for polygon in polygons:
        draw.polygon(polygon, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1.0))


def translated(image: Image.Image, dx: int, dy: int) -> Image.Image:
    return image.transform(
        image.size,
        Image.Transform.AFFINE,
        (1, 0, -dx, 0, 1, -dy),
        resample=Image.Resampling.BICUBIC,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--shoe-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = Image.open(args.base).convert("RGBA")
    shoe_source = Image.open(args.shoe_source).convert("RGBA")
    if base.size != (1024, 1536) or shoe_source.size != base.size:
        raise ValueError(f"expected two 1024x1536 images, got {base.size=} {shoe_source.size=}")

    corrected_shoe_polygons = [
        [(357, 1451), (369, 1430), (396, 1415), (452, 1413), (488, 1433), (503, 1460), (492, 1482), (439, 1487), (365, 1478)],
        [(453, 1450), (466, 1429), (493, 1415), (546, 1410), (577, 1434), (596, 1460), (580, 1494), (518, 1497), (457, 1481)],
    ]
    original_shoe_polygons = [
        [(332, 1459), (344, 1438), (371, 1423), (427, 1421), (463, 1441), (478, 1468), (467, 1507), (414, 1510), (340, 1491)],
        [(428, 1458), (441, 1437), (468, 1423), (521, 1418), (552, 1442), (571, 1468), (555, 1510), (493, 1512), (432, 1489)],
    ]

    source_mask = polygon_mask(base.size, corrected_shoe_polygons)
    source_alpha = Image.fromarray(
        np.minimum(np.asarray(source_mask), np.asarray(shoe_source.getchannel("A"))).astype(np.uint8),
        mode="L",
    )
    shoe_layer = shoe_source.copy()
    shoe_layer.putalpha(source_alpha)
    shoe_layer = translated(shoe_layer, SHIFT_X, SHIFT_Y)

    # Keep the original hem and ankles untouched.  The aligned flat-shoe layer
    # is opaque over the old heels, so erasing a broad polygon would introduce
    # a visible horizontal seam into the translucent skirt edge.
    result = Image.alpha_composite(base, shoe_layer)

    output_pixels = np.asarray(result).copy()
    original_pixels = np.asarray(base)
    output_pixels[:LOCK_Y] = original_pixels[:LOCK_Y]
    output_pixels[output_pixels[:, :, 3] == 0, :3] = 0
    result = Image.fromarray(output_pixels, mode="RGBA")

    output = args.output_dir / "yaw+045-pitch+00.flat-white-shoes-owner-review-rgba.png"
    result.save(output)

    diff = np.any(output_pixels != original_pixels, axis=2)
    above_diff = int(diff[:LOCK_Y].sum())
    changed_y, changed_x = np.where(diff)
    changed_bbox = None
    if changed_x.size:
        changed_bbox = [
            int(changed_x.min()),
            int(changed_y.min()),
            int(changed_x.max() + 1),
            int(changed_y.max() + 1),
        ]

    alpha = output_pixels[:, :, 3]
    evidence = {
        "base": str(args.base.resolve()),
        "base_sha256": sha256(args.base),
        "shoe_source": str(args.shoe_source.resolve()),
        "shoe_source_sha256": sha256(args.shoe_source),
        "output": str(output.resolve()),
        "output_sha256": sha256(output),
        "size": list(result.size),
        "mode": result.mode,
        "lock_y_exclusive": LOCK_Y,
        "pixels_changed_above_lock_y": above_diff,
        "changed_pixel_count": int(diff.sum()),
        "changed_bbox": changed_bbox,
        "shoe_translation": [SHIFT_X, SHIFT_Y],
        "corner_alpha": [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])],
        "transparent_rgb_nonzero_pixels": int(np.any(output_pixels[:, :, :3] != 0, axis=2)[alpha == 0].sum()),
        "formal_art_status": False,
        "visual_review": "pending_owner_review",
    }
    evidence_path = args.output_dir / "yaw+045-pitch+00.flat-white-shoes-evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    preview = Image.new("RGBA", (1024, 1536), (96, 96, 96, 255))
    preview.alpha_composite(result)
    preview.convert("RGB").save(args.output_dir / "yaw+045-pitch+00.flat-white-shoes-preview.jpg", quality=94)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if above_diff == 0 and evidence["transparent_rgb_nonzero_pixels"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
