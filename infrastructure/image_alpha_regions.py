"""Native image ownership for every visible alpha value."""
from __future__ import annotations

lazy from PySide6.QtGui import QBitmap, QImage, QRegion

_VISIBLE_ALPHA_TABLE = bytes([0] + [255] * 255)


def visible_alpha_region(image: QImage) -> QRegion:
    """Return nonzero-alpha ownership while preserving validated source RGBA."""
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    binary = bytes(alpha.constBits()).translate(_VISIBLE_ALPHA_TABLE)
    ownership = QImage(
        binary, alpha.width(), alpha.height(), alpha.bytesPerLine(),
        QImage.Format_Alpha8,
    ).convertToFormat(QImage.Format_ARGB32)
    # Qt's direct alpha-mask conversion drops faint pixels. Binarize ownership
    # only; callers continue drawing the untouched source colors and alpha.
    return QRegion(QBitmap.fromImage(ownership.createAlphaMask()))
