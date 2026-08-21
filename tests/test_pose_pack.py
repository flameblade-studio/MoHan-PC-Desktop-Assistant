from __future__ import annotations

lazy import copy
lazy import hashlib
lazy import json
lazy import struct
lazy import sys
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from pose_pack import (
    BUILTIN_POSES,
    CANONICAL_YAWS,
    PosePackError,
    inspect_pose_pack,
    install_pose_pack,
    list_installed_pose_packs,
    remove_pose_pack,
)

REAR_YAW = -180
FRONT_YAW = 165
VIEW_COUNT = 24
SCHEMA_VERSION = 2
MULTI_POSE_VIEW_COUNT = 48


def _png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 256, 512)


def _names(name: str) -> dict[str, str]:
    return {"zh-TW": name, "zh-CN": name, "en": name, "ja-JP": name}


def _manifest(data: bytes) -> tuple[dict, dict[str, bytes]]:
    roles = (
        "body", "left-arm-correction", "right-arm-correction",
        "left-hand-correction", "right-hand-correction",
        "left-leg-correction", "right-leg-correction",
        "left-foot-correction", "right-foot-correction",
        "left-sole-correction", "right-sole-correction",
    )
    rig = {
        "contract": "full-body-v4",
        "rig_id": "mohan-full-body-v1",
        "rig_version_range": ">=1,<2",
        "body_profile_id": "mohan-body-v1",
        "body_profile_version_range": ">=1,<2",
    }
    views, assets = [], {}
    for yaw in CANONICAL_YAWS:
        layers = []
        for depth, role in enumerate(roles):
            yaw_name = f"m{abs(yaw)}" if yaw < 0 else f"p{yaw}"
            path = f"assets/reading/level/{yaw_name}-{role}.png"
            assets[path] = data
            layers.append({
                "role": role,
                "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "width": 256,
                "height": 512,
                "anchor": [0, 0],
                "depth": depth,
                "occlusion": "front-of-body" if role != "body" else "behind-hands",
                "transparent": True,
            })
        views.append({
            "pose_id": "reading",
            "pitch_band": "level",
            "yaw": yaw,
            "layers": layers,
            "full_body_rig": dict(rig),
        })
    return (
        {
            "format": "mohan-pose-pack",
            "version": 2,
            "id": "reading-turntable",
            "pack_version": "1.0.0",
            "app_range": ">=4.0.0,<5.0.0",
            "display_names": _names("閱讀姿態環景"),
            "compatible_body_profile": {"id": "mohan-body-v1", "version": 1},
            "full_body_rig": rig,
            "pitch_bands": ["level"],
            "pose_ids": ["reading"],
            "compatibility": {
                "face": "core-owned",
                "hair": "appearance-slot",
                "garment": "appearance-slot",
                "headwear": "optional-slot",
                "weapon": "optional-slot",
            },
            "source": {
                "kind": "original",
                "author": "Example Artist",
                "license": "MIT",
                "provenance": "Created from the official mohan-body-v1 authoring rig.",
                "reference_included": False,
            },
            "views": views,
        },
        assets,
    )


