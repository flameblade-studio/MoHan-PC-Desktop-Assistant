"""Makeup slot of the appearance-pack format: schema, safe-region gate, built-in default, state."""

from __future__ import annotations

lazy import copy
lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import sys
lazy import zipfile
lazy from dataclasses import replace
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice
lazy from PySide6.QtGui import QColor, QImage

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from application.wardrobe_service import WardrobeService
lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_PACK_ID,
    MAKEUP_CANVASES,
    POSE_ATLAS_SILHOUETTES,
    REQUIRED_SILHOUETTES,
    SELECTION_CATEGORIES,
    OutfitPackError,
    apply_appearance_selection,
    clear_appearance_selection,
    inspect_outfit_pack,
    install_outfit_pack,
    list_installed_selections,
    remove_outfit_pack,
    resolve_active_selection,
    restore_builtin_outfit,
)
lazy from domain.outfit_pack_makeup import (
    SAFE_REGION_PATH,
    load_makeup_safe_regions,
    read_makeup_intensity,
    select_builtin_makeup,
    verify_makeup_layers,
    write_makeup_intensity,
)
lazy from test_outfit_pack import _manifest, _names, _pack, _png
lazy from tools.build_makeup_safe_regions import silhouette_regions
lazy from tools.assemble_official_default_pack import makeup_authoring_mode, makeup_layer_paths
lazy from tools.scaffold_makeup_pack_manifest import main as scaffold_main

SLOT_Z = {"cheeks": 0, "eyes": 1, "lips": 2}
RED = QColor(220, 30, 40, 255)
BLOCK = 4
BUILTIN_VARIANTS = ("classic", "light")
EXPECTED_VARIANTS = 2
EXPECTED_SILHOUETTES = 31
HALF = 0.5
BUILTIN_SCAFFOLD_ARGS = (
    "--pack-id", BUILTIN_MAKEUP_PACK_ID,
    "--pack-name", "墨寒內建妝容|墨寒内置妆容|MoHan built-in makeup|墨寒内蔵メイク",
    "--item-id", BUILTIN_MAKEUP_ITEM_ID,
    "--item-name", "墨寒妝容|墨寒妆容|MoHan face makeup|墨寒メイク",
    "--variant", "classic:原妝|原妆|Classic|基本メイク",
    "--variant", "light:淡雅|淡雅|Light|淡めメイク",
    "--license", "All Rights Reserved - see ASSETS-LICENSE.md",
)

Block = tuple[int, int, int, int]


