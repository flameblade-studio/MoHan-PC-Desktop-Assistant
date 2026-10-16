"""Exact straight-alpha pixels at public Qt image boundaries."""

lazy import numpy as np
lazy from PySide6.QtGui import QImage


def rgba8888_image(image: QImage) -> QImage:
    """Detach RGBA8888 pixels without Qt's approximate SIMD unpremultiply.

    Decoded straight-alpha images retain their authored bytes, including RGB
    under zero alpha. Painted premultiplied images use exact integer rounding
    (channel * 255 + alpha // 2) // alpha, with transparent RGB set to zero.
    """
    if image.isNull() or image.format() in {
        QImage.Format_RGBA8888, QImage.Format_ARGB32, QImage.Format_RGB32,
    }:
        return image.convertToFormat(QImage.Format_RGBA8888).copy()
    source = image.convertToFormat(QImage.Format_RGBA8888_Premultiplied)
    rows = np.frombuffer(source.constBits(), dtype=np.uint8).reshape(
        source.height(), source.bytesPerLine(),
    )
    pixels = rows[:, :source.width() * 4].reshape(source.height(), source.width(), 4)
    alpha = pixels[:, :, 3:4].astype(np.uint32)
    divisor = np.maximum(alpha, 1)
    color = np.where(
        alpha > 0,
        (pixels[:, :, :3].astype(np.uint32) * 255 + divisor // 2) // divisor,
        0,
    )
    rgba = np.concatenate((np.minimum(color, 255), alpha), axis=2).astype(np.uint8)
    result = QImage(
        rgba.data, source.width(), source.height(), source.width() * 4,
        QImage.Format_RGBA8888,
    ).copy()
    result.setDevicePixelRatio(image.devicePixelRatio())
    result.setDotsPerMeterX(image.dotsPerMeterX())
    result.setDotsPerMeterY(image.dotsPerMeterY())
    result.setOffset(image.offset())
    result.setColorSpace(image.colorSpace())
    for key in image.textKeys():
        result.setText(key, image.text(key))
    return result
