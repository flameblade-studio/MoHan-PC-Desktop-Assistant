#!/usr/bin/env python3
"""Build a <=2048px owner contact with face and bilateral-thumb details."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def existing(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def fitted_crop(image: Image.Image, box: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image.crop(box).convert("RGB"), size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt6-raw", required=True, type=existing)
    parser.add_argument("--attempt6-refined", required=True, type=existing)
    parser.add_argument("--attempt7-raw", required=True, type=existing)
    parser.add_argument("--attempt7-refined", required=True, type=existing)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args()
    if not parsed.output.is_absolute() or parsed.output.drive.upper() != "D:":
        raise ValueError("output must be an absolute D-drive path")
    if parsed.output.exists():
        raise FileExistsError(parsed.output)

    sources = (
        ("attempt6 RAW", parsed.attempt6_raw),
        ("attempt6 B00 FACE REFINE", parsed.attempt6_refined),
        ("attempt7 RAW true_cfg2", parsed.attempt7_raw),
        ("attempt7 B00 FACE REFINE", parsed.attempt7_refined),
    )
    canvas = Image.new("RGB", (2048, 930), (26, 29, 33))
    draw = ImageDraw.Draw(canvas)
    for index, (label, path) in enumerate(sources):
        image = Image.open(path).convert("RGBA")
        if image.size != (1024, 1536):
            raise ValueError(f"unexpected candidate size: {path}: {image.size}")
        background = Image.new("RGB", image.size, (18, 18, 18))
        background.paste(image, mask=image.getchannel("A"))
        x = index * 512
        draw.text((x + 12, 12), label, fill=(150, 255, 175) if "REFINE" in label else (240, 240, 240))
        canvas.paste(fitted_crop(background, (430, 130, 598, 330), (512, 610)), (x, 42))
        draw.text((x + 12, 662), "viewer-left thumb", fill=(220, 220, 220))
        draw.text((x + 268, 662), "viewer-right thumb", fill=(220, 220, 220))
        canvas.paste(fitted_crop(background, (210, 725, 320, 880), (256, 230)), (x, 700))
        canvas.paste(fitted_crop(background, (705, 725, 815, 880), (256, 230)), (x + 256, 700))
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(parsed.output)
    print(parsed.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
