from __future__ import annotations

lazy import copy
lazy import hashlib
lazy import json
lazy import struct
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.outfit_pack import (
    EXPRESSION_SILHOUETTE_ALIASES,
    GESTURE_SILHOUETTES,
    POSE_ATLAS_SILHOUETTES,
    REQUIRED_SILHOUETTES,
    OutfitPackError,
    apply_appearance_selection,
    apply_ensemble,
    clear_appearance_selection,
    inspect_outfit_pack,
    install_outfit_pack,
    list_installed_ensembles,
    list_installed_outfits,
    list_installed_selections,
    remove_outfit_pack,
    resolve_active_selection,
    resolve_variant_for_view,
    restore_builtin_outfit,
)

EXPECTED_INSTALLED_SELECTIONS = 7


def _png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 512, 768)


def _names(name: str) -> dict[str, str]:
    return {"zh-TW": name, "zh-CN": name, "en": name, "ja-JP": name}


def _asset(path: str, data: bytes, slot: str) -> dict:
    return {
        "slot": slot, "path": path, "sha256": hashlib.sha256(data).hexdigest(),
        "width": 512, "height": 768, "anchor": [0, 0], "z_order": 10,
    }


def _pose_assets(prefix: str, data: bytes, slots: tuple[str, ...]) -> tuple[dict, dict[str, bytes]]:
    poses, assets = {}, {}
    for silhouette in REQUIRED_SILHOUETTES:
        entries = []
        for slot in slots:
            path = f"assets/{prefix}-{silhouette}-{slot}.png"
            assets[path] = data
            entries.append(_asset(path, data, slot))
        poses[silhouette] = entries
    return poses, assets


def _silhouette_rules(value: str) -> dict[str, str]:
    return dict.fromkeys(REQUIRED_SILHOUETTES, value)


def _body_visibility() -> dict[str, dict[str, str]]:
    regions = (
        "neck",
        "shoulder-left",
        "shoulder-right",
        "arm-left",
        "arm-right",
        "torso",
        "leg-left",
        "leg-right",
    )
    return {
        silhouette: dict.fromkeys(regions, "covered")
        for silhouette in REQUIRED_SILHOUETTES
    }


def _appearance_assets(data: bytes) -> tuple[dict[str, dict], dict[str, bytes]]:
    definitions = {
        "garment": ("robe", ("outerwear",)),
        "hair": ("hair", ("back", "front", "bangs")),
        "headwear": ("pin", ("headwear",)),
        "weapon": ("sword", ("weapon", "sheath")),
        "handheld": ("gift", ("handheld",)),
        "jewelry": ("jewel", ("jewelry",)),
        "foreground": ("glow", ("foreground-effect",)),
    }
    poses: dict[str, dict] = {}
    assets: dict[str, bytes] = {}
    for category, (prefix, slots) in definitions.items():
        category_poses, category_assets = _pose_assets(prefix, data, slots)
        poses[category] = category_poses
        assets.update(category_assets)
    return poses, assets


