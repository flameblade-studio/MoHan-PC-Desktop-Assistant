from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.face_renderer import FaceRenderLayers, ParametricFaceRenderer


def solid(color: str) -> QPixmap:
    pixmap = QPixmap(96, 96)
    pixmap.fill(QColor(color))
    return pixmap


def mask(region: QRect) -> QPixmap:
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.fillRect(region, QColor("white"))
    painter.end()
    return pixmap


def run() -> None:
    app = QApplication.instance() or QApplication([])
    mouth_rect = QRect(32, 55, 32, 18)
    blink_rect = QRect(25, 30, 46, 12)
    layers = FaceRenderLayers(
        mouth_source=solid("#d04a62"),
        mouth_mask=mask(mouth_rect),
        mouth_rect=mouth_rect,
        blink_source=solid("#202030"),
        blink_mask=mask(blink_rect),
    )
    motion = FaceMotionFrame(
        pose=FacePose.FRONT,
        expression="happy",
        viseme=Viseme.A,
        mouth=MouthShape(0.8, 0.8, 0.1, 0.7),
        expression_shape=ExpressionShape(blink=1.0, eye_smile=0.7),
    )
    base = solid("#f2d2c4")
    rendered = ParametricFaceRenderer().render(
        base,
        motion,
        layers,
    ).toImage()
    assert rendered.pixelColor(mouth_rect.center()).name() != "#f2d2c4"
    assert rendered.pixelColor(blink_rect.center()).name() == "#202030"
    corner = rendered.pixelColor(2, 2)
    base_corner = base.toImage().pixelColor(2, 2)
    assert corner == base_corner, (corner.name(), base_corner.name())
    app.processEvents()
    print("FACE_RENDERER_OK")


if __name__ == "__main__":
    run()