@pytest.fixture(autouse=True)
def _pending_official_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test before the official packs ship; ``official_builtin_pack`` opts back in."""
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")


def canvas_for(silhouette: str) -> tuple[int, int]:
    return MAKEUP_CANVASES["full-body" if silhouette in POSE_ATLAS_SILHOUETTES else "half-body"]


def _declared_makeup_assets(manifest: dict) -> tuple[tuple[str, dict], ...]:
    entries: list[tuple[str, dict]] = []
    for item in manifest["makeup"]:
        for variant in item["variants"]:
            for silhouette, assets in variant.get("poses", {}).items():
                entries.extend((silhouette, asset) for asset in assets)
            for state_poses in variant.get("eye_states", {}).values():
                for silhouette, assets in state_poses.items():
                    entries.extend((silhouette, asset) for asset in assets)
    return tuple(entries)


def _write_blank_makeup_assets(manifest: dict, root: Path) -> None:
    blank = {size: layer_png(size) for size in MAKEUP_CANVASES.values()}
    for silhouette, entry in _declared_makeup_assets(manifest):
        target = root / Path(*entry["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blank[canvas_for(silhouette)])


def _copy_committed_makeup_manifest(root: Path) -> tuple[Path, dict]:
    source = ROOT / "assets" / "makeup" / "builtin" / "manifest.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    target_root = root / "committed-authoring"
    target_root.mkdir(parents=True, exist_ok=True)
    _write_blank_makeup_assets(manifest, target_root)
    manifest_path = target_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path, manifest


def layer_png(size: tuple[int, int], blocks: tuple[Block, ...] = (), color: QColor = RED) -> bytes:
    image = QImage(size[0], size[1], QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for x, y, width, height in blocks:
        for row in range(y, y + height):
            for column in range(x, x + width):
                image.setPixelColor(column, row, color)
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _entry(path: str, data: bytes, slot: str, size: tuple[int, int], anchor: tuple[int, int] = (0, 0)) -> dict:
    return {
        "slot": slot, "path": path, "sha256": hashlib.sha256(data).hexdigest(),
        "width": size[0], "height": size[1], "anchor": list(anchor), "z_order": SLOT_Z[slot],
    }


def makeup_manifest(
    pack_id: str = "festival-makeup",
    item_id: str = "festival",
    variants: tuple[str, ...] = ("classic",),
    blocks: dict[tuple[str, str, str], tuple[Block, ...]] | None = None,
    intensity: dict[str, float] | None = None,
) -> tuple[dict, dict[str, bytes]]:
    """A makeup-only pack: every variant carries the three full-canvas layers for all 31 silhouettes."""
    blank = {size: layer_png(size) for size in MAKEUP_CANVASES.values()}
    assets: dict[str, bytes] = {}
    parsed_variants = []
    for variant_id in variants:
        poses = {}
        for silhouette in REQUIRED_SILHOUETTES:
            size = canvas_for(silhouette)
            entries = []
            for slot in ("cheeks", "eyes", "lips"):
                path = f"assets/{item_id}-{variant_id}-{silhouette}-{slot}.png"
                painted = (blocks or {}).get((variant_id, silhouette, slot))
                data = layer_png(size, painted) if painted else blank[size]
                assets[path] = data
                entries.append(_entry(path, data, slot, size))
            poses[silhouette] = entries
        variant = {"id": variant_id, "display_names": _names(variant_id), "poses": poses}
        if intensity and variant_id in intensity:
            variant["intensity"] = intensity[variant_id]
        parsed_variants.append(variant)
    manifest = {
        "format": "mohan-outfit-pack", "version": 2, "id": pack_id,
        "pack_version": "1.0.0", "app_range": ">=4.0.0,<5.0.0",
        "display_names": _names(pack_id),
        "compatible_body_profile": {"id": "mohan-body-v2", "version": 2},
        "source": {"kind": "original", "author": "Example Artist", "license": "MIT", "reference_included": False},
        "authoring": {"template": "mohan-official-poses", "version": 2},
        "looks": [], "hairstyles": [], "headwear": [],
        "makeup": [{"id": item_id, "display_names": _names(item_id), "variants": parsed_variants}],
        "accessories": [], "ensembles": [],
    }
    return manifest, assets


def makeup_pack(path: Path, **options) -> Path:
    manifest, assets = makeup_manifest(**options)
    path.parent.mkdir(parents=True, exist_ok=True)
    return _pack(path, manifest, assets)


def official_builtin_pack(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stand in for the studio-authored built-in pack at the official (non-removable) root."""
    official = root / "official"
    makeup_pack(
        official / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit",
        pack_id=BUILTIN_MAKEUP_PACK_ID,
        item_id=BUILTIN_MAKEUP_ITEM_ID,
        variants=BUILTIN_VARIANTS,
    )
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", official)
    return official


def _identity(resolution) -> tuple[str, str, str]:
    return (resolution.effective_pack_id, resolution.effective_item_id, resolution.effective_variant_id)


def test_makeup_pack_parses_two_variants_and_lists_them(tmp_path: Path) -> None:
    assert "makeup" in SELECTION_CATEGORIES
    pack_path = makeup_pack(
        tmp_path / "festival-makeup.mohan-outfit",
        variants=("classic", "light"),
        intensity={"light": 0.6},
    )
    pack = inspect_outfit_pack(pack_path)
    items = [item for item in pack.items if item.category == "makeup"]
    assert [item.item_id for item in items] == ["festival"]
    variants = {variant.variant_id: variant for variant in items[0].variants}
    assert set(variants) == {"classic", "light"}
    assert variants["classic"].intensity == 1.0
    assert variants["light"].intensity == pytest.approx(0.6)
    assert set(variants["classic"].poses) == set(REQUIRED_SILHOUETTES)
    assert {asset.slot for asset in variants["classic"].poses["front-crossed"]} == {"eyes", "cheeks", "lips"}
    store = tmp_path / "store"
    install_outfit_pack(pack_path, store)
    installed = list_installed_selections(store, "makeup")
    assert {(item.item_id, item.variant_id) for item in installed} == {("festival", "classic"), ("festival", "light")}


