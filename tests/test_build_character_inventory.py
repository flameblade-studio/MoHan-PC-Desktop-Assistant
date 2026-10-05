"""Measured inventory completeness, reproducibility and source-evidence contracts."""

from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import zipfile
lazy import xml.etree.ElementTree as ET
lazy from pathlib import Path
lazy from typing import Any

lazy import pytest
lazy from PIL import Image

lazy from tools import build_character_inventory as builder
lazy from tools.check_four_language_docs import audit_fragment, audit_text

ROOT = Path(__file__).resolve().parents[1]
MASTER_COUNT = 24
CORE_COUNT = 600
PACK_COUNT = 2


@pytest.fixture(scope="module")
def inventory() -> dict[str, Any]:
    return builder.build_inventory(ROOT)


def test_inventory_rebuild_matches_committed_bytes(inventory: dict[str, Any]) -> None:
    expected = builder.render_inventory(inventory)
    assert builder.render_inventory(builder.build_inventory(ROOT)) == expected
    assert (ROOT / "docs/character-pack/mohan-inventory.json").read_text(encoding="utf-8") == expected
    assert (ROOT / "docs/character-pack/mohan-inventory-summary.md").read_text(encoding="utf-8") == builder.render_summary(inventory)
    paths = [row["path"] for row in inventory["files"]]
    assert paths == sorted(set(paths))
    assert str(ROOT) not in expected
    assert "timestamp" not in inventory


def test_every_file_hash_image_and_reader_is_measured(inventory: dict[str, Any]) -> None:
    archives: dict[str, dict[str, bytes]] = {}
    sources: dict[str, list[str]] = {}
    for row in inventory["files"]:
        name = row["path"]
        if "!" in name:
            archive_name, member = name.split("!", maxsplit=1)
            if archive_name not in archives:
                with zipfile.ZipFile(ROOT / archive_name) as archive:
                    archives[archive_name] = {entry: archive.read(entry) for entry in archive.namelist() if not entry.endswith("/")}
            data = archives[archive_name][member]
        else:
            data = (ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"], name
        assert len(data) == row["bytes"], name
        if "image" in row:
            if row["image"]["mode"] == "SVG":
                attributes = ET.fromstring(data).attrib
                assert str(row["image"]["width"]) == attributes["width"]
                assert str(row["image"]["height"]) == attributes["height"]
                assert row["image"]["view_box"] == attributes.get("viewBox")
            else:
                with Image.open(io.BytesIO(data)) as image:
                    assert row["image"] == {"width": image.width, "height": image.height, "mode": image.mode}, name
        for evidence in row["readers"] + row.get("content_locations", []):
            path = evidence["path"]
            if path not in sources:
                sources[path] = (ROOT / path).read_text(encoding="utf-8").splitlines()
            assert sources[path][evidence["line"] - 1].strip() == evidence["text"]
        if row["scope"] in {"runtime_data", "product_validation_data"}:
            assert row["readers"], name


def test_formal_counts_and_archive_separation(inventory: dict[str, Any]) -> None:
    counts = inventory["runtime_file_counts"]
    assert counts["fullbody_master"] == MASTER_COUNT
    assert counts["fullbody_core_layer"] == CORE_COUNT
    assert {key: counts[key] for key in ("fullbody_blink", "fullbody_visible_hand", "fullbody_complete_frames", "fullbody_complete_masks", "fullbody_complete_oral")} == {
        "fullbody_blink": 24, "fullbody_visible_hand": 8, "fullbody_complete_frames": 156,
        "fullbody_complete_masks": 13, "fullbody_complete_oral": 33,
    }
    by_path = {row["path"]: row for row in inventory["files"]}
    for name, row in by_path.items():
        if name.startswith(("assets/pose-atlas/v4", "docs/media/")):
            assert row["scope"].startswith("excluded_"), name
    assert by_path["assets/pose-atlas/v5-base/DISPLAY-PLACEMENT.json"]["scope"] == "runtime_data"
    assert by_path["assets/pose-atlas/v5-base/yaw+000-pitch+00.blink-binding.json"]["scope"] == "runtime_data"
    assert by_path["assets/pose-atlas/v5-base/yaw+000-pitch+00.hands.json"]["scope"] == "product_validation_data"
    assert by_path["assets/expressions/cheek_native_bcc8.png"]["scope"] == "excluded_review_source"
    assert by_path["assets/expressions/cheek_native_gray_20260914.png"]["scope"] == "runtime_data"
    assert by_path["assets/mohan-taskbar-icon.png"]["scope"] == "excluded_support"
    assert counts["appearance_pack"] == PACK_COUNT
    assert any("hairstyles" in row.get("appearance_categories", []) for row in inventory["files"])
    assert any("headwear" in row.get("appearance_categories", []) for row in inventory["files"])
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT / "assets").rglob("*") if p.is_file()} <= set(by_path)


def test_lineage_is_excluded_but_actual_manifest_paths_are_retained(tmp_path: Path) -> None:
    (tmp_path / "frame.png").write_bytes(b"frame")
    (tmp_path / "review.png").write_bytes(b"review")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"frame": {"path": "frame.png", "base": {"path": "review.png"}}, "source_lineage": {"path": "review.png"}}), encoding="utf-8")
    refs = builder.manifest_references(tmp_path, manifest)
    assert set(refs) == {"frame.png"}
    assert refs["frame.png"] == [{"path": "manifest.json", "pointer": "/frame/path"}]


def test_cli_checks_both_outputs_and_detects_stale_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inventory: dict[str, Any]) -> None:
    monkeypatch.setattr(builder, "build_inventory", lambda: inventory)
    args = ["--output-dir", str(tmp_path)]
    assert builder.main(args) == 0
    assert builder.main([*args, "--check"]) == 0
    (tmp_path / "mohan-inventory-summary.md").write_text("過期摘要", encoding="utf-8")
    assert builder.main([*args, "--check"]) == 1


def test_summary_fragment_and_owner_boundaries(inventory: dict[str, Any]) -> None:
    assert not audit_text(builder.render_summary(inventory), require_h1=True)
    fragment = (ROOT / "changelog.d/mohan-character-inventory.md").read_text(encoding="utf-8")
    assert not audit_fragment(fragment)
    decisions = inventory["owner_decisions"]
    assert decisions["standalone_download_design"] is True
    for key in ("pack_visibility", "character_asset_license", "dlc_relationship"):
        assert decisions[key] == "owner_decision_pending"
    for row in inventory["files"]:
        if row["scope"] == "embedded_code":
            assert row["migration"] == builder.EMBEDDED
            assert row["symbols"]
