from __future__ import annotations

lazy import hashlib
lazy import importlib
lazy import json
lazy import logging
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure import active_outfit_overlay as adapter_module
lazy from infrastructure import active_outfit_base_clear as base_clear_module
lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    OFFICIAL_PACK_ROOT,
    AppearanceAsset,
    AppearanceItem,
    AppearanceVariant,
    OutfitPack,
    SelectionResolution,
    apply_ensemble,
    resolve_active_selection,
    restore_builtin_outfit,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack
lazy from infrastructure.layered_full_body_assets import load_layered_full_body_assets
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from infrastructure.outfit_layer_cache_key import OutfitLayerCacheKey
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme

CANVAS = 1254
OUTFIT_BLUE = 180
ACCESSORY_RED = 210
OPAQUE_ALPHA = 255


def _app() -> object:
    return QApplication.instance() or QApplication([])


def test_official_pack_root_defaults_to_public_domain_constant(
    tmp_path: Path,
) -> None:
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    assert overlay._official_pack_root == OFFICIAL_PACK_ROOT


def _encoded_layer(color: QColor | None = None) -> bytes:
    image = QImage(96, 96, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    color = color or QColor(20, 80, OUTFIT_BLUE, 255)
    for y in range(8, 88):
        for x in range(8, 88):
            image.setPixelColor(x, y, color)
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _encoded_transparent_layer() -> bytes:
    image = QImage(96, 96, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _authority(root: Path) -> None:
    path = root / "assets" / "expressions" / "layered" / "front_base.png"
    path.parent.mkdir(parents=True)
    image = QImage(CANVAS, CANVAS, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for y in range(100, 451):
        for x in range(400, 801):
            image.setPixelColor(x, y, QColor(255, 255, 255, 255))
    assert image.save(str(path), "PNG")
    iris = QImage(CANVAS, CANVAS, QImage.Format_RGBA8888)
    iris.fill(QColor(0, 0, 0, 0))
    iris.setPixelColor(600, 250, QColor(255, 255, 255, 255))
    assert iris.save(str(path.with_name("front_iris_left.png")), "PNG")


def _configure(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    encoded: bytes,
    *,
    anchor: tuple[int, int] = (20, 500),
    body_profile: str = BODY_PROFILE_ID,
    occludes_makeup: bool = False,
) -> None:
    store = root / "store"
    packages = store / "packages"
    packages.mkdir(parents=True)
    archive_path = packages / "pack.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/garment.png", encoded)
    declaration = AppearanceAsset(
        "outerwear",
        "assets/garment.png",
        hashlib.sha256(encoded).hexdigest(),
        96,
        96,
        anchor[0],
        anchor[1],
        10,
        occludes_makeup=occludes_makeup,
    )
    variant = AppearanceVariant(
        "navy",
        frozendict(),
        frozendict({"front-crossed": (declaration,)}),
    )
    item = AppearanceItem("garment", "robe", frozendict(), (variant,))
    pack = OutfitPack(
        "pack",
        "1.0.0",
        ">=4.0.0,<5.0.0",
        frozendict(),
        "original",
        "artist",
        "MIT",
        body_profile,
        (item,),
        (),
    )

    def selection(
        _store: Path, category: str, **_kwargs: object
    ) -> SimpleNamespace:
        if category != "garment":
            return SimpleNamespace(status="builtin")
        return SimpleNamespace(
            status="installed",
            effective_pack_id="pack",
            effective_item_id="robe",
            effective_variant_id="navy",
        )

    monkeypatch.setattr(adapter_module, "resolve_active_selection", selection)
    monkeypatch.setattr(adapter_module, "inspect_installed_outfit_pack", lambda _: pack)


@pytest.mark.parametrize(
    ("poses", "expected"),
    (("cheek-rest", "cheek-glance"), True),
    (("cheek-rest",), False),
)
def test_appearance_declares_view_checks_active_pack_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    poses: tuple[str, ...],
    expected: bool,
) -> None:
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )
    selected = SimpleNamespace(status="installed")
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda category: selected if category == "garment" else SimpleNamespace(status="builtin"),
    )
    declaration = AppearanceAsset(
        "outerwear", "assets/garment.png", "0" * 64,
        96, 96, 0, 0, 10,
    )
    variant = AppearanceVariant(
        "navy",
        frozendict(),
        frozendict(dict.fromkeys(poses, (declaration,))),
    )
    monkeypatch.setattr(
        overlay,
        "_selected_variant",
        lambda _category, _selected: (tmp_path / "pack.zip", object(), variant),
    )

    assert overlay.appearance_declares_view("cheek-glance") is expected


def _selection_resolution(
    category: str,
    status: str,
    requested: tuple[str, str, str],
    effective: tuple[str, str, str],
) -> SelectionResolution:
    return SelectionResolution(category, status, *requested, *effective)


def _transparent_runtime_stack() -> AppearanceLayerStack:
    layer = QPixmap(1, 1)
    layer.fill(QColor(0, 0, 0, 0))
    return AppearanceLayerStack(
        (),
        ((layer, 0, 0, QRegion(QRect(0, 0, 1, 1)), 1.0),),
    )


def _official_base_selections(
    headwear: SelectionResolution,
) -> dict[str, SelectionResolution]:
    official = importlib.import_module("domain.outfit_pack_official").OFFICIAL_OUTFIT_PACK_ID
    default_requested = ("builtin", "builtin", "builtin")
    return {
        "garment": _selection_resolution(
            "garment", "installed", default_requested, (official, "robe", "blue-white"),
        ),
        "hairstyle": _selection_resolution(
            "hairstyle", "installed", default_requested, (official, "loose-hair", "ink-black"),
        ),
        "headwear": headwear,
    }


