"""Snapshot the existing half-body surface for adaptive rendering fallback."""

from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QImage, QPainter

lazy from application.adaptive_character_composition import (
    DEFAULT_CHARACTER_IMAGE_SIZE as CHARACTER_IMAGE_SIZE,
)
lazy from application.body_pose_renderer import BodyPoseFrame
lazy from domain.qt_image_pixels import rgba8888_image


def current_legacy_character_frame(window: object, generation: int) -> BodyPoseFrame:
    """Snapshot the proven renderer for the adaptive fallback boundary."""

    size = CHARACTER_IMAGE_SIZE
    canvas = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.transparent)
    pixmap = window.character.pixmap()
    if pixmap is not None and not pixmap.isNull():
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
        image = image.scaled(
            size,
            size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        painter = QPainter(canvas)
        painter.drawImage(
            (size - image.width()) // 2,
            (size - image.height()) // 2,
            image,
        )
        painter.end()
    rgba = rgba8888_image(canvas)
    return BodyPoseFrame(
        size,
        size,
        bytes(rgba.constBits()),
        generation,
        ("legacy-current",),
        ("legacy-current",),
        False,
    )
