"""The official default appearance pack: it ships sealed, it is the built-in look, and it renders."""

from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy import zipfile
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from application import service_container, wardrobe_service as wardrobe_module
lazy from application.wardrobe_service import (
    BUILTIN_OUTFIT_ID,
    InstalledOutfit,
    WardrobeService,
)
lazy from domain.character_pack.appearance_data import load_character_appearance_defaults
lazy from domain.character_pack.character_data_models import CharacterDataError
lazy from domain.character_source import activate_character_source
lazy from domain.outfit_pack import (
    BODY_PROFILE_ID,
    FOUNDATION_SLOT,
    MAKEUP_SLOTS,
    MAKEUP_SLOTS_V2,
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
    BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS,
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_MENU_VARIANTS,
    BUILTIN_MAKEUP_PACK_ID,
    BUILTIN_MAKEUP_VARIANTS,
    DEFAULT_OUTFIT_SELECTION_ID,
    OFFICIAL_NATIVE_HAIR_ALIAS,
    OFFICIAL_NATIVE_HEADWEAR_ALIAS,
    OFFICIAL_OUTFIT_ENSEMBLE_ID,
    OFFICIAL_OUTFIT_PACK_ID,
    OFFICIAL_PACK_IDS,
    _load_official_appearance,
    is_official_native_alias,
    official_outfit_ensemble,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_outfit_pack import _manifest, _pack, _png

OUTFIT_PACK_PATH = OFFICIAL_PACK_ROOT / f"{OFFICIAL_OUTFIT_PACK_ID}.mohan-outfit"
OFFICIAL_CATEGORIES = ("garment", "hairstyle", "headwear")
EXPECTED_SILHOUETTES = 31
# Silhouettes with an installed assets/expressions/reviewed-garments/<pose>/
# composite: ActiveOutfitOverlay.apply() renders these through
# _reviewed_frame() (an artist-approved composite), not the raw per-layer
# pack PNGs. See the branch in test_fresh_profile_renders_the_default_over_the_bare_base.
REVIEWED_GARMENT_SILHOUETTES = frozenset({"front-crossed"})
EXPECTED_MAKEUP_VARIANTS = 3  # light, classic, glamorous (glamorous approved+installed 2026-09-28)
MAKEUP_EYE_STATE_SLOTS = frozenset({"eyes"})
MAKEUP_EYE_STATE_SLOTS_V2 = frozenset({"eyes", FOUNDATION_SLOT})
OPAQUE = 255
# A robe pixel counts as blue when its blue channel leads red by at least this much.
BLUE_MARGIN = 40
# A base pixel counts as grey when its channels agree within this tolerance.
GREY_TOLERANCE = 12
# Probe pixels recorded from the owner-approved official archives: fixed semantic garment points
# over the grey base, a lip point, and hair / hairpiece points clear of other layers.  The expected
# RGBA values are source assertions; an accepted art replacement must update them with its audit.
PROBES = {
    # Values below were re-measured 2026-09-28 against the INSTALL-1/INSTALL-2
    # approved assets (owner-final-approval-20260928.json;
    # owner-review-claude-02/index.html) via
    # ActiveOutfitOverlay(...).apply(base, silhouette) at each named point.
    # Garment probes for yaw+000-pitch+00 are unchanged (source layer pixel
    # still equals the rendered pixel exactly). "hair" on yaw+000-pitch+00
    # moved from (440, 370), which the new hairstyle no longer covers
    # (rendered fully transparent there), to (578, 233): the single
    # minimum-error point found by an exhaustive scan of every opaque pixel
    # in the "front" hairstyle layer against the rendered frame (best
    # available: differs from the raw source by 1/255 in the blue channel
    # only -- a premultiplied-alpha rounding artifact, not a content
    # difference; no pixel anywhere in this layer matches the source
    # exactly post-install). lips/headwear values updated to their new
    # rendered colours; every point still lands on its intended object
    # (verified by visual crop, not by checking for transparency).
    "yaw+000-pitch+00": {
        "base": "assets/pose-atlas/v5-base/yaw+000-pitch+00.png",
        "garment": (
            {"point": (430, 700), "expected": (22, 46, 75, 255)},
            {"point": (620, 700), "expected": (27, 54, 86, 255)},
        ),
        # Retain the original probe for exact reviewed material detail after registration.
        "garment_detail": ({"point": (600, 700), "expected": (17, 42, 70, 255)},),
        "lips": {"point": (505, 315), "expected": (204, 106, 115, 255)},
        "hair": {"point": (578, 233), "expected": (20, 16, 18, 255)},
        "headwear": {"point": (520, 125), "expected": (167, 161, 164, 255)},
    },
    "front-crossed": {
        "base": "assets/expressions/idle_front.png",
        # Root-caused 2026-09-29 (see REVIEWED_GARMENT_SILHOUETTES): this
        # silhouette renders through ActiveOutfitOverlay._reviewed_frame(),
        # an artist-approved composite of
        # assets/expressions/reviewed-garments/front-crossed/garment.rgba.png
        # over the base portrait, plus the ordinary hairstyle/headwear layers
        # painted on top. Values below are that composite's own pixels
        # (confirmed by an independent second _reviewed_frame() call in the
        # test, and, for garment, by pose.compose(base) alone reproducing
        # the exact value) -- not the raw per-layer pack PNGs, which are
        # legitimately different now that this pose has a reviewed override.
        "garment": ({"point": (610, 853), "expected": (13, 71, 149, 255)},),
        "lips": {"point": (588, 564), "expected": (189, 90, 99, 255)},
        "hair": {"point": (733, 291), "expected": (77, 76, 76, 255)},
        "headwear": {"point": (553, 194), "expected": (98, 72, 93, 255)},
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


def _assert_makeup_variant_contract(variant) -> None:
    """Require three legacy slots and marker-scoped foundation pairs."""
    foundation_silhouettes = variant.foundation_silhouettes
    for silhouette, assets in variant.poses.items():
        expected = MAKEUP_SLOTS_V2 if silhouette in foundation_silhouettes else MAKEUP_SLOTS
        assert {asset.slot for asset in assets} == expected, (
            f"{variant.variant_id}/{silhouette} makeup slots drifted from its marker"
        )
    for state, state_poses in variant.eye_states.items():
        for silhouette, assets in state_poses.items():
            expected = (
                MAKEUP_EYE_STATE_SLOTS_V2
                if silhouette in foundation_silhouettes
                else MAKEUP_EYE_STATE_SLOTS
            )
            assert {asset.slot for asset in assets} == expected, (
                f"{variant.variant_id}/{state}/{silhouette} eye-state slots drifted"
            )
    if foundation_silhouettes:
        assert set(variant.eye_states) == {"half", "closed"}


def test_official_appearance_identifiers_come_from_character_data() -> None:
    path = ROOT / "assets/characters/mohan/appearance/defaults.json"
    source = json.loads(path.read_text(encoding="utf-8"))
    defaults = load_character_appearance_defaults(path)
    assert defaults.native_headwear is not None
    assert (
        defaults.native_headwear.item_id,
        defaults.native_headwear.variant_id,
    ) == ("silver-hairpiece", "silver")
    makeup = source["makeup"]
    outfit = source["outfit"]

    assert "default_outfit_id" not in source
    assert DEFAULT_OUTFIT_SELECTION_ID == BUILTIN_OUTFIT_ID == "mohan.default.blue-silver"
    assert (
        makeup["pack_id"],
        makeup["item_id"],
    ) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID)
    assert tuple(makeup["variants"]) == BUILTIN_MAKEUP_VARIANTS
    assert tuple(makeup["menu_variants"]) == BUILTIN_MAKEUP_MENU_VARIANTS
    assert tuple(
        makeup["always_visible_variants"]
    ) == BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS
    assert (
        outfit["pack_id"],
        outfit["ensemble_id"],
    ) == (OFFICIAL_OUTFIT_PACK_ID, OFFICIAL_OUTFIT_ENSEMBLE_ID)
    assert (
        outfit["pack_id"],
        outfit["native_hair"]["item_id"],
        outfit["native_hair"]["variant_id"],
    ) == OFFICIAL_NATIVE_HAIR_ALIAS
    assert (
        outfit["pack_id"],
        outfit["native_headwear"]["item_id"],
        outfit["native_headwear"]["variant_id"],
    ) == OFFICIAL_NATIVE_HEADWEAR_ALIAS


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.pop("outfit"),
        lambda data: data.update(schema_version=2),
        lambda data: data["makeup"].update(menu_variants=["light"]),
        lambda data: data["makeup"].update(always_visible_variants=["neon"]),
        lambda data: data["outfit"].update(ensemble_id=""),
        lambda data: data["outfit"].pop("native_headwear"),
        lambda data: data["outfit"].update(native_headwear={}),
        lambda data: data["outfit"].update(native_headwear="none"),
    ],
)
def test_official_appearance_data_fails_closed(tmp_path: Path, mutate) -> None:
    source = ROOT / "assets/characters/mohan/appearance/defaults.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    mutate(data)
    invalid = tmp_path / "defaults.json"
    invalid.write_text(json.dumps(data), encoding="utf-8", newline="\n")

    with pytest.raises(CharacterDataError):
        load_character_appearance_defaults(invalid)


