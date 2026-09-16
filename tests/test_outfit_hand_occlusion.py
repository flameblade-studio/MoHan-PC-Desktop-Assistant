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
lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import AppearanceAsset, AppearanceItem, AppearanceVariant, OutfitPackError
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_PACK_ID
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack

VIEW = "front-crossed"
FULL_VIEW = "yaw+165-pitch+00"
HAND = (25, 505)
CLOTH = (35, 505)
OPAQUE = 255
HALF_ALPHA = 128


def _full_body_hand_pair(
    root: Path,
    directory_name: str,
    stem: str,
    point: tuple[int, int] | None,
) -> tuple[Path, Path]:
    directory = root / "assets/pose-atlas" / directory_name
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for side in ("left", "right"):
        image = QImage(1024, 1536, QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        if side == "left" and point is not None:
            image.setPixelColor(*point, QColor("green"))
        path = directory / f"{stem}_{side}.png"
        assert image.save(str(path))
        paths.append(path)
    return paths[0], paths[1]


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


def test_frozen_absence_blocks_late_disk_overlays_but_legacy_callable_keeps_fallback(
    tmp_path,
):
    app = QApplication.instance() or QApplication([])
    canonical_absent = ActiveOutfitOverlay(tmp_path / "canonical-store", tmp_path)
    explicit_absent = ActiveOutfitOverlay(
        tmp_path / "explicit-store",
        tmp_path,
        visible_hand_region=None,
    )
    legacy_callable = ActiveOutfitOverlay(
        tmp_path / "legacy-store",
        tmp_path,
        visible_hand_region=lambda _view: QRegion(),
    )
    _full_body_hand_pair(
        tmp_path,
        "v5-hand-overlays",
        FULL_VIEW,
        (300, 800),
    )

    assert canonical_absent._core_hand_overlay_layers(FULL_VIEW, (1024, 1536)) == ()
    assert explicit_absent._core_hand_overlay_layers(FULL_VIEW, (1024, 1536)) == ()
    assert len(legacy_callable._core_hand_overlay_layers(FULL_VIEW, (1024, 1536))) == 1
    app.processEvents()


@pytest.mark.parametrize("legacy_point", [None, (300, 800)])
def test_legacy_snapshot_view_blocks_late_preferred_overlays(tmp_path, legacy_point):
    app = QApplication.instance() or QApplication([])
    legacy_paths = _full_body_hand_pair(
        tmp_path,
        "v5-base-layered",
        f"{FULL_VIEW}_visible_hand",
        legacy_point,
    )
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    for path in legacy_paths:
        path.unlink()
    _full_body_hand_pair(
        tmp_path,
        "v5-hand-overlays",
        FULL_VIEW,
        (300, 800),
    )

    assert overlay._core_hand_overlay_layers(FULL_VIEW, (1024, 1536)) == ()
    app.processEvents()


def _green_over_red(alpha: int) -> QColor:
    reference = QImage(1, 1, QImage.Format_RGBA8888)
    reference.fill(QColor("red"))
    pigment = QColor("green")
    pigment.setAlpha(alpha)
    painter = QPainter(reference)
    painter.fillRect(reference.rect(), pigment)
    painter.end()
    return reference.pixelColor(0, 0)


def _green_over_blue(alpha: int) -> QColor:
    reference = QImage(1, 1, QImage.Format_RGBA8888)
    reference.fill(QColor("blue"))
    pigment = QColor("green")
    pigment.setAlpha(alpha)
    painter = QPainter(reference)
    painter.fillRect(reference.rect(), pigment)
    painter.end()
    return reference.pixelColor(0, 0)


@pytest.mark.parametrize("alpha", [1, 127, 254, 255])
def test_fractional_core_hand_composites_over_garment_without_alpha_holes(
    tmp_path,
    monkeypatch,
    alpha,
):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-hand-overlays"
    directory.mkdir(parents=True)
    left = QImage(1024, 1536, QImage.Format_RGBA8888)
    left.fill(QColor(0, 0, 0, 0))
    pigment = QColor("green")
    pigment.setAlpha(alpha)
    left.setPixelColor(300, 800, pigment)
    assert left.save(str(directory / f"{FULL_VIEW}_left.png"))
    right = QImage(1024, 1536, QImage.Format_RGBA8888)
    right.fill(QColor(0, 0, 0, 0))
    assert right.save(str(directory / f"{FULL_VIEW}_right.png"))
    replacement_directory = (
        tmp_path
        / "assets/pose-atlas/v5-appearance-replacement-masks"
        / OFFICIAL_OUTFIT_PACK_ID
    )
    replacement_directory.mkdir(parents=True)
    replacement = QImage(1024, 1536, QImage.Format_RGBA8888)
    replacement.fill(QColor(0, 0, 0, 0))
    replacement.setPixelColor(300, 800, QColor("white"))
    assert replacement.save(str(replacement_directory / f"{FULL_VIEW}.png"))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    garment = QPixmap(1024, 1536)
    garment.fill(QColor("blue"))
    canvas = QRegion(QRect(0, 0, 1024, 1536))
    overlay._phase_layers_by_view[(FULL_VIEW, "appearance", frozenset(), "rest")] = AppearanceLayerStack(
        (),
        ((garment, 0, 0, canvas, 1.0),),
        behind_hand_indices=frozenset({0}),
    )
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_selected_silhouette_region", lambda *_args: None)
    body = QPixmap(1024, 1536)
    body.fill(QColor("red"))
    result = overlay.apply_appearance(body, FULL_VIEW).toImage()
    assert result.pixelColor(300, 800) == _green_over_blue(alpha)
    assert result.pixelColor(300, 800).alpha() == OPAQUE
    assert result.pixelColor(301, 800) == QColor("blue")
    app.processEvents()


def test_animated_makeup_garment_and_repaintable_hand_keep_partial_depth_order(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-hand-overlays"
    directory.mkdir(parents=True)
    left = QImage(1024, 1536, QImage.Format_RGBA8888)
    left.fill(Qt.transparent)
    left.setPixelColor(300, 800, QColor("green"))
    assert left.save(str(directory / f"{FULL_VIEW}_left.png"))
    right = QImage(1024, 1536, QImage.Format_RGBA8888)
    right.fill(Qt.transparent)
    assert right.save(str(directory / f"{FULL_VIEW}_right.png"))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    garment_image = QImage(1024, 1536, QImage.Format_RGBA8888)
    garment_image.fill(Qt.transparent)
    garment_image.setPixelColor(300, 800, QColor("blue"))
    garment_image.setPixelColor(100, 100, QColor("blue"))
    garment = QPixmap.fromImage(garment_image)
    canvas = QRegion(QRect(0, 0, 1024, 1536))
    appearance = AppearanceLayerStack(
        (),
        ((garment, 0, 0, canvas, 1.0),),
        makeup_occluder_indices=frozenset({0}),
        behind_hand_indices=frozenset({0}),
    )
    overlay._phase_layers_by_view[(FULL_VIEW, "appearance", frozenset(), "rest")] = appearance
    overlay._phase_layers_by_view[(FULL_VIEW, "makeup", frozenset(), "rest")] = AppearanceLayerStack((), ())
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_selected_silhouette_region", lambda *_args: None)

    def paint_skin_and_makeup(target: QPixmap) -> None:
        painter = QPainter(target)
        painter.setPen(QColor("yellow"))
        painter.drawPoint(300, 800)
        painter.drawPoint(100, 100)
        painter.drawPoint(101, 100)
        painter.end()

    body = QPixmap(1024, 1536)
    body.fill(QColor("red"))
    result = overlay.apply_animated(body, FULL_VIEW, paint_skin_and_makeup).toImage()
    assert result.pixelColor(300, 800) == QColor("green")
    assert result.pixelColor(100, 100) == QColor("blue")
    assert result.pixelColor(101, 100) == QColor("yellow")
    app.processEvents()


def test_combined_repaintable_hand_keeps_makeup_source_atop_and_native_alpha(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-hand-overlays"
    directory.mkdir(parents=True)
    left = QImage(1024, 1536, QImage.Format_RGBA8888)
    left.fill(Qt.transparent)
    left.setPixelColor(300, 800, QColor("green"))
    assert left.save(str(directory / f"{FULL_VIEW}_left.png"))
    right = QImage(1024, 1536, QImage.Format_RGBA8888)
    right.fill(Qt.transparent)
    assert right.save(str(directory / f"{FULL_VIEW}_right.png"))

    makeup_image = QImage(1024, 1536, QImage.Format_RGBA8888)
    makeup_image.fill(Qt.transparent)
    pigment = QColor("green")
    pigment.setAlpha(127)
    makeup_image.setPixelColor(100, 100, pigment)
    makeup_image.setPixelColor(101, 100, pigment)
    garment_image = QImage(1024, 1536, QImage.Format_RGBA8888)
    garment_image.fill(Qt.transparent)
    garment_image.setPixelColor(300, 800, QColor("blue"))
    canvas = QRegion(QRect(0, 0, 1024, 1536))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    overlay._layers_by_view[FULL_VIEW] = AppearanceLayerStack(
        (),
        (
            (QPixmap.fromImage(makeup_image), 0, 0, canvas, 1.0),
            (QPixmap.fromImage(garment_image), 0, 0, canvas, 1.0),
        ),
        makeup_prefix_count=1,
        behind_hand_indices=frozenset({1}),
    )
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_selected_silhouette_region", lambda *_args: None)

    body_image = QImage(1024, 1536, QImage.Format_RGBA8888)
    body_image.fill(Qt.transparent)
    native = QColor("red")
    native.setAlpha(HALF_ALPHA)
    body_image.setPixelColor(101, 100, native)
    body = QPixmap.fromImage(body_image)
    result = overlay.apply(body, FULL_VIEW).toImage()
    assert result.pixelColor(100, 100).alpha() == 0
    assert result.pixelColor(101, 100).alpha() == HALF_ALPHA
    assert result.pixelColor(300, 800) == QColor("green")
    app.processEvents()


def test_makeup_phase_accepts_empty_early_stage_and_keeps_source_atop(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    canvas = QRegion(QRect(0, 0, 2, 1))
    makeup_image = QImage(2, 1, QImage.Format_RGBA8888)
    makeup_image.fill(Qt.transparent)
    pigment = QColor("green")
    pigment.setAlpha(127)
    makeup_image.setPixelColor(0, 0, pigment)
    makeup_image.setPixelColor(1, 0, pigment)

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    overlay._phase_layers_by_view[
        (FULL_VIEW, "makeup", frozenset(), "rest")
    ] = AppearanceLayerStack(
        (),
        ((QPixmap.fromImage(makeup_image), 0, 0, canvas, 1.0),),
        makeup_prefix_count=1,
    )
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)

    body_image = QImage(2, 1, QImage.Format_RGBA8888)
    body_image.fill(Qt.transparent)
    native = QColor("red")
    native.setAlpha(HALF_ALPHA)
    body_image.setPixelColor(1, 0, native)

    result = overlay.apply_makeup(QPixmap.fromImage(body_image), FULL_VIEW).toImage()

    assert result.pixelColor(0, 0).alpha() == 0
    assert result.pixelColor(1, 0).alpha() == HALF_ALPHA
    app.processEvents()


@pytest.mark.parametrize("alpha", [1, 127, 255])
def test_core_body_overlay_restores_visible_skin_before_appearance(tmp_path, monkeypatch, alpha):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path / "assets/pose-atlas/v5-body-overlays"
    directory.mkdir(parents=True)
    skin = QImage(1024, 1536, QImage.Format_RGBA8888)
    skin.fill(QColor(0, 0, 0, 0))
    pigment = QColor("green")
    pigment.setAlpha(alpha)
    skin.setPixelColor(600, 250, pigment)
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
    assert result.pixelColor(600, 250) == _green_over_red(alpha)
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


def test_official_replacement_mask_clears_shared_base_before_appearance(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    directory = (
        tmp_path
        / "assets/pose-atlas/v5-appearance-replacement-masks"
        / OFFICIAL_OUTFIT_PACK_ID
    )
    directory.mkdir(parents=True)
    replacement = QImage(10, 10, QImage.Format_RGBA8888)
    replacement.fill(QColor(0, 0, 0, 0))
    replacement.setPixelColor(3, 4, QColor("white"))
    assert replacement.save(str(directory / f"{FULL_VIEW}.png"))

    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    garment = QPixmap(10, 10)
    garment.fill(QColor(0, 0, 0, 0))
    garment_image = garment.toImage()
    garment_image.setPixelColor(5, 4, QColor("blue"))
    garment = QPixmap.fromImage(garment_image)
    overlay._phase_layers_by_view[
        (FULL_VIEW, "appearance", frozenset(), "rest")
    ] = ((garment, 0, 0, QRegion(QRect(0, 0, 10, 10)), 1.0),)
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: True)

    body = QPixmap(10, 10)
    body.fill(QColor(0, 0, 0, 0))
    body_image = body.toImage()
    body_image.fill(QColor("red"))
    body = QPixmap.fromImage(body_image)
    result = overlay.apply_appearance(body, FULL_VIEW).toImage()
    assert result.pixelColor(3, 4).alpha() == 0
    assert result.pixelColor(4, 4) == QColor("red")
    assert result.pixelColor(5, 4) == QColor("blue")
    app.processEvents()


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("OUTFIT_HAND_OCCLUSION_OK")


if __name__ == "__main__":
    main()
