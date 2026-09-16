"""A reviewed neutral face precedes motion and cannot fall back to the old rig."""
from __future__ import annotations

import os
from types import SimpleNamespace
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication
from domain.face_rig import FaceMotionFrame, FacePose, Viseme, MouthShape, ExpressionShape
from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer


def test_reviewed_neutral_bypasses_obsolete_rig_and_preserves_speech(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    native = QPixmap(20, 20)
    native.fill(QColor("blue"))
    stale = QPixmap(20, 20)
    stale.fill(QColor("green"))
    overlay = SimpleNamespace(native_neutral=lambda view: native.copy(), apply=lambda frame, view: frame)
    renderer = LayeredParametricFaceRenderer(outfit_overlay=overlay)
    def obsolete(*args, **kwargs):
        pytest.fail("Reviewed neutral must not use the obsolete face rig")
    monkeypatch.setattr(renderer, "_detachable_portrait", obsolete)
    monkeypatch.setattr(renderer, "render_pose", obsolete)
    motion = FaceMotionFrame(FacePose.CHEEK, "idle", Viseme.CLOSED, MouthShape(), ExpressionShape())
    rest = renderer.render(stale, motion, None)
    assert rest.toImage().pixelColor(10, 10) == QColor("blue")
    mouth = QPixmap(20, 20)
    mouth.fill(QColor("red"))
    mask = QPixmap(20, 20)
    mask.fill(Qt.transparent)
    image = mask.toImage()
    image.setPixelColor(10, 10, QColor("white"))
    mask = QPixmap.fromImage(image)
    spoken = renderer.render(stale, motion, SimpleNamespace(mouth_source=mouth, mouth_mask=mask), aperture=1)
    assert spoken.toImage().pixelColor(10, 10) == QColor("red")
    assert spoken.toImage().pixelColor(0, 0) == QColor("blue")
    assert native.toImage().pixelColor(10, 10) == QColor("blue")
