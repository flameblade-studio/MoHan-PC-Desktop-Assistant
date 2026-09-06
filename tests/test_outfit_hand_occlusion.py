"""Core hand ownership survives cloth while front-of-hand props remain visible."""
from __future__ import annotations

lazy import hashlib
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from infrastructure import active_outfit_overlay as active_outfit_overlay_module
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QColor, QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import AppearanceAsset, AppearanceItem, AppearanceVariant, OutfitPackError
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay

VIEW = "front-crossed"
FULL_VIEW = "yaw+165-pitch+00"
HAND = (25, 505)
CLOTH = (35, 505)


def _layer(tmp_path: Path, overlay: ActiveOutfitOverlay, category: str, rule: str | None):
    image = QImage(20, 20, QImage.Format_RGBA8888)
    image.fill(QColor("blue"))
    image.setPixelColor(0, 0, QColor(0, 0, 0, 0))
    path = tmp_path / "layer.png"
    assert image.save(str(path))
    encoded = path.read_bytes()
    declaration = AppearanceAsset("outerwear", "layer.png", hashlib.sha256(encoded).hexdigest(), 20, 20, 20, 500, 10)
    variant = AppearanceVariant("test", frozendict(), frozendict({VIEW: (declaration,)}),
                                hand_rules=frozendict({VIEW: rule}) if rule else None)
    item = AppearanceItem(category, "test", frozendict(), (variant,))
    archive_path = tmp_path / "layers.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("layer.png", encoded)
    with zipfile.ZipFile(archive_path) as archive:
        return tuple(layer for _, layer in overlay._garment_layers(
            archive, (declaration,), category, item, variant, VIEW, (1254, 1254)))


@pytest.mark.parametrize(("category", "rule", "hand_color"), [
    ("garment", None, "red"),
    ("handheld", "behind-hands", "red"),
    ("handheld", "front-of-hands", "blue"),
])
def test_runtime_obeys_core_hand_ownership(tmp_path, monkeypatch, category, rule, hand_color):
    app = QApplication.instance() or QApplication([])
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path,
                                  visible_hand_region=lambda view: QRegion(20, 500, 10, 10))
    monkeypatch.setattr(overlay, "_forbidden_face_region", lambda *args: QRegion())
    overlay._layers_by_view[VIEW] = _layer(tmp_path, overlay, category, rule)
    body = QPixmap(1254, 1254)
    body.fill(QColor("red"))
    result = overlay.apply(body, VIEW).toImage()
    assert result.pixelColor(*HAND) == QColor(hand_color)
    assert result.pixelColor(*CLOTH) == QColor("blue")
    assert body.toImage().pixelColor(*CLOTH) == QColor("red")
    app.processEvents()


def test_invalid_core_mask_rejected_and_legacy_preserved(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path,
                                  visible_hand_region=lambda view: QRegion(-1, 0, 2, 2))
    monkeypatch.setattr(overlay, "_forbidden_face_region", lambda *args: QRegion())
    with pytest.raises(OutfitPackError, match="Core hand region"):
        _layer(tmp_path, overlay, "garment", None)
    legacy = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    monkeypatch.setattr(legacy, "_forbidden_face_region", lambda *args: QRegion())
    legacy._layers_by_view[VIEW] = _layer(tmp_path, legacy, "garment", None)
    body = QPixmap(1254, 1254)
    body.fill(QColor("red"))
    assert legacy.apply(body, VIEW).toImage().pixelColor(*HAND) == QColor("blue")
    app.processEvents()


