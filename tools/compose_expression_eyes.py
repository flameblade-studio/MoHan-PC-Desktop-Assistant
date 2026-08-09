from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy from PIL import Image, ImageChops, ImageFilter


def ellipse_mask(
    size: tuple[int, int],
    boxes: tuple[tuple[int, int, int, int], ...],
) -> Image.Image:
    mask = Image.new("L", size, 0)
    for left, top, right, bottom in boxes:
        width = right - left
        height = bottom - top
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
        mask.paste(ImageChops.lighter(
            mask.crop((left, top, right, bottom)),
            ellipse,
        ), (left, top))
    return mask


def compose(
    base_path: Path,
    donor_path: Path,
    output_path: Path,
    boxes: tuple[tuple[int, int, int, int], ...],
) -> None:
    base = Image.open(base_path).convert("RGBA")
    donor = Image.open(donor_path).convert("RGBA")
    if donor.size != base.size:
        donor = donor.resize(base.size, Image.Resampling.LANCZOS)
    mask = ellipse_mask(base.size, boxes)
    result = Image.composite(donor, base, mask)
    result.putalpha(base.getchannel("A"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)

    changed = ImageChops.difference(
        base.convert("RGB"),
        result.convert("RGB"),
    ).getbbox()
    if changed is None:
        raise RuntimeError("閉眼素材沒有產生像素差異")
    allowed = (
        min(box[0] for box in boxes) - 10,
        min(box[1] for box in boxes) - 10,
        max(box[2] for box in boxes) + 10,
        max(box[3] for box in boxes) + 10,
    )
    if (
        changed[0] < allowed[0]
        or changed[1] < allowed[1]
        or changed[2] > allowed[2]
        or changed[3] > allowed[3]
    ):
        raise RuntimeError(f"眼部變更超出安全區：{changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--donor", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--boxes",
        required=True,
        help="left,top,right,bottom;left,top,right,bottom",
    )
    args = parser.parse_args()
    boxes = tuple(
        tuple(int(value) for value in item.split(","))
        for item in args.boxes.split(";")
    )
    if not boxes or any(len(box) != 4 for box in boxes):
        raise ValueError("--boxes 必須包含一至多個四值矩形")
    compose(args.base, args.donor, args.out, boxes)


if __name__ == "__main__":
    main()
