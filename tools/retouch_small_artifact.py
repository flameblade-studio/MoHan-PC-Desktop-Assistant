from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image, ImageFilter


def ellipse_mask(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
) -> np.ndarray:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    local = Image.new("L", (width, height), 0)
    pixels = local.load()
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
    mask = Image.new("L", size, 0)
    mask.paste(local, (left, top))
    return np.asarray(mask, dtype=np.uint8) > 0


def retouch(
    source: Path,
    destination: Path,
    box: tuple[int, int, int, int],
) -> None:
    original = Image.open(source).convert("RGBA")
    rgba = np.asarray(original, dtype=np.uint8)
    rgb = rgba[:, :, :3].astype(np.float32)
    mask = ellipse_mask(original.size, box)
    working = rgb.copy()

    # Harmonic inpainting: masked pixels repeatedly converge to the colour
    # field at the untouched boundary. This removes a tiny isolated speck
    # without borrowing a differently aligned face or changing the lip shape.
    for _ in range(240):
        neighbors = (
            np.roll(working, 1, axis=0)
            + np.roll(working, -1, axis=0)
            + np.roll(working, 1, axis=1)
            + np.roll(working, -1, axis=1)
        ) * 0.25
        working[mask] = neighbors[mask]

    hard_mask = Image.fromarray((mask * 255).astype(np.uint8), "L")
    feather = hard_mask.filter(ImageFilter.GaussianBlur(1.0))
    repaired = Image.fromarray(
        np.clip(working, 0, 255).astype(np.uint8),
        "RGB",
    ).convert("RGBA")
    repaired.putalpha(original.getchannel("A"))
    result = Image.composite(repaired, original, feather)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--box",
        required=True,
        help="left,top,right,bottom",
    )
    args = parser.parse_args()
    box = tuple(int(value) for value in args.box.split(","))
    if len(box) != 4:
        raise ValueError("--box must contain four comma-separated integers")
    retouch(args.source, args.out, box)


if __name__ == "__main__":
    main()