def test_explicit_headwear_none_keeps_official_silhouette_base_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    store = tmp_path / "store"
    store.mkdir()
    headwear = _selection_resolution(
        "headwear", "builtin", ("builtin", "none", "none"), ("builtin", "none", "none"),
    )
    selections = _official_base_selections(headwear)
    monkeypatch.setattr(
        adapter_module,
        "resolve_active_selection",
        lambda _store, category, **_kwargs: selections[category],
    )
    overlay = ActiveOutfitOverlay(store, tmp_path, visible_hand_region=None)
    silhouette = QRegion(QRect(400, 400, 400, 400))
    monkeypatch.setattr(overlay, "_official_silhouette_region", lambda *_args: silhouette)
    monkeypatch.setattr(overlay, "_active_layers", lambda *_args, **_kwargs: _transparent_runtime_stack())
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))

    result = overlay.apply(frame, "none-headwear")

    assert overlay._official_outfit_is_active()
    assert result.toImage().pixelColor(50, 300).alpha() == 0
    assert result.toImage().pixelColor(600, 600) == frame.toImage().pixelColor(600, 600)


def test_bare_default_fallback_does_not_use_headwear_none_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    store = tmp_path / "store"
    store.mkdir()
    monkeypatch.setattr(adapter_module, "resolve_active_selection", outfit_pack.resolve_active_selection)
    overlay = ActiveOutfitOverlay(
        store,
        tmp_path,
        visible_hand_region=None,
        official_pack_root=tmp_path / "missing-official",
    )
    silhouette = QRegion(QRect(400, 400, 400, 400))
    monkeypatch.setattr(overlay, "_official_silhouette_region", lambda *_args: silhouette)
    monkeypatch.setattr(overlay, "_active_layers", lambda *_args, **_kwargs: _transparent_runtime_stack())
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))

    result = overlay.apply(frame, "bare-fallback")

    assert not overlay._official_outfit_is_active()
    assert result.toImage().pixelColor(50, 300) == frame.toImage().pixelColor(50, 300)


def test_custom_headwear_does_not_use_explicit_none_silhouette(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    store = tmp_path / "store"
    store.mkdir()
    headwear = _selection_resolution(
        "headwear", "installed", ("custom-pack", "hairpiece", "silver"),
        ("custom-pack", "hairpiece", "silver"),
    )
    selections = _official_base_selections(headwear)
    monkeypatch.setattr(
        adapter_module,
        "resolve_active_selection",
        lambda _store, category, **_kwargs: selections[category],
    )
    overlay = ActiveOutfitOverlay(store, tmp_path, visible_hand_region=None)
    silhouette = QRegion(QRect(400, 400, 400, 400))
    head = QRegion(QRect(400, 100, 400, 100))
    monkeypatch.setattr(overlay, "_official_silhouette_region", lambda *_args: silhouette)
    monkeypatch.setattr(overlay, "_protected_face_region", lambda *_args: head)
    monkeypatch.setattr(overlay, "_active_layers", lambda *_args, **_kwargs: _transparent_runtime_stack())
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))

    result = overlay.apply(frame, "custom-headwear")

    assert not overlay._official_outfit_is_active()
    assert result.toImage().pixelColor(50, 300).alpha() == 0
    assert result.toImage().pixelColor(500, 150).alpha() == OPAQUE_ALPHA


def test_active_garment_is_composited_without_touching_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    encoded = _encoded_layer()
    _configure(monkeypatch, tmp_path, encoded)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path).apply(
        frame,
        "front-crossed",
    )
    assert result.toImage().pixelColor(40, 520).blue() == OUTFIT_BLUE
    assert result.toImage().pixelColor(600, 200) == frame.toImage().pixelColor(600, 200)


def test_declared_garment_depth_reaches_runtime_stack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    _configure(monkeypatch, tmp_path, _encoded_layer(), occludes_makeup=True)
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)

    layers = overlay._active_layers("front-crossed", (CANVAS, CANVAS))

    assert layers.makeup_occluder_indices == frozenset({0})
    assert len(layers.foreground) == 1


def test_declared_garment_depth_cannot_bypass_identity_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    _configure(monkeypatch, tmp_path, _encoded_layer(), anchor=(500, 200), occludes_makeup=True)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)

    with pytest.raises(outfit_pack.OutfitPackError, match="overlaps protected identity"):
        overlay._active_layers("front-crossed", (CANVAS, CANVAS))
    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()


def test_invalid_anchor_fails_closed_to_original_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    encoded = _encoded_layer()
    _configure(monkeypatch, tmp_path, encoded, anchor=(CANVAS - 40, 0))
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path).apply(
        frame,
        "front-crossed",
    )
    assert result.toImage() == frame.toImage()


def _fallback_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == "mohan.outfit_overlay"
        and record.getMessage() == "outfit_overlay_fallback"
    ]