def _manifest(data: bytes) -> tuple[dict, dict[str, bytes]]:
    poses, assets = _appearance_assets(data)
    manifest = {
        "format": "mohan-outfit-pack", "version": 2, "id": "modern-collection",
        "pack_version": "1.0.0", "app_range": ">=4.0.0,<5.0.0",
        "display_names": _names("現代合輯"),
        "compatible_body_profile": {"id": "mohan-body-v1", "version": 1},
        "source": {"kind": "original", "author": "Example Artist", "license": "MIT", "reference_included": False},
        "authoring": {"template": "mohan-official-poses", "version": 2},
        "looks": [{
            "id": "city-dress", "display_names": _names("城市洋裝"),
            "variants": [{"id": "navy", "display_names": _names("深藍"), "fabric_behavior": "draped", "body_visibility": _body_visibility(), "poses": poses["garment"]}],
        }],
        "hairstyles": [{
            "id": "long-soft", "display_names": _names("柔順長髮"),
            "variants": [{"id": "black", "display_names": _names("墨黑"), "poses": poses["hair"], "face_occlusion_masks": _silhouette_rules("bangs-safe"), "hand_occlusion": _silhouette_rules("behind-hands"), "garment_occlusion": _silhouette_rules("behind-collar")}],
        }],
        "headwear": [{
            "id": "silver-pin", "display_names": _names("銀簪"),
            "attachment_point": "crown", "safe_mask": "crown-safe",
            "variants": [{"id": "silver", "display_names": _names("銀色"), "poses": poses["headwear"]}],
        }],
        "accessories": [
            {
                "id": "short-sword", "accessory_kind": "weapon", "display_names": _names("短劍"),
                "variants": [{"id": "steel", "display_names": _names("鋼色"), "poses": poses["weapon"], "placement": _silhouette_rules("waist-left"), "attachment_contract": _silhouette_rules("waist-sheath"), "hand_occlusion": _silhouette_rules("behind-hands"), "garment_occlusion": _silhouette_rules("behind-collar"), "hair_occlusion": _silhouette_rules("behind-hair")}],
            },
            {
                "id": "held-gift", "accessory_kind": "handheld", "display_names": _names("手持禮物"),
                "variants": [{"id": "wrapped", "display_names": _names("包裝"), "poses": poses["handheld"], "placement": _silhouette_rules("hand-right"), "hand_occlusion": _silhouette_rules("behind-hands")}],
            },
            {
                "id": "necklace", "accessory_kind": "jewelry", "display_names": _names("珠寶"),
                "variants": [{"id": "silver", "display_names": _names("銀色"), "poses": poses["jewelry"]}],
            },
            {
                "id": "soft-glow", "accessory_kind": "foreground-effect", "display_names": _names("前景光暈"),
                "variants": [{"id": "blue", "display_names": _names("藍色"), "poses": poses["foreground"]}],
            },
        ],
        "ensembles": [{
            "id": "city-day", "display_names": _names("城市日常"),
            "autonomous_profile": {
                "thermal_bands": ["mild", "cool"],
                "weather": ["clear", "cloudy", "indoor"],
                "moods": ["calm", "focused"],
                "occasions": ["everyday", "work"],
                "priority": 10,
            },
            "selections": {
                "garment": {"item_id": "city-dress", "variant_id": "navy"},
                "hairstyle": {"item_id": "long-soft", "variant_id": "black"},
                "headwear": None,
                "weapon": {"item_id": "short-sword", "variant_id": "steel"},
                "handheld": {"item_id": "held-gift", "variant_id": "wrapped"},
                "jewelry": None,
                "foreground-effect": {"item_id": "soft-glow", "variant_id": "blue"},
            },
        }],
    }
    return manifest, assets


def _referenced_assets(manifest: dict, all_assets: dict[str, bytes]) -> dict[str, bytes]:
    paths = {
        *(
            asset["path"]
            for item in manifest[group]
            for variant in item["variants"]
            for assets in variant["poses"].values()
            for asset in assets
        )
        for group in ("looks", "hairstyles", "headwear", "accessories")
    }
    return {path: all_assets[path] for path in paths}


