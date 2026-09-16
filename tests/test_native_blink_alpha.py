"""A blink changes eye colour without increasing the native body matte."""
from __future__ import annotations

lazy import os
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from domain.face_rig import EyeState

SOURCE_RED = 200
QUANTIZATION_TOLERANCE = 1


@pytest.mark.parametrize("state", ("half", "closed"))
@pytest.mark.parametrize("full_body", (False, True))
def test_registered_blink_preserves_translucent_and_empty_native_pixels(state, full_body):
    app = QApplication.instance() or QApplication([])
    base = QImage(3, 1, QImage.Format_RGBA8888)
    for x, alpha in enumerate((0, 128, 255)):
        base.setPixelColor(x, 0, QColor(20, 60, 90, alpha))
    source = QImage(3, 1, QImage.Format_RGBA8888)
    source.fill(QColor(SOURCE_RED, 40, 20, 255))
    if full_body:
        renderer = object.__new__(LayeredFullBodyRenderer)
        renderer._cached_pixmap = lambda _path: QPixmap.fromImage(source)
        target = QPixmap.fromImage(base)
        view = SimpleNamespace(blink_frames={EyeState(state): "registered.png"})
        motion = SimpleNamespace(expression_shape=SimpleNamespace(blink=.5 if state == "half" else 1.))
        renderer._paint_dynamic_eye_layers(target, view, motion)
        result = target.toImage()
    else:
        renderer = object.__new__(LayeredParametricFaceRenderer)
        renderer._outfit_overlay = None
        # The probe bypasses __init__; no complete half-body source claims this blink.
        renderer._complete_halfbody = SimpleNamespace(blink=lambda _base, _eye_state: None)
        result = renderer.render_overlay(
            QPixmap.fromImage(base), QPixmap.fromImage(source),
            eye_state=state, view_id="front-crossed",
        ).toImage()

    assert [result.pixelColor(x, 0).alpha() for x in range(3)] == [0, 128, 255]
    assert result.pixelColor(1, 0).red() >= SOURCE_RED - QUANTIZATION_TOLERANCE
    assert result.pixelColor(2, 0).red() == SOURCE_RED
    assert app is not None