def _assert_single_fallback(
    caplog: pytest.LogCaptureFixture,
    *,
    reason: str,
    view_id: str,
    pack_id: str,
    asset_path: str,
) -> None:
    records = _fallback_records(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.outfit_reason == reason
    assert record.outfit_view == view_id
    assert record.outfit_pack_id == pack_id
    assert record.outfit_asset_path == asset_path


def test_duplicate_pack_id_fallback_is_logged_once_without_changing_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _app()
    caplog.set_level(logging.WARNING, logger="mohan.outfit_overlay")
    store = tmp_path / "store"
    packages = store / "packages"
    official = tmp_path / "official"
    packages.mkdir(parents=True)
    official.mkdir()
    for root in (packages, official):
        (root / "duplicate.mohan-outfit").write_bytes(b"duplicate")
    frame = QPixmap(8, 8)
    frame.fill(QColor("white"))
    overlay = ActiveOutfitOverlay(
        store, tmp_path, visible_hand_region=None, official_pack_root=official,
    )

    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()
    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()

    _assert_single_fallback(
        caplog,
        reason="duplicate_pack_id",
        view_id="front-crossed",
        pack_id="duplicate",
        asset_path="duplicate.mohan-outfit",
    )


def test_path_traversal_fallback_is_logged_once_without_changing_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _app()
    caplog.set_level(logging.WARNING, logger="mohan.outfit_overlay")
    store = tmp_path / "store"
    packages = store / "packages"
    packages.mkdir(parents=True)
    official = tmp_path / "official"
    with zipfile.ZipFile(packages / "unsafe.mohan-outfit", "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("../escape.png", b"not-an-image")
    frame = QPixmap(8, 8)
    frame.fill(QColor("white"))
    overlay = ActiveOutfitOverlay(
        store, tmp_path, visible_hand_region=None, official_pack_root=official,
    )

    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()
    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()

    _assert_single_fallback(
        caplog,
        reason="asset_path_traversal",
        view_id="front-crossed",
        pack_id="unsafe",
        asset_path="../escape.png",
    )


def test_manifest_hash_fallback_is_logged_once_without_changing_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _app()
    caplog.set_level(logging.WARNING, logger="mohan.outfit_overlay")
    _authority(tmp_path)
    _configure(monkeypatch, tmp_path, _encoded_layer())
    archive_path = tmp_path / "store" / "packages" / "pack.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/garment.png", _encoded_layer(QColor("red")))
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor("white"))
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)

    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()
    assert overlay.apply(frame, "front-crossed").toImage() == frame.toImage()

    _assert_single_fallback(
        caplog,
        reason="manifest_asset_hash_mismatch",
        view_id="front-crossed",
        pack_id="pack",
        asset_path="assets/garment.png",
    )


def test_incompatible_runtime_range_is_rejected() -> None:
    assert ActiveOutfitOverlay._compatible(">=4.0.0,<5.0.0")
    assert not ActiveOutfitOverlay._compatible(">=5.0.0,<6.0.0")
    assert not ActiveOutfitOverlay._compatible("any")


def test_dev_app_version_tolerates_range_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local development version must preserve available outfit rendering.

    The old int() conversion preceded the guard; a development version raised
    ValueError into apply() and cleared every layer. Own development versions
    are tolerated; malformed pack ranges still close the acceptance gate.
    """

    monkeypatch.setattr(adapter_module, "APP_VERSION", "4.6.dev0")
    assert ActiveOutfitOverlay._compatible(">=4.0.0,<5.0.0")
    assert not ActiveOutfitOverlay._compatible("any")
    monkeypatch.setattr(adapter_module, "APP_VERSION", "4.6")
    assert ActiveOutfitOverlay._compatible(">=99.0.0,<100.0.0")
    monkeypatch.setattr(adapter_module, "APP_VERSION", "5.0.0-rc.1")
    assert ActiveOutfitOverlay._compatible(">=4.0.0,<5.0.0")


def test_missing_optional_category_in_active_state_is_transparent_builtin(
    tmp_path: Path,
) -> None:
    # In a stripped build with the official packs absent, an unlisted slot uses the bare base.
    store = tmp_path / "store"
    store.mkdir()
    (store / "active.json").write_text(
        json.dumps(
            {
                "garment": {
                    "pack_id": "builtin",
                    "item_id": "builtin",
                    "variant_id": "builtin",
                }
            }
        ),
        encoding="utf-8",
    )
    official = tmp_path / "official"
    assert resolve_active_selection(
        store, "headwear", official_pack_root=official,
    ).status == "builtin"
    assert resolve_active_selection(
        store, "jewelry", official_pack_root=official,
    ).status == "builtin"


def test_hair_is_clipped_only_out_of_the_feature_core_not_the_face_box(
    tmp_path: Path,
) -> None:
    """Hair falls over the brow and cheeks; only the eye/mouth core is off limits.

    Garments keep the full protected-face rule, so the same cheek pixel stays
    forbidden for them.
    """
    _app()
    _authority(tmp_path)
    adapter = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    item = SimpleNamespace(safe_mask=None)
    variant = SimpleNamespace(
        face_masks=frozendict({"front-crossed": "bangs-safe"})
    )
    forbidden = adapter._forbidden_face_region(
        "hairstyle",
        item,
        variant,
        "front-crossed",
    )
    assert not forbidden.contains(QPoint(600, 120))
    assert forbidden.contains(QPoint(600, 250))
    assert not forbidden.contains(QPoint(600, 400))
    garment_forbidden = adapter._forbidden_face_region("garment", item, variant, "front-crossed")
    assert garment_forbidden.contains(QPoint(600, 250))
    assert garment_forbidden.contains(QPoint(600, 400))


def test_back_hair_keeps_authored_alpha_outside_exact_feature_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Back hair retains its own clipping boundary around the mouth."""
    _app()
    _authority(tmp_path)
    encoded = _encoded_layer(QColor(20, 20, 20, 255))
    archive_path = tmp_path / "hair.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/back.png", encoded)
        archive.writestr("assets/front.png", encoded)

    def declaration(path: str, slot: str, z_order: int) -> AppearanceAsset:
        return AppearanceAsset(
            slot,
            path,
            hashlib.sha256(encoded).hexdigest(),
            96,
            96,
            20,
            500,
            z_order,
        )

    adapter = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    feathered_slots: list[str] = []

    def record_feather(pixmap, anchor_x, anchor_y, view_id):
        feathered_slots.append(view_id)
        return pixmap

    monkeypatch.setattr(adapter, "_feathered_hair_layer", record_feather)
    item = SimpleNamespace(safe_mask=None)
    variant = SimpleNamespace(face_masks=None, hand_rules=None)
    with zipfile.ZipFile(archive_path) as archive:
        layers = adapter._garment_layers(
            archive,
            (
                declaration("assets/back.png", "back", 0),
                declaration("assets/front.png", "front", 20),
            ),
            "hairstyle",
            item,
            variant,
            "front-crossed",
            (CANVAS, CANVAS),
        )

    assert len(layers) == len(("back", "front"))
    assert feathered_slots == ["front-crossed"]


