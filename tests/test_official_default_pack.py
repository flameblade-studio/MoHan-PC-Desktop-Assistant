"""The official default appearance pack: it ships sealed, it is the built-in look, and it renders."""

from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from application.wardrobe_service import BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    OFFICIAL_PACK_ROOT,
    REQUIRED_SILHOUETTES,
    OutfitPackError,
    apply_ensemble,
    inspect_outfit_pack,
    install_outfit_pack,
    remove_outfit_pack,
    resolve_active_selection,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_makeup import builtin_makeup_pack_path, verify_makeup_layers
lazy from domain.outfit_pack_official import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_PACK_ID,
    OFFICIAL_OUTFIT_ENSEMBLE_ID,
    OFFICIAL_OUTFIT_PACK_ID,
    OFFICIAL_PACK_IDS,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_outfit_pack import _manifest, _pack, _png

OUTFIT_PACK_PATH = OFFICIAL_PACK_ROOT / f"{OFFICIAL_OUTFIT_PACK_ID}.mohan-outfit"
OFFICIAL_CATEGORIES = ("garment", "hairstyle", "headwear")
EXPECTED_SILHOUETTES = 31
EXPECTED_MAKEUP_VARIANTS = 2
MAKEUP_SLOTS_PER_SILHOUETTE = 3
OPAQUE = 255
# A robe pixel counts as blue when its blue channel leads red by at least this much.
BLUE_MARGIN = 40
# A base pixel counts as grey when its channels agree within this tolerance.
GREY_TOLERANCE = 12
# Probe pixels recorded by tools/assemble_official_default_pack.py: a fully opaque robe pixel over
# the grey base top, the strongest lip pixel, and hair / hairpiece pixels clear of other layers.
PROBES = {
    "yaw+000-pitch+00": {
        "base": "assets/pose-atlas/v5-base/yaw+000-pitch+00.png",
        "garment": (488, 585), "lips": (552, 292), "hair": (455, 350), "headwear": (482, 134),
    },
    "front-crossed": {
        "base": "assets/expressions/idle_front.png",
        "garment": (610, 853), "lips": (588, 564), "hair": (733, 291), "headwear": (553, 194),
    },
}


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _identity(resolution) -> tuple[str, str, str]:
    return (resolution.effective_pack_id, resolution.effective_item_id, resolution.effective_variant_id)


def _is_grey(color: QColor) -> bool:
    red, green, blue, _alpha = color.getRgb()
    return abs(red - green) <= GREY_TOLERANCE and abs(green - blue) <= GREY_TOLERANCE


def _distance(color: QColor, target: tuple[int, int, int]) -> int:
    return sum(abs(value - expected) for value, expected in zip(color.getRgb()[:3], target, strict=True))


def _layer_pixel(archive_path: Path, member: str, point: tuple[int, int]) -> QColor:
    with zipfile.ZipFile(archive_path) as archive:
        image = QImage.fromData(archive.read(member), "PNG")
    assert not image.isNull(), member
    return image.pixelColor(*point)


def _member(archive_path: Path, category: str, silhouette: str, slot: str) -> str:
    """The archive member the official pack declares for one category/silhouette/slot."""
    pack = inspect_outfit_pack(archive_path)
    item = next(item for item in pack.items if item.category == category)
    return next(asset.path for asset in item.variants[0].poses[silhouette] if asset.slot == slot)


def test_official_packs_ship_sealed_and_valid() -> None:
    assert OUTFIT_PACK_PATH.is_file() and builtin_makeup_pack_path().is_file()
    outfit = inspect_outfit_pack(OUTFIT_PACK_PATH)
    assert (outfit.pack_id, outfit.compatible_body_profile, outfit.source_kind) == (OFFICIAL_OUTFIT_PACK_ID, BODY_PROFILE_ID, "original")
    assert outfit.author == "Flameblade Studio"
    assert "ASSETS-LICENSE.md" in outfit.license_name
    assert ActiveOutfitOverlay._compatible(outfit.app_range)
    assert [ensemble.ensemble_id for ensemble in outfit.ensembles] == [OFFICIAL_OUTFIT_ENSEMBLE_ID]
    items = {item.category: item for item in outfit.items}
    assert tuple(items) == OFFICIAL_CATEGORIES
    for item in items.values():
        assert len(item.variants) == 1
        assert set(item.variants[0].poses) == set(REQUIRED_SILHOUETTES)
        assert len(item.variants[0].poses) == EXPECTED_SILHOUETTES
    assert {asset.slot for asset in items["hairstyle"].variants[0].poses["front-crossed"]} == {"back", "front"}
    assert (items["headwear"].attachment_point, items["headwear"].safe_mask) == ("crown", "crown-safe")
    selections = {selection.category: selection for selection in outfit.ensembles[0].selections}
    assert all(selections[category].item_id == items[category].item_id for category in OFFICIAL_CATEGORIES)
    makeup = inspect_outfit_pack(builtin_makeup_pack_path())
    item = next(item for item in makeup.items if item.category == "makeup")
    assert (makeup.pack_id, item.item_id) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID)
    assert len(item.variants) == EXPECTED_MAKEUP_VARIANTS
    assert all(
        len(assets) == MAKEUP_SLOTS_PER_SILHOUETTE
        for variant in item.variants
        for assets in variant.poses.values()
    )
    verify_makeup_layers(builtin_makeup_pack_path())


