"""Resizable celestial scenery and decorative frames, independent of controls.

The approved artwork keeps character and text outside the artwork. Fixed-size corners and the
central jade clasp retain their proportions while plain rails stretch. Theme
colorization belongs only to the decorative child, with the live character kept separate.
"""
from __future__ import annotations

lazy from functools import lru_cache
lazy from pathlib import Path
lazy from typing import Literal

lazy from PySide6.QtCore import QEvent, QObject, QRectF, Qt
lazy from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPixmap
lazy from PySide6.QtWidgets import QFrame, QGraphicsColorizeEffect, QWidget

lazy from domain.theme_pack import ThemePack
lazy from presentation.dashboard_theme_materials import MaterialPalette, resolve_material_palette
lazy from presentation.lingxiao_tokens import PALETTE, LingxiaoPalette
lazy from presentation.presentation_resources import resource_path

__all__ = ("CelestialFrame", "SCENE_GROUND_RATIO", "apply_dashboard_artwork")
SCENE_GROUND_RATIO = 0.835

ArtworkKind = Literal["panel", "ribbon", "navigation", "scene"]
ARTWORK_PATH = "assets/ui/mohan-celestial-palace-v1.png"
_REGIONS = {
    "panel": (0.533, 0.128, 0.452, 0.720),
    "ribbon": (0.014, 0.019, 0.971, 0.077),
    "navigation": (0.014, 0.127, 0.095, 0.721),
    "scene": (0.110, 0.098, 0.422, 0.795),
}


@lru_cache(maxsize=1)
def _artwork() -> QPixmap:
    image = QPixmap(str(resource_path(ARTWORK_PATH)))
    if image.isNull():
        raise FileNotFoundError(ARTWORK_PATH)
    return image


def _source_rect(image: QPixmap, kind: ArtworkKind) -> QRectF:
    x, y, width, height = _REGIONS[kind]
    return QRectF(x * image.width(), y * image.height(), width * image.width(), height * image.height())


def _rail_positions(length: float, corner: float, center: float) -> tuple[float, ...]:
    corner = min(corner, length / 5)
    center = min(center, length / 5)
    return (0, corner, (length - center) / 2, (length + center) / 2, length - corner, length)


def _cover_rect(source: QRectF, target: QRectF) -> QRectF:
    """Preserve scene proportions and keep the altar at the same height."""
    if target.width() <= 0 or target.height() <= 0:
        return source
    ratio = target.width() / target.height()
    width = min(source.width(), source.height() * ratio)
    height = min(source.height(), source.width() / ratio)
    return QRectF(
        source.x() + (source.width() - width) / 2,
        source.y() + (source.height() - height) * SCENE_GROUND_RATIO,
        width, height,
    )


class _ArtworkCanvas(QWidget):
    def __init__(self, parent: QWidget, kind: ArtworkKind) -> None:
        super().__init__(parent)
        self.kind = kind
        self.scale = 1.0
        self.background: QPixmap | None = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName("")
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.lower()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Resize, QEvent.Show):
            parent = self.parentWidget()
            if parent is not None:
                self.setGeometry(parent.rect())
                self.lower()
        return False

    def set_tint(self, color: str | None) -> None:
        if color is None:
            self.setGraphicsEffect(None)
            return
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsColorizeEffect):
            effect = QGraphicsColorizeEffect(self)
            self.setGraphicsEffect(effect)
        effect.setColor(QColor(color))
        effect.setStrength(0.68)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        image = _artwork()
        source = _source_rect(image, self.kind)
        if self.kind == "scene":
            if self.background is not None:
                image = self.background
                source = QRectF(image.rect())
            target = QRectF(self.rect())
            painter.drawPixmap(target, image, _cover_rect(source, target))
            return
        self._paint_frame(painter, image, source)

    def _paint_frame(self, painter: QPainter, image: QPixmap, source: QRectF) -> None:
        corner = 42.0 if self.kind != "ribbon" else 48.0
        top = min(60.0, source.height() / 2)
        bottom = min(42.0, source.height() / 2)
        sx = _rail_positions(source.width(), corner, 88.0)
        dx = _rail_positions(self.width(), corner * self.scale, 88.0 * self.scale)
        sy = (0, top, source.height() - bottom, source.height())
        dy = (0, min(top*self.scale, self.height()/2), max(self.height()/2, self.height()-bottom*self.scale), self.height())
        for row in range(3):
            for column in range(5):
                if row == 1 and column in (1, 2, 3):
                    continue
                target = QRectF(dx[column], dy[row], dx[column+1]-dx[column], dy[row+1]-dy[row])
                sample = QRectF(source.x()+sx[column], source.y()+sy[row], sx[column+1]-sx[column], sy[row+1]-sy[row])
                if target.width() > 0 and target.height() > 0:
                    painter.drawPixmap(target, image, sample)


class CelestialFrame(QFrame):
    """A semantic frame whose ornament keeps focus and pointer events with the parent."""

    def __init__(self, parent: QWidget | None = None, *, kind: ArtworkKind = "panel") -> None:
        super().__init__(parent)
        self.setProperty("celestialArtwork", True)
        self._materials = resolve_material_palette(PALETTE)
        self._art = _ArtworkCanvas(self, kind)

    def set_materials(
        self, materials: MaterialPalette, *, tint: str | None, scale: float,
        background: QPixmap | None = None,
        high_contrast: bool = False,
    ) -> None:
        self._materials = materials
        self._art.scale = scale
        self._art.background = background
        self._art.set_tint(tint)
        self._art.setVisible(not high_contrast)
        self._art.update()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self._materials.panel))


def apply_dashboard_artwork(
    root: QWidget,
    palette: LingxiaoPalette,
    theme: ThemePack | None = None,
    background: Path | None = None,
    *,
    high_contrast: bool = False,
) -> None:
    """Refresh decoration while preserving theme archives or control state."""
    materials = resolve_material_palette(palette, theme)
    tint = theme.tokens["primary"] if theme is not None else (
        palette.gold if palette.ink != PALETTE.ink else None
    )
    image = QPixmap(str(background)) if background is not None else None
    if image is not None and image.isNull():
        raise ValueError(f"Theme background cannot be decoded: {background}")
    scale = float(root.property("celestialScale") or 1.0)
    for frame in root.findChildren(CelestialFrame):
        frame.set_materials(
            materials, tint=tint, scale=scale, background=image,
            high_contrast=high_contrast,
        )