def test_compositor_uses_each_layers_own_face_clip(tmp_path: Path) -> None:
    _app()
    _authority(tmp_path)
    adapter = ActiveOutfitOverlay(tmp_path / "store", tmp_path)
    layer = QPixmap(CANVAS, CANVAS)
    layer.fill(QColor(40, 30, 20, 255))
    forbidden = adapter._forbidden_face_region(
        "hairstyle",
        SimpleNamespace(safe_mask=None),
        SimpleNamespace(
            face_masks=frozendict({"front-crossed": "bangs-safe"})
        ),
        "front-crossed",
    )
    allowed = QRegion(QRect(0, 0, CANVAS, CANVAS)).subtracted(forbidden)
    adapter._layers_by_view[OutfitLayerCacheKey.combined("front-crossed")] = (
        (layer, 0, 0, allowed, 1.0),
    )
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = adapter.apply(frame, "front-crossed").toImage()
    assert result.pixelColor(600, 120) == QColor(40, 30, 20, 255)
    assert result.pixelColor(600, 250) == QColor(240, 240, 240, 255)
    # The cheek remains outside the hair clip.
    assert result.pixelColor(600, 400) == QColor(40, 30, 20, 255)


def test_every_layer_cache_writer_is_visible_to_layer_count(tmp_path: Path) -> None:
    _app()
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    layer = QPixmap(1, 1)
    layer.fill(QColor("white"))
    one_layer = ((layer, 0, 0, QRegion(), 1.0),)

    overlay._layers_by_view[OutfitLayerCacheKey.combined("simple")] = one_layer
    assert overlay.layer_count("simple") == 1

    suppressed = frozenset({"eyes"})
    overlay._layers_by_view_without_makeup_slots[
        OutfitLayerCacheKey.combined("combined", suppressed, "closed")
    ] = one_layer
    assert overlay.layer_count(
        "combined", suppress_makeup_slots=suppressed, eye_state="closed",
    ) == 1

    overlay._phase_layers_by_view[
        OutfitLayerCacheKey.for_phase("split", "appearance")
    ] = one_layer
    overlay._phase_layers_by_view[
        OutfitLayerCacheKey.for_phase("split", "makeup")
    ] = one_layer
    expected_count = len(one_layer) + len(one_layer)
    assert overlay.layer_count("split") == expected_count


@pytest.mark.parametrize(
    ("category", "identity", "view_id", "canvas", "expected_layers"),
    (
        ("hairstyle", ("mohan.official.blue-white-hanfu", "loose-hair", "ink-black"),
         "yaw+000-pitch+00", (1024, 1536), 0),
        ("hairstyle", ("mohan.official.blue-white-hanfu", "loose-hair", "ink-black"),
         "yaw+090-pitch+00", (1024, 1536), 0),
        ("headwear", ("mohan.official.blue-white-hanfu", "silver-hairpiece", "silver"),
         "yaw+090-pitch+00", (1024, 1536), 0),
        ("headwear", ("mohan.official.blue-white-hanfu", "silver-hairpiece", "silver"),
         "yaw+000-pitch+00", (1024, 1536), 1),
        ("hairstyle", ("user.pack", "loose-hair", "ink-black"),
         "yaw+090-pitch+00", (1024, 1536), 1),
        ("hairstyle", ("mohan.official.blue-white-hanfu", "loose-hair", "ink-black"),
         "front-crossed", (1254, 1254), 1),
    ),
)
def test_v5_native_alias_suppresses_only_old_full_body_overlays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    identity: tuple[str, str, str],
    view_id: str,
    canvas: tuple[int, int],
    expected_layers: int,
) -> None:
    _app()
    archive_path = tmp_path / "selection.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w"):
        pass
    selected = SelectionResolution(category, "installed", *identity, *identity)
    monkeypatch.setattr(
        adapter_module,
        "resolve_active_selection",
        lambda *_args, **_kwargs: selected,
    )
    monkeypatch.setattr(
        adapter_module, "resolve_variant_for_view",
        lambda *_args: SimpleNamespace(assets=(SimpleNamespace(
            slot="front" if category == "hairstyle" else "headwear",
            z_order=20,
            occludes_makeup=False,
        ),)),
    )
    adapter = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    monkeypatch.setattr(
        adapter, "_selected_variant",
        lambda *_args: (archive_path, object(), SimpleNamespace(hand_rules=None)),
    )
    pixmap = QPixmap(1, 1)
    pixmap.fill(QColor(20, 20, 20))
    monkeypatch.setattr(
        adapter, "_garment_layers",
        lambda _archive, declarations, *_args: (
            [(20, (pixmap, 0, 0, QRegion(), 1.0))] if declarations else []
        ),
    )

    layers = adapter._active_layers(view_id, canvas, categories=frozenset({category}))

    assert len(layers) == expected_layers


def test_official_legacy_ensemble_and_restore_use_v5_native_hair(tmp_path: Path) -> None:
    """Keep native V5 hair and the installed, independently switchable safe ornament."""
    _app()
    store = tmp_path / "outfits"
    root = Path(__file__).resolve().parents[1]
    overlay = ActiveOutfitOverlay(store, root, visible_hand_region=None)
    hair = frozenset({"hairstyle"})
    headwear = frozenset({"headwear"})

    apply_ensemble(store, "mohan.official.blue-white-hanfu", "blue-white-hanfu")
    assert resolve_active_selection(store, "hairstyle").effective_item_id == "loose-hair"
    assert len(overlay._active_layers("yaw+000-pitch+00", (1024, 1536), categories=hair)) == 0
    assert len(overlay._active_layers("yaw+090-pitch+00", (1024, 1536), categories=hair)) == 0
    assert len(overlay._active_layers("yaw+090-pitch+00", (1024, 1536), categories=headwear)) == 1
    assert len(overlay._active_layers("yaw+000-pitch+00", (1024, 1536), categories=headwear)) > 0

    restore_builtin_outfit(store)
    assert resolve_active_selection(store, "hairstyle").effective_item_id == "loose-hair"
    assert len(overlay._active_layers("yaw+000-pitch+00", (1024, 1536), categories=hair)) == 0
    assert len(overlay._active_layers("yaw+090-pitch+00", (1024, 1536), categories=headwear)) == 1


