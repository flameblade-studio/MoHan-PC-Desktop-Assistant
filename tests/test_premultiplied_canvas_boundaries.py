"""Exact public pixels and premultiplied painting across CPU boundaries."""

from __future__ import annotations

lazy import os
lazy from types import SimpleNamespace

lazy import numpy as np
lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import QPoint, QRect
lazy from PySide6.QtGui import QColor, QColorSpace, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.qt_image_pixels import rgba8888_image
lazy from infrastructure.active_outfit_overlay_layers import ActiveOutfitLayerMixin
lazy from infrastructure.image_alpha_regions import visible_alpha_region
lazy from infrastructure.reviewed_garment_assets import (
    DIMENSION, ReviewedGarmentPose, ReviewedPng, ReviewedSelection,
)
lazy from presentation.companion_blink_brow_guard import _rgba
lazy from presentation.companion_legacy_frame import current_legacy_character_frame
lazy from presentation.companion_speech_mask import recover_speech_mask_edges
lazy from presentation.pose_atlas_assets import PoseAtlasAssets

BYTE_VALUES = 256
FRAME_GENERATION = 17
BOUNDARY_CANVAS_COUNT = 2


def _image_bytes(image: QImage) -> bytes:
    """Keep the Qt storage owner alive until the byte copy completes."""
    return bytes(image.constBits())


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def paint_contract(monkeypatch):
    """Fail if a caller asks Qt to unpremultiply or paints a straight image."""
    original_convert = QImage.convertToFormat
    original_init = QPainter.__init__
    painted = []

    def convert(image, target, *args, **kwargs):
        assert not (
            image.format() in {QImage.Format_ARGB32_Premultiplied, QImage.Format_RGBA8888_Premultiplied}
            and target in {QImage.Format_ARGB32, QImage.Format_RGBA8888}
        )
        return original_convert(image, target, *args, **kwargs)

    def begin(painter, *args, **kwargs):
        if args and isinstance(args[0], QImage):
            painted.append(args[0].format())
            assert args[0].format() in {
                QImage.Format_ARGB32_Premultiplied, QImage.Format_RGBA8888_Premultiplied,
            }
        original_init(painter, *args, **kwargs)

    monkeypatch.setattr(QImage, "convertToFormat", convert)
    monkeypatch.setattr(QPainter, "__init__", begin)
    return painted


