from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy from PySide6.QtGui import QImage


def extract_chroma_alpha(
    source: Path,
    destination: Path,
    *,
    spill_threshold: int = 92,
    hard_threshold: int = 34,
) -> None:
    """Remove a magenta screen while preserving antialiased subject edges."""

    image = QImage(str(source))
    if image.isNull():
        raise ValueError(f"Cannot decode source image: {source}")
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = image.bits()
    for index in range(0, image.sizeInBytes(), 4):
        red, green, blue = (
            pixels[index],
            pixels[index + 1],
            pixels[index + 2],
        )
        magenta = min(red, blue) - green
        chroma_balance = abs(red - blue)
        distance = max(0, magenta - chroma_balance // 2)
        if distance >= spill_threshold:
            pixels[index + 3] = 0
            continue
        if distance <= hard_threshold:
            pixels[index + 3] = 255
            continue
        pixels[index + 3] = round(
            255
            * (spill_threshold - distance)
            / (spill_threshold - hard_threshold)
        )
        pixels[index] = min(red, green + max(0, red - blue))
        pixels[index + 2] = min(blue, green + max(0, blue - red))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination), "PNG"):
        raise OSError(f"Cannot write destination image: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a pure-magenta character render into transparent RGBA."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    extract_chroma_alpha(args.source, args.destination)


if __name__ == "__main__":
    main()