def test_official_plus090_renders_after_legacy_alias_suppression(tmp_path: Path) -> None:
    """The installed side outfit renders without the old hair/headwear collision."""
    _app()
    root = Path(__file__).resolve().parents[1]
    store = tmp_path / "outfits"
    apply_ensemble(store, "mohan.official.blue-white-hanfu", "blue-white-hanfu")
    overlay = ActiveOutfitOverlay(store, root, visible_hand_region=None)
    manifest = load_layered_full_body_assets(root / "assets/pose-atlas/v5-base-layered")
    renderer = LayeredFullBodyRenderer(manifest, outfit_overlay=overlay)
    motion = FaceMotionFrame(
        FacePose.FRONT, "idle_front", Viseme.CLOSED, MouthShape(), ExpressionShape(),
    )

    dressed = renderer.render_view("yaw+090-pitch+00", motion)

    assert not dressed.isNull()
    assert overlay.layer_count("yaw+090-pitch+00") > 0
    assert len(overlay._active_layers(
        "yaw+090-pitch+00", (1024, 1536), categories=frozenset({"garment"}),
    )) > 0


def test_garment_and_accessory_coexist_in_global_z_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    blue = _encoded_layer(QColor(20, 80, OUTFIT_BLUE, 255))
    red = _encoded_layer(QColor(ACCESSORY_RED, 30, 20, 255))
    packages = tmp_path / "store" / "packages"
    packages.mkdir(parents=True)
    archive_path = packages / "pack.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/garment.png", blue)
        archive.writestr("assets/jewelry.png", red)

    def declaration(path: str, payload: bytes, slot: str, z_order: int):
        return AppearanceAsset(
            slot,
            path,
            hashlib.sha256(payload).hexdigest(),
            96,
            96,
            20,
            500,
            z_order,
        )

    garment_variant = AppearanceVariant(
        "navy",
        frozendict(),
        frozendict({
            "front-crossed": (
                declaration("assets/garment.png", blue, "outerwear", 10),
            )
        }),
    )
    jewelry_variant = AppearanceVariant(
        "ruby",
        frozendict(),
        frozendict({
            "front-crossed": (
                declaration("assets/jewelry.png", red, "jewelry", 20),
            )
        }),
    )
    pack = OutfitPack(
        "pack",
        "1.0.0",
        ">=4.0.0,<5.0.0",
        frozendict(),
        "original",
        "artist",
        "MIT",
        "mohan-body-v2",
        (
            AppearanceItem("garment", "robe", frozendict(), (garment_variant,)),
            AppearanceItem("jewelry", "jewel", frozendict(), (jewelry_variant,)),
        ),
        (),
    )

    def selection(
        _store: Path, category: str, **_kwargs: object
    ) -> SimpleNamespace:
        identities = {
            "garment": ("robe", "navy"),
            "jewelry": ("jewel", "ruby"),
        }
        if category not in identities:
            return SimpleNamespace(status="builtin")
        item_id, variant_id = identities[category]
        return SimpleNamespace(
            status="installed",
            effective_pack_id="pack",
            effective_item_id=item_id,
            effective_variant_id=variant_id,
        )

    monkeypatch.setattr(adapter_module, "resolve_active_selection", selection)
    monkeypatch.setattr(adapter_module, "inspect_installed_outfit_pack", lambda _: pack)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path).apply(
        frame,
        "front-crossed",
    )
    assert result.toImage().pixelColor(40, 520).red() == ACCESSORY_RED


def test_transparent_compatibility_hair_does_not_hide_generated_garment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    _authority(tmp_path)
    garment = _encoded_layer()
    transparent = _encoded_transparent_layer()
    packages = tmp_path / "store" / "packages"
    packages.mkdir(parents=True)
    archive_path = packages / "cloud-pack.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/garment.png", garment)
        archive.writestr("assets/hair-back.png", transparent)
        archive.writestr("assets/hair-front.png", transparent)

    def asset(path: str, payload: bytes, slot: str, z_order: int):
        return AppearanceAsset(
            slot,
            path,
            hashlib.sha256(payload).hexdigest(),
            96,
            96,
            20,
            500,
            z_order,
        )

    garment_variant = AppearanceVariant(
        "generated",
        frozendict(),
        frozendict({
            "front-crossed": (
                asset("assets/garment.png", garment, "outerwear", 10),
            )
        }),
    )
    hair_variant = AppearanceVariant(
        "preserved",
        frozendict(),
        frozendict({
            "front-crossed": (
                asset("assets/hair-back.png", transparent, "back", -10),
                asset("assets/hair-front.png", transparent, "front", 20),
            )
        }),
        face_masks=frozendict({"front-crossed": "none"}),
    )
    pack = OutfitPack(
        "cloud-pack",
        "1.0.0",
        ">=4.0.0,<5.0.0",
        frozendict(),
        "original",
        "provider",
        "Project License",
        "mohan-body-v2",
        (
            AppearanceItem("garment", "look", frozendict(), (garment_variant,)),
            AppearanceItem("hairstyle", "hair", frozendict(), (hair_variant,)),
        ),
        (),
    )

    def selection(
        _store: Path, category: str, **_kwargs: object
    ) -> SimpleNamespace:
        if category == "garment":
            item_id, variant_id = "look", "generated"
        elif category == "hairstyle":
            item_id, variant_id = "hair", "preserved"
        else:
            return SimpleNamespace(status="builtin")
        return SimpleNamespace(
            status="installed",
            effective_pack_id="cloud-pack",
            effective_item_id=item_id,
            effective_variant_id=variant_id,
        )

    monkeypatch.setattr(adapter_module, "resolve_active_selection", selection)
    monkeypatch.setattr(adapter_module, "inspect_installed_outfit_pack", lambda _: pack)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path).apply(
        frame,
        "front-crossed",
    )
    assert result.toImage().pixelColor(40, 520).blue() == OUTFIT_BLUE


