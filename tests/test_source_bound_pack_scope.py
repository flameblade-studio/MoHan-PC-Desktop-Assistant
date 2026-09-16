"""A preview may replace only members of the active ensemble's exact pose."""

from __future__ import annotations

import copy

import pytest

from tools.art_pipeline.source_bound_pack_scope import verify_pack_scope

VIEW = "yaw+060-pitch+00"
MEMBER = "assets/robe.png"
REQUEST = {"pack_id": "example", "ensemble_id": "selected", "view_id": VIEW}


def pack_manifest():
    return {
        "id": "example",
        "ensembles": [{"id": "selected", "selections": {
            "garment": {"item_id": "robe", "variant_id": "blue"},
        }}],
        "looks": [{"id": "robe", "variants": [{
            "id": "blue", "poses": {VIEW: [{"path": MEMBER}]},
        }]}],
    }


def test_selected_exact_pose_is_allowed():
    verify_pack_scope(pack_manifest(), REQUEST, {MEMBER})


def test_cross_view_shared_member_is_rejected():
    pack = pack_manifest()
    pack["looks"][0]["variants"][0]["poses"]["yaw+045-pitch+00"] = [{"path": MEMBER}]
    with pytest.raises(ValueError, match="shared"):
        verify_pack_scope(pack, REQUEST, {MEMBER})


def test_inactive_variant_member_is_rejected():
    pack = pack_manifest()
    variant = copy.deepcopy(pack["looks"][0]["variants"][0])
    variant["id"] = "white"
    variant["poses"][VIEW] = [{"path": "assets/unused.png"}]
    pack["looks"][0]["variants"].append(variant)
    with pytest.raises(ValueError, match="outside"):
        verify_pack_scope(pack, REQUEST, {"assets/unused.png"})


def test_another_pack_is_rejected():
    pack = pack_manifest()
    pack["id"] = "other"
    with pytest.raises(ValueError, match="identity"):
        verify_pack_scope(pack, REQUEST, {MEMBER})


def test_repeated_selected_declaration_is_rejected():
    pack = pack_manifest()
    pack["looks"][0]["variants"][0]["poses"][VIEW].append({"path": MEMBER})
    with pytest.raises(ValueError, match="repeated"):
        verify_pack_scope(pack, REQUEST, {MEMBER})
