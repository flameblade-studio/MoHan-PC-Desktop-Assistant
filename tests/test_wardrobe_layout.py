"""Narrow windows must expose the whole wardrobe through vertical scrolling."""
from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
lazy from presentation.wardrobe_layout import WardrobeScrollArea


def test_narrow_wardrobe_stacks_and_scrolls_to_actions_then_restores_columns() -> None:
    app = QApplication.instance() or QApplication([])
    content = QWidget()
    columns = QHBoxLayout(content)
    stage = QWidget()
    controls = QWidget()
    actions = QVBoxLayout(controls)
    actions.addStretch(1)
    apply_button = QPushButton("Apply appearance")
    actions.addWidget(apply_button)
    columns.addWidget(stage)
    columns.addWidget(controls)
    scroll = WardrobeScrollArea(content, columns, stage, controls)
    try:
        scroll.resize(540, 320)
        scroll.show()
        app.processEvents()
        assert controls.y() >= stage.geometry().bottom()
        assert scroll.verticalScrollBar().maximum() > 0
        scroll.ensureWidgetVisible(apply_button)
        app.processEvents()
        button_position = apply_button.mapTo(scroll.viewport(), apply_button.rect().center())
        assert scroll.viewport().rect().contains(button_position)
        assert content.width() <= scroll.viewport().width()
        scroll.resize(1200, 760)
        app.processEvents()
        assert controls.x() >= stage.geometry().right()
        assert controls.y() == stage.y()
    finally:
        scroll.close()
        scroll.deleteLater()
        app.processEvents()