def test_stale_active_pack_restores_builtin_and_notifies_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #140 option 3: generation-1 packs are rejected with a visible reason."""
    _app()
    _authority(tmp_path)
    _configure(monkeypatch, tmp_path, _encoded_layer(), body_profile="mohan-body-v1")
    notices: list[str] = []
    overlay = ActiveOutfitOverlay(
        tmp_path / "store",
        tmp_path,
        on_stale_body_profile=lambda: notices.append("body-profile-outdated"),
    )
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    first = overlay.apply(frame, "front-crossed")
    second = overlay.apply(frame, "front-crossed")
    assert first.toImage() == frame.toImage()
    assert second.toImage() == frame.toImage()
    assert notices == ["body-profile-outdated"]
    active = json.loads((tmp_path / "store" / "active.json").read_text(encoding="utf-8"))
    assert {value["pack_id"] for value in active.values()} == {"builtin"}


@pytest.mark.parametrize("viseme", [None, "A"])
def test_empty_combined_cache_does_not_reuse_phase_layers(
    tmp_path: Path, viseme: str | None,
) -> None:
    app = _app()
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    view = "yaw+000-pitch+00"
    overlay._active_viseme = viseme
    layer = (QPixmap(), 0, 0, QRegion(), 1.0)
    phase_key = OutfitLayerCacheKey.for_phase(view, "appearance", active_viseme=viseme)
    overlay._phase_layers_by_view[phase_key] = (layer,)
    assert overlay.layer_count(view) == 1
    combined_key = OutfitLayerCacheKey.combined(view, active_viseme=viseme)
    if viseme is None:
        overlay._layers_by_view[combined_key] = ()
    else:
        overlay._layers_by_view_without_makeup_slots[combined_key] = ()
    assert overlay.layer_count(view) == 0
    assert app is not None