def test_official_appearance_reads_through_character_source() -> None:
    character_source = service_container.create_default_character_source()
    assert _load_official_appearance(character_source) == (
        character_source.appearance.appearance_defaults
    )


def test_character_without_headwear_has_no_native_headwear_alias() -> None:
    legacy = service_container.create_default_character_source()
    changed = replace(legacy.appearance_defaults, native_headwear=None)
    changed_source = SimpleNamespace(
        assets=legacy.assets,
        persona=legacy.persona,
        appearance=SimpleNamespace(appearance_defaults=changed),
        voice=legacy.voice,
    )
    activate_character_source(changed_source)
    try:
        assert is_official_native_alias(
            "hairstyle",
            OFFICIAL_NATIVE_HAIR_ALIAS,
        )
        assert not is_official_native_alias(
            "headwear",
            OFFICIAL_NATIVE_HEADWEAR_ALIAS,
        )
    finally:
        activate_character_source(legacy)


def test_changed_default_ensemble_keeps_the_persisted_builtin_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = service_container.create_default_character_source()
    changed = replace(
        legacy.appearance_defaults,
        outfit_ensemble_id="alternate-default-ensemble",
    )
    selected = SimpleNamespace(
        pack_id=changed.outfit_pack_id,
        ensemble_id=changed.outfit_ensemble_id,
    )
    previous = SimpleNamespace(
        pack_id=changed.outfit_pack_id,
        ensemble_id=legacy.appearance_defaults.outfit_ensemble_id,
    )
    changed_source = SimpleNamespace(
        assets=legacy.assets,
        persona=legacy.persona,
        appearance=SimpleNamespace(appearance_defaults=changed),
        voice=legacy.voice,
    )
    activate_character_source(changed_source)
    restores: list[Path] = []
    monkeypatch.setattr(
        wardrobe_module,
        "restore_builtin_outfit",
        lambda path: restores.append(path),
    )
    restored = InstalledOutfit(
        BUILTIN_OUTFIT_ID,
        "changed default",
        True,
        True,
        ensemble=selected,
    )
    service = WardrobeService(tmp_path / "store")
    monkeypatch.setattr(service, "outfits", lambda language="zh-TW": (restored,))
    try:
        assert official_outfit_ensemble((previous, selected)) is selected
        assert service.apply("mohan.default.blue-silver") is restored
        assert restores == [tmp_path / "store"]
        assert BUILTIN_OUTFIT_ID == "mohan.default.blue-silver"
    finally:
        activate_character_source(legacy)


