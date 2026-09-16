"""Reviewed defaults preserve native animation and independent outfit choices."""
from __future__ import annotations

import os
from dataclasses import replace
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication

from domain.outfit_pack import OutfitPackError
from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
from infrastructure.appearance_layer_stack import AppearanceLayerStack
from infrastructure import reviewed_garment_overlay as module
from infrastructure.reviewed_garment_assets import (
    DIMENSION, ReviewedGarmentAssets, ReviewedGarmentPose, ReviewedPng, ReviewedSelection,
)

VIEW = "cheek-rest"
LAYER_COUNT = 3


def _record(name, rect, color):
    image = QImage(DIMENSION, DIMENSION, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.fillRect(*rect, QColor(color))
    painter.end()
    return ReviewedPng(name, "0" * 64, b"", image)


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    selection = ReviewedSelection("official", "robe", "blue")
    visibility = _record("visibility", (0, 0, DIMENSION, 500), "white")
    visibility = ReviewedPng(
        visibility.path, visibility.sha256, visibility.payload,
        visibility.image.convertToFormat(QImage.Format_Grayscale8),
    )
    pose = ReviewedGarmentPose(
        VIEW, "0" * 64, visibility,
        (_record("cloth", (0, 600, 800, 300), "blue"),
         _record("hand", (300, 680, 80, 50), "red"),
         _record("cuff", (340, 680, 80, 50), "green")),
        selection, {"hairstyle": ReviewedSelection("official", "hair", "black")},
    )
    state = {"garment": ("official", "robe", "blue"), "hairstyle": ("official", "hair", "black")}

    def resolve(_store, category):
        pack, item, variant = state.get(category, ("builtin", "none", "none"))
        return SimpleNamespace(
            effective_pack_id=pack, effective_item_id=item, effective_variant_id=variant,
            status="builtin" if pack == "builtin" else "installed",
        )

    monkeypatch.setattr(module, "resolve_active_selection", resolve)
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    overlay._reviewed_assets_loaded = True
    overlay._reviewed_assets = ReviewedGarmentAssets(tmp_path, {VIEW: pose})
    validated = []
    monkeypatch.setattr(overlay, "_selected_variant", lambda category, _: validated.append(category))
    monkeypatch.setattr(overlay, "_active_layers", lambda *args, **kwargs: AppearanceLayerStack((), ()))
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    frame = QPixmap(DIMENSION, DIMENSION)
    frame.fill(QColor("tan"))
    return app, overlay, frame, state, validated


def test_approved_default_preserves_face_and_native_hand_cuff_depth(reviewed):
    _, overlay, frame, _, validated = reviewed
    before = frame.toImage().copy()
    result = overlay.apply(frame, VIEW).toImage()
    assert result.pixelColor(100, 100) == before.pixelColor(100, 100)
    assert result.pixelColor(100, 700) == QColor("blue")
    assert result.pixelColor(310, 700) == QColor("red")
    assert result.pixelColor(350, 700) == QColor("green")
    assert result.pixelColor(1000, 1000).alpha() == 0
    assert frame.toImage() == before
    assert validated == ["garment", "hairstyle"]
    assert overlay.layer_count(VIEW) == LAYER_COUNT


def test_removal_restores_original_body_and_clears_reviewed_count(reviewed):
    _, overlay, frame, state, _ = reviewed
    overlay.apply(frame, VIEW)
    state["garment"] = ("builtin", "none", "none")
    result = overlay.apply(frame, VIEW)
    assert result.toImage() == frame.toImage()
    assert overlay.layer_count(VIEW) == 0


def test_native_identity_survives_garment_removal_or_replacement(reviewed):
    _, overlay, _, state, _ = reviewed
    assets = overlay._reviewed_assets
    native = _record("native", (0, 0, DIMENSION, DIMENSION), "tan")
    pose = replace(assets.poses[VIEW], native_source=native)
    overlay._reviewed_assets = ReviewedGarmentAssets(assets.root, {VIEW: pose})
    expected = native.image
    for garment in (("official", "robe", "blue"), ("builtin", "none", "none"), ("custom", "robe", "red")):
        state["garment"] = garment
        assert overlay.native_neutral(VIEW).toImage().convertToFormat(expected.format()) == expected
    assert overlay.native_neutral("front-crossed") is None


def test_independent_custom_hair_still_covers_animated_skin(reviewed, monkeypatch):
    _, overlay, frame, state, _ = reviewed
    state["hairstyle"] = ("custom", "hair", "red")
    categories_seen = []
    patch = QPixmap(1, 1)
    patch.fill(QColor("orange"))

    def layers(*args, categories, **kwargs):
        categories_seen.append(categories)
        if "hairstyle" in categories:
            return AppearanceLayerStack(
                (), ((patch, 100, 100, QRegion(frame.rect()), 1.0),),
                front_hair_indices=frozenset({0}),
            )
        return AppearanceLayerStack((), ())

    def motion(target):
        painter = QPainter(target)
        painter.fillRect(100, 100, 2, 1, QColor("yellow"))
        painter.end()

    monkeypatch.setattr(overlay, "_active_layers", layers)
    result = overlay.apply_animated(frame, VIEW, motion).toImage()
    assert "hairstyle" in categories_seen[0]
    assert "garment" not in categories_seen[0]
    assert result.pixelColor(100, 100) == QColor("orange")
    assert result.pixelColor(101, 100) == QColor("yellow")
    assert frame.toImage().pixelColor(100, 100) == QColor("tan")


def test_reviewed_motion_errors_propagate_without_becoming_asset_fallback(reviewed):
    _, overlay, frame, _, _ = reviewed

    def broken_motion(_target):
        raise ValueError("native motion failed")

    with pytest.raises(ValueError, match="native motion failed"):
        overlay.apply_animated(frame, VIEW, broken_motion)


def test_failed_makeup_rolls_back_reviewed_garment_but_keeps_motion(reviewed, monkeypatch):
    _, overlay, frame, _, _ = reviewed
    overlay.apply(frame, VIEW)

    def layers(*args, categories, **kwargs):
        if categories == {"makeup"}:
            raise OutfitPackError("corrupt makeup")
        return AppearanceLayerStack((), ())

    def motion(target):
        painter = QPainter(target)
        painter.fillRect(100, 100, 1, 1, QColor("yellow"))
        painter.end()

    monkeypatch.setattr(overlay, "_active_layers", layers)
    expected = QPixmap(frame)
    motion(expected)
    assert overlay.apply_animated(frame, VIEW, motion).toImage() == expected.toImage()
    assert overlay.layer_count(VIEW) == 0