def _pack(path: Path, manifest: dict, assets: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for name, data in assets.items():
            archive.writestr(name, data)
    return path


def _assert_authoring_builder(
    root: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    authoring = copy.deepcopy(manifest)
    for entry in (
        asset
        for group in ("looks", "hairstyles", "headwear", "accessories")
        for item in authoring[group]
        for variant in item["variants"]
        for pose_assets in variant["poses"].values()
        for asset in pose_assets
    ):
        entry.pop("sha256")
        entry.pop("width")
        entry.pop("height")
    source = root / "authoring.json"
    source.write_text(json.dumps(authoring, ensure_ascii=False), encoding="utf-8")
    asset_root = root / "authoring-assets"
    for name, data in assets.items():
        path = asset_root / Path(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    output = root / "built.mohan-outfit"
    assert build_outfit_pack(source, asset_root, output) == output
    assert inspect_outfit_pack(output).pack_id == "modern-collection"
    try:
        build_outfit_pack(source, asset_root, output)
    except OutfitPackError:
        pass
    else:
        raise AssertionError("the builder must not overwrite an existing package")


def _reject(path: Path) -> None:
    try:
        inspect_outfit_pack(path)
    except OutfitPackError:
        return
    raise AssertionError("invalid appearance pack must fail closed")


def _expect_remove_error(store: Path, pack_id: str, message: str) -> None:
    try:
        remove_outfit_pack(store, pack_id)
    except OutfitPackError:
        return
    raise AssertionError(message)


def _expect_install_error(path: Path, store: Path, message: str) -> None:
    try:
        install_outfit_pack(path, store)
    except OutfitPackError:
        return
    raise AssertionError(message)


def _assert_pack_contract(valid: Path) -> None:
    pack = inspect_outfit_pack(valid)
    assert {item.category for item in pack.items} == {
        "garment",
        "hairstyle",
        "headwear",
        "weapon",
        "handheld",
        "jewelry",
        "foreground-effect",
    }
    assert GESTURE_SILHOUETTES == (
        "front-mock-scold",
        "front-mock-hit",
        "front-eureka",
        "front-exasperated",
    )
    assert "front-protective" not in REQUIRED_SILHOUETTES
    assert EXPRESSION_SILHOUETTE_ALIASES["protective_front"] == "front-crossed"
    garment = next(item for item in pack.items if item.category == "garment")
    exact = resolve_variant_for_view(
        garment.variants[0],
        POSE_ATLAS_SILHOUETTES[12],
    )
    assert exact.resolved_silhouette == POSE_ATLAS_SILHOUETTES[12]
    assert exact.exact_pose_atlas_match


def _prepare_store(root: Path, valid: Path) -> Path:
    store = root / "store"
    install_outfit_pack(valid, store)
    assert not (store / "active.json").exists()
    assert len(list_installed_selections(store)) == EXPECTED_INSTALLED_SELECTIONS
    assert len(list_installed_selections(store, "hairstyle")) == 1
    assert len(list_installed_ensembles(store)) == 1
    return store


def _assert_ensemble_contract(store: Path) -> None:
    apply_ensemble(store, "modern-collection", "city-day")
    active = json.loads((store / "active.json").read_text(encoding="utf-8"))
    assert active["headwear"]["item_id"] == "none"
    assert active["weapon"]["item_id"] == "short-sword"
    assert active["handheld"]["item_id"] == "held-gift"
    assert active["jewelry"]["item_id"] == "none"
    assert active["foreground-effect"]["item_id"] == "soft-glow"
    clear_appearance_selection(store, "weapon")
    cleared = json.loads((store / "active.json").read_text(encoding="utf-8"))
    assert cleared["weapon"]["item_id"] == "none"
    assert cleared["handheld"]["item_id"] == "held-gift"
    assert "_ensemble" not in cleared
    assert active["_ensemble"] == {
        "pack_id": "modern-collection",
        "ensemble_id": "city-day",
    }
    _expect_remove_error(
        store,
        "modern-collection",
        "an active ensemble must block removal",
    )
    headwear = list_installed_selections(store, "headwear")[0]
    apply_appearance_selection(store, headwear)
    saved = json.loads((store / "active.json").read_text(encoding="utf-8"))
    assert saved["headwear"]["item_id"] == "silver-pin"
    assert "_ensemble" not in saved
    restore_builtin_outfit(store)
    restored = json.loads((store / "active.json").read_text(encoding="utf-8"))
    assert set(restored) == {
        "garment",
        "hairstyle",
        "headwear",
        "weapon",
        "handheld",
        "jewelry",
        "foreground-effect",
    }


def _assert_removal_guards(
    root: Path,
    store: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    preview = {
        "hairstyle": {
            "pack_id": "modern-collection",
            "item_id": "long-soft",
            "variant_id": "black",
        }
    }
    (store / "preview.json").write_text(json.dumps(preview), encoding="utf-8")
    _expect_remove_error(
        store,
        "modern-collection",
        "a previewed item must block removal",
    )
    (store / "preview.json").unlink()
    _expect_remove_error(store, "builtin", "builtin must never be removable")
    for invalid_id in ("missing", "../modern-collection"):
        _expect_remove_error(
            store,
            invalid_id,
            "unknown and traversal IDs must fail closed",
        )
    other_manifest = copy.deepcopy(manifest)
    other_manifest["id"] = "other-pack"
    install_outfit_pack(_pack(root / "other.zip", other_manifest, assets), store)
    mismatch = store / "packages" / "wrong-name.mohan-outfit"
    installed = store / "packages" / "other-pack.mohan-outfit"
    mismatch.write_bytes(installed.read_bytes())
    _expect_remove_error(
        store,
        "wrong-name",
        "manifest and filename identity mismatch must fail",
    )
    mismatch.unlink()


def _assert_removal_fails_closed(store: Path, valid: Path) -> None:
    removed = remove_outfit_pack(store, "modern-collection")
    assert removed.pack_id == "modern-collection"
    assert all(
        pack.pack_id != "modern-collection"
        for pack in list_installed_outfits(store)
    )
    missing_state = {
        "garment": {
            "pack_id": "modern-collection",
            "item_id": "city-dress",
            "variant_id": "navy",
        }
    }
    (store / "active.json").write_text(json.dumps(missing_state), encoding="utf-8")
    try:
        resolve_active_selection(store, "garment")
    except OutfitPackError:
        pass
    else:
        raise AssertionError("a missing selected outfit must never be replaced")
    install_outfit_pack(valid, store)


def _assert_single_category_packs(
    root: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    groups = ("looks", "hairstyles", "headwear", "accessories")
    for sole_group in groups[:-1]:
        pure = copy.deepcopy(manifest)
        for group in groups:
            if group != sole_group:
                pure[group] = []
        pure["ensembles"] = []
        pure["id"] = f"pure-{sole_group}"
        archive = _pack(
            root / f"{sole_group}.zip",
            pure,
            _referenced_assets(pure, assets),
        )
        assert inspect_outfit_pack(archive).items


def _assert_pose_rejections(
    root: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    invalid = copy.deepcopy(manifest)
    del invalid["hairstyles"][0]["variants"][0]["poses"]["front-mock-hit"]
    _reject(_pack(root / "missing-gesture.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    missing_view = POSE_ATLAS_SILHOUETTES[7]
    del invalid["looks"][0]["variants"][0]["poses"][missing_view]
    _reject(_pack(root / "missing-pose-atlas-view.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    poses = invalid["looks"][0]["variants"][0]["poses"]
    poses["unknown-pose"] = copy.deepcopy(poses["front-crossed"])
    _reject(_pack(root / "unknown-pose.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    invalid["hairstyles"][0]["variants"][0]["poses"]["front-crossed"].pop()
    _reject(_pack(root / "missing-hair-layer.zip", invalid, assets))


def _assert_visual_contract_rejections(
    root: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    invalid = copy.deepcopy(manifest)
    masks = invalid["hairstyles"][0]["variants"][0]["face_occlusion_masks"]
    masks["front-crossed"] = "cover-face"
    _reject(_pack(root / "bad-occlusion.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    invalid["headwear"][0]["attachment_point"] = "face"
    _reject(_pack(root / "bad-attachment.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    hair_pose = invalid["hairstyles"][0]["variants"][0]["poses"]
    hair_pose["front-crossed"][0]["slot"] = "face"
    _reject(_pack(root / "core.zip", invalid, assets))


def _assert_accessory_rejections(
    root: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    invalid = copy.deepcopy(manifest)
    invalid["accessories"][0]["variants"][0]["placement"]["front-crossed"] = "floating"
    _reject(_pack(root / "bad-weapon-placement.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    attachments = invalid["accessories"][0]["variants"][0]["attachment_contract"]
    attachments["front-crossed"] = "right-grip"
    _reject(_pack(root / "mismatched-grip.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    occlusion = invalid["accessories"][0]["variants"][0]["hair_occlusion"]
    del occlusion["front-mock-hit"]
    _reject(_pack(root / "missing-weapon-occlusion.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    placement = invalid["accessories"][1]["variants"][0]["placement"]
    placement["front-crossed"] = "waist-left"
    _reject(_pack(root / "bad-handheld-placement.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    invalid["accessories"][2]["accessory_kind"] = "unknown"
    _reject(_pack(root / "bad-accessory-kind.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    selections = invalid["ensembles"][0]["selections"]
    selections["hairstyle"]["item_id"] = "not-in-this-pack"
    _reject(_pack(root / "cross-pack.zip", invalid, assets))


def _assert_asset_rejections(
    root: Path,
    data: bytes,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    invalid = copy.deepcopy(manifest)
    invalid["looks"][0]["variants"][0]["poses"]["front-crossed"][0]["sha256"] = "0" * 64
    _reject(_pack(root / "hash.zip", invalid, assets))
    invalid = copy.deepcopy(manifest)
    invalid["looks"][0]["variants"][0]["poses"]["front-crossed"][0]["width"] = 511
    _reject(_pack(root / "dimension.zip", invalid, assets))
    _reject(
        _pack(
            root / "sidecar.zip",
            manifest,
            {**assets, "assets/unreferenced.png": data},
        )
    )
    invalid = copy.deepcopy(manifest)
    target = invalid["headwear"][0]["variants"][0]["poses"]["front-crossed"][0]
    old_path, svg_path = target["path"], "assets/unsafe.svg"
    svg = b'<svg width="512" height="768" onload="bad()"/>'
    target["path"] = svg_path
    target["sha256"] = hashlib.sha256(svg).hexdigest()
    unsafe_assets = {**assets, svg_path: svg}
    unsafe_assets.pop(old_path)
    _reject(_pack(root / "svg.zip", invalid, unsafe_assets))


def _assert_invalid_update_is_atomic(
    root: Path,
    store: Path,
    manifest: dict,
    assets: dict[str, bytes],
) -> None:
    installed = store / "packages" / "modern-collection.mohan-outfit"
    before = installed.read_bytes()
    invalid = copy.deepcopy(manifest)
    invalid["source"]["reference_included"] = True
    path = _pack(root / "invalid-update.zip", invalid, assets)
    _expect_install_error(path, store, "invalid update must fail")
    assert installed.read_bytes() == before


def run() -> None:
    with TemporaryDirectory() as temporary:
        root, data = Path(temporary), _png()
        manifest, assets = _manifest(data)
        _assert_authoring_builder(root, manifest, assets)
        valid = _pack(root / "valid.mohan-appearance", manifest, assets)
        _assert_pack_contract(valid)
        store = _prepare_store(root, valid)
        _assert_ensemble_contract(store)
        _assert_removal_guards(root, store, manifest, assets)
        _assert_removal_fails_closed(store, valid)
        _assert_single_category_packs(root, manifest, assets)
        _assert_pose_rejections(root, manifest, assets)
        _assert_visual_contract_rejections(root, manifest, assets)
        _assert_accessory_rejections(root, manifest, assets)
        _assert_asset_rejections(root, data, manifest, assets)
        _assert_invalid_update_is_atomic(root, store, manifest, assets)
    print("OUTFIT_PACK_OK")


if __name__ == "__main__":
    run()