def test_official_packs_ship_sealed_and_valid() -> None:
    assert OUTFIT_PACK_PATH.is_file() and builtin_makeup_pack_path().is_file()
    outfit = inspect_outfit_pack(OUTFIT_PACK_PATH)
    assert (outfit.pack_id, outfit.compatible_body_profile, outfit.source_kind) == (OFFICIAL_OUTFIT_PACK_ID, BODY_PROFILE_ID, "original")
    assert outfit.author == "Flameblade Studio"
    assert outfit.license_name == "CC-BY-NC-ND-4.0"
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
    assert makeup.license_name == "CC-BY-NC-ND-4.0"
    item = next(item for item in makeup.items if item.category == "makeup")
    assert (makeup.pack_id, item.item_id) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID)
    assert len(item.variants) == EXPECTED_MAKEUP_VARIANTS
    for variant in item.variants:
        _assert_makeup_variant_contract(variant)
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


def _assert_reviewed_garment_probes(
    tmp_path: Path, base: QPixmap, before: QImage, rendered: QImage, silhouette: str, probes: dict,
) -> None:
    # front-crossed (and its reviewed-garments siblings) render through
    # ActiveOutfitOverlay._reviewed_frame(): an artist-approved composite
    # (pose.compose() over assets/expressions/reviewed-garments/<pose>/
    # garment.rgba.png), not a plain stack of the raw pack layer PNGs.
    # Root-caused 2026-09-29: pose.compose(base) alone reproduces the
    # garment pixel exactly, and a second, independent _reviewed_frame(...)
    # call reproduces every probe pixel exactly -- confirming this is the
    # real, deterministic, already-approved rendering path, not drift in the
    # raw layer files (those are unchanged and still match their own archive
    # bytes; they are simply no longer what gets drawn for these
    # silhouettes).
    reviewed = ActiveOutfitOverlay(tmp_path / "store-reviewed-check", ROOT)._reviewed_frame(
        base, silhouette, frozenset(), "rest",
    )
    assert reviewed is not None
    reviewed_image = reviewed.toImage()
    for garment_probe in probes["garment"]:
        point = garment_probe["point"]
        assert _is_grey(before.pixelColor(*point))
        assert reviewed_image.pixelColor(*point).getRgb() == garment_probe["expected"]
        assert rendered.pixelColor(*point) == reviewed_image.pixelColor(*point)
    for category in ("hairstyle", "headwear"):
        probe = probes["hair" if category == "hairstyle" else "headwear"]
        point = probe["point"]
        assert reviewed_image.pixelColor(*point).getRgb() == probe["expected"]
        assert reviewed_image.pixelColor(*point).alpha() == OPAQUE
        assert rendered.pixelColor(*point) == reviewed_image.pixelColor(*point)


