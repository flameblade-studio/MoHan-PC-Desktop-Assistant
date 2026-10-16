"""Half-body staging authority stays pinned when the process changes cwd."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer


def test_relative_authority_does_not_switch_to_another_portrait(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root, color in ((first, Qt.red), (second, Qt.blue)):
        (root / "authority").mkdir(parents=True)
        portrait = QPixmap(8, 8)
        portrait.fill(color)
        assert portrait.save(str(root / "authority" / "eureka_front.png"), "PNG")
    monkeypatch.chdir(first)
    renderer = LayeredParametricFaceRenderer(authority_dir=Path("authority"))
    # This first decode exposes the current path directly before cache population.
    monkeypatch.chdir(second)
    actual = renderer._gesture_portrait("eureka_front").toImage()
    assert actual.pixelColor(4, 4) == QColor(Qt.red)
    assert app is not None
