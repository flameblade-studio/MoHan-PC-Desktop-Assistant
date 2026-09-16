from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect
lazy from PySide6.QtGui import QColor, QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure import active_outfit_overlay as adapter_module
lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    AppearanceAsset,
    AppearanceItem,
    AppearanceVariant,
    OutfitPack,
    SelectionResolution,
    resolve_active_selection,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack

CANVAS = 1254
OUTFIT_BLUE = 180
ACCESSORY_RED = 210
OPAQUE_ALPHA = 255


def _app() -> object:
    return QApplication.instance() or QApplication([])


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
    def selection(_store: Path, category: str) -> SimpleNamespace:
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
    official = adapter_module.OFFICIAL_OUTFIT_PACK_ID
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
        lambda _store, category: selections[category],
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
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "missing-official")
    monkeypatch.setattr(adapter_module, "resolve_active_selection", outfit_pack.resolve_active_selection)
    overlay = ActiveOutfitOverlay(store, tmp_path, visible_hand_region=None)
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
        lambda _store, category: selections[category],
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # In a stripped build with the official packs absent, an unlisted slot uses the bare base.
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")
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
    assert resolve_active_selection(store, "headwear").status == "builtin"
    assert resolve_active_selection(store, "jewelry").status == "builtin"


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
    adapter._layers_by_view["front-crossed"] = ((layer, 0, 0, allowed, 1.0),)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = adapter.apply(frame, "front-crossed").toImage()
    assert result.pixelColor(600, 120) == QColor(40, 30, 20, 255)
    assert result.pixelColor(600, 250) == QColor(240, 240, 240, 255)
    # The cheek remains outside the hair clip.
    assert result.pixelColor(600, 400) == QColor(40, 30, 20, 255)


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

    def selection(_store: Path, category: str) -> SimpleNamespace:
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

    def selection(_store: Path, category: str) -> SimpleNamespace:
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