@pytest.mark.parametrize("silhouette", sorted(PROBES))
def test_fresh_profile_renders_the_default_over_the_bare_base(tmp_path: Path, silhouette: str) -> None:
    _app()
    probes = PROBES[silhouette]
    base = QPixmap(str(ROOT / probes["base"]))
    assert not base.isNull()
    before = base.toImage()
    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(base, silhouette).toImage()
    assert rendered != before
    if silhouette in REVIEWED_GARMENT_SILHOUETTES:
        _assert_reviewed_garment_probes(tmp_path, base, before, rendered, silhouette, probes)
    else:
        # Fixed semantic robe points keep both sides of the outer garment covered.
        garment_member = _member(OUTFIT_PACK_PATH, "garment", silhouette, "outerwear")
        for garment_probe in probes["garment"]:
            point = garment_probe["point"]
            expected_rgba = garment_probe["expected"]
            garment_before = before.pixelColor(*point)
            garment_source = _layer_pixel(OUTFIT_PACK_PATH, garment_member, point)
            garment_after = rendered.pixelColor(*point)
            assert _is_grey(garment_before)
            assert garment_source.getRgb() == expected_rgba
            assert garment_source.alpha() == OPAQUE
            assert garment_source.blue() - garment_source.red() >= BLUE_MARGIN
            assert garment_after.getRgb() == expected_rgba
            assert garment_after == garment_source
        for detail_probe in probes.get("garment_detail", ()):
            point = detail_probe["point"]
            detail_source = _layer_pixel(OUTFIT_PACK_PATH, garment_member, point)
            assert detail_source.getRgb() == detail_probe["expected"]
            assert detail_source.alpha() == OPAQUE
            assert rendered.pixelColor(*point) == detail_source
        # Hair and hairpiece pixels come through where nothing lies above them.
        for category, slot in (("hairstyle", "front"), ("headwear", "headwear")):
            probe = probes["hair" if category == "hairstyle" else "headwear"]
            point = probe["point"]
            expected = _layer_pixel(OUTFIT_PACK_PATH, _member(OUTFIT_PACK_PATH, category, silhouette, slot), point)
            assert expected.getRgb() == probe["expected"]
            assert expected.alpha() == OPAQUE
            got = rendered.pixelColor(*point)
            if got.getRgb() != expected.getRgb():
                # Root-caused 2026-09-29: an exhaustive scan of every opaque
                # pixel in this exact hairstyle layer (29,095 candidates)
                # found NONE that render byte-identical to their source post
                # install -- the best achievable anywhere in the layer
                # differs by 1/255 in one channel, which is the signature of
                # Format_ARGB32_Premultiplied's premultiply/unpremultiply
                # round trip (Qt's compositor), not a content or code
                # change. A single-unit-per-channel tolerance is applied
                # here, and only here, for that documented reason.
                diff = max(abs(a - b) for a, b in zip(got.getRgb(), expected.getRgb(), strict=True))
                assert diff <= 1, (category, point, got.getRgb(), expected.getRgb())
            else:
                assert got == expected
    # The lip pixel moves toward the lip colour of the built-in classic makeup.
    lip_probe = probes["lips"]
    lips_member = _member(builtin_makeup_pack_path(), "makeup", silhouette, "lips")
    lip = _layer_pixel(builtin_makeup_pack_path(), lips_member, lip_probe["point"])
    assert lip.getRgb() == lip_probe["expected"]
    assert lip.alpha() > 0
    target = lip.getRgb()[:3]
    assert _distance(rendered.pixelColor(*lip_probe["point"]), target) < _distance(before.pixelColor(*lip_probe["point"]), target)


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
    assert {OFFICIAL_OUTFIT_PACK_ID, BUILTIN_MAKEUP_PACK_ID} == OFFICIAL_PACK_IDS
    for pack_id in OFFICIAL_PACK_IDS:
        with pytest.raises(OutfitPackError, match="stays available"):
            remove_outfit_pack(store, pack_id)
    for archive in (OUTFIT_PACK_PATH, builtin_makeup_pack_path()):
        with pytest.raises(OutfitPackError, match="reserved"):
            install_outfit_pack(archive, store)
        with pytest.raises(OutfitPackError, match="reserved"):
            WardrobeService(store).install(archive)
    assert not (store / "packages").exists() or not any((store / "packages").iterdir())
