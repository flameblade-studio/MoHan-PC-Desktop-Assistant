#!/usr/bin/env python3
"""Build one raw/refined face-and-thumb contact for owner review."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def fitted_crop(
    image: Image.Image,
    box: tuple[int, int, int, int],
    size: tuple[int, int],
) -> Image.Image:
    return ImageOps.fit(image.crop(box).convert("RGB"), size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True, type=existing_file)
    parser.add_argument("--refined", required=True, type=existing_file)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args()
    if not parsed.output.is_absolute() or parsed.output.drive.upper() != "D:":
        raise ValueError("output must be an absolute D-drive path")
    if parsed.output.exists():
        raise FileExistsError(parsed.output)

    canvas = Image.new("RGB", (2048, 1100), (26, 29, 33))
    draw = ImageDraw.Draw(canvas)
    for index, (label, path) in enumerate((("RAW BASE", parsed.raw), ("V5 AUTHORITY FACE REFINE", parsed.refined))):
        image = Image.open(path).convert("RGBA")
        if image.size != (1024, 1536):
            raise ValueError(f"unexpected candidate size: {path}: {image.size}")
        background = Image.new("RGB", image.size, (18, 18, 18))
        background.paste(image, mask=image.getchannel("A"))
        x = index * 1024
        draw.text((x + 16, 12), label, fill=(150, 255, 175) if index else (240, 240, 240))
        canvas.paste(fitted_crop(background, (390, 95, 635, 360), (1024, 700)), (x, 42))
        draw.text((x + 16, 754), "viewer-left thumb", fill=(220, 220, 220))
        draw.text((x + 528, 754), "viewer-right thumb", fill=(220, 220, 220))
        canvas.paste(fitted_crop(background, (210, 725, 320, 880), (512, 320)), (x, 780))
        canvas.paste(fitted_crop(background, (705, 725, 815, 880), (512, 320)), (x + 512, 780))
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(parsed.output)
    print(parsed.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
