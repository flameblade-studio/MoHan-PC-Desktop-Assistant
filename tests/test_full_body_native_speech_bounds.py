"""Regression coverage for native speech bounds below the old face cutoff."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QColor, QImage, QPainter
lazy from PySide6.QtWidgets import QApplication
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
)
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW_ID = "yaw+000-pitch+00"
CANVAS_SIZE = (128, 160)
BODY_COLOR = (28, 35, 48, 255)
AUTHORITY_COLOR = (214, 183, 165, 255)
FACE_LAYER_COLOR = (77, 86, 101, 255)
ORAL_COLOR = (132, 32, 57, 255)
TRANSPARENT = (0, 0, 0, 0)

# The registered lip footprint is below the historical face-height cutoff. The
# jaw continues lower, so a speech clip that is too broad would repaint it.
BASE_RECT = QRect(18, 12, 92, 116)
JAW_RECT = QRect(28, 92, 72, 40)
ORAL_RECT = QRect(46, 104, 32, 30)
LIP_UPPER_RECT = QRect(50, 112, 20, 3)
LIP_LOWER_RECT = QRect(47, 115, 26, 6)
CORNER_LEFT_RECT = QRect(44, 114, 4, 4)
CORNER_RIGHT_RECT = QRect(72, 114, 4, 4)
CHIN_RECT = QRect(46, 124, 32, 5)
LOWER_EDGE_POINT = (60, LIP_LOWER_RECT.bottom())
FULL_CANVAS_RECT = QRect(0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1])
OPEN_APERTURE = 1.0
NEUTRAL_APERTURE = 0.0


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_layer(
    path: Path,
    *,
    fill: tuple[int, int, int, int] = TRANSPARENT,
    rectangles: tuple[tuple[QRect, tuple[int, int, int, int]], ...] = (),
) -> None:
    image = QImage(CANVAS_SIZE[0], CANVAS_SIZE[1], QImage.Format_RGBA8888)
    image.fill(QColor(*fill))
    painter = QPainter(image)
    for rectangle, color in rectangles:
        painter.fillRect(rectangle, QColor(*color))
    painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")


def _fixture(tmp_path: Path) -> LayeredFullBodyRenderer:
    authority_root = tmp_path / "authority"
    layer_root = tmp_path / "layers"
    _write_layer(authority_root / f"{VIEW_ID}.png", fill=AUTHORITY_COLOR)

    layers = {
        "body": layer_root / f"{VIEW_ID}_body.png",
        "base": layer_root / f"{VIEW_ID}_base.png",
        "jaw": layer_root / f"{VIEW_ID}_jaw.png",
        "oral_cavity": layer_root / f"{VIEW_ID}_oral_cavity.png",
        "lip_upper": layer_root / f"{VIEW_ID}_lip_upper.png",
        "lip_lower": layer_root / f"{VIEW_ID}_lip_lower.png",
        "corner_left": layer_root / f"{VIEW_ID}_corner_left.png",
        "corner_right": layer_root / f"{VIEW_ID}_corner_right.png",
    }
    _write_layer(layers["body"], fill=BODY_COLOR)
    _write_layer(
        layers["base"],
        rectangles=((BASE_RECT, FACE_LAYER_COLOR),),
    )
    _write_layer(
        layers["jaw"],
        rectangles=((JAW_RECT, FACE_LAYER_COLOR),),
    )
    _write_layer(
        layers["oral_cavity"],
        rectangles=((ORAL_RECT, ORAL_COLOR),),
    )
    for layer_name, rectangle in (
        ("lip_upper", LIP_UPPER_RECT),
        ("lip_lower", LIP_LOWER_RECT),
        ("corner_left", CORNER_LEFT_RECT),
        ("corner_right", CORNER_RIGHT_RECT),
    ):
        _write_layer(layers[layer_name], rectangles=((rectangle, FACE_LAYER_COLOR),))

    view = LayeredFullBodyView(VIEW_ID, layers)
    manifest = LayeredFullBodyManifest({VIEW_ID: view})
    return LayeredFullBodyRenderer(manifest, authority_root=authority_root)


def _motion(*, aperture: float, viseme: Viseme) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "synthetic_speech_bounds",
        viseme,
        MouthShape(aperture=aperture),
        ExpressionShape(),
        breath=0.5,
    )


def _pixel(image: QImage, point: tuple[int, int]) -> tuple[int, int, int, int]:
    color = image.pixelColor(*point)
    return color.red(), color.green(), color.blue(), color.alpha()


def _region_pixels(image: QImage, rectangle: QRect) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        _pixel(image, (x, y))
        for y in range(rectangle.top(), rectangle.bottom() + 1)
        for x in range(rectangle.left(), rectangle.right() + 1)
    )


def test_native_speech_uses_registered_lips_below_face_cutoff(tmp_path: Path) -> None:
    """Speech reaches the native lip edge while preserving the lower jaw."""

    _app()
    renderer = _fixture(tmp_path)
    neutral = renderer.render_view(
        VIEW_ID,
        _motion(aperture=NEUTRAL_APERTURE, viseme=Viseme.CLOSED),
    ).toImage()
    zero_aperture_speech = renderer.render_view(
        VIEW_ID,
        _motion(aperture=NEUTRAL_APERTURE, viseme=Viseme.A),
    ).toImage()
    speaking = renderer.render_view(
        VIEW_ID,
        _motion(aperture=OPEN_APERTURE, viseme=Viseme.A),
    ).toImage()

    assert _region_pixels(zero_aperture_speech, FULL_CANVAS_RECT) == _region_pixels(
        neutral,
        FULL_CANVAS_RECT,
    )
    assert _pixel(speaking, LOWER_EDGE_POINT) != _pixel(neutral, LOWER_EDGE_POINT)
    assert _region_pixels(speaking, CHIN_RECT) == _region_pixels(neutral, CHIN_RECT)
