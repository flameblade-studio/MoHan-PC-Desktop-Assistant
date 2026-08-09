from __future__ import annotations

lazy import math
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtGui import QImage


@dataclass(frozen=True, slots=True)
class EllipseSpec:
    center_x: int
    center_y: int
    radius_x: int
    radius_y: int


@dataclass(frozen=True, slots=True)
class AttentionLayerSpec:
    source: str
    face: EllipseSpec
    eyes: tuple[EllipseSpec, EllipseSpec]


SPECS = {
    "": AttentionLayerSpec(
        source="idle.png",
        face=EllipseSpec(575, 500, 116, 158),
        eyes=(EllipseSpec(496, 438, 24, 15), EllipseSpec(601, 458, 24, 15)),
    ),
    "_lean": AttentionLayerSpec(
        source="idle_lean.png",
        face=EllipseSpec(571, 500, 116, 158),
        eyes=(EllipseSpec(477, 439, 24, 15), EllipseSpec(578, 459, 24, 15)),
    ),
    "_front": AttentionLayerSpec(
        source="idle_front.png",
        face=EllipseSpec(625, 482, 120, 154),
        eyes=(EllipseSpec(551, 447, 24, 15), EllipseSpec(661, 447, 24, 15)),
    ),
}


def ellipse_weight(
    x: int,
    y: int,
    spec: EllipseSpec,
    feather: float,
) -> float:
    distance = math.sqrt(
        ((x - spec.center_x) / spec.radius_x) ** 2
        + ((y - spec.center_y) / spec.radius_y) ** 2
    )
    if distance >= 1.0:
        return 0.0
    if distance <= 1.0 - feather:
        return 1.0
    return (1.0 - distance) / feather


def _apply_ellipse(
    original: QImage,
    layer: QImage,
    spec: EllipseSpec,
    feather: float,
) -> None:
    x_range = range(
        spec.center_x - spec.radius_x,
        spec.center_x + spec.radius_x + 1,
    )
    y_range = range(
        spec.center_y - spec.radius_y,
        spec.center_y + spec.radius_y + 1,
    )
    for y in y_range:
        for x in x_range:
            weight = ellipse_weight(x, y, spec, feather)
            if weight <= 0.0:
                continue
            color = original.pixelColor(x, y)
            color.setAlpha(round(color.alpha() * weight))
            layer.setPixelColor(x, y, color)


def _empty_layer(original: QImage) -> QImage:
    layer = QImage(original.size(), QImage.Format_ARGB32)
    layer.fill(0)
    return layer


def _save_layer(layer: QImage, output: Path, label: str) -> None:
    if not layer.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save {label} layer: {output}")


def extract_face(
    original: QImage,
    output: Path,
    spec: EllipseSpec,
) -> None:
    layer = _empty_layer(original)
    _apply_ellipse(original, layer, spec, 0.18)
    _save_layer(layer, output, "face")


def extract_eyes(
    original: QImage,
    output: Path,
    specs: tuple[EllipseSpec, EllipseSpec],
) -> None:
    layer = _empty_layer(original)
    for spec in specs:
        _apply_ellipse(original, layer, spec, 0.32)
    _save_layer(layer, output, "eye")


def main() -> int:
    assets = Path(sys.argv[1])
    for suffix, spec in SPECS.items():
        original = QImage(str(assets / spec.source)).convertToFormat(
            QImage.Format_ARGB32
        )
        extract_face(original, assets / f"physics_face{suffix}.png", spec.face)
        extract_eyes(original, assets / f"physics_eyes{suffix}.png", spec.eyes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
