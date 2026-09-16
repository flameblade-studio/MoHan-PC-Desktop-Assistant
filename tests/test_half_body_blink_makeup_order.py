"""Eye-state pigment is composited after the registered bare eyelid patch."""
from __future__ import annotations

lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QPixmap, QPainter
lazy from PySide6.QtWidgets import QApplication
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme

CANVAS = 1254


class EyeMakeup:
    def apply_makeup(self, frame, view_id, *, suppress_makeup_slots, eye_state):
        assert frame.size().toTuple() == (CANVAS, CANVAS)
        assert view_id == "front-crossed"
        assert set(suppress_makeup_slots) == {"eyes", "cheeks", "lips"}
        assert eye_state in {"half", "closed"}
        result = QPixmap(frame)
        painter = QPainter(result)
        painter.fillRect(0, 0, CANVAS, CANVAS, QColor("red"))
        painter.end()
        return result


@pytest.mark.parametrize("state", ("half", "closed"))
@pytest.mark.parametrize("canvas_size", (CANVAS, CANVAS // 2))
def test_blink_pigment_survives_patch_without_touching_surroundings(state, canvas_size):
    QApplication.instance() or QApplication([])
    base = QPixmap(canvas_size, canvas_size)
    base.fill(QColor("blue"))
    patch = QPixmap(base.size())
    patch.fill(Qt.transparent)
    painter = QPainter(patch)
    painter.fillRect(600, 250, 10, 10, QColor("green"))
    painter.end()
    renderer = LayeredParametricFaceRenderer(outfit_overlay=EyeMakeup())
    result = renderer.render_overlay(
        base, patch, eye_state=state, view_id="front-crossed"
    ).toImage()
    assert result.pixelColor(605, 255) == QColor("red")
    assert result.pixelColor(610, 255) == QColor("blue")
    assert base.toImage().pixelColor(605, 255) == QColor("blue")
    assert patch.toImage().pixelColor(605, 255) == QColor("green")


@pytest.mark.parametrize("blink", (0.5, 1.0))
def test_base_remains_rest_until_a_registered_eyelid_patch_exists(blink, monkeypatch):
    QApplication.instance() or QApplication([])
    base = QPixmap(CANVAS, CANVAS)
    base.fill(QColor("blue"))
    states = []

    class BaseMakeup:
        def apply(self, frame, view_id, *, eye_state="rest", **options):
            states.append(eye_state)
            return frame

    renderer = LayeredParametricFaceRenderer(outfit_overlay=BaseMakeup())
    monkeypatch.setattr(renderer, "_pose", lambda motion: None)
    monkeypatch.setattr(renderer, "render_pose", lambda *args, **kwargs: QPixmap(base))
    motion = FaceMotionFrame(
        FacePose.FRONT, "idle_front", Viseme.CLOSED, MouthShape(), ExpressionShape(blink=blink)
    )
    assert renderer.render(base, motion, None).toImage() == base.toImage()
    assert states == ["rest"]
