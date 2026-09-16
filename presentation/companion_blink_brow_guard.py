"""Protect authored gesture brows when a neutral closed-eye source is reused."""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

NATIVE_SIZE = 1254
BROW_REGIONS = ((490, 370, 605, 434), (605, 370, 725, 434))
DARK_LIMIT = 130
EUREKA_DARK_LIMIT = 155
EUREKA_GUARD_WIDTH = 9
GUARD_CACHE_SIZE = 8
NATIVE_GUARD_WIDTH = 7
GUARD_SIGMA = 1.1
GUARDED_EXPRESSIONS = frozenset({"eureka_front", "mock_hit_front", "mock_scold"})


def _rgba(pixmap: QPixmap) -> np.ndarray:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    rows = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(
        image.height(), image.bytesPerLine(),
    )
    return rows[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()


@lru_cache(maxsize=GUARD_CACHE_SIZE)
def _cached_guard(
    base_brows: bytes, donor_brows: bytes, width: int, height: int, expression: str | None,
) -> QPixmap:
    crop_left, crop_top = round(490 * width / NATIVE_SIZE), round(370 * height / NATIVE_SIZE)
    crop_width = round(725 * width / NATIVE_SIZE) - crop_left
    crop_height = round(434 * height / NATIVE_SIZE) - crop_top
    guard = np.zeros((height, width), dtype=np.uint8)
    for raw in (base_brows, donor_brows):
        pixels = np.frombuffer(raw, dtype=np.uint8).reshape(crop_height, crop_width, 4)
        dark = (pixels[:, :, :3].mean(axis=2) < (EUREKA_DARK_LIMIT if expression == "eureka_front" else DARK_LIMIT)) & (pixels[:, :, 3] > 0)
        for left, top, right, bottom in BROW_REGIONS:
            x0, x1 = round(left * width / NATIVE_SIZE), round(right * width / NATIVE_SIZE)
            y0, y1 = round(top * height / NATIVE_SIZE), round(bottom * height / NATIVE_SIZE)
            sample = dark[y0-crop_top:y1-crop_top, x0-crop_left:x1-crop_left].astype(np.uint8)
            count, labels, stats, _ = cv2.connectedComponentsWithStats(sample, 8)
            if count > 1:
                largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                guard[y0:y1, x0:x1][labels == largest] = 255
    kernel_size = max(1, round((EUREKA_GUARD_WIDTH if expression == "eureka_front" else NATIVE_GUARD_WIDTH) * width / NATIVE_SIZE)) | 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    guard = cv2.dilate(guard, kernel)
    guard = cv2.GaussianBlur(guard, (kernel_size, kernel_size), GUARD_SIGMA)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 3] = guard
    return QPixmap.fromImage(
        QImage(rgba.data, width, height, width * 4, QImage.Format_RGBA8888).copy()
    )


def preserve_gesture_brows(
    base: QPixmap, donor: QPixmap, mask: QPixmap, *, expression: str | None = None,
) -> QPixmap:
    """Remove source-shaped brow pigment from an otherwise unchanged eye mask."""
    if base.size() != donor.size() or base.size() != mask.size():
        raise ValueError("Gesture brow protection requires matching native frame sizes.")
    width, height = base.width(), base.height()
    left, top = round(490 * width / NATIVE_SIZE), round(370 * height / NATIVE_SIZE)
    right, bottom = round(725 * width / NATIVE_SIZE), round(434 * height / NATIVE_SIZE)
    source = _rgba(base.copy(left, top, right - left, bottom - top))
    replacement = _rgba(donor.copy(left, top, right - left, bottom - top))
    guard = _cached_guard(source.tobytes(), replacement.tobytes(), width, height, expression)
    result = QPixmap(mask.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    try:
        painter.drawPixmap(0, 0, mask)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        painter.drawPixmap(0, 0, guard)
    finally:
        painter.end()
    return result