def test_candidate_makeup_pack_accepts_glamorous_variant(tmp_path: Path) -> None:
    """A candidate archive may carry the fourth look without formal built-in art."""
    pack_path = makeup_pack(
        tmp_path / "four-look-candidate.mohan-outfit",
        pack_id="four-look-candidate",
        item_id="mohan-look",
        variants=("classic", "light", "glamorous"),
    )
    pack = inspect_outfit_pack(pack_path)
    item = next(item for item in pack.items if item.category == "makeup")
    assert [variant.variant_id for variant in item.variants] == [
        "classic", "light", "glamorous",
    ]

    store = tmp_path / "store"
    service = WardrobeService(store)
    service.install(pack_path)
    assert {
        (selection.item_id, selection.variant_id)
        for selection in list_installed_selections(store, "makeup")
    } == {
        ("mohan-look", "classic"),
        ("mohan-look", "light"),
        ("mohan-look", "glamorous"),
    }
    service.apply_makeup("four-look-candidate/mohan-look/glamorous")
    assert service.active_makeup().option_id == "four-look-candidate/mohan-look/glamorous"


def test_packs_without_makeup_stay_valid_and_ensembles_may_omit_or_null_makeup(tmp_path: Path) -> None:
    manifest, assets = _manifest(_png())
    assert "makeup" not in manifest
    assert inspect_outfit_pack(_pack(tmp_path / "plain.mohan-outfit", manifest, assets)).ensembles
    nulled = copy.deepcopy(manifest)
    nulled["ensembles"][0]["selections"]["makeup"] = None
    assert inspect_outfit_pack(_pack(tmp_path / "nulled.mohan-outfit", nulled, assets)).ensembles
    combined, makeup_assets = makeup_manifest(pack_id="modern-collection")
    combined.update({key: manifest[key] for key in ("looks", "hairstyles", "headwear", "accessories", "ensembles")})
    combined["ensembles"] = copy.deepcopy(manifest["ensembles"])
    combined["ensembles"][0]["selections"]["makeup"] = {"item_id": "festival", "variant_id": "classic"}
    pack = inspect_outfit_pack(_pack(tmp_path / "combined.mohan-outfit", combined, {**assets, **makeup_assets}))
    selections = {selection.category: selection for selection in pack.ensembles[0].selections}
    assert selections["makeup"].item_id == "festival"
    foreign = copy.deepcopy(combined)
    foreign["ensembles"][0]["selections"]["makeup"] = {"item_id": "missing", "variant_id": "classic"}
    with pytest.raises(OutfitPackError):
        inspect_outfit_pack(_pack(tmp_path / "foreign.mohan-outfit", foreign, {**assets, **makeup_assets}))


def _mutations() -> dict[str, tuple]:
    def missing_lips(manifest, assets):
        for entries in manifest["makeup"][0]["variants"][0]["poses"].values():
            entries[:] = [entry for entry in entries if entry["slot"] != "lips"]
        return "exactly the eyes, cheeks and lips"

    def wrong_canvas(manifest, assets):
        entry = manifest["makeup"][0]["variants"][0]["poses"]["front-crossed"][0]
        fake = _png()
        assets[entry["path"]] = fake
        entry.update(_entry(entry["path"], fake, entry["slot"], (512, 768)))
        return "full 1254x1254 canvas"

    def shifted_anchor(manifest, assets):
        manifest["makeup"][0]["variants"][0]["poses"]["yaw+000-pitch+00"][1]["anchor"] = [1, 0]
        return "anchor 0,0"

    def hot_intensity(manifest, assets):
        manifest["makeup"][0]["variants"][0]["intensity"] = 1.5
        return "intensity"

    def boolean_intensity(manifest, assets):
        manifest["makeup"][0]["variants"][0]["intensity"] = True
        return "intensity"

    def missing_silhouette(manifest, assets):
        poses = manifest["makeup"][0]["variants"][0]["poses"]
        for entry in poses.pop("front-eureka"):
            assets.pop(entry["path"])
        return "complete v2 view set"

    def duplicate_variant(manifest, assets):
        variants = manifest["makeup"][0]["variants"]
        variants.append(copy.deepcopy(variants[0]))
        return "Duplicate variant"

    def unknown_slot(manifest, assets):
        manifest["makeup"][0]["variants"][0]["poses"]["cheek-rest"][0]["slot"] = "brows"
        return "recognized slot or asset path"

    return {
        function.__name__: (function,)
        for function in (
            missing_lips, wrong_canvas, shifted_anchor, hot_intensity, boolean_intensity,
            missing_silhouette, duplicate_variant, unknown_slot,
        )
    }