def test_generic_full_body_replacement_clears_native_hair_and_garment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    view = "yaw+000-pitch+00"
    overlay = ActiveOutfitOverlay(
        tmp_path / "store",
        tmp_path,
        visible_hand_region=lambda _view: QRegion(QRect(116, 1416, 4, 4)),
    )
    native_head = QRegion(QRect(10, 10, 12, 12))
    monkeypatch.setattr(
        overlay,
        "_native_head_region",
        lambda _view, _size: native_head,
    )
    monkeypatch.setattr(
        overlay,
        "_native_identity_region",
        lambda _view, _size: QRegion(),
    )
    monkeypatch.setattr(
        overlay,
        "_protected_face_region",
        lambda _view, _size: QRegion(QRect(108, 1408, 4, 4)),
    )
    selections = {
        "garment": SimpleNamespace(
            status="installed",
            effective_pack_id="candidate",
            effective_item_id="office",
            effective_variant_id="dark",
        ),
        "hairstyle": SimpleNamespace(
            status="installed",
            effective_pack_id="candidate",
            effective_item_id="long-hair",
            effective_variant_id="brown",
        ),
    }
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda category: selections[category],
    )
    encoded = _encoded_layer()
    declaration = AppearanceAsset(
        "garment-occluder",
        "assets/garment.png",
        hashlib.sha256(encoded).hexdigest(),
        1024,
        1536,
        0,
        0,
        10,
        clears_base=True,
    )
    variant = AppearanceVariant(
        "dark",
        frozendict(),
        frozendict({view: (declaration,)}),
    )
    archive_path = tmp_path / "candidate.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w"):
        pass
    monkeypatch.setattr(
        overlay,
        "_selected_variant",
        lambda _category, _selected: (archive_path, None, variant),
    )
    image = QImage(1024, 1536, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    for y in range(1400, 1421):
        for x in range(100, 121):
            image.setPixelColor(x, y, QColor(20, 20, 20, 255))
    monkeypatch.setattr(
        overlay,
        "_decoded_layer",
        lambda _archive, _asset: (encoded, image),
    )

    replacement, clears_garment = overlay._generic_replacement_region(
        view, (1024, 1536),
    )

    assert replacement is not None
    assert clears_garment is True
    assert replacement.contains(QPoint(10, 10))
    assert replacement.contains(QPoint(100, 1400))
    assert not replacement.contains(QPoint(109, 1409))
    assert not replacement.contains(QPoint(117, 1417))


def test_generic_half_body_replacement_uses_shared_rig_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    view = "front-crossed"
    overlay = ActiveOutfitOverlay(
        tmp_path / "store",
        tmp_path,
        visible_hand_region=lambda _view: QRegion(QRect(116, 116, 4, 4)),
    )
    monkeypatch.setattr(
        overlay,
        "_native_head_region",
        lambda _view, _size: QRegion(QRect(10, 10, 12, 12)),
    )
    monkeypatch.setattr(
        overlay,
        "_native_identity_region",
        lambda _view, _size: QRegion(),
    )
    monkeypatch.setattr(
        overlay,
        "_protected_face_region",
        lambda _view, _size: QRegion(QRect(108, 108, 4, 4)),
    )
    monkeypatch.setattr(
        overlay,
        "_active_hairstyle_region",
        lambda _view, _size, _hairstyle: QRegion(QRect(10, 10, 12, 12)),
    )
    selections = {
        "garment": SimpleNamespace(
            status="installed",
            effective_pack_id="candidate",
            effective_item_id="office",
            effective_variant_id="dark",
        ),
        "hairstyle": SimpleNamespace(
            status="installed",
            effective_pack_id="candidate",
            effective_item_id="long-hair",
            effective_variant_id="brown",
        ),
    }
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda category: selections[category],
    )
    encoded = _encoded_layer()
    declaration = AppearanceAsset(
        "garment-occluder",
        "assets/garment.png",
        hashlib.sha256(encoded).hexdigest(),
        1254,
        1254,
        0,
        0,
        10,
        clears_base=True,
    )
    variant = AppearanceVariant(
        "dark",
        frozendict(),
        frozendict({view: (declaration,)}),
    )
    archive_path = tmp_path / "candidate.mohan-outfit"
    with zipfile.ZipFile(archive_path, "w"):
        pass
    monkeypatch.setattr(
        overlay,
        "_selected_variant",
        lambda _category, _selected: (archive_path, None, variant),
    )
    image = QImage(1254, 1254, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    for y in range(100, 121):
        for x in range(100, 121):
            image.setPixelColor(x, y, QColor(20, 20, 20, 255))
    monkeypatch.setattr(
        overlay,
        "_decoded_layer",
        lambda _archive, _asset: (encoded, image),
    )

    replacement, clears_garment = overlay._generic_replacement_region(
        view, (1254, 1254),
    )

    assert replacement is not None
    assert clears_garment is True
    # Half-body soft-alpha hair must not retain the old hair beneath it.
    assert replacement.contains(QPoint(10, 10))
    assert replacement.contains(QPoint(100, 100))
    assert not replacement.contains(QPoint(109, 109))
    assert not replacement.contains(QPoint(117, 117))


def test_native_identity_skin_region_excludes_hair_and_white_cloth(
) -> None:
    _app()
    image = QImage(3, 1, QImage.Format_RGBA8888)
    image.setPixelColor(0, 0, QColor(198, 151, 126, 255))
    image.setPixelColor(1, 0, QColor(45, 31, 28, 255))
    image.setPixelColor(2, 0, QColor(240, 240, 238, 255))

    region = ActiveOutfitOverlay._skin_region(image)

    assert region.contains(QPoint(0, 0))
    assert not region.contains(QPoint(1, 0))
    assert not region.contains(QPoint(2, 0))


def test_optional_cheek_wrist_artifact_region_tracks_only_source_seam() -> None:
    region = ActiveOutfitOverlay._optional_cheek_wrist_artifact_region()

    assert region.contains(QPoint(587, 1140))
    assert region.contains(QPoint(611, 1217))
    assert not region.contains(QPoint(580, 1140))
    assert not region.contains(QPoint(611, 1130))


def test_half_body_native_head_clear_covers_layered_crown_gap(
    tmp_path: Path,
) -> None:
    _app()
    layered = tmp_path / "assets" / "expressions" / "layered"
    layered.mkdir(parents=True)
    for layer in base_clear_module.NATIVE_HEAD_LAYERS:
        image = QImage(1254, 1254, QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        if layer == "hair_back":
            image.setPixelColor(100, 100, QColor(20, 20, 20, 255))
        assert image.save(str(layered / f"front_{layer}.png"), "PNG")
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )

    region = overlay._native_head_region("front-crossed", (1254, 1254))

    assert region.contains(QPoint(60, 100))
    assert region.contains(QPoint(140, 100))
    assert not region.contains(QPoint(59, 100))


def test_gesture_native_head_and_identity_come_from_exact_source(
    tmp_path: Path,
) -> None:
    _app()
    frames = (
        tmp_path / "assets" / "expressions" / "complete-expressions" / "frames"
    )
    frames.mkdir(parents=True)
    source = QImage(1254, 1254, QImage.Format_RGBA8888)
    source.fill(Qt.transparent)
    source.setPixelColor(100, 100, QColor(20, 20, 20, 255))
    source.setPixelColor(110, 100, QColor(210, 214, 220, 255))
    source.setPixelColor(120, 100, QColor(35, 60, 145, 255))
    source.setPixelColor(130, 100, QColor(245, 245, 245, 255))
    source.setPixelColor(459, 442, QColor(210, 214, 220, 255))
    source.setPixelColor(600, 442, QColor(35, 25, 20, 255))
    source.setPixelColor(200, 100, QColor(198, 151, 126, 255))
    source.setPixelColor(200, 200, QColor(198, 151, 126, 255))
    assert source.save(
        str(frames / "front-eureka-neutral-rest.rgba.png"), "PNG",
    )
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )

    head = overlay._native_head_region("front-eureka", (1254, 1254))
    identity = overlay._native_identity_region("front-eureka", (1254, 1254))

    assert head.contains(QPoint(100, 100))
    assert head.contains(QPoint(110, 100))
    assert head.contains(QPoint(120, 100))
    assert head.contains(QPoint(130, 100))
    assert head.contains(QPoint(200, 100))
    assert not head.contains(QPoint(200, 200))
    assert not identity.contains(QPoint(200, 100))
    assert not identity.contains(QPoint(200, 200))
    assert head.contains(QPoint(459, 442))
    assert not identity.contains(QPoint(459, 442))
    assert identity.contains(QPoint(600, 442))


