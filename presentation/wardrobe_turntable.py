"""Mouse and keyboard rotation over the canonical full-circle pose atlas."""
from __future__ import annotations

lazy from PySide6.QtCore import QEvent, Qt, Signal
lazy from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent, QShowEvent
lazy from PySide6.QtWidgets import QLabel

lazy from domain.character_pose import CANONICAL_YAWS

__all__ = ("TURN_TABLE_VIEWS", "WardrobeTurntableLabel")

TURN_TABLE_VIEWS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in CANONICAL_YAWS)
FRONT_INDEX = CANONICAL_YAWS.index(0)


class WardrobeTurntableLabel(QLabel):
    """Drag right to expose MoHan's left side; one surface width is one turn."""

    shown = Signal()
    view_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._view_index = FRONT_INDEX
        self._drag_origin: float | None = None
        self._drag_start_index = FRONT_INDEX
        self._rendered_source = QPixmap()
        self._scene_ground: float | None = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)

    @property
    def view_id(self) -> str:
        return TURN_TABLE_VIEWS[self._view_index]

    def set_view(self, view_id: str) -> None:
        """Select a canonical view while preserving authored frame orientation."""
        self._select_index(TURN_TABLE_VIEWS.index(view_id))

    def set_rendered_pixmap(self, pixmap: QPixmap) -> None:
        """Keep the unscaled frame so resizing uses one resampling step."""
        self._rendered_source = pixmap
        self._fit_rendered_frame()

    def attach_to_scene(self, ground_ratio: float) -> None:
        """Place the visible feet at the scene's ground, independent of text rows."""
        scene = self.parentWidget()
        if scene is None:
            raise ValueError("A scene parent is required for ground alignment.")
        self._scene_ground = ground_ratio
        scene.installEventFilter(self)
        self.setGeometry(scene.rect())

    def eventFilter(self, watched, event: QEvent) -> bool:
        if watched is self.parentWidget() and event.type() in (QEvent.Resize, QEvent.Show):
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def _fit_rendered_frame(self) -> None:
        if not self._rendered_source.isNull():
            if self._scene_ground is not None:
                self._fit_scene_frame()
                return
            self.setPixmap(self._rendered_source.scaled(
                self.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
            ))

    def _fit_scene_frame(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        ground = self.height() * self._scene_ground
        # Keep scale tied to the native canvas so taller hair or headwear stays within
        # shrink the body when appearance layers change.
        scale = min(
            self.width() * 0.90 / self._rendered_source.width(),
            self.height() * 0.82 / self._rendered_source.height(),
        )
        scaled = self._rendered_source.scaled(
            max(1, round(self._rendered_source.width() * scale)),
            max(1, round(self._rendered_source.height() * scale)),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        canvas = QPixmap(self.size())
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(
            (self.width() - scaled.width()) // 2,
            round(ground) - _visible_bottom(scaled),
            scaled,
        )
        painter.end()
        self.setPixmap(canvas)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit_rendered_frame()

    def _select_index(self, index: int) -> None:
        index %= len(TURN_TABLE_VIEWS)
        if index != self._view_index:
            self._view_index = index
            self.view_changed.emit(self.view_id)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.shown.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.position().x()
            self._drag_start_index = self._view_index
            self.setFocus(Qt.MouseFocusReason)
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            pixels_per_view = max(1.0, self.width() / len(TURN_TABLE_VIEWS))
            steps = int((event.position().x() - self._drag_origin) / pixels_per_view)
            self._select_index(self._drag_start_index + steps)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._drag_origin is not None:
            self._drag_origin = None
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Home):
            if event.key() == Qt.Key_Home:
                self._select_index(FRONT_INDEX)
            else:
                self._select_index(self._view_index + (1 if event.key() == Qt.Key_Right else -1))
            event.accept()
            return
        super().keyPressEvent(event)


def _visible_bottom(pixmap: QPixmap) -> int:
    """Return the exclusive alpha bottom after resampling, including soft edges."""
    alpha = pixmap.toImage().convertToFormat(QImage.Format_Alpha8)
    pixels = alpha.constBits()
    stride = alpha.bytesPerLine()
    for row in range(alpha.height() - 1, -1, -1):
        if any(pixels[row * stride:row * stride + alpha.width()]):
            return row + 1
    return 0
