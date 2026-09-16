"""The presentation composition root shares validated hand-region providers."""

from __future__ import annotations

lazy import sys
lazy import importlib
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure import core_hand_regions as hand_regions
lazy from infrastructure import active_outfit_overlay as overlay_module
lazy import pytest
lazy from PySide6.QtCore import QPoint, Qt
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication
lazy from application import service_container
lazy from domain.outfit_pack import OutfitPackError


HALF_CANVAS = 1254
HAND_X = 20
HAND_Y = 30
HAND_SIZE = 5


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _write_hand_mask(path: Path, x: int = HAND_X, y: int = HAND_Y) -> None:
    image = QImage(HALF_CANVAS, HALF_CANVAS, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    for row in range(y, y + HAND_SIZE):
        for column in range(x, x + HAND_SIZE):
            image.setPixelColor(column, row, QColor(255, 255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")


def _write_front_hand_pair(root: Path) -> None:
    directory = root / "assets" / "expressions" / "layered"
    _write_hand_mask(directory / "front_visible_hand_left.png")
    _write_hand_mask(directory / "front_visible_hand_right.png", HAND_X + 20, HAND_Y + 20)


def _patch_composition_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    original_resource_path = importlib.import_module("infrastructure.app_resources").resource_path
    monkeypatch.setattr(
        service_container,
        "resource_path",
        lambda relative: root if relative == "." else original_resource_path(relative),
    )
    monkeypatch.setenv("MOHAN_DATA_DIR", str(root / "data"))


def test_composition_root_loads_one_provider_and_keeps_regions_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _write_front_hand_pair(tmp_path)
    _patch_composition_root(monkeypatch, tmp_path)
    calls: list[Path] = []
    def counted_loader(root: Path):
        calls.append(root)
        return hand_regions.load_core_hand_regions(root)

    monkeypatch.setattr(service_container, "load_core_hand_regions", counted_loader)
    ports = service_container.create_presentation_ports()
    # Startup must leave the gesture store's public API usable in this same
    # process; isolated module-import tests miss nested lazy-export proxies.
    gesture_store = importlib.import_module("infrastructure.gesture_configuration_store")
    assert gesture_store.import_gesture_configuration.__module__ == "domain.gesture_configuration"
    gesture_domain = importlib.import_module("domain.gesture_configuration")
    assert gesture_store.import_gesture_configuration is gesture_domain.import_gesture_configuration
    assert gesture_store.export_gesture_configuration is gesture_domain.export_gesture_configuration
    assert gesture_store.GestureConfiguration is gesture_domain.GestureConfiguration
    assert gesture_store.GestureDefinition is gesture_domain.GestureDefinition
    first = ports.outfit_overlay_factory()
    second = ports.outfit_overlay_factory()
    face_renderer = ports.face_renderer_factory()
    third = face_renderer._outfit_overlay

    assert calls == [tmp_path]
    assert first._visible_hand_region is second._visible_hand_region is third._visible_hand_region
    first_region = first._visible_hand_region("front-crossed")
    second_region = second._visible_hand_region("front-crossed")
    third_region = third._visible_hand_region("front-crossed")
    assert first_region.contains(QPoint(HAND_X, HAND_Y))
    assert second_region.contains(QPoint(HAND_X, HAND_Y))
    assert third_region.contains(QPoint(HAND_X, HAND_Y))

    first_region.translate(100, 100)
    assert first_region.contains(QPoint(HAND_X + 100, HAND_Y + 100))
    assert not first_region.contains(QPoint(HAND_X, HAND_Y))
    assert second_region.contains(QPoint(HAND_X, HAND_Y))
    assert third_region.contains(QPoint(HAND_X, HAND_Y))


def test_missing_provider_snapshot_is_shared_even_if_masks_appear_later(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _patch_composition_root(monkeypatch, tmp_path)
    calls: list[Path] = []

    def counted_loader(root: Path):
        calls.append(root)
        return hand_regions.load_core_hand_regions(root)

    monkeypatch.setattr(service_container, "load_core_hand_regions", counted_loader)
    monkeypatch.setattr(overlay_module, "load_core_hand_regions", counted_loader)
    ports = service_container.create_presentation_ports()
    first = ports.outfit_overlay_factory()
    assert first._visible_hand_region is None
    assert calls == [tmp_path]

    _write_front_hand_pair(tmp_path)
    second = ports.outfit_overlay_factory()
    third = ports.face_renderer_factory()._outfit_overlay
    assert first._visible_hand_region is second._visible_hand_region is third._visible_hand_region is None
    assert calls == [tmp_path]
    refreshed = service_container.create_presentation_ports().outfit_overlay_factory()
    assert refreshed._visible_hand_region("front-crossed").contains(QPoint(HAND_X, HAND_Y))
    assert calls == [tmp_path, tmp_path]


def test_malformed_provider_still_fails_at_first_overlay_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _write_hand_mask(tmp_path / "assets" / "expressions" / "layered" / "front_visible_hand_left.png")
    _patch_composition_root(monkeypatch, tmp_path)
    ports = service_container.create_presentation_ports()
    with pytest.raises(OutfitPackError, match="Invalid core visible-hand pair"):
        ports.outfit_overlay_factory()
