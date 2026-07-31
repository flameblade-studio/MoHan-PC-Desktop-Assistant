from __future__ import annotations

import math
import sys
from pathlib import Path

from PySide6.QtGui import QImage


SPECS = {
    "": {
        "source": "idle.png",
        "face": (575, 500, 116, 158),
        "eyes": ((496, 438, 24, 15), (601, 458, 24, 15)),
    },
    "_lean": {
        "source": "idle_lean.png",
        "face": (571, 500, 116, 158),
        "eyes": ((477, 439, 24, 15), (578, 459, 24, 15)),
    },
    "_front": {
        "source": "idle_front.png",
        "face": (625, 482, 120, 154),
        "eyes": ((551, 447, 24, 15), (661, 447, 24, 15)),
    },
}


def ellipse_weight(
    x: int,
    y: int,
    center_x: int,
    center_y: int,
    radius_x: int,
    radius_y: int,
    feather: float,
) -> float:
    distance = math.sqrt(
        ((x - center_x) / radius_x) ** 2
        + ((y - center_y) / radius_y) ** 2
    )
    if distance >= 1.0:
        return 0.0
    if distance <= 1.0 - feather:
        return 1.0
    return (1.0 - distance) / feather


def extract_face(
    original: QImage,
    output: Path,
    spec: tuple[int, int, int, int],
) -> None:
    center_x, center_y, radius_x, radius_y = spec
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    for y in range(center_y - radius_y, center_y + radius_y + 1):
        for x in range(center_x - radius_x, center_x + radius_x + 1):
            weight = ellipse_weight(
                x,
                y,
                center_x,
                center_y,
                radius_x,
                radius_y,
                0.18,
            )
            if weight <= 0.0:
                continue
            color = original.pixelColor(x, y)
            color.setAlpha(round(color.alpha() * weight))
            layer.setPixelColor(x, y, color)
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save face layer: {output}")


def extract_eyes(
    original: QImage,
    output: Path,
    specs: tuple[tuple[int, int, int, int], ...],
) -> None:
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    for center_x, center_y, radius_x, radius_y in specs:
        for y in range(center_y - radius_y, center_y + radius_y + 1):
            for x in range(center_x - radius_x, center_x + radius_x + 1):
                weight = ellipse_weight(
                    x,
                    y,
                    center_x,
                    center_y,
                    radius_x,
                    radius_y,
                    0.32,
                )
                if weight <= 0.0:
                    continue
                color = original.pixelColor(x, y)
                color.setAlpha(round(color.alpha() * weight))
                layer.setPixelColor(x, y, color)
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save eye layer: {output}")


def main() -> int:
    assets = Path(sys.argv[1])
    for suffix, spec in SPECS.items():
        original = QImage(str(assets / spec["source"])).convertToFormat(
            QImage.Format_ARGB32
        )
        extract_face(
            original,
            assets / f"physics_face{suffix}.png",
            spec["face"],
        )
        extract_eyes(
            original,
            assets / f"physics_eyes{suffix}.png",
            spec["eyes"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