@pytest.mark.parametrize("mutation", list(_mutations()))
def test_invalid_makeup_declarations_are_rejected(tmp_path: Path, mutation: str) -> None:
    manifest, assets = makeup_manifest()
    (mutate,) = _mutations()[mutation]
    expected = mutate(manifest, assets)
    with pytest.raises(OutfitPackError, match=expected):
        inspect_outfit_pack(_pack(tmp_path / f"{mutation}.mohan-outfit", manifest, assets))


def test_pixel_gate_blocks_layers_outside_the_safe_region(tmp_path: Path) -> None:
    regions = load_makeup_safe_regions()
    x, y, width, height = regions["front-crossed"].rects("lips")[0]
    inside = (x + width // 2, y + height // 2, BLOCK, BLOCK)
    good = makeup_pack(
        tmp_path / "good.mohan-outfit",
        pack_id="good-makeup",
        blocks={("classic", "front-crossed", "lips"): (inside,)},
    )
    verify_makeup_layers(good)
    store = tmp_path / "store"
    assert WardrobeService(store).install(good).pack_id == "good-makeup"
    cases = {
        "front-crossed": {("classic", "front-crossed", "lips"): ((8, 8, BLOCK, BLOCK),)},
        "yaw-180-pitch+00": {("classic", "yaw-180-pitch+00", "eyes"): ((500, 240, BLOCK, BLOCK),)},
    }
    for silhouette, blocks in cases.items():
        bad = makeup_pack(tmp_path / f"bad-{silhouette}.mohan-outfit", pack_id="bad-makeup", blocks=blocks)
        with pytest.raises(OutfitPackError, match=re.escape(silhouette)):
            verify_makeup_layers(bad)
        with pytest.raises(OutfitPackError):
            WardrobeService(store).install(bad)
        assert not (store / "packages" / "bad-makeup.mohan-outfit").exists()


def test_safe_region_document_matches_the_rigs() -> None:
    document = json.loads(SAFE_REGION_PATH.read_text(encoding="utf-8"))
    regions = load_makeup_safe_regions()
    assert set(regions) == set(REQUIRED_SILHOUETTES)
    for silhouette, region in regions.items():
        assert region.canvas == canvas_for(silhouette)
        for slot in ("eyes", "cheeks", "lips"):
            for x, y, width, height in region.rects(slot):
                assert 0 <= x and 0 <= y and x + width <= region.canvas[0] and y + height <= region.canvas[1]
    front = regions["front-crossed"]
    assert all(front.rects(slot) for slot in ("eyes", "cheeks", "lips"))
    for gesture in ("front-mock-scold", "front-mock-hit", "front-eureka", "front-exasperated"):
        assert regions[gesture].slots == front.slots
    assert all(not regions["yaw-180-pitch+00"].rects(slot) for slot in ("eyes", "cheeks", "lips"))
    for silhouette in ("front-crossed", "yaw+000-pitch+00"):
        # The rig generator owns geometry; load_makeup_safe_regions above also
        # validates authored v2 foundation/aperture declarations and their files.
        derived = silhouette_regions(ROOT, silhouette)
        authored = document["silhouettes"][silhouette]
        assert derived == {key: authored[key] for key in derived}
        assert set(authored) - set(derived) <= {"foundation_masks", "eye_aperture_masks"}


def test_fresh_profile_defaults_to_builtin_classic_and_bare_is_selectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    bare = resolve_active_selection(store, "makeup")
    assert bare.status == "builtin"  # official art absent: the default renders a bare face
    official_builtin_pack(tmp_path, monkeypatch)
    resolution = resolve_active_selection(store, "makeup")
    assert resolution.status == "installed"
    assert _identity(resolution) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, "classic")
    assert (resolution.requested_pack_id, resolution.requested_item_id) == ("builtin", "builtin")
    select_builtin_makeup(store, "light")
    assert _identity(resolve_active_selection(store, "makeup"))[2] == "light"
    with pytest.raises(OutfitPackError):
        select_builtin_makeup(store, "glitter")
    clear_appearance_selection(store, "makeup")
    cleared = resolve_active_selection(store, "makeup")
    assert cleared.status == "builtin"
    assert _identity(cleared) == ("builtin", "none", "none")
    restore_builtin_outfit(store)
    assert _identity(resolve_active_selection(store, "makeup"))[2] == "classic"
    with pytest.raises(OutfitPackError):
        install_outfit_pack(tmp_path / "official" / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit", store)


def test_removed_makeup_pack_falls_back_to_builtin_classic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    official_builtin_pack(tmp_path, monkeypatch)
    store = tmp_path / "store"
    service = WardrobeService(store)
    service.install(makeup_pack(tmp_path / "festival-makeup.mohan-outfit"))
    festival = next(item for item in list_installed_selections(store, "makeup") if item.pack_id == "festival-makeup")
    apply_appearance_selection(store, festival)
    assert _identity(resolve_active_selection(store, "makeup")) == ("festival-makeup", "festival", "classic")
    with pytest.raises(OutfitPackError, match="switched"):
        remove_outfit_pack(store, "festival-makeup")
    (store / "packages" / "festival-makeup.mohan-outfit").unlink()
    fallback = resolve_active_selection(store, "makeup")
    assert _identity(fallback) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, "classic")
    assert fallback.requested_pack_id == "festival-makeup"
    state = service.active_makeup()
    assert (state.option_id, state.requested_option_id, state.fallback) == (
        "builtin/classic", "festival-makeup/festival/classic", True,
    )
    service.apply_makeup(state.option_id)
    assert service.active_makeup().fallback is False