def test_fresh_profile_resolves_to_the_official_default(tmp_path: Path) -> None:
    store = tmp_path / "store"
    outfit = inspect_outfit_pack(OUTFIT_PACK_PATH)
    selections = {selection.category: selection for selection in outfit.ensembles[0].selections}
    for category in OFFICIAL_CATEGORIES:
        resolution = resolve_active_selection(store, category)
        assert resolution.status == "installed"
        assert (resolution.requested_pack_id, resolution.requested_item_id) == ("builtin", "builtin")
        assert _identity(resolution) == (OFFICIAL_OUTFIT_PACK_ID, selections[category].item_id, selections[category].variant_id)
    makeup = resolve_active_selection(store, "makeup")
    assert (makeup.status, _identity(makeup)) == ("installed", (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, "classic"))
    assert resolve_active_selection(store, "weapon").status == "builtin"


@pytest.mark.parametrize("silhouette", sorted(PROBES))
def test_fresh_profile_renders_the_default_over_the_bare_base(tmp_path: Path, silhouette: str) -> None:
    _app()
    probes = PROBES[silhouette]
    base = QPixmap(str(ROOT / probes["base"]))
    assert not base.isNull()
    before = base.toImage()
    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(base, silhouette).toImage()
    assert rendered != before
    # A robe-blue pixel where the bare base is grey.
    garment_before, garment_after = before.pixelColor(*probes["garment"]), rendered.pixelColor(*probes["garment"])
    assert _is_grey(garment_before)
    assert garment_after.blue() - garment_after.red() >= BLUE_MARGIN
    assert garment_after == _layer_pixel(OUTFIT_PACK_PATH, _member(OUTFIT_PACK_PATH, "garment", silhouette, "outerwear"), probes["garment"])
    # Hair and hairpiece pixels come through exactly where nothing lies above them.
    for category, slot in (("hairstyle", "front"), ("headwear", "headwear")):
        point = probes["hair" if category == "hairstyle" else "headwear"]
        expected = _layer_pixel(OUTFIT_PACK_PATH, _member(OUTFIT_PACK_PATH, category, silhouette, slot), point)
        assert expected.alpha() == OPAQUE
        assert rendered.pixelColor(*point) == expected
    # The lip pixel moves toward the lip colour of the built-in classic makeup.
    lips_member = _member(builtin_makeup_pack_path(), "makeup", silhouette, "lips")
    lip = _layer_pixel(builtin_makeup_pack_path(), lips_member, probes["lips"])
    assert lip.alpha() > 0
    target = lip.getRgb()[:3]
    assert _distance(rendered.pixelColor(*probes["lips"]), target) < _distance(before.pixelColor(*probes["lips"]), target)


def test_restore_builtin_returns_to_the_official_pack(tmp_path: Path) -> None:
    store = tmp_path / "store"
    manifest, assets = _manifest(_png())
    service = WardrobeService(store)
    service.install(_pack(tmp_path / "modern.mohan-outfit", manifest, assets))
    apply_ensemble(store, "modern-collection", "city-day")
    assert resolve_active_selection(store, "garment").effective_pack_id == "modern-collection"
    restored = service.apply(BUILTIN_OUTFIT_ID)
    assert (restored.outfit_id, restored.built_in) == (BUILTIN_OUTFIT_ID, True)
    assert restored.display_name == "藍白漢服"
    assert restored.ensemble is not None and restored.ensemble.pack_id == OFFICIAL_OUTFIT_PACK_ID
    for category in OFFICIAL_CATEGORIES:
        assert resolve_active_selection(store, category).effective_pack_id == OFFICIAL_OUTFIT_PACK_ID
    assert _identity(resolve_active_selection(store, "makeup"))[2] == "classic"
    restore_builtin_outfit(store)
    assert set(json.loads((store / "active.json").read_text(encoding="utf-8"))) >= set(OFFICIAL_CATEGORIES)
    listed = service.outfits("en")
    assert [outfit.outfit_id for outfit in listed if outfit.built_in] == [BUILTIN_OUTFIT_ID]
    assert listed[0].display_name == "Blue-and-White Hanfu"
    assert all(not outfit.outfit_id.startswith(OFFICIAL_OUTFIT_PACK_ID) for outfit in listed)
    candidates = [candidate.outfit_id for candidate in service.autonomous_candidates()]
    assert candidates.count(BUILTIN_OUTFIT_ID) == 1
    assert all(not candidate.startswith(OFFICIAL_OUTFIT_PACK_ID) for candidate in candidates)


def test_official_packs_cannot_be_removed_or_shadowed(tmp_path: Path) -> None:
    store = tmp_path / "store"
    assert OFFICIAL_PACK_IDS == {OFFICIAL_OUTFIT_PACK_ID, BUILTIN_MAKEUP_PACK_ID}
    for pack_id in OFFICIAL_PACK_IDS:
        with pytest.raises(OutfitPackError, match="cannot be removed"):
            remove_outfit_pack(store, pack_id)
    for archive in (OUTFIT_PACK_PATH, builtin_makeup_pack_path()):
        with pytest.raises(OutfitPackError, match="reserved"):
            install_outfit_pack(archive, store)
        with pytest.raises(OutfitPackError, match="reserved"):
            WardrobeService(store).install(archive)
    assert not (store / "packages").exists() or not any((store / "packages").iterdir())
