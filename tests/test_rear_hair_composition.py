"""Rear hair stays behind opaque and translucent native head pixels."""
from __future__ import annotations
lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID
lazy from types import SimpleNamespace


@pytest.mark.parametrize("method", ["apply", "apply_appearance"])
def test_rear_hair_underpaints_native_head_and_preserves_front_hair(tmp_path, monkeypatch, method):
    app = QApplication.instance() or QApplication([])
    image = QImage(3, 2, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    image.setPixelColor(0, 0, QColor(0, 255, 0, 255))
    image.setPixelColor(1, 0, QColor(0, 255, 0, 128))
    frame = QPixmap.fromImage(image)
    rear = QPixmap(3, 2); rear.fill(QColor("red"))
    front = QPixmap(3, 2); front.fill(QColor("blue"))
    layers = AppearanceLayerStack(
        ((rear, 0, 0, QRegion(0, 0, 3, 2), 1.0),),
        ((front, 0, 0, QRegion(0, 1, 3, 1), 1.0),),
    )
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    monkeypatch.setattr(overlay, "_active_layers", lambda *args, **kwargs: layers)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    result = getattr(overlay, method)(frame, "yaw+000-pitch+00").toImage()
    assert result.pixelColor(0, 0) == QColor(0, 255, 0, 255)
    edge = result.pixelColor(1, 0)
    assert edge.alpha() == QColor("red").alpha() and abs(edge.red() - 127) <= 1 and abs(edge.green() - 128) <= 1
    assert result.pixelColor(2, 0) == QColor("red")
    assert all(result.pixelColor(x, 1) == QColor("blue") for x in range(3))
    assert frame.toImage() == QPixmap.fromImage(image).toImage()
    assert overlay.layer_count("yaw+000-pitch+00") == len(layers)
    assert app is not None


@pytest.mark.parametrize("method", ["apply", "apply_appearance"])
def test_removing_headwear_keeps_shoe_occlusion_and_native_head(tmp_path, monkeypatch, method):
    app = QApplication.instance() or QApplication([])
    frame = QPixmap(3, 4)
    frame.fill(QColor("green"))
    clothing = QPixmap(1, 2)
    clothing.fill(QColor("blue"))
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    layers = ((clothing, 1, 2, QRegion(1, 2, 1, 2), 1.0),)
    monkeypatch.setattr(overlay, "_active_layers", lambda *args, **kwargs: layers)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_official_silhouette_region", lambda *args: QRegion(1, 0, 1, 4))
    monkeypatch.setattr(overlay, "_protected_face_region", lambda *args: QRegion(1, 0, 1, 2))
    monkeypatch.setattr("infrastructure.active_outfit_overlay.resolve_active_selection",
                        lambda *args: SimpleNamespace(effective_pack_id=OFFICIAL_OUTFIT_PACK_ID))
    result = getattr(overlay, method)(frame, "yaw+000-pitch+00").toImage()
    assert result.pixelColor(0, 0) == QColor("green")
    assert result.pixelColor(2, 1) == QColor("green")
    assert result.pixelColor(0, 3).alpha() == 0
    assert result.pixelColor(2, 3).alpha() == 0
    assert result.pixelColor(1, 3) == QColor("blue")
    assert frame.toImage().pixelColor(0, 3) == QColor("green")
    assert app is not None
