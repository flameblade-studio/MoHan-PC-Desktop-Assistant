from __future__ import annotations

lazy import math
lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtGui import QColor, QImage

BLEND_CORE_THRESHOLD = 0.55
BLEND_FALLOFF = 0.45
ARGV_COUNT = 5


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def composite_mouth(
    base_path: Path,
    generated_path: Path,
    output_path: Path,
    box: tuple[int, int, int, int],
) -> None:
    base = QImage(str(base_path)).convertToFormat(QImage.Format_ARGB32)
    generated = QImage(str(generated_path)).convertToFormat(QImage.Format_ARGB32)
    if base.isNull() or generated.isNull():
        raise RuntimeError(f"無法讀取嘴型素材：{base_path} / {generated_path}")
    if base.size() != generated.size():
        generated = generated.scaled(base.size())

    left, top, width, height = box
    center_x = left + width / 2
    center_y = top + height / 2
    radius_x = width / 2
    radius_y = height / 2
    for y in range(top, top + height):
        for x in range(left, left + width):
            distance = math.sqrt(
                ((x - center_x) / radius_x) ** 2
                + ((y - center_y) / radius_y) ** 2
            )
            if distance >= 1.0:
                continue
            weight = 1.0 if distance <= BLEND_CORE_THRESHOLD else 1.0 - smoothstep(
                (distance - BLEND_CORE_THRESHOLD) / BLEND_FALLOFF
            )
            original = base.pixelColor(x, y)
            edited = generated.pixelColor(x, y)
            mixed = QColor(
                round(original.red() * (1 - weight) + edited.red() * weight),
                round(original.green() * (1 - weight) + edited.green() * weight),
                round(original.blue() * (1 - weight) + edited.blue() * weight),
                original.alpha(),
            )
            base.setPixelColor(x, y, mixed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not base.save(str(output_path), "PNG"):
        raise RuntimeError(f"無法輸出：{output_path}")


def main() -> int:
    if len(sys.argv) != ARGV_COUNT:
        raise SystemExit(
            "usage: compose_viseme.py BASE GENERATED OUTPUT X,Y,W,H"
        )
    composite_mouth(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        tuple(int(part) for part in sys.argv[4].split(",")),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
