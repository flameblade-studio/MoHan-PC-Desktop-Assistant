from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFilter


SIZE = (1024, 1536)
LOCK_Y = 1410
# Only erase legacy heel pixels below this row (keeps skirt and ankles).
HEEL_ERASE_MIN_Y = 1438
DONOR_SHIFT = (-25, 8)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def polygon_mask(polygons: list[list[tuple[int, int]]], blur: float = 0.0) -> Image.Image:
    result = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(result)
    for polygon in polygons:
        draw.polygon(polygon, fill=255)
    return result.filter(ImageFilter.GaussianBlur(blur)) if blur else result


def translated(image: Image.Image, dx: int, dy: int) -> Image.Image:
    return image.transform(
        SIZE,
        Image.Transform.AFFINE,
        (1, 0, -dx, 0, 1, -dy),
        resample=Image.Resampling.BICUBIC,
    )


def _donor_flat_shoe_layer(
    donor: Image.Image,
    donor_polygons: list[list[tuple[int, int]]],
) -> Image.Image:
    donor_area = polygon_mask(donor_polygons, blur=0.8)
    donor_alpha_array = np.minimum(
        np.asarray(donor_area, dtype=np.uint8),
        np.asarray(donor.getchannel("A"), dtype=np.uint8),
    )
    # The donor includes the lower edge of its own white skirt in the broad
    # shoe polygons.  Keep only the actual flat-shoe body; retaining the
    # target's original ankles prevents a white triangular splice.
    donor_alpha_array[:HEEL_ERASE_MIN_Y] = 0
    donor_layer = donor.copy()
    donor_layer.putalpha(Image.fromarray(donor_alpha_array, mode="L"))
    return translated(donor_layer, *DONOR_SHIFT)


def _composite_with_heel_erased(
    base: Image.Image,
    donor_layer: Image.Image,
    old_shoe_polygons: list[list[tuple[int, int]]],
) -> Image.Image:
    # Remove the old shoe only below the ankle lock.  A slightly dilated donor
    # footprint removes the former heel while keeping the skirt and ankles.
    old_area = np.asarray(polygon_mask(old_shoe_polygons), dtype=np.uint8) > 0
    donor_footprint = np.asarray(donor_layer.getchannel("A"), dtype=np.uint8) > 0
    yy = np.indices((SIZE[1], SIZE[0]))[0]
    erase = old_area & (yy >= HEEL_ERASE_MIN_Y) & donor_footprint
    base_pixels = np.asarray(base, dtype=np.uint8).copy()
    base_pixels[erase] = 0
    cleared = Image.fromarray(base_pixels, mode="RGBA")
    return Image.alpha_composite(cleared, donor_layer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--shoe-source", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = Image.open(args.base).convert("RGBA")
    donor = Image.open(args.shoe_source).convert("RGBA")
    if base.size != SIZE or donor.size != SIZE:
        raise ValueError(f"expected {SIZE}: {base.size=} {donor.size=}")

    donor_polygons = [
        [(357, 1451), (369, 1430), (396, 1415), (452, 1413), (488, 1433),
         (503, 1460), (492, 1482), (439, 1487), (365, 1478)],
        [(453, 1450), (466, 1429), (493, 1415), (546, 1410), (577, 1434),
         (596, 1460), (580, 1494), (518, 1497), (457, 1481)],
    ]
    old_shoe_polygons = [
        [(330, 1430), (381, 1405), (469, 1410), (505, 1442), (496, 1518),
         (405, 1518), (333, 1491)],
        [(423, 1428), (470, 1404), (560, 1408), (607, 1440), (601, 1520),
         (500, 1520), (430, 1492)],
    ]

    donor_layer = _donor_flat_shoe_layer(donor, donor_polygons)
    result = _composite_with_heel_erased(base, donor_layer, old_shoe_polygons)

    result_pixels = np.asarray(result, dtype=np.uint8).copy()
    original_pixels = np.asarray(base, dtype=np.uint8)
    result_pixels[:LOCK_Y] = original_pixels[:LOCK_Y]
    result_pixels[result_pixels[:, :, 3] == 0, :3] = 0
    result = Image.fromarray(result_pixels, mode="RGBA")

    output = args.output_dir / f"{args.view_id}.flat-white-shoes-owner-review-v2.png"
    result.save(output)
    diff = np.any(result_pixels != original_pixels, axis=2)
    changed_y, changed_x = np.where(diff)
    alpha = result_pixels[:, :, 3]
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
        "pixels_changed_above_lock_y": int(diff[:LOCK_Y].sum()),
        "changed_pixel_count": int(diff.sum()),
        "changed_bbox": [
            int(changed_x.min()), int(changed_y.min()),
            int(changed_x.max() + 1), int(changed_y.max() + 1),
        ],
        "corner_alpha": [
            int(alpha[0, 0]), int(alpha[0, -1]),
            int(alpha[-1, 0]), int(alpha[-1, -1]),
        ],
        "transparent_rgb_nonzero_pixels": int(
            np.any(result_pixels[:, :, :3] != 0, axis=2)[alpha == 0].sum()
        ),
        "formal_art_status": False,
        "visual_review": "pending_owner_review",
    }
    (args.output_dir / f"{args.view_id}.flat-white-shoes-v2.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    preview = Image.new("RGBA", SIZE, (96, 96, 96, 255))
    preview.alpha_composite(result)
    preview.convert("RGB").save(
        args.output_dir / f"{args.view_id}.flat-white-shoes-owner-review-v2.jpg",
        quality=95,
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["pixels_changed_above_lock_y"] == 0 and evidence["transparent_rgb_nonzero_pixels"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
