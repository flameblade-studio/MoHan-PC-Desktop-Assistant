from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


OFFSET_X = 0
OFFSET_Y = 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def shape(size: tuple[int, int], kind: str, points: list[tuple[int, int]]) -> Image.Image:
    points = [(x + OFFSET_X, y + OFFSET_Y) for x, y in points]
    mask = Image.new("1", size, 0)
    draw = ImageDraw.Draw(mask)
    if kind == "ellipse":
        draw.ellipse([points[0], points[1]], fill=1)
    else:
        draw.polygon(points, fill=1)
    return mask


def logical_or(*masks: Image.Image) -> Image.Image:
    result = Image.new("1", masks[0].size, 0)
    for mask in masks:
        result = ImageChops.logical_or(result, mask)
    return result


def logical_and(*masks: Image.Image) -> Image.Image:
    result = masks[0]
    for mask in masks[1:]:
        result = ImageChops.logical_and(result, mask)
    return result


def subtract(mask: Image.Image, removed: Image.Image) -> Image.Image:
    return ImageChops.logical_and(mask, ImageChops.invert(removed))


def rgba_for_mask(source: Image.Image, mask: Image.Image) -> Image.Image:
    output = Image.new("RGBA", source.size, (0, 0, 0, 0))
    output.paste(source, (0, 0), mask.convert("L"))
    return output


def nonzero(mask: Image.Image) -> int:
    return sum(mask.convert("L").histogram()[1:])


