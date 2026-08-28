from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure import active_outfit_overlay as adapter_module
lazy from domain.outfit_pack import (
    AppearanceAsset,
    AppearanceItem,
    AppearanceVariant,
    OutfitPack,
    resolve_active_selection,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay

CANVAS = 1254
OUTFIT_BLUE = 180
ACCESSORY_RED = 210


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
        "mohan-body-v1",
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
    monkeypatch.setattr(adapter_module, "inspect_outfit_pack", lambda _: pack)


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
    """A non-semver local build must not silently disable every outfit.

    ``int()`` used to run before any guard, so a dev version raised ValueError
    into ``apply()``'s broad handler and every layer vanished without a trace.
    A malformed pack range still fails closed; only our own dev version is
    tolerated.
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


def test_bangs_mask_allows_only_upper_face_and_still_protects_eye_features(
    tmp_path: Path,
) -> None:
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
    assert forbidden.contains(QPoint(600, 400))


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
    adapter._layers_by_view["front-crossed"] = ((layer, 0, 0, forbidden),)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = adapter.apply(frame, "front-crossed").toImage()
    assert result.pixelColor(600, 120) == QColor(40, 30, 20, 255)
    assert result.pixelColor(600, 250) == QColor(240, 240, 240, 255)
    assert result.pixelColor(600, 400) == QColor(240, 240, 240, 255)


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
        "mohan-body-v1",
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
    monkeypatch.setattr(adapter_module, "inspect_outfit_pack", lambda _: pack)
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
        "mohan-body-v1",
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
    monkeypatch.setattr(adapter_module, "inspect_outfit_pack", lambda _: pack)
    frame = QPixmap(CANVAS, CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    result = ActiveOutfitOverlay(tmp_path / "store", tmp_path).apply(
        frame,
        "front-crossed",
    )
    assert result.toImage().pixelColor(40, 520).blue() == OUTFIT_BLUE
