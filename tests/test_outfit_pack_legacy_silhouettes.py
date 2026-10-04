"""Retired old-face makeup views are rejected while complete views remain valid."""
from __future__ import annotations

lazy import json
lazy import zipfile
lazy from dataclasses import replace
lazy from pathlib import Path

lazy import pytest

lazy from domain.outfit_pack import (
    COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES,
    OPTIONAL_MAKEUP_SILHOUETTES,
    OutfitPackError,
    inspect_outfit_pack,
)
lazy from domain.outfit_pack_makeup import load_makeup_safe_regions, verify_makeup_layers

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PACK = ROOT / "assets" / "official-packs" / "mohan.makeup.builtin.mohan-outfit"


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
    with zipfile.ZipFile(OFFICIAL_PACK) as source:
        manifest = json.loads(source.read("manifest.json"))
        variant = manifest["makeup"][0]["variants"][0]
        entries = variant["poses"] if section == "rest" else variant["eye_states"][section]
        entries[view] = json.loads(
            json.dumps(entries["cheek-rest"])
        )
        target = tmp_path / OFFICIAL_PACK.name
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as destination:
            for entry in source.infolist():
                if entry.filename != "manifest.json":
                    destination.writestr(entry, source.read(entry.filename))
            destination.writestr("manifest.json", json.dumps(manifest))
    return target


@pytest.mark.parametrize("view", ("cheek-rest-legacy", "left-neutral-legacy"))
@pytest.mark.parametrize("section", ("rest", "half", "closed"))
def test_retired_legacy_view_is_rejected(tmp_path: Path, view: str, section: str) -> None:
    with pytest.raises(OutfitPackError):
        inspect_outfit_pack(_pack_with_retired_view(tmp_path, view, section))


@pytest.mark.parametrize("view", COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES)
def test_complete_view_layer_escaping_its_safe_region_is_rejected(tmp_path: Path, view: str) -> None:
    regions = dict(load_makeup_safe_regions())
    region = regions[view]
    slots = dict(region.slots)
    slots["cheeks"] = ((0, 0, 1, 1),)
    regions[view] = replace(region, slots=frozendict(slots))
    # Visit the target view first; required views and real PNG bytes stay intact.
    # This exercises the production importer without rescanning unrelated pixels
    # before each intentionally invalid complete-expression view.
    with zipfile.ZipFile(OFFICIAL_PACK) as source:
        manifest = json.loads(source.read("manifest.json"))
        variant = manifest["makeup"][0]["variants"][0]
        poses = variant["poses"]
        variant["poses"] = {view: poses[view], **poses}
        target = tmp_path / OFFICIAL_PACK.name
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as destination:
            for entry in source.infolist():
                if entry.filename != "manifest.json":
                    destination.writestr(entry, source.read(entry.filename))
            destination.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(OutfitPackError, match=f"cheeks safe region of {view}\\."):
        verify_makeup_layers(target, regions=frozendict(regions))
