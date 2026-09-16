"""Transparent silhouettes cross-fade and fully release the prior view."""
from __future__ import annotations

lazy import os
lazy from pathlib import Path
lazy import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

CURRENT_VIEW = "yaw+000-pitch+00"
NEXT_VIEW = "yaw+015-pitch+00"
CHANNEL_TOLERANCE = 1
HALF_OPACITY = 128
OPAQUE = 255


def _frames() -> dict[str, QPixmap]:
    QApplication.instance() or QApplication([])
    first = QImage(4, 1, QImage.Format_RGBA8888)
    first.fill(QColor("transparent"))
    second = first.copy()
    first.setPixelColor(0, 0, QColor("red"))
    first.setPixelColor(1, 0, QColor("red"))
    second.setPixelColor(1, 0, QColor("blue"))
    second.setPixelColor(2, 0, QColor("blue"))
    first.setPixelColor(3, 0, QColor(255, 0, 0, 128))
    second.setPixelColor(3, 0, QColor(0, 0, 255, 64))
    return {CURRENT_VIEW: QPixmap.fromImage(first), NEXT_VIEW: QPixmap.fromImage(second)}


class FixedFramesRenderer(LayeredFullBodyRenderer):
    def __init__(self, frames: dict[str, QPixmap]) -> None:
        super().__init__()
        self.frames = frames

    def render_view(self, view_id, motion, **kwargs) -> QPixmap:
        return self.frames[view_id]


@pytest.mark.parametrize("blend,view", [(0.0, CURRENT_VIEW), (1.0, NEXT_VIEW)])
def test_blend_endpoint_is_exact_next_or_current_frame(blend: float, view: str) -> None:
    frames = _frames()
    renderer = FixedFramesRenderer(frames)
    assert renderer.render_blended(CURRENT_VIEW, None, blend=blend).toImage() == frames[view].toImage()


def test_midpoint_fades_disjoint_silhouettes_without_fading_overlap() -> None:
    frames = _frames()
    snapshots = {view: frame.toImage().copy() for view, frame in frames.items()}
    result = FixedFramesRenderer(frames).render_blended(CURRENT_VIEW, None, blend=0.5).toImage()
    assert result.pixelColor(0, 0).alpha() == pytest.approx(HALF_OPACITY, abs=CHANNEL_TOLERANCE)
    assert result.pixelColor(2, 0).alpha() == pytest.approx(HALF_OPACITY, abs=CHANNEL_TOLERANCE)
    overlap = result.pixelColor(1, 0)
    assert overlap.alpha() == pytest.approx(OPAQUE, abs=CHANNEL_TOLERANCE)
    assert overlap.red() == pytest.approx(HALF_OPACITY, abs=CHANNEL_TOLERANCE)
    assert overlap.blue() == pytest.approx(HALF_OPACITY, abs=CHANNEL_TOLERANCE)
    expected_edge_alpha = (snapshots[CURRENT_VIEW].pixelColor(3, 0).alpha()
                           + snapshots[NEXT_VIEW].pixelColor(3, 0).alpha()) / 2
    assert result.pixelColor(3, 0).alpha() == pytest.approx(expected_edge_alpha, abs=CHANNEL_TOLERANCE)
    assert all(frame.toImage() == snapshots[view] for view, frame in frames.items())
