#!/usr/bin/env python3
"""Build a compact visual comparison from two face-refinement attempts."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def existing(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt6", required=True, type=existing)
    parser.add_argument("--attempt7", required=True, type=existing)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args()
    if not parsed.output.is_absolute() or parsed.output.drive.upper() != "D:":
        raise ValueError("output must be an absolute D-drive path")
    if parsed.output.exists():
        raise FileExistsError(parsed.output)

    panels: list[Image.Image] = []
    for source in (parsed.attempt6, parsed.attempt7):
        image = Image.open(source).convert("RGB")
        if image.size != (1344, 848):
            raise ValueError(f"unexpected detail contact size: {source}: {image.size}")
        panels.extend((image.crop((0, 48, 672, 848)), image.crop((672, 48, 1344, 848))))

    canvas = Image.new("RGB", (2688, 850), (28, 31, 35))
    draw = ImageDraw.Draw(canvas)
    labels = ("attempt6 raw", "attempt6 B00 refine", "attempt7 raw", "attempt7 B00 refine")
    for index, (panel, label) in enumerate(zip(panels, labels, strict=True)):
        x = index * 672
        canvas.paste(panel.resize((672, 800), Image.Resampling.LANCZOS), (x, 50))
        draw.text((x + 12, 16), label, fill=(160, 255, 180) if "refine" in label else (240, 240, 240))
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(parsed.output)
    print(parsed.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
