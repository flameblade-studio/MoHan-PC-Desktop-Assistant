"""Generation-2 PoseAtlas assets must retain owner-authorized provenance."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy from domain.constants import POSE_ATLAS_ROOT_NAME

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AUTHORIZATION = "confirmed_by_rights_holder_2026-08-16"
EXPECTED_REDISTRIBUTION = "authorized_under_project_license"
EXPECTED_VIEW_COUNT = 24


def test_generation_two_pose_atlas_has_approved_provenance() -> None:
    atlas_root = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
    metadata = json.loads(
        (atlas_root / "BUILD-METADATA.json").read_text(encoding="utf-8")
    )
    assert metadata["source_authorization"] == EXPECTED_AUTHORIZATION
    assert metadata["redistribution"] == EXPECTED_REDISTRIBUTION
    assert metadata["formal_promotion"] == "approved"
    assert metadata["status"] == "release-assets"
    assert len(metadata["views"]) == EXPECTED_VIEW_COUNT
    for view in metadata["views"]:
        path = atlas_root / f"{view['view_id']}.png"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == view["normalized_sha256"]
