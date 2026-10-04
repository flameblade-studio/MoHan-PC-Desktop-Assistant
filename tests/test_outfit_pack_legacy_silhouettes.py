"""Retired old-face makeup views are rejected while complete views remain valid."""
from __future__ import annotations

lazy import json
lazy import zipfile
lazy from dataclasses import replace
lazy from functools import cache
lazy from pathlib import Path

lazy import pytest

lazy from domain.outfit_pack import (
    COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES,
    OPTIONAL_MAKEUP_SILHOUETTES,
    OutfitPackError,
    inspect_outfit_pack,
)
lazy from domain.outfit_pack_makeup import (
    load_makeup_safe_regions,
    makeup_layer_escapes,
    verify_makeup_layers,
)

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PACK = ROOT / "assets" / "official-packs" / "mohan.makeup.builtin.mohan-outfit"


@cache
def _official_entries() -> tuple[tuple[str, bytes], ...]:
    """Read the shipped pack once; every case rewrites only its manifest."""
    with zipfile.ZipFile(OFFICIAL_PACK) as source:
        return tuple((name, source.read(name)) for name in source.namelist())


def _write_pack_with_manifest(target: Path, manifest: dict) -> Path:
    # PNG members are already compressed, so storing them keeps each case fast.
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as destination:
        for name, data in _official_entries():
            if name != "manifest.json":
                destination.writestr(name, data)
        destination.writestr("manifest.json", json.dumps(manifest))
    return target


def _official_manifest() -> dict:
    return json.loads(dict(_official_entries())["manifest.json"])


def test_official_pack_has_complete_views_and_no_retired_views() -> None:
    pack = inspect_outfit_pack(OFFICIAL_PACK)
    assert len(pack.items) >= 1
    verify_makeup_layers(OFFICIAL_PACK)
    assert set(COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES) <= set(
        OPTIONAL_MAKEUP_SILHOUETTES
    )
    with zipfile.ZipFile(OFFICIAL_PACK) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    pose_ids = set()
    for item in manifest["makeup"]:
        for variant in item["variants"]:
            pose_ids.update(variant["poses"])
    assert not any(pose.endswith("-legacy") for pose in pose_ids)
    assert set(COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES) <= pose_ids


def _pack_with_retired_view(tmp_path: Path, view: str, section: str) -> Path:
    manifest = _official_manifest()
    variant = manifest["makeup"][0]["variants"][0]
    entries = variant["poses"] if section == "rest" else variant["eye_states"][section]
    entries[view] = json.loads(json.dumps(entries["cheek-rest"]))
    return _write_pack_with_manifest(tmp_path / OFFICIAL_PACK.name, manifest)


@pytest.mark.parametrize("view", ("cheek-rest-legacy", "left-neutral-legacy"))
@pytest.mark.parametrize("section", ("rest", "half", "closed"))
def test_retired_legacy_view_is_rejected(tmp_path: Path, view: str, section: str) -> None:
    with pytest.raises(OutfitPackError):
        inspect_outfit_pack(_pack_with_retired_view(tmp_path, view, section))


def test_complete_view_escaping_its_safe_region_is_rejected_on_import(tmp_path: Path) -> None:
    """One end-to-end case proves the importer wires the per-layer gate."""
    view = COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES[0]
    regions = dict(load_makeup_safe_regions())
    region = regions[view]
    slots = dict(region.slots)
    slots["cheeks"] = ((0, 0, 1, 1),)
    regions[view] = replace(region, slots=frozendict(slots))
    # Visit the target view first; required views and real PNG bytes stay intact.
    manifest = _official_manifest()
    variant = manifest["makeup"][0]["variants"][0]
    poses = variant["poses"]
    variant["poses"] = {view: poses[view], **poses}
    target = _write_pack_with_manifest(tmp_path / OFFICIAL_PACK.name, manifest)
    with pytest.raises(OutfitPackError, match=rf"cheeks safe region of {view}\."):
        verify_makeup_layers(target, regions=frozendict(regions))


@pytest.mark.parametrize("view", COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES)
def test_complete_view_cheeks_layer_escapes_only_a_shrunken_region(view: str) -> None:
    """Every complete view's real cheeks layer fits its region and escapes a 1 px one."""
    region = load_makeup_safe_regions()[view]
    slots = dict(region.slots)
    slots["cheeks"] = ((0, 0, 1, 1),)
    shrunken = replace(region, slots=frozendict(slots))
    manifest = _official_manifest()
    variant = manifest["makeup"][0]["variants"][0]
    cheeks = next(asset for asset in variant["poses"][view] if asset["slot"] == "cheeks")
    layer = dict(_official_entries())[cheeks["path"]]
    assert not makeup_layer_escapes(layer, region, "cheeks")
    assert makeup_layer_escapes(layer, shrunken, "cheeks")