def alpha_mask(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.size != size:
        raise ValueError(f"mask source size mismatch: {path}")
    return image.getchannel("A").point(lambda value: 255 if value else 0).convert("1")


def skin_mask(source: Image.Image) -> Image.Image:
    mask = Image.new("1", source.size, 0)
    output = mask.load()
    for y in range(source.height):
        for x in range(source.width):
            red, green, blue, alpha = source.getpixel((x, y))
            if not alpha:
                continue
            # Conservative pale-skin gate. Geometry ROIs below prevent clothing leakage.
            output[x, y] = (
                red > 105
                and green > 58
                and blue > 48
                and red > green * 1.035
                and red > blue * 1.06
                and red - min(green, blue) > 12
            )
    return mask


def hair_color_mask(source: Image.Image) -> Image.Image:
    mask = Image.new("1", source.size, 0)
    output = mask.load()
    for y in range(source.height):
        for x in range(source.width):
            red, green, blue, alpha = source.getpixel((x, y))
            if not alpha:
                continue
            luminance = (red * 3 + green * 6 + blue) // 10
            output[x, y] = (
                luminance < 132
                and red < 112
                and green < 122
                and blue < 158
                and blue - red < 78
            )
    return mask


def main() -> int:
    global OFFSET_X, OFFSET_Y
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layers-dir", type=Path, required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--offset-x", type=int, default=0)
    parser.add_argument("--offset-y", type=int, default=0)
    args = parser.parse_args()
    OFFSET_X = args.offset_x
    OFFSET_Y = args.offset_y

    source = Image.open(args.source).convert("RGBA")
    if source.size != (1024, 1536):
        raise ValueError(f"expected 1024x1536, got {source.size}")
    clean = source.copy()
    pixels = clean.load()
    for y in range(clean.height):
        for x in range(clean.width):
            red, green, blue, alpha = pixels[x, y]
            if not alpha:
                pixels[x, y] = (0, 0, 0, 0)

    size = clean.size
    visible = clean.getchannel("A").point(lambda value: 255 if value else 0).convert("1")
    skin = skin_mask(clean)
    hair_color = hair_color_mask(clean)
    face_roi = shape(size, "ellipse", [(414, 140), (552, 309)])
    neck_roi = shape(size, "polygon", [(463, 265), (535, 264), (551, 390), (463, 390)])
    hand_left_roi = shape(size, "polygon", [(250, 717), (331, 708), (341, 847), (247, 853)])
    hand_right_roi = shape(size, "polygon", [(662, 720), (752, 718), (760, 858), (665, 858)])
    anatomy_roi = logical_or(face_roi, neck_roi, hand_left_roi, hand_right_roi)
    visible_anatomy = logical_and(visible, skin, anatomy_roi)

    hair_masks = [
        alpha_mask(args.layers_dir / f"{args.view_id}_{layer}.png", size)
        for layer in ("hair_back", "hair_left", "hair_right")
    ]
    ornament = alpha_mask(args.layers_dir / f"{args.view_id}_ornament.png", size)
    head_identity_roi = shape(size, "ellipse", [(386, 38), (625, 337)])
    head_identity = subtract(logical_and(visible, head_identity_roi), face_roi)
    hair_left_identity_roi = shape(size, "polygon", [(420, 174), (468, 185), (447, 616), (382, 654), (389, 344)])
    hair_right_identity_roi = shape(size, "polygon", [(513, 161), (570, 178), (608, 651), (526, 622)])
    hair_strands = logical_and(visible, hair_color, logical_or(hair_left_identity_roi, hair_right_identity_roi))
    identity_exclusion = logical_or(face_roi, head_identity, hair_strands, *hair_masks, ornament)
    default_outfit = subtract(visible, logical_or(visible_anatomy, identity_exclusion))

    overlap = nonzero(logical_and(visible_anatomy, default_outfit))
    if overlap:
        raise RuntimeError(f"ownership overlap rejected: {overlap}")
    anatomy_pixels = nonzero(visible_anatomy)
    outfit_pixels = nonzero(default_outfit)
    if anatomy_pixels == 0 or outfit_pixels == 0:
        raise RuntimeError("empty ownership output rejected")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    anatomy_png = args.output_dir / f"{args.view_id}_visible_anatomy_rgba.png"
    outfit_png = args.output_dir / f"{args.view_id}_default_outfit_rgba.png"
    anatomy_mask_png = args.output_dir / f"{args.view_id}_visible_anatomy_mask.png"
    outfit_mask_png = args.output_dir / f"{args.view_id}_default_outfit_mask.png"
    rgba_for_mask(clean, visible_anatomy).save(anatomy_png)
    rgba_for_mask(clean, default_outfit).save(outfit_png)
    visible_anatomy.convert("L").save(anatomy_mask_png)
    default_outfit.convert("L").save(outfit_mask_png)

    composite = Image.alpha_composite(rgba_for_mask(clean, default_outfit), rgba_for_mask(clean, visible_anatomy))
    composite_png = args.output_dir / f"{args.view_id}_anatomy-plus-outfit.png"
    composite.save(composite_png)

    thumb = (256, 384)
    contact = Image.new("RGB", (thumb[0] * 4, thumb[1] + 28), "#444444")
    draw = ImageDraw.Draw(contact)
    panels = [
        ("source", clean),
        ("visible_anatomy", rgba_for_mask(clean, visible_anatomy)),
        ("default_outfit", rgba_for_mask(clean, default_outfit)),
        ("two-way composite", composite),
    ]
    for index, (label, image) in enumerate(panels):
        preview = Image.alpha_composite(Image.new("RGBA", size, (70, 70, 70, 255)), image).convert("RGB")
        contact.paste(preview.resize(thumb), (index * thumb[0], 28))
        draw.text((index * thumb[0] + 5, 7), label, fill="white")
    contact_png = args.output_dir / f"{args.view_id}_dlc-ownership-contact.png"
    contact.save(contact_png)

    manifest = {
        "schema": "mohan.poseatlas.dlc-ownership-staging.v1",
        "status": "OWNER_REVIEW_REQUIRED_NOT_FORMAL",
        "source": {"path": str(args.source.resolve()), "sha256": sha256(args.source)},
        "visible_anatomy_rgba": {"path": anatomy_png.name, "sha256": sha256(anatomy_png), "nonzero_alpha_pixels": anatomy_pixels},
        "default_outfit_rgba": {"path": outfit_png.name, "sha256": sha256(outfit_png), "nonzero_alpha_pixels": outfit_pixels},
        "visible_anatomy_mask": {"path": anatomy_mask_png.name, "sha256": sha256(anatomy_mask_png)},
        "default_outfit_mask": {"path": outfit_mask_png.name, "sha256": sha256(outfit_mask_png)},
        "composite": {"path": composite_png.name, "sha256": sha256(composite_png)},
        "contact": {"path": contact_png.name, "sha256": sha256(contact_png)},
        "ownership_overlap_pixels": overlap,
        "truth_boundary": "DLC ownership staging only. Face geometry, hair, and ornament are excluded from default_outfit. Source 25-layer files were not modified.",
    }
    manifest_path = args.output_dir / "dlc-ownership-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
