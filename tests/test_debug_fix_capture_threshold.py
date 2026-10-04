"""Regression probes for REPORT-C #6 and #7 using synthetic pixels."""

from __future__ import annotations

lazy import json
lazy from types import SimpleNamespace

lazy import pytest
lazy from PIL import Image
lazy from PySide6.QtCore import QPoint, QRect
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from tools import analyze_layered_assets as analysis
lazy from tools import capture_blink_layer_audit as blink
lazy from tools import capture_eye_alignment_preview as eye
lazy from tools import capture_motion_transition_audit as motion
lazy from tools import capture_mouth_layer_audit as mouth
lazy from tools import capture_v120_flagship_preview as flagship


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_threshold_controls_actual_outlier_decision(tmp_path, app, monkeypatch):
    views = analysis.VIEW_IDS[:3]
    monkeypatch.setattr(analysis, "VIEW_IDS", views)
    monkeypatch.setattr(analysis, "LAYER_NAMES", ("body", "hair_left"))
    for index, view in enumerate(views):
        for layer in analysis.LAYER_NAMES:
            image = Image.new("RGBA", (16, 16))
            x = 8 if layer == "hair_left" and index == 1 else 3
            image.putpixel((x, 3), (255, 0, 0, 255))
            image.save(tmp_path / f"{view}_{layer}.png")
    for threshold, expected in ((2, 1), (5, 0), (99, 0)):
        output = tmp_path / f"report-{threshold}.json"
        assert analysis.main([
            "--asset-dir", str(tmp_path), "--output", str(output),
            "--threshold", str(threshold),
        ]) == 0
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["outlier_threshold_pixels"] == threshold
        assert report["outlier_count"] == expected


class AuditWindow:
    """A fixed logical red rectangle on blue, captured at a chosen DPR."""

    character_base_x = 0
    character_base_y = 230
    blink_generation = 0

    def __init__(self, ratio, rectangle):
        self.ratio = ratio
        self.rectangle = rectangle
        self.physics_features = {}
        self.character = SimpleNamespace(x=lambda: 0, y=lambda: 230, pos=lambda: QPoint(0, 230))
        self.bubble = SimpleNamespace(hide=lambda: None)
        for name in (
            "expression_overlay", "sleeve_left_overlay", "sleeve_right_overlay",
            "hair_left_overlay", "hair_right_overlay", "physics_overlay",
            "face_overlay", "eye_overlay",
        ):
            setattr(self, name, SimpleNamespace(hide=lambda: None, pos=lambda: QPoint(0, 230)))

    def width(self):
        return 470

    def show(self):
        return None

    def close(self):
        return None

    def findChildren(self, _kind):
        return []

    def _set_expression(self, _expression, *, fade):
        return None

    def _render_attention_layers(self, *, force):
        return None

    _render_sleeve_layers = _render_attention_layers
    _render_hair_layers = _render_attention_layers
    _render_physics_layer = _render_attention_layers

    def _attention_tick(self):
        return None

    def _blink(self):
        return None

    def _finish_blink(self, _expression, _generation):
        return None

    def grab(self, rectangle=None):
        image = QImage(round(470 * self.ratio), round(760 * self.ratio), QImage.Format_ARGB32)
        image.setDevicePixelRatio(self.ratio)
        image.fill(QColor("blue"))
        painter = QPainter(image)
        painter.fillRect(self.rectangle, QColor("red"))
        painter.end()
        if rectangle is not None:
            image = image.copy(QRect(
                round(rectangle.x() * self.ratio), round(rectangle.y() * self.ratio),
                round(rectangle.width() * self.ratio), round(rectangle.height() * self.ratio),
            ))
        return QPixmap.fromImage(image)


@pytest.mark.parametrize("ratio", (1.0, 1.5, 2.0))
@pytest.mark.parametrize("tool", ("blink", "eye", "motion", "mouth", "flagship"))
def test_audit_crop_and_composition_preserve_logical_region(tool, ratio, app, monkeypatch, tmp_path):
    rectangles = {
        "blink": QRect(120, 330, 170, 155),
        "eye": QRect(120, 330, 230, 220),
        "motion": QRect(0, 230, 470, 465),
        "mouth": QRect(145, 370, 145, 125),
        "flagship": QRect(0, 230, 470, 465),
    }
    window = AuditWindow(ratio, rectangles[tool])
    module = {"blink": blink, "eye": eye, "motion": motion, "mouth": mouth, "flagship": flagship}[tool]
    if tool == "motion":
        frames = module.capture_frames(app, window, 1, 0)
        image = module.compose_audit_canvas(window, frames)
        sample = (469, 464)
    elif tool == "mouth":
        frame = module.capture_face_frame(window, QRect(145, 140, 145, 125))
        image = module.compose_audit_canvas([("cheek", [frame])])
        sample = (module.GRID_MARGIN + 225, module.GRID_MARGIN + module.TITLE_HEIGHT + 197)
    else:
        monkeypatch.setattr(module, "QApplication", lambda _args: app)
        monkeypatch.setattr(module, "CompanionWindow", lambda **_kwargs: window)
        output = tmp_path / f"{tool}-{ratio}.png"
        if tool == "blink":
            module.render(output)
            sample = (340, 290)
        else:
            monkeypatch.setattr(module.sys, "argv", ["capture", str(output)])
            assert module.main() == 0
            sample = (242, 268) if tool == "eye" else (488, 531)
        image = QImage(str(output))
    assert image.pixelColor(*sample) == QColor("red"), (tool, ratio, image.pixelColor(*sample).name())
