from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtGui import QImage

MIN_OPAQUE_ALPHA = 5
COOL_METAL_BRIGHTNESS_MIN = 72
DARK_HAIR_BRIGHTNESS_MAX = 122
DARK_HAIR_SPREAD_MAX = 76
BLUE_FABRIC_BRIGHTNESS_MIN = 54
BLUE_FABRIC_RED_MAX = 188
EMBROIDERY_BRIGHTNESS_MIN = 108

SPECS = {
    "": ("idle.png", (780, 175, 885, 525), 835),
    "_lean": ("idle_lean.png", (780, 170, 875, 520), 820),
    "_front": ("idle_front.png", (745, 165, 855, 500), 790),
}

HAIR_SPECS = {
    "": {
        "left": (445, 470, 570, 1085),
        "right": (675, 440, 795, 1085),
    },
    "_lean": {
        "left": (415, 465, 545, 1060),
        "right": (640, 430, 780, 1060),
    },
    "_front": {
        "left": (425, 460, 555, 1060),
        "right": (700, 450, 800, 1060),
    },
}

SLEEVE_SPECS = {
    "": {
        "left": (45, 675, 455, 1235),
        "right": (785, 625, 1225, 1235),
    },
    "_lean": {
        "left": (25, 675, 475, 1235),
        "right": (775, 625, 1228, 1235),
    },
    "_front": {
        "left": (35, 675, 475, 1235),
        "right": (780, 675, 1222, 1235),
    },
}


def extract(source: Path, output: Path, box, free_edge: int) -> None:
    original = QImage(str(source)).convertToFormat(QImage.Format_ARGB32)
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    left, top, right, bottom = box
    for y in range(top, bottom):
        for x in range(left, right):
            color = original.pixelColor(x, y)
            if color.alpha() <= MIN_OPAQUE_ALPHA:
                continue
            brightness = max(color.red(), color.green(), color.blue())
            cool_metal = (
                color.blue() >= color.red() * 0.88
                and color.blue() >= color.green() * 0.82
                and brightness >= COOL_METAL_BRIGHTNESS_MIN
            )
            if x >= free_edge or (
                x >= free_edge - 18 and y < top + 125 and cool_metal
            ):
                layer.setPixelColor(x, y, color)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"無法輸出物理圖層：{output}")


def extract_hair(source: Path, output: Path, box) -> None:
    original = QImage(str(source)).convertToFormat(QImage.Format_ARGB32)
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    left, top, right, bottom = box
    for y in range(top, bottom):
        for x in range(left, right):
            color = original.pixelColor(x, y)
            if color.alpha() <= MIN_OPAQUE_ALPHA:
                continue
            channels = (color.red(), color.green(), color.blue())
            brightness = max(channels)
            spread = max(channels) - min(channels)
            dark_hair = (
                brightness <= DARK_HAIR_BRIGHTNESS_MAX
                and spread <= DARK_HAIR_SPREAD_MAX
                and color.blue() >= color.red() * 0.82
            )
            if dark_hair:
                layer.setPixelColor(x, y, color)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"無法輸出長髮圖層：{output}")


def extract_sleeve(source: Path, output: Path, box) -> None:
    """Extract original robe pixels while keeping skin on the stable base."""
    original = QImage(str(source)).convertToFormat(QImage.Format_ARGB32)
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    left, top, right, bottom = box
    for y in range(top, bottom):
        for x in range(left, right):
            color = original.pixelColor(x, y)
            if color.alpha() <= MIN_OPAQUE_ALPHA:
                continue
            red = color.red()
            green = color.green()
            blue = color.blue()
            brightness = max(red, green, blue)
            blue_fabric = (
                brightness >= BLUE_FABRIC_BRIGHTNESS_MIN
                and blue >= red + 9
                and blue >= green - 4
                and red <= BLUE_FABRIC_RED_MAX
            )
            cool_embroidery = (
                brightness >= EMBROIDERY_BRIGHTNESS_MIN
                and blue >= red * 0.93
                and blue >= green * 0.90
            )
            if blue_fabric or cool_embroidery:
                layer.setPixelColor(x, y, color)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save sleeve layer: {output}")


def main() -> int:
    assets = Path(sys.argv[1])
    for suffix, (source_name, box, free_edge) in SPECS.items():
        extract(
            assets / source_name,
            assets / f"physics_ornament{suffix}.png",
            box,
            free_edge,
        )
        source_path = assets / source_name
        for side, hair_box in HAIR_SPECS[suffix].items():
            extract_hair(
                source_path,
                assets / f"physics_hair_{side}{suffix}.png",
                hair_box,
            )
        for side, sleeve_box in SLEEVE_SPECS[suffix].items():
            extract_sleeve(
                source_path,
                assets / f"physics_sleeve_{side}{suffix}.png",
                sleeve_box,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