@pytest.mark.parametrize("format_id", [QImage.Format_ARGB32_Premultiplied, QImage.Format_RGBA8888_Premultiplied])
def test_exact_rounding_for_every_valid_channel_and_alpha(format_id, paint_contract):
    # Each row supplies an alpha; every valid premultiplied channel <= alpha
    # occurs once. Equal RGB also makes the raw buffer endian independent.
    pixels = bytearray()
    expected = bytearray()
    for alpha in range(BYTE_VALUES):
        for channel in range(BYTE_VALUES):
            value = min(channel, alpha)
            pixels.extend((value, value, value, alpha))
            straight = (value * 255 + alpha // 2) // alpha if alpha else 0
            expected.extend((straight, straight, straight, alpha))
    source = QImage(bytes(pixels), BYTE_VALUES, BYTE_VALUES, BYTE_VALUES * 4, format_id)
    result = rgba8888_image(source)
    assert result.format() == QImage.Format_RGBA8888
    assert bytes(result.constBits()) == expected
    assert bytes(source.constBits()) == pixels


def test_decoded_straight_pixels_keep_hidden_rgb_and_detach():
    raw = bytes((71, 93, 115, 0, 19, 37, 55, 128))
    source = QImage(raw, 2, 1, 8, QImage.Format_RGBA8888)
    result = rgba8888_image(source)
    assert bytes(result.constBits()) == raw
    result.setPixelColor(0, 0, QColor("red"))
    assert bytes(source.constBits()) == raw
    assert rgba8888_image(QImage()).isNull()


@pytest.mark.parametrize("format_id", [QImage.Format_ARGB32_Premultiplied, QImage.Format_RGBA8888_Premultiplied])
def test_premultiplied_channel_order_and_padded_rows(format_id, paint_contract):
    if format_id == QImage.Format_ARGB32_Premultiplied:
        source = QImage(1, 1, format_id)
        source.setPixel(0, 0, 0x61112943)  # Raw ARGB: alpha=97, R=17, G=41, B=67.
    else:
        source = QImage(
            bytes((17, 41, 67, 97, 255, 255, 255, 255)), 1, 1, 8, format_id,
        )
    expected = bytes((*((channel * 255 + 97 // 2) // 97 for channel in (17, 41, 67)), 97))
    assert _image_bytes(rgba8888_image(source)) == expected


def _metadata(image: QImage) -> tuple:
    return (
        image.devicePixelRatio(), image.dotsPerMeterX(), image.dotsPerMeterY(),
        image.offset(), image.colorSpace(),
        tuple((key, image.text(key)) for key in image.textKeys()),
    )


def _set_metadata(image: QImage) -> None:
    image.setDevicePixelRatio(1.5)
    image.setDotsPerMeterX(1000)
    image.setDotsPerMeterY(2000)
    image.setOffset(QPoint(3, -4))
    image.setColorSpace(QColorSpace(QColorSpace.NamedColorSpace.SRgb))
    image.setText("sample", "metadata")


def test_exact_boundary_preserves_public_image_metadata(paint_contract):
    image = QImage(2, 1, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor(50, 60, 70, 100))
    _set_metadata(image)
    assert _metadata(rgba8888_image(image)) == _metadata(image)


def _sample_pixmap() -> QPixmap:
    image = QImage(7, 5, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor(153, 87, 39, 103))
    image.setPixelColor(3, 2, QColor(91, 181, 73, 201))
    return QPixmap.fromImage(image)


def test_legacy_and_pose_atlas_paint_before_exact_rgba_boundary(app, paint_contract):
    assert app is not None
    pixmap = _sample_pixmap()
    window = SimpleNamespace(character=SimpleNamespace(pixmap=lambda: pixmap))
    frame = current_legacy_character_frame(window, FRAME_GENERATION)
    atlas = object.__new__(PoseAtlasAssets)
    atlas._image_size = frame.width
    assert atlas._pixmap_rgba(pixmap) == frame.rgba
    assert len(frame.rgba) == frame.width * frame.height * 4
    assert frame.generation == FRAME_GENERATION
    assert len(paint_contract) == BOUNDARY_CANVAS_COUNT


def test_brow_pixel_samples_use_exact_straight_colors(app, paint_contract):
    assert app is not None
    pixmap = _sample_pixmap()
    assert _rgba(pixmap).tobytes() == _image_bytes(rgba8888_image(pixmap.toImage()))


def test_speech_mask_preserves_alpha_and_recovers_skin_corner(app, paint_contract):
    assert app is not None
    mask_image = QImage(4, 2, QImage.Format_ARGB32_Premultiplied)
    mask_image.fill(QColor(0, 0, 0, 71))
    closed = QPixmap(4, 2)
    closed.fill(QColor(40, 30, 20))
    skin = QPixmap(4, 2)
    skin.fill(QColor(201, 151, 111))
    source = QPixmap.fromImage(mask_image)
    recovered = recover_speech_mask_edges(
        {"idle": closed, "speaking": skin}, source, "", QRect(0, 0, 4, 1),
    )
    alpha = recovered.toImage().convertToFormat(QImage.Format_Alpha8)
    assert bytes(alpha.constBits())[:4] == bytes([255] * 4)
    assert bytes(alpha.constBits())[alpha.bytesPerLine():][:4] == bytes([71] * 4)
    assert _image_bytes(source.toImage().convertToFormat(QImage.Format_Alpha8))[:4] == bytes([71] * 4)


def test_hair_multiplier_uses_only_exact_alpha(app):
    assert app is not None
    alpha_bytes = bytes(range(BYTE_VALUES))
    alpha = QImage(alpha_bytes, BYTE_VALUES, 1, BYTE_VALUES, QImage.Format_Alpha8)
    image = QImage(BYTE_VALUES, 1, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor("white"))
    masked = ActiveOutfitLayerMixin._masked_hair(
        QPixmap.fromImage(image), 0, 0, alpha, QRect(0, 0, BYTE_VALUES, 1),
    ).toImage()
    assert _image_bytes(masked.convertToFormat(QImage.Format_Alpha8)) == alpha_bytes
    assert visible_alpha_region(masked).boundingRect() == QRect(1, 0, BYTE_VALUES - 1, 1)
    # RGB is ignored by DestinationIn; only alpha determines the product.
    raw = np.frombuffer(masked.constBits(), dtype=np.uint8).reshape(1, BYTE_VALUES, 4)
    assert np.array_equal(raw[0, :, :3], np.repeat(np.arange(BYTE_VALUES)[:, None], 3, axis=1))


def test_reviewed_image_and_pixmap_boundaries_share_exact_composition(app, paint_contract):
    assert app is not None
    source = QImage(DIMENSION, DIMENSION, QImage.Format_ARGB32_Premultiplied)
    source.fill(QColor(153, 87, 39, 103))
    _set_metadata(source)
    original = bytes(source.constBits())
    visibility = QImage(DIMENSION, DIMENSION, QImage.Format_Grayscale8)
    visibility.fill(173)
    layer = QImage(DIMENSION, DIMENSION, QImage.Format_RGBA8888)
    layer.fill(QColor(81, 193, 57, 67))
    selection = ReviewedSelection("pack", "item", "variant")
    pose = ReviewedGarmentPose(
        "sample", "sample-digest", ReviewedPng("mask", "mask-digest", b"", visibility),
        (ReviewedPng("layer", "layer-digest", b"", layer),), selection, {},
    )
    image_result = pose.compose(source)
    pixmap_result = pose.compose(QPixmap.fromImage(source))
    assert image_result.format() == QImage.Format_RGBA8888
    assert _metadata(image_result) == _metadata(source)
    assert bytes(image_result.constBits()) == _image_bytes(rgba8888_image(pixmap_result.toImage()))
    assert bytes(source.constBits()) == original
