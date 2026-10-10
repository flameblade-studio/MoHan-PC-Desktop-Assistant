"""Character-neutral Qt render values shared by presentation adapters."""

from __future__ import annotations

lazy from dataclasses import dataclass

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QPixmap


@dataclass(frozen=True, slots=True)
class FaceRenderLayers:
    """Qt image layers passed through the injected face-renderer port."""

    mouth_source: QPixmap
    mouth_mask: QPixmap
    mouth_rect: QRect
    mouth_expression: str | None = None
    blink_source: QPixmap | None = None
    blink_mask: QPixmap | None = None
    blush_source: QPixmap | None = None
    blush_mask: QPixmap | None = None


__all__ = ("FaceRenderLayers",)