def test_makeup_intensity_state_round_trips(tmp_path: Path) -> None:
    store = tmp_path / "store"
    assert read_makeup_intensity(store) == 1.0
    assert write_makeup_intensity(store, HALF) == HALF
    assert read_makeup_intensity(store) == HALF
    assert write_makeup_intensity(store, 1.7) == 1.0
    assert write_makeup_intensity(store, -3) == 0.0
    assert write_makeup_intensity(store, float("nan")) == 1.0
    (store / "makeup.json").write_text("{not json", encoding="utf-8")
    assert read_makeup_intensity(store) == 1.0
    (store / "makeup.json").write_text(json.dumps({"intensity": True}), encoding="utf-8")
    assert read_makeup_intensity(store) == 1.0


def test_wardrobe_service_menu_lists_bare_builtin_and_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "store"
    service = WardrobeService(store)
    pending = service.makeup_options("en")
    assert [option.option_id for option in pending] == [
        "none", "builtin/light", "builtin/classic",
    ]
    assert [option.available for option in pending] == [True, False, False]
    with pytest.raises(OutfitPackError):
        service.apply_makeup("builtin/glamorous")
    assert service.active_makeup().option_id == "builtin/classic"
    official_builtin_pack(tmp_path, monkeypatch)
    service.install(makeup_pack(tmp_path / "festival-makeup.mohan-outfit"))
    options = service.makeup_options("en")
    assert [option.option_id for option in options] == [
        "none", "builtin/light", "builtin/classic",
        "festival-makeup/festival/classic",
    ]
    assert [option.available for option in options] == [True, True, True, True]
    assert options[2].display_name.endswith("classic")
    assert options[3].display_name == "festival-makeup · festival · classic"
    service.apply_makeup("festival-makeup/festival/classic")
    assert service.active_makeup().option_id == "festival-makeup/festival/classic"
    service.apply_makeup("builtin/light")
    assert _identity(resolve_active_selection(store, "makeup"))[2] == "light"
    service.apply_makeup("none")
    assert service.active_makeup().option_id == "none"
    with pytest.raises(OutfitPackError):
        service.apply_makeup("ghost-pack/item/variant")
    assert service.set_makeup_intensity(0.25) == pytest.approx(0.25)
    assert service.makeup_intensity() == pytest.approx(0.25)


