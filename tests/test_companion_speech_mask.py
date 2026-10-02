from __future__ import annotations

"""Mouth-only conversion preserves the full-canvas recovery result."""

lazy import os
lazy import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.qt_image_pixels import rgba8888_image
lazy from presentation import companion_speech_mask as recovery

OPAQUE_ALPHA = 250
SKIN_RED = 150
SKIN_GREEN = 85
SKIN_BLUE = 65
RED_GREEN_DELTA = 20
GREEN_BLUE_DELTA = 5
CORNER_WIDTH = 14
FULL_ALPHA = 255
CANVAS_SIZE = 465


@pytest.mark.parametrize("suffix", ("", "_lean", "_front"))
@pytest.mark.parametrize("premultiplied", (False, True))
def test_recovery_matches_full_canvas_pixels(
    monkeypatch: pytest.MonkeyPatch, suffix: str, premultiplied: bool,
) -> None:
    app = QApplication.instance() or QApplication([])
    image_format = (
        QImage.Format_ARGB32_Premultiplied if premultiplied else QImage.Format_RGBA8888
    )
    generator = random.Random(207)
    clip = QRect(21, 17, 54, 35)
    images = []
    for _ in range(6):
        image = QImage(CANVAS_SIZE, CANVAS_SIZE, image_format)
        image.fill(QColor(12, 34, 56, 0))
        for y in range(clip.top(), clip.bottom() + 1):
            for x in range(clip.left(), clip.right() + 1):
                image.setPixelColor(x, y, QColor(
                    generator.randrange(140, 256), generator.randrange(70, 220),
                    generator.randrange(50, 200), generator.choice((128, 249, 250, 254, 255)),
                ))
        images.append(image)
    pixmaps = {
        f"{name}{suffix}": QPixmap.fromImage(image)
        for name, image in zip(("idle", *recovery.SOURCE_ROOTS), images, strict=True)
    }
    mask = QImage(CANVAS_SIZE, CANVAS_SIZE, QImage.Format_ARGB32_Premultiplied)
    mask.fill(QColor(255, 255, 255, 82))
    for y in range(clip.top(), clip.bottom() + 1):
        for x in range(clip.left(), clip.right() + 1):
            mask.setPixelColor(x, y, QColor(255, 255, 255, generator.choice((0, 82, 255))))
    expected = mask.copy()
    full_images = [rgba8888_image(pixmap.toImage()) for pixmap in pixmaps.values()]
    for y in range(clip.top(), clip.bottom() + 1):
        for x in range(clip.left(), clip.right() + 1):
            if clip.left() + CORNER_WIDTH <= x <= clip.right() - CORNER_WIDTH:
                continue
            if not 0 < mask.pixelColor(x, y).alpha() < FULL_ALPHA:
                continue
            closed = full_images[0].pixelColor(x, y)
            if closed.alpha() < OPAQUE_ALPHA:
                continue
            for source in full_images[1:]:
                color = source.pixelColor(x, y)
                skin = (
                    color.alpha() >= OPAQUE_ALPHA and color.red() >= SKIN_RED
                    and color.green() >= SKIN_GREEN and color.blue() >= SKIN_BLUE
                    and color.red() - color.green() >= RED_GREEN_DELTA
                    and color.green() - color.blue() >= GREEN_BLUE_DELTA
                )
                if skin:
                    expected.setPixelColor(x, y, QColor(255, 255, 255, 255))
                    break
    converted_sizes = []

    def record_conversion(image: QImage) -> QImage:
        converted_sizes.append(image.size().toTuple())
        return rgba8888_image(image)

    monkeypatch.setattr(recovery, "rgba8888_image", record_conversion)
    actual = recovery.recover_speech_mask_edges(pixmaps, QPixmap.fromImage(mask), suffix, clip)
    assert expected != mask
    assert actual.toImage().convertToFormat(mask.format()) == expected
    assert converted_sizes == [clip.size().toTuple()] * 6
    assert app is not None
