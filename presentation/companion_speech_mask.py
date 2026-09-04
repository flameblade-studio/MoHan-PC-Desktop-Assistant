from __future__ import annotations

lazy from collections.abc import Mapping

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QColor, QImage, QPixmap

FULL_ALPHA = 255
OPAQUE_ALPHA_THRESHOLD = 250
DARK_EDGE_MAX_RGB = 185
MIN_SKIN_RED = 150
MIN_SKIN_GREEN = 85
MIN_SKIN_BLUE = 65
MIN_RED_GREEN_DELTA = 20
MIN_GREEN_BLUE_DELTA = 5
MIN_SOURCE_LIFT = 16
MOUTH_CORNER_EDGE_WIDTH = 14
SOURCE_ROOTS = (
    "viseme_mid",
    "speaking",
    "viseme_i",
    "viseme_round",
    "viseme_o",
)


def _max_rgb(color: QColor) -> int:
    return max(color.red(), color.green(), color.blue())


def _is_recovery_source(closed_max: int, source: QColor) -> bool:
    source_max = _max_rgb(source)
    return (
        source.alpha() >= OPAQUE_ALPHA_THRESHOLD
        and source_max >= closed_max + MIN_SOURCE_LIFT
        and source.red() >= MIN_SKIN_RED
        and source.green() >= MIN_SKIN_GREEN
        and source.blue() >= MIN_SKIN_BLUE
        and source.red() - source.green() >= MIN_RED_GREEN_DELTA
        and source.green() - source.blue() >= MIN_GREEN_BLUE_DELTA
    )


def recover_speech_mask_edges(
    expression_pixmaps: Mapping[str, QPixmap],
    mask: QPixmap,
    suffix: str,
    mouth_clip: QRect,
) -> QPixmap:
    """Close source-backed dark gaps at the two existing mouth edges."""

    closed_name = f"idle{suffix}" if suffix else "idle"
    closed = expression_pixmaps.get(closed_name)
    if closed is None or closed.isNull():
        return mask
    sources = tuple(
        pixmap
        for root in SOURCE_ROOTS
        if (pixmap := expression_pixmaps.get(f"{root}{suffix}"))
        is not None
        and not pixmap.isNull()
    )
    if not sources:
        return mask
    mask_image = mask.toImage().convertToFormat(QImage.Format_ARGB32)
    closed_image = closed.toImage().convertToFormat(QImage.Format_ARGB32)
    source_images = tuple(
        pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        for pixmap in sources
    )
    for y in range(mouth_clip.top(), mouth_clip.bottom() + 1):
        for x in range(mouth_clip.left(), mouth_clip.right() + 1):
            if (
                mouth_clip.left() + MOUTH_CORNER_EDGE_WIDTH <= x
                <= mouth_clip.right() - MOUTH_CORNER_EDGE_WIDTH
            ):
                continue
            mask_color = mask_image.pixelColor(x, y)
            if not 0 < mask_color.alpha() < FULL_ALPHA:
                continue
            closed_color = closed_image.pixelColor(x, y)
            if closed_color.alpha() < OPAQUE_ALPHA_THRESHOLD:
                continue
            closed_max = _max_rgb(closed_color)
            if closed_max > DARK_EDGE_MAX_RGB:
                continue
            if any(
                _is_recovery_source(closed_max, source_image.pixelColor(x, y))
                for source_image in source_images
            ):
                mask_image.setPixelColor(x, y, QColor(255, 255, 255, 255))
    return QPixmap.fromImage(mask_image)