def test_official_glamorous_variant_adds_the_fourth_builtin_look(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    official = tmp_path / "official"
    makeup_pack(
        official / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit",
        pack_id=BUILTIN_MAKEUP_PACK_ID,
        item_id=BUILTIN_MAKEUP_ITEM_ID,
        variants=("classic", "light", "glamorous"),
    )
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", official)

    options = WardrobeService(tmp_path / "store").makeup_options("en")
    assert [option.option_id for option in options] == [
        "none", "builtin/light", "builtin/classic", "builtin/glamorous",
    ]
    assert [option.available for option in options] == [True, True, True, True]


def test_generic_scaffold_contract_seals_into_a_makeup_only_pack(tmp_path: Path) -> None:
    manifest_path = tmp_path / "builtin" / "manifest.json"
    assert scaffold_main([str(manifest_path), *BUILTIN_SCAFFOLD_ARGS]) == 0
    scaffolded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert makeup_authoring_mode(manifest_path) == "legacy"
    variants = scaffolded["makeup"][0]["variants"]
    assert [variant["id"] for variant in variants] == list(BUILTIN_VARIANTS)
    assert all("eye_states" not in variant for variant in variants)
    assert all("foundation_silhouettes" not in variant for variant in variants)
    assert all(
        {entry["slot"] for entries in variant["poses"].values() for entry in entries}
        == set(SLOT_Z)
        for variant in variants
    )
    _write_blank_makeup_assets(scaffolded, manifest_path.parent)
    output = tmp_path / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit"
    build_outfit_pack(manifest_path, manifest_path.parent, output)
    pack = inspect_outfit_pack(output)
    item = next(item for item in pack.items if item.category == "makeup")
    assert (pack.pack_id, item.item_id) == (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID)
    assert [variant.variant_id for variant in item.variants] == list(BUILTIN_VARIANTS)
    assert len(item.variants) == EXPECTED_VARIANTS
    assert all(len(variant.poses) == EXPECTED_SILHOUETTES for variant in item.variants)


def test_committed_authoring_rebuild_includes_all_declared_makeup_members(tmp_path: Path) -> None:
    manifest_path, committed = _copy_committed_makeup_manifest(tmp_path)
    output = tmp_path / "committed.mohan-outfit"
    build_outfit_pack(manifest_path, manifest_path.parent, output)
    pack = inspect_outfit_pack(output)
    item = next(item for item in pack.items if item.category == "makeup")
    declared_paths = [entry["path"] for _silhouette, entry in _declared_makeup_assets(committed)]
    parsed_paths = [
        asset.path
        for variant in item.variants
        for assets in variant.poses.values()
        for asset in assets
    ]
    parsed_paths.extend(
        asset.path
        for variant in item.variants
        for state_poses in variant.eye_states.values()
        for assets in state_poses.values()
        for asset in assets
    )
    assert len(parsed_paths) == len(declared_paths)
    assert sorted(parsed_paths) == sorted(declared_paths)
    with zipfile.ZipFile(output) as archive:
        assert set(declared_paths) <= set(archive.namelist())


def test_scaffold_and_canonical_authoring_modes_remain_distinct(tmp_path: Path) -> None:
    manifest_path = tmp_path / "legacy.json"
    assert scaffold_main([str(manifest_path), *BUILTIN_SCAFFOLD_ARGS]) == 0
    canonical = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical["makeup"][0]["variants"][0]["eye_states"] = {"half": {}, "closed": {}}
    canonical_path = tmp_path / "canonical.json"
    canonical_path.write_text(json.dumps(canonical), encoding="utf-8")
    assert makeup_authoring_mode(manifest_path) == "legacy"
    assert makeup_authoring_mode(canonical_path) == "canonical"
    with pytest.raises(SystemExit, match="Canonical foundation"):
        makeup_layer_paths(canonical_path)


def test_builder_calibration_keeps_pixel_gate_and_import_boundary(tmp_path: Path) -> None:
    """Staging calibration preserves the installed body's existing acceptance gate."""
    silhouette = "front-crossed"
    painted = (0, 0, BLOCK, BLOCK)
    manifest, assets = makeup_manifest(blocks={("classic", silhouette, "eyes"): (painted,)})
    source = tmp_path / "authoring"
    source.mkdir()
    manifest_path = source / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for name, payload in assets.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    rejected = tmp_path / "rejected.mohan-outfit"
    with pytest.raises(OutfitPackError, match="safe region"):
        build_outfit_pack(manifest_path, source, rejected)
    assert not rejected.exists()
    assert not rejected.with_name(f".{rejected.name}.building").exists()
    installed = load_makeup_safe_regions()
    region = installed[silhouette]
    staging = frozendict({
        **installed,
        silhouette: replace(region, slots=frozendict({**region.slots, "eyes": (painted,)})),
    })
    sealed = tmp_path / "staging.mohan-outfit"
    build_outfit_pack(manifest_path, source, sealed, makeup_regions=staging)
    verify_makeup_layers(sealed, staging)
    with pytest.raises(OutfitPackError, match="safe region"):
        verify_makeup_layers(sealed)
    escaped = frozendict({
        **staging,
        silhouette: replace(region, slots=frozendict({**region.slots, "eyes": ()})),
    })
    with pytest.raises(OutfitPackError, match="safe region"):
        build_outfit_pack(manifest_path, source, rejected, makeup_regions=escaped)
    assert not rejected.exists()


def main() -> int:
    result = pytest.main([__file__, "-q", *sys.argv[1:]])
    if result == 0:
        print("OUTFIT_PACK_MAKEUP_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
