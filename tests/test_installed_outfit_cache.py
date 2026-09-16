"""Selection and rendering share validated archives and reject changed inputs."""

from __future__ import annotations

lazy import hashlib
lazy import os
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice
lazy from PySide6.QtGui import QColor, QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    OutfitPackError, inspect_installed_outfit_pack, install_outfit_pack,
    list_installed_selections, apply_appearance_selection, resolve_active_selection,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_active_outfit_overlay import _authority
lazy from test_outfit_pack import _manifest, _pack, _png


CANVAS = 1254
ASSET_WIDTH = 512
ASSET_HEIGHT = 768
FIRST_COLOR = QColor(20, 80, 180, 255)
SECOND_COLOR = QColor(180, 40, 80, 255)


def _colored_png(color: QColor) -> bytes:
    image = QImage(ASSET_WIDTH, ASSET_HEIGHT, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    image.setPixelColor(0, 0, color)
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _install_colored_pack(root: Path, store: Path, pack_id: str, color: QColor):
    manifest, assets = _manifest(_colored_png(color))
    manifest["id"] = pack_id
    archive = _pack(root / f"{pack_id}-source.mohan-outfit", manifest, assets)
    return install_outfit_pack(archive, store)


def _assert_overlay_selection(overlay, store: Path, selection, expected_path: Path) -> None:
    selected = resolve_active_selection(store, "garment")
    path, item, variant = overlay._selected_variant("garment", selected)
    assert selected.effective_pack_id == selection.pack_id
    assert path == expected_path
    assert item.item_id == selection.item_id
    assert variant.variant_id == selection.variant_id


def test_listing_and_independent_overlays_share_verified_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")
    manifest, assets = _manifest(_png())
    archive = _pack(tmp_path / "source.mohan-outfit", manifest, assets)
    store = tmp_path / "store"
    installed = install_outfit_pack(archive, store)
    calls = []
    original = outfit_pack.inspect_outfit_pack

    def counted(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(outfit_pack, "inspect_outfit_pack", counted)
    selection = next(iter(list_installed_selections(store, "garment")))
    apply_appearance_selection(store, selection)
    selected = resolve_active_selection(store, "garment")
    for _ in range(2):
        overlay = ActiveOutfitOverlay(store, tmp_path, visible_hand_region=lambda _: QRegion())
        path, item, variant = overlay._selected_variant("garment", selected)
        assert path.name == f"{installed.pack_id}.mohan-outfit"
        assert item.item_id == selection.item_id
        assert variant.variant_id == selection.variant_id
    assert len(calls) == 1


def test_replaced_corrupt_and_deleted_archive_never_returns_old_pack(tmp_path):
    manifest, assets = _manifest(_png())
    archive = _pack(tmp_path / "source.mohan-outfit", manifest, assets)
    first = inspect_installed_outfit_pack(archive)
    assert first is not None
    old_stat = archive.stat()
    manifest["pack_version"] = "1.0.1"
    replacement = _pack(tmp_path / "replacement.mohan-outfit", manifest, assets)
    archive.write_bytes(replacement.read_bytes())
    os.utime(archive, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000_000))
    second = inspect_installed_outfit_pack(archive)
    assert second is not None and second.pack_version == "1.0.1"
    assert second != first
    archive.write_bytes(b"invalid archive")
    with pytest.raises(OutfitPackError):
        inspect_installed_outfit_pack(archive)
    archive.unlink()
    with pytest.raises(OutfitPackError):
        inspect_installed_outfit_pack(archive)


def test_warm_overlay_switches_active_selection_between_installed_packs(tmp_path, monkeypatch):
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")
    QApplication.instance() or QApplication([])
    _authority(tmp_path)

    store = tmp_path / "store"
    first_pack = _install_colored_pack(tmp_path, store, "warm-first", FIRST_COLOR)
    second_pack = _install_colored_pack(tmp_path, store, "warm-second", SECOND_COLOR)

    installed_paths = {
        pack.pack_id: store / "packages" / f"{pack.pack_id}.mohan-outfit"
        for pack in (first_pack, second_pack)
    }
    source_hashes = {
        pack_id: hashlib.sha256(path.read_bytes()).hexdigest()
        for pack_id, path in installed_paths.items()
    }
    selections = {
        selection.pack_id: selection
        for selection in list_installed_selections(store, "garment")
    }
    assert set(selections) == {first_pack.pack_id, second_pack.pack_id}

    apply_appearance_selection(store, selections[first_pack.pack_id])
    overlay = ActiveOutfitOverlay(
        store,
        tmp_path,
        visible_hand_region=lambda _view_id: QRegion(),
    )
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    assert overlay.apply(frame, "front-crossed").toImage().pixelColor(0, 0).getRgb() == FIRST_COLOR.getRgb()
    assert overlay.apply(frame, "front-crossed").toImage().pixelColor(0, 0).getRgb() == FIRST_COLOR.getRgb()
    _assert_overlay_selection(overlay, store, selections[first_pack.pack_id], installed_paths[first_pack.pack_id])

    apply_appearance_selection(store, selections[second_pack.pack_id])
    assert overlay.apply(frame, "front-crossed").toImage().pixelColor(0, 0).getRgb() == SECOND_COLOR.getRgb()
    assert overlay.apply(frame, "front-crossed").toImage().pixelColor(0, 0).getRgb() == SECOND_COLOR.getRgb()
    _assert_overlay_selection(overlay, store, selections[second_pack.pack_id], installed_paths[second_pack.pack_id])
    assert installed_paths[first_pack.pack_id] != installed_paths[second_pack.pack_id]
    assert {
        pack_id: hashlib.sha256(path.read_bytes()).hexdigest()
        for pack_id, path in installed_paths.items()
    } == source_hashes


def main() -> int:
    return int(pytest.main([__file__, "-q", *sys.argv[1:]]))


if __name__ == "__main__":
    raise SystemExit(main())
