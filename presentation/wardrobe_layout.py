"""Keep wardrobe controls reachable when the dashboard is narrow or short."""
from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QResizeEvent
lazy from PySide6.QtWidgets import QBoxLayout, QFrame, QScrollArea, QWidget

__all__ = ("WardrobeScrollArea",)
STACK_BELOW_WIDTH = 820


class WardrobeScrollArea(QScrollArea):
    """Stack the scene and controls on narrow windows and scroll the full page."""

    def __init__(
        self,
        content: QWidget,
        columns: QBoxLayout,
        stage: QWidget,
        controls: QWidget,
    ) -> None:
        super().__init__()
        self._columns = columns
        self._stage = stage
        self._controls = controls
        self.setObjectName("wardrobePageScroll")
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(content)
        self._update_columns()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_columns()

    def _update_columns(self) -> None:
        stacked = self.viewport().width() < STACK_BELOW_WIDTH
        self._columns.setDirection(
            QBoxLayout.TopToBottom if stacked else QBoxLayout.LeftToRight
        )
        self._stage.setMinimumHeight(620)
        self._controls.setMinimumHeight(560 if stacked else 620)