def test_tilted_gesture_identity_excludes_non_skin_contact_support(
    tmp_path: Path,
) -> None:
    _app()
    frames = (
        tmp_path / "assets" / "expressions" / "complete-expressions" / "frames"
    )
    frames.mkdir(parents=True)
    source = QImage(1254, 1254, QImage.Format_RGBA8888)
    source.fill(Qt.transparent)
    source.setPixelColor(400, 350, QColor(35, 30, 28, 255))
    source.setPixelColor(401, 350, QColor(35, 30, 28, 127))
    source.setPixelColor(900, 350, QColor(35, 30, 28, 255))
    source.setPixelColor(500, 500, QColor(198, 151, 126, 255))
    assert source.save(
        str(frames / "front-exasperated-neutral-rest.rgba.png"), "PNG",
    )
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )

    identity = overlay._native_identity_region(
        "front-exasperated", (1254, 1254),
    )

    assert not identity.contains(QPoint(400, 350))
    assert not identity.contains(QPoint(401, 350))
    assert not identity.contains(QPoint(900, 350))
    assert identity.contains(QPoint(500, 500))


def test_source_bound_hair_clear_preserves_native_hands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    hand = QRegion(QRect(110, 100, 10, 10))
    overlay = ActiveOutfitOverlay(
        tmp_path / "store",
        tmp_path,
        visible_hand_region=lambda _view: hand,
    )
    selected = SimpleNamespace(
        status="installed",
        effective_pack_id="custom",
        effective_item_id="straight-hair",
        effective_variant_id="brown",
    )
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda _category: selected,
    )
    monkeypatch.setattr(
        overlay,
        "_native_head_region",
        lambda _view, _size: QRegion(QRect(100, 100, 30, 10)),
    )
    monkeypatch.setattr(
        overlay,
        "_native_identity_region",
        lambda _view, _size: QRegion(),
    )
    monkeypatch.setattr(
        overlay,
        "_active_hairstyle_region",
        lambda _view, _size, _selection: QRegion(),
    )
    replacement, native_head = overlay._generic_hair_replacement_region(
        "front-eureka", (1254, 1254),
    )

    assert replacement.contains(QPoint(105, 105))
    assert not replacement.contains(QPoint(115, 105))
    assert replacement.contains(QPoint(125, 105))
    assert native_head.contains(QPoint(115, 105))


def test_native_identity_region_keeps_explicit_protected_forehead(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    layered = tmp_path / "assets" / "expressions" / "layered"
    layered.mkdir(parents=True)
    body = QImage(1254, 1254, QImage.Format_RGBA8888)
    body.fill(Qt.transparent)
    assert body.save(str(layered / "front_body.png"), "PNG")
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )
    monkeypatch.setattr(overlay, "_feature_region", lambda _view: QRegion())
    monkeypatch.setattr(
        overlay,
        "_protected_face_region",
        lambda _view, _size: QRegion(QRect(100, 100, 10, 10)),
    )
    monkeypatch.setattr(
        overlay,
        "_native_head_region",
        lambda _view, _size: QRegion(QRect(50, 50, 100, 100)),
    )

    identity = overlay._native_identity_region("front-crossed", (1254, 1254))

    assert identity.contains(QPoint(105, 105))


def test_generic_replacement_does_not_clear_regular_garment_or_native_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    view = "yaw+000-pitch+00"
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )
    monkeypatch.setattr(
        overlay,
        "_native_head_region",
        lambda _view, _size: QRegion(QRect(10, 10, 12, 12)),
    )
    selections = {
        "garment": SimpleNamespace(
            status="installed",
            effective_pack_id="candidate",
            effective_item_id="office",
            effective_variant_id="dark",
        ),
        "hairstyle": SimpleNamespace(
            status="installed",
            effective_pack_id="mohan.official.blue-white-hanfu",
            effective_item_id="loose-hair",
            effective_variant_id="ink-black",
        ),
    }
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda category: selections[category],
    )
    declaration = AppearanceAsset(
        "outerwear", "assets/garment.png", "0" * 64,
        1024, 1536, 0, 0, 10,
    )
    variant = AppearanceVariant(
        "dark", frozendict(), frozendict({view: (declaration,)}),
    )
    monkeypatch.setattr(
        overlay,
        "_selected_variant",
        lambda _category, _selected: (tmp_path / "unused.zip", None, variant),
    )

    replacement, clears_garment = overlay._generic_replacement_region(
        view, (1024, 1536),
    )

    assert replacement is None
    assert clears_garment is False


def test_source_bound_replacement_merges_custom_hair_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    view = "yaw+000-pitch+00"
    overlay = ActiveOutfitOverlay(
        tmp_path / "store", tmp_path, visible_hand_region=None,
    )
    manifest = tmp_path / base_clear_module.MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.touch()
    selected = SimpleNamespace(status="installed")
    monkeypatch.setattr(
        overlay,
        "_resolve_base_clear_selection",
        lambda _category: selected,
    )
    monkeypatch.setattr(
        overlay,
        "_selected_variant",
        lambda _category, _selected: (tmp_path / "pack.zip", None, None),
    )
    source_region = QRegion(QRect(100, 100, 5, 5))
    hair_region = QRegion(QRect(200, 200, 5, 5))
    hand_overlays = ((QPixmap(), 0, 0, QRegion(), 1.0),)
    monkeypatch.setattr(
        base_clear_module,
        "load_garment_binding",
        lambda *_args: base_clear_module.GarmentBinding(
            source_region, hand_overlays, QRegion(),
        ),
    )
    monkeypatch.setattr(
        base_clear_module,
        "validate_garment_removal",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        overlay,
        "_protected_face_region",
        lambda _view, _size: QRegion(),
    )
    monkeypatch.setattr(
        overlay,
        "_generic_replacement_region",
        lambda _view, _size: (hair_region, False),
    )

    silhouette, replacement, binding = overlay._base_clear_regions(
        view, (1024, 1536), True, True,
    )

    assert silhouette is None
    assert replacement is not None
    assert replacement.contains(QPoint(101, 101))
    assert replacement.contains(QPoint(201, 201))
    assert binding is not None
    assert binding.hand_overlays == hand_overlays
