"""Prove the animated appearance depth order and atomic rollback contract."""
from __future__ import annotations

lazy import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtGui import QColor, QPainter, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import OutfitPackError
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack

VIEW = "yaw+000-pitch+00"
CANVAS = (2, 2)
EXPECTED_ROLLBACK_MOTION_CALLS = 2


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    return QApplication.instance() or QApplication([])


def _solid(color: QColor) -> QPixmap:
    pixmap = QPixmap(*CANVAS)
    pixmap.fill(color)
    return pixmap


def _layer(color: QColor, x: int, y: int) -> tuple[QPixmap, int, int, QRegion, float]:
    return (_solid(color), 0, 0, QRegion(x, y, 1, 1), 1.0)


def _body() -> QPixmap:
    """Use opaque blue pixels as the core body authority in this fixture."""
    return _solid(QColor(0, 0, 255, 255))


def _motion(target: QPixmap) -> None:
    painter = QPainter(target)
    painter.fillRect(1, 0, 1, 1, QColor(0, 255, 0, 255))
    painter.end()


def _stub_layers(
    overlay: ActiveOutfitOverlay,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_makeup: bool = False,
    occludes_makeup: bool = False,
    garment_alpha: int = 255,
) -> None:
    rear = _layer(QColor(0, 255, 0, 255), 0, 0)
    # The front-hair index is relative to the foreground sequence. Garment
    # and headwear stay early in that sequence so only front hair is deferred.
    front = _layer(QColor(255, 0, 0, 128), 1, 0)
    garment = _layer(QColor(0, 255, 255, garment_alpha), 0, 1)
    headwear = _layer(QColor(128, 0, 128, 255), 0, 1)
    # Keep one makeup pixel under the front hair and one over the early
    # garment/headwear pixels, so both depth boundaries are observable.
    makeup_under_front = _layer(QColor(255, 255, 0, 255), 1, 0)
    makeup_over_early_layers = _layer(QColor(255, 255, 0, 255), 0, 1)

    def layers(_view_id, _canvas_size, *, categories, **_kwargs):
        if set(categories) == {"makeup"}:
            if fail_makeup:
                raise OutfitPackError("synthetic makeup failure")
            return AppearanceLayerStack(
                (),
                (makeup_under_front, makeup_over_early_layers),
                makeup_prefix_count=2,
            )
        return AppearanceLayerStack(
            (rear,),
            (front, garment, headwear),
            front_hair_indices=frozenset({0}),
            makeup_occluder_indices=frozenset({1}) if occludes_makeup else frozenset(),
        )

    monkeypatch.setattr(overlay, "_active_layers", layers)


@pytest.fixture
def overlay(tmp_path, monkeypatch: pytest.MonkeyPatch) -> ActiveOutfitOverlay:
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    monkeypatch.setattr(result, "_garment_is_active", lambda: False)
    monkeypatch.setattr(result, "_official_outfit_is_active", lambda: False)
    return result


def test_animated_depth_draws_rear_under_body_makeup_then_front_once(
    overlay: ActiveOutfitOverlay, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_layers(overlay, monkeypatch)

    image = overlay.apply_animated(_body(), VIEW, _motion).toImage()

    # Rear hair is DestinationOver, so the opaque body remains authoritative.
    assert image.pixelColor(0, 0).getRgb() == (0, 0, 255, 255)
    # Makeup stays above early garment/headwear even while front hair is
    # deferred: the later headwear draw would otherwise leave purple here.
    assert image.pixelColor(0, 1).getRgb() == (255, 255, 0, 255)
    # Makeup is painted over motion and the translucent front hair is painted
    # once after it: a second hair draw would produce (255, 63, 0, 255).
    assert image.pixelColor(1, 0).getRgb() == (255, 127, 0, 255)


def test_animated_makeup_failure_rolls_back_appearance_and_replays_motion(
    overlay: ActiveOutfitOverlay, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_layers(overlay, monkeypatch, fail_makeup=True)
    calls = 0

    def motion(target: QPixmap) -> None:
        nonlocal calls
        calls += 1
        _motion(target)

    image = overlay.apply_animated(_body(), VIEW, motion).toImage()

    # The interrupted attempt is discarded, while motion is replayed on the bare
    # body so the animation continues after the outfit is removed.
    assert calls == EXPECTED_ROLLBACK_MOTION_CALLS
    assert image.pixelColor(0, 0).getRgb() == (0, 0, 255, 255)
    assert image.pixelColor(1, 0).getRgb() == (0, 255, 0, 255)


@pytest.mark.parametrize("garment_alpha, expected", [(255, (0, 255, 255, 255)), (128, (127, 255, 128, 255))])
def test_declared_cloth_covers_makeup_once_with_authored_alpha(
    overlay: ActiveOutfitOverlay,
    monkeypatch: pytest.MonkeyPatch,
    garment_alpha: int,
    expected: tuple[int, int, int, int],
) -> None:
    _stub_layers(overlay, monkeypatch, occludes_makeup=True, garment_alpha=garment_alpha)

    image = overlay.apply_animated(_body(), VIEW, _motion).toImage()

    assert image.pixelColor(0, 1).getRgb() == expected
    assert image.pixelColor(1, 0).getRgb() == (255, 127, 0, 255)


@pytest.mark.parametrize("headwear_alpha, expected", [(255, (0, 0, 255, 255)), (128, (127, 0, 128, 255))])
def test_opted_in_headwear_stays_above_front_hair_once(
    overlay: ActiveOutfitOverlay,
    monkeypatch: pytest.MonkeyPatch,
    headwear_alpha: int,
    expected: tuple[int, int, int, int],
) -> None:
    hair = _layer(QColor(255, 0, 0, 255), 1, 0)
    headwear = _layer(QColor(0, 0, 255, headwear_alpha), 1, 0)
    pigment = _layer(QColor(255, 255, 0, 255), 1, 0)

    def layers(_view, _size, *, categories, **_kwargs):
        if set(categories) == {"makeup"}:
            return AppearanceLayerStack((), (pigment,), makeup_prefix_count=1)
        return AppearanceLayerStack(
            (), (hair, headwear), front_hair_indices=frozenset({0}),
            makeup_occluder_indices=frozenset({1}),
        )

    monkeypatch.setattr(overlay, "_active_layers", layers)
    image = overlay.apply_animated(_body(), VIEW, _motion).toImage()

    assert image.pixelColor(1, 0).getRgb() == expected
    assert image.pixelColor(0, 0) == _body().toImage().pixelColor(0, 0)
