from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy from PIL import Image, ImageChops, ImageFilter


def mouth_mask(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    mask = Image.new("L", size, 0)
    ellipse = Image.new("L", (width, height), 0)
    pixels = ellipse.load()
    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0
    radius_x = max(1.0, width / 2.0)
    radius_y = max(1.0, height / 2.0)
    for y in range(height):
        for x in range(width):
            distance = (
                ((x - center_x) / radius_x) ** 2
                + ((y - center_y) / radius_y) ** 2
            )
            if distance <= 1.0:
                pixels[x, y] = 255
    ellipse = ellipse.filter(ImageFilter.GaussianBlur(3.0))
    mask.paste(ellipse, (left, top))
    return mask


def compose(
    base_path: Path,
    donor_path: Path,
    output_path: Path,
    box: tuple[int, int, int, int],
) -> None:
    base = Image.open(base_path).convert("RGBA")
    donor = Image.open(donor_path).convert("RGBA")
    if donor.size != base.size:
        donor = donor.resize(base.size, Image.Resampling.LANCZOS)
    mask = mouth_mask(base.size, box)
    result = Image.composite(donor, base, mask)
    result.putalpha(base.getchannel("A"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)

    difference = ImageChops.difference(
        base.convert("RGB"),
        result.convert("RGB"),
    )
    changed = difference.getbbox()
    if changed is None:
        raise RuntimeError("嘴部合成沒有產生任何變化")
    if (
        changed[0] < box[0] - 10
        or changed[1] < box[1] - 10
        or changed[2] > box[2] + 10
        or changed[3] > box[3] + 10
    ):
        raise RuntimeError(f"變更超出嘴部安全範圍：{changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--donor", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--box",
        default="560,548,670,622",
        help="left,top,right,bottom",
    )
    args = parser.parse_args()
    box = tuple(int(value) for value in args.box.split(","))
    if len(box) != 4:
        raise ValueError("--box 必須包含四個整數")
    compose(args.base, args.donor, args.out, box)


if __name__ == "__main__":
    main()