def test_core_hand_overlay_is_painted_before_clipped_garment(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-hand-overlays"
    directory.mkdir(parents=True)
    left = QImage(1024, 1536, QImage.Format_RGBA8888)
    left.fill(QColor(0, 0, 0, 0))
    left.setPixelColor(300, 800, QColor("green"))
    assert left.save(str(directory / f"{FULL_VIEW}_left.png"))
    right = QImage(1024, 1536, QImage.Format_RGBA8888)
    right.fill(QColor(0, 0, 0, 0))
    assert right.save(str(directory / f"{FULL_VIEW}_right.png"))

    hand = QRegion(300, 800, 1, 1)
    overlay = ActiveOutfitOverlay(
        tmp_path / "store",
        tmp_path,
        visible_hand_region=lambda view: QRegion(hand),
    )
    garment = QPixmap(1024, 1536)
    garment.fill(QColor("blue"))
    canvas = QRegion(QRect(0, 0, 1024, 1536))
    overlay._layers_by_view[FULL_VIEW] = (
        (garment, 0, 0, canvas.subtracted(hand), 1.0),
    )
    monkeypatch.setattr(
        active_outfit_overlay_module,
        "resolve_active_selection",
        lambda _store, _category: SimpleNamespace(status="active"),
    )
    body = QPixmap(1024, 1536)
    body.fill(QColor("red"))
    result = overlay.apply(body, FULL_VIEW).toImage()
    assert result.pixelColor(300, 800) == QColor("green")
    assert result.pixelColor(301, 800) == QColor("blue")
    app.processEvents()


def test_core_body_overlay_restores_visible_skin_before_appearance(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-body-overlays"
    directory.mkdir(parents=True)
    skin = QImage(1024, 1536, QImage.Format_RGBA8888)
    skin.fill(QColor(0, 0, 0, 0))
    skin.setPixelColor(600, 250, QColor("green"))
    assert skin.save(str(directory / f"{FULL_VIEW}.png"))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    garment = QPixmap(1024, 1536)
    garment.fill(QColor("blue"))
    canvas = QRegion(QRect(0, 0, 1024, 1536))
    overlay._layers_by_view[FULL_VIEW] = (
        (garment, 0, 0, canvas.subtracted(QRegion(600, 250, 1, 1)), 1.0),
    )
    monkeypatch.setattr(
        active_outfit_overlay_module,
        "resolve_active_selection",
        lambda _store, _category: SimpleNamespace(
            status="active",
            effective_pack_id="custom.pack",
        ),
    )
    body = QPixmap(1024, 1536)
    body.fill(QColor("red"))
    result = overlay.apply(body, FULL_VIEW).toImage()
    assert result.pixelColor(600, 250) == QColor("green")
    assert result.pixelColor(601, 250) == QColor("blue")
    app.processEvents()


def test_official_appearance_silhouette_clears_protruding_body(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    directory = (
        tmp_path
        / "assets/pose-atlas/v5-appearance-silhouettes"
        / OFFICIAL_OUTFIT_PACK_ID
    )
    directory.mkdir(parents=True)
    silhouette = QImage(1024, 1536, QImage.Format_RGBA8888)
    silhouette.fill(QColor(0, 0, 0, 0))
    silhouette.setPixelColor(300, 800, QColor("white"))
    assert silhouette.save(str(directory / f"{FULL_VIEW}.png"))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    garment = QPixmap(1024, 1536)
    garment.fill(QColor(0, 0, 0, 0))
    garment.fill(QColor("blue"))
    overlay._layers_by_view[FULL_VIEW] = (
        (garment, 0, 0, QRegion(300, 800, 1, 1), 1.0),
    )
    monkeypatch.setattr(
        active_outfit_overlay_module,
        "resolve_active_selection",
        lambda _store, _category: SimpleNamespace(
            status="active",
            effective_pack_id=OFFICIAL_OUTFIT_PACK_ID,
        ),
    )
    body = QPixmap(1024, 1536)
    body.fill(QColor("red"))
    result = overlay.apply(body, FULL_VIEW).toImage()
    assert result.pixelColor(0, 0).alpha() == 0
    assert result.pixelColor(300, 800) == QColor("blue")
    app.processEvents()


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("OUTFIT_HAND_OCCLUSION_OK")


if __name__ == "__main__":
    main()
