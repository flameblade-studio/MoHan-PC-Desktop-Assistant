"""Wardrobe readiness follows successful split-phase runtime composition."""
from __future__ import annotations

lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
lazy import pytest
lazy from PySide6.QtGui import QColor, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import OutfitPackError
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack

VIEW = "yaw+000-pitch+00"
COMBINED_PHASE_LAYER_COUNT = 2


@pytest.fixture
def phases(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    frame = QPixmap(2, 2)
    frame.fill(QColor("blue"))
    layer = (frame, 0, 0, QRegion(0, 0, 2, 2), 1.0)
    monkeypatch.setattr(overlay, "_active_layers", lambda *args, **kwargs: AppearanceLayerStack((), (layer,)))
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    return overlay, frame


def test_split_phases_report_their_composited_layers(phases):
    overlay, frame = phases
    assert overlay.layer_count(VIEW) == 0
    overlay.apply_appearance(frame, VIEW)
    assert overlay.layer_count(VIEW) == 1
    overlay.apply_makeup(frame, VIEW)
    assert overlay.layer_count(VIEW) == COMBINED_PHASE_LAYER_COUNT
    overlay.apply_makeup(frame, VIEW, eye_state="closed", suppress_makeup_slots={"eyes"})
    assert overlay.layer_count(VIEW, eye_state="closed", suppress_makeup_slots={"eyes"}) == COMBINED_PHASE_LAYER_COUNT
    assert overlay.layer_count(VIEW) == COMBINED_PHASE_LAYER_COUNT


@pytest.mark.parametrize("method", ["apply_appearance", "apply"])
def test_failed_core_validation_does_not_report_cached_success(phases, monkeypatch, method):
    overlay, frame = phases
    compose = getattr(overlay, method)
    compose(frame, VIEW)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: True)

    def invalid(*args):
        raise OutfitPackError("invalid silhouette")

    monkeypatch.setattr(overlay, "_official_silhouette_region", invalid)
    assert compose(frame, VIEW).toImage() == frame.toImage()
    assert overlay.layer_count(VIEW) == 0


@pytest.mark.parametrize("failed_phase", ["appearance", "makeup"])
def test_animated_failure_rolls_back_both_phases_but_keeps_motion(phases, monkeypatch, failed_phase):
    overlay, frame = phases

    def layers(*args, categories, **kwargs):
        phase = "makeup" if categories == {"makeup"} else "appearance"
        if phase == failed_phase:
            raise OutfitPackError("invalid phase asset")
        red = QPixmap(frame.size())
        red.fill(QColor("red"))
        return AppearanceLayerStack((), ((red, 0, 0, QRegion(frame.rect()), 1.0),))

    def motion(target):
        from PySide6.QtGui import QPainter
        painter = QPainter(target)
        painter.fillRect(0, 0, 1, 1, QColor("green"))
        painter.end()

    monkeypatch.setattr(overlay, "_active_layers", layers)
    expected = QPixmap(frame)
    motion(expected)
    actual = overlay.apply_animated(frame, VIEW, motion)
    assert actual.toImage() == expected.toImage()
    assert frame.toImage().pixelColor(0, 0) == QColor("blue")
    assert overlay.layer_count(VIEW) == 0


@pytest.mark.parametrize("method", ["apply", "apply_appearance", "apply_makeup"])
def test_canvas_change_revalidates_layers(phases, monkeypatch, method):
    overlay, frame = phases
    sizes = []

    def layers(view_id, size, **kwargs):
        sizes.append(size)
        if size != (2, 2):
            raise OutfitPackError("asset canvas mismatch")
        return AppearanceLayerStack((), ((frame, 0, 0, QRegion(frame.rect()), 1.0),))

    monkeypatch.setattr(overlay, "_active_layers", layers)
    compose = getattr(overlay, method)
    compose(frame, VIEW)
    larger = QPixmap(3, 3)
    larger.fill(QColor("green"))
    assert compose(larger, VIEW).toImage() == larger.toImage()
    assert sizes == [(2, 2), (3, 3)]
    assert overlay.layer_count(VIEW) == 0


def test_core_motion_error_is_not_hidden_as_an_asset_fallback(phases):
    overlay, frame = phases

    def broken_motion(target):
        raise ValueError("core motion defect")

    with pytest.raises(ValueError, match="core motion defect"):
        overlay.apply_animated(frame, VIEW, broken_motion)


def test_successful_animation_keeps_motion_makeup_and_foreground(phases, monkeypatch):
    from PySide6.QtGui import QPainter
    overlay, frame = phases

    def layers(*args, categories, **kwargs):
        patch = QPixmap(1, 1)
        makeup = categories == {"makeup"}
        patch.fill(QColor("yellow" if makeup else "red"))
        return AppearanceLayerStack(
            (), ((patch, 0 if makeup else 1, 0, QRegion(frame.rect()), 1.0),),
            makeup_prefix_count=int(makeup),
        )

    def motion(target):
        painter = QPainter(target)
        painter.fillRect(0, 0, 1, 2, QColor("green"))
        painter.end()

    monkeypatch.setattr(overlay, "_active_layers", layers)
    image = overlay.apply_animated(frame, VIEW, motion).toImage()
    assert image.pixelColor(0, 0) == QColor("yellow")
    assert image.pixelColor(0, 1) == QColor("green")
    assert image.pixelColor(1, 0) == QColor("red")
    assert overlay.layer_count(VIEW) == COMBINED_PHASE_LAYER_COUNT


def test_oral_protection_runs_after_makeup_and_before_front_hair(phases, monkeypatch):
    from PySide6.QtGui import QPainter
    overlay, frame = phases

    def layers(*args, categories, **kwargs):
        patch = QPixmap(1, 1)
        makeup = categories == {"makeup"}
        patch.fill(QColor("yellow" if makeup else "red"))
        return AppearanceLayerStack(
            (), ((patch, 0 if makeup else 1, 0, QRegion(frame.rect()), 1.0),),
            makeup_prefix_count=int(makeup),
            front_hair_indices=frozenset() if makeup else frozenset({0}),
        )

    def protect(target):
        painter = QPainter(target)
        painter.fillRect(0, 0, 2, 1, QColor("white"))
        painter.end()

    monkeypatch.setattr(overlay, "_active_layers", layers)
    image = overlay.apply_animated(frame, VIEW, lambda target: None, paint_after_makeup=protect).toImage()
    assert image.pixelColor(0, 0) == QColor("white")
    assert image.pixelColor(1, 0) == QColor("red")
    assert image.pixelColor(0, 1) == QColor("blue")


def test_oral_protection_error_is_not_hidden_as_appearance_fallback(phases):
    overlay, frame = phases

    def broken_protection(target):
        raise ValueError("oral protection defect")

    with pytest.raises(ValueError, match="oral protection defect"):
        overlay.apply_animated(frame, VIEW, lambda target: None, paint_after_makeup=broken_protection)