def _pack(path: Path, manifest: dict, assets: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for name, data in assets.items():
            archive.writestr(name, data)
    return path


def _reject(path: Path) -> None:
    try:
        inspect_pose_pack(path)
    except PosePackError:
        return
    raise AssertionError("invalid pose pack must fail closed")


@dataclass(frozen=True, slots=True)
class _Fixture:
    root: Path
    data: bytes
    manifest: dict
    assets: dict[str, bytes]
    valid: Path


def _fixture(root: Path) -> _Fixture:
    data = _png()
    manifest, assets = _manifest(data)
    valid = _pack(root / "valid.mohan-pose", manifest, assets)
    return _Fixture(root, data, manifest, assets, valid)


def _assert_valid_pack(fixture: _Fixture) -> None:
    pack = inspect_pose_pack(fixture.valid)
    assert CANONICAL_YAWS[0] == REAR_YAW
    assert CANONICAL_YAWS[-1] == FRONT_YAW
    assert len(CANONICAL_YAWS) == VIEW_COUNT
    assert len(pack.views) == VIEW_COUNT
    assert pack.schema_version == SCHEMA_VERSION
    assert pack.rig.complete
    assert all(view.rig == pack.rig for view in pack.views)


def _assert_multi_pose_pack(fixture: _Fixture) -> None:
    manifest = copy.deepcopy(fixture.manifest)
    manifest["pose_ids"].append("standing")
    standing_views = []
    standing_assets = dict(fixture.assets)
    for original in manifest["views"]:
        cloned = copy.deepcopy(original)
        cloned["pose_id"] = "standing"
        for layer in cloned["layers"]:
            old_path = layer["path"]
            layer["path"] = old_path.replace(
                "assets/reading/",
                "assets/standing/",
                1,
            )
            standing_assets[layer["path"]] = fixture.assets[old_path]
        standing_views.append(cloned)
    manifest["views"].extend(standing_views)
    collection = inspect_pose_pack(
        _pack(
            fixture.root / "multi-pose.mohan-pose",
            manifest,
            standing_assets,
        )
    )
    assert collection.pose_ids == ("reading", "standing")
    assert len(collection.views) == MULTI_POSE_VIEW_COUNT
    assert collection.compatibility["garment"] == "appearance-slot"
    assert all(view.rig.complete for view in collection.views)
    assert {"cheek-rest", "left-neutral", "front-crossed"} == BUILTIN_POSES


def _assert_install_and_removal(fixture: _Fixture) -> Path:
    store = fixture.root / "store"
    installed = install_pose_pack(fixture.valid, store)
    assert list_installed_pose_packs(store) == (installed,)
    assert not (store / "active.json").exists()

    active = {"pack_id": "reading-turntable", "pose_id": "reading"}
    (store / "active.json").write_text(json.dumps(active), encoding="utf-8")
    try:
        remove_pose_pack(store, "reading-turntable")
    except PosePackError:
        pass
    else:
        raise AssertionError("active pose pack must be protected")
    (store / "active.json").unlink()
    remove_pose_pack(store, "reading-turntable")
    assert list_installed_pose_packs(store) == ()
    assert {"cheek-rest", "left-neutral", "front-crossed"} == BUILTIN_POSES

    for invalid_id in ("builtin", "missing", "../reading-turntable"):
        try:
            remove_pose_pack(store, invalid_id)
        except PosePackError:
            pass
        else:
            raise AssertionError("unsafe removal must fail closed")
    return store


def _reject_without_layer(
    fixture: _Fixture,
    role: str,
    filename: str,
) -> None:
    manifest = copy.deepcopy(fixture.manifest)
    removed = next(
        layer
        for layer in manifest["views"][0]["layers"]
        if layer["role"] == role
    )
    manifest["views"][0]["layers"].remove(removed)
    assets = dict(fixture.assets)
    assets.pop(removed["path"])
    _reject(_pack(fixture.root / filename, manifest, assets))


def _assert_view_contract_rejections(fixture: _Fixture) -> None:
    missing_yaw = copy.deepcopy(fixture.manifest)
    missing_yaw["views"].pop()
    _reject(_pack(fixture.root / "missing-yaw.zip", missing_yaw, fixture.assets))

    unknown_yaw = copy.deepcopy(fixture.manifest)
    unknown_yaw["views"][0]["yaw"] = 180
    _reject(_pack(fixture.root / "unknown-yaw.zip", unknown_yaw, fixture.assets))

    missing_hand = copy.deepcopy(fixture.manifest)
    removed = missing_hand["views"][0]["layers"].pop()
    reduced_assets = dict(fixture.assets)
    reduced_assets.pop(removed["path"])
    _reject(_pack(fixture.root / "missing-hand.zip", missing_hand, reduced_assets))
    _reject_without_layer(fixture, "left-leg-correction", "missing-leg.zip")
    _reject_without_layer(fixture, "right-sole-correction", "missing-sole.zip")


def _assert_manifest_rejections(fixture: _Fixture) -> None:
    candidate = copy.deepcopy(fixture.manifest)
    candidate["views"][0]["full_body_rig"]["rig_version_range"] = ">=2,<3"
    _reject(_pack(fixture.root / "mismatched-rig.zip", candidate, fixture.assets))

    candidate = copy.deepcopy(fixture.manifest)
    candidate["full_body_rig"]["body_profile_version_range"] = ">=2,<3"
    _reject(_pack(fixture.root / "profile-range.zip", candidate, fixture.assets))

    candidate = copy.deepcopy(fixture.manifest)
    candidate["views"][0]["layers"][0]["sha256"] = "0" * 64
    _reject(_pack(fixture.root / "bad-hash.zip", candidate, fixture.assets))

    candidate = copy.deepcopy(fixture.manifest)
    candidate["views"][0]["layers"][0]["transparent"] = False
    _reject(_pack(fixture.root / "opaque.zip", candidate, fixture.assets))

    candidate = copy.deepcopy(fixture.manifest)
    candidate["compatibility"]["face"] = "appearance-slot"
    _reject(_pack(fixture.root / "face.zip", candidate, fixture.assets))


def _assert_archive_member_rejections(fixture: _Fixture) -> None:
    traversal = copy.deepcopy(fixture.manifest)
    old_path = traversal["views"][0]["layers"][0]["path"]
    traversal["views"][0]["layers"][0]["path"] = "../payload.png"
    traversal_assets = dict(fixture.assets)
    traversal_assets.pop(old_path)
    traversal_assets["../payload.png"] = fixture.data
    _reject(_pack(fixture.root / "traversal.zip", traversal, traversal_assets))

    executable_assets = {**fixture.assets, "assets/payload.py": b"print('bad')"}
    _reject(
        _pack(
            fixture.root / "code.zip",
            fixture.manifest,
            executable_assets,
        )
    )


def _legacy_manifest(fixture: _Fixture) -> tuple[dict, dict[str, bytes]]:
    legacy = copy.deepcopy(fixture.manifest)
    legacy["version"] = 1
    legacy.pop("full_body_rig")
    legacy_assets: dict[str, bytes] = {}
    legacy_views = []
    legacy_roles = {
        "body",
        "left-arm-correction",
        "right-arm-correction",
        "left-hand-correction",
        "right-hand-correction",
    }
    for view in legacy["views"]:
        if view["yaw"] not in {-30, 0, 30}:
            continue
        view.pop("full_body_rig")
        kept_layers = [
            layer for layer in view["layers"] if layer["role"] in legacy_roles
        ]
        view["layers"] = kept_layers
        legacy_views.append(view)
        legacy_assets.update(
            {layer["path"]: fixture.assets[layer["path"]] for layer in kept_layers}
        )
    legacy["views"] = legacy_views
    return legacy, legacy_assets


def _assert_legacy_fallback(fixture: _Fixture) -> None:
    legacy, legacy_assets = _legacy_manifest(fixture)
    legacy_pack = inspect_pose_pack(
        _pack(
            fixture.root / "legacy-v3.mohan-pose",
            legacy,
            legacy_assets,
        )
    )
    assert legacy_pack.legacy_fallback
    assert not legacy_pack.rig.complete
    assert tuple(view.yaw for view in legacy_pack.views) == (-30, 0, 30)

    lying_legacy = copy.deepcopy(legacy)
    lying_legacy["full_body_rig"] = copy.deepcopy(
        fixture.manifest["full_body_rig"]
    )
    _reject(
        _pack(
            fixture.root / "lying-legacy.zip",
            lying_legacy,
            legacy_assets,
        )
    )


def _assert_invalid_update_is_atomic(fixture: _Fixture, store: Path) -> None:
    install_pose_pack(fixture.valid, store)
    destination = store / "packages" / "reading-turntable.mohan-pose"
    before = destination.read_bytes()
    invalid_update = copy.deepcopy(fixture.manifest)
    invalid_update["source"]["reference_included"] = True
    try:
        install_pose_pack(
            _pack(
                fixture.root / "invalid-update.zip",
                invalid_update,
                fixture.assets,
            ),
            store,
        )
    except PosePackError:
        pass
    else:
        raise AssertionError("invalid update must not install")
    assert destination.read_bytes() == before


def run() -> None:
    with TemporaryDirectory() as temporary:
        fixture = _fixture(Path(temporary))
        _assert_valid_pack(fixture)
        _assert_multi_pose_pack(fixture)
        store = _assert_install_and_removal(fixture)
        _assert_view_contract_rejections(fixture)
        _assert_manifest_rejections(fixture)
        _assert_archive_member_rejections(fixture)
        _assert_legacy_fallback(fixture)
        _assert_invalid_update_is_atomic(fixture, store)
    print("POSE_PACK_OK")


if __name__ == "__main__":
    run()
