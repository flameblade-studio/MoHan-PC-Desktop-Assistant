"""Measured inventory completeness, reproducibility and source-evidence contracts."""

from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import zipfile
lazy from xml.etree import ElementTree as ET
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
DERIVATIVE_COUNT = 234
DERIVATIVE_COUNTS = {
    "fullbody_blink": 24,
    "fullbody_visible_hand": 8,
    "fullbody_complete_frames": 156,
    "fullbody_complete_masks": 13,
    "fullbody_complete_oral": 33,
}


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
    assert {key: counts[key] for key in DERIVATIVE_COUNTS} == DERIVATIVE_COUNTS
    assert sum(DERIVATIVE_COUNTS.values()) == DERIVATIVE_COUNT
    by_path = {row["path"]: row for row in inventory["files"]}
    formal_image_categories = {
        "fullbody_master", "fullbody_core_layer", *DERIVATIVE_COUNTS,
    }
    formal_images = [
        row for row in inventory["files"]
        if row["scope"] == "runtime_data" and row["category"] in formal_image_categories
    ]
    assert len(formal_images) == MASTER_COUNT + CORE_COUNT + DERIVATIVE_COUNT
    assert all(
        row["image"] == {"width": 1024, "height": 1536, "mode": "RGBA"}
        for row in formal_images
    )
    assert all(row["migration"] == builder.DIRECT for row in formal_images)
    for name, row in by_path.items():
        if name.startswith(("assets/pose-atlas/v4", "docs/media/")):
            assert row["scope"].startswith("excluded_"), name
    assert by_path["assets/pose-atlas/v5-base/DISPLAY-PLACEMENT.json"]["scope"] == "runtime_data"
    assert by_path["assets/pose-atlas/v5-base/yaw+000-pitch+00.blink-binding.json"]["scope"] == "runtime_data"
    assert by_path["assets/pose-atlas/v5-base/yaw+000-pitch+00.hands.json"]["scope"] == "product_validation_data"
    assert by_path["assets/expressions/cheek_native_bcc8.png"]["scope"] == "excluded_review_source"
    assert by_path["assets/expressions/cheek_native_gray_20260914.png"]["scope"] == "runtime_data"
    taskbar = by_path["assets/mohan-taskbar-icon.png"]
    assert taskbar["scope"] == "excluded_product_build_output"
    assert taskbar["category"] == "ui_character_icon_build_output"
    assert "mohan-halfbody.ico" in taskbar["reason"]
    assert counts["appearance_pack"] == PACK_COUNT
    assert any("hairstyles" in row.get("appearance_categories", []) for row in inventory["files"])
    assert any("headwear" in row.get("appearance_categories", []) for row in inventory["files"])
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT / "assets").rglob("*") if p.is_file()} <= set(by_path)


def test_non_product_roots_are_structured_and_outside_payload(inventory: dict[str, Any]) -> None:
    assert inventory["non_product_roots"] == [dict(row) for row in builder.NON_PRODUCT_ROOTS]
    paths = {row["path"] for row in inventory["non_product_roots"]}
    assert {
        ".quality-tmp/", "artifacts/", "assets/pose-atlas/v4/",
        "assets/pose-atlas/v4-layered/", "assets/pose-atlas/v4-source/",
        "assets/pose-atlas/v4-working/", "docs/media/",
        "docs/release-evidence/", "tests/golden/",
    } == paths
    assert all(not row["path"].startswith(tuple(paths)) for row in inventory["files"] if row["scope"] == "runtime_data")


CHARACTER_DATA_FILE_COUNT = 13  # 11 persona/dialogue/voice files + rig manifest + expression catalog


def test_character_data_files_are_runtime_data(inventory: dict[str, Any]) -> None:
    rows = {row["path"]: row for row in inventory["files"] if row["path"].startswith("assets/characters/mohan/")}
    build_only = {"assets/characters/mohan/README.md", "assets/characters/mohan/pack-source.json"}
    data_rows = {path: row for path, row in rows.items() if path.endswith(".json") and path not in build_only}
    assert len(data_rows) == CHARACTER_DATA_FILE_COUNT
    assert {row["scope"] for row in data_rows.values()} == {"runtime_data"}
    assert {rows[path]["scope"] for path in build_only} == {"excluded_support"}


def test_required_embedded_content_locations_are_indexed(inventory: dict[str, Any]) -> None:
    required = {
        "identity_persona_dialogue": {
            "domain/persona_defaults.py", "domain/app_profile.py", "domain/language_support.py",
            "infrastructure/db.py", "integrations/ai_client.py",
            "application/companion_phrasebook.py", "application/special_occasion.py",
            "application/wellbeing_reminder.py", "application/wellbeing_runtime.py",
            "presentation/ui_localization.py", "presentation/ui_localization_en.py",
            "presentation/ui_localization_ja.py", "presentation/auxiliary_ui_localization.py",
            "presentation/flagship/localization_remote_vision.py",
        },
        "voice_preferences": {
            "domain/speech_configuration.py", "application/presentation_ports.py",
            "presentation/dashboard_voice.py", "integrations/speech_voice_catalog.py",
            "integrations/azure_voice_catalog.py",
        },
        "rig_angle_expression_pose_rules": {
            "domain/character_body_profile.py", "domain/constants.py", "domain/character_pose.py",
            "domain/companion_animation_contract.py", "domain/expression_system.py",
            "presentation/companion_wait_expression.py", "presentation/companion_face_assets.py",
            "presentation/companion_visual_physics.py",
        },
    }
    by_path = {row["path"]: row for row in inventory["files"]}
    for category, paths in required.items():
        for path in paths:
            row = by_path[path]
            assert row["scope"] == "embedded_code"
            assert row["migration"] == builder.EMBEDDED
            assert category in row["content_categories"]
            assert row["symbols"]
            line_count = len((ROOT / path).read_text(encoding="utf-8").splitlines())
            assert all(1 <= symbol["line"] <= symbol["end_line"] <= line_count for symbol in row["symbols"])


def test_lineage_is_excluded_but_actual_manifest_paths_are_retained(tmp_path: Path) -> None:
    (tmp_path / "frame.png").write_bytes(b"frame")
    (tmp_path / "review.png").write_bytes(b"review")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"frame": {"path": "frame.png", "base": {"path": "review.png"}}, "source_lineage": {"path": "review.png"}}), encoding="utf-8")
    refs = builder.manifest_references(tmp_path, manifest)
    assert set(refs) == {"frame.png"}
    assert refs["frame.png"] == [{"path": "manifest.json", "pointer": "/frame/path"}]


def test_reader_evidence_names_the_actual_format_and_function(inventory: dict[str, Any]) -> None:
    by_path = {row["path"]: row for row in inventory["files"]}
    for name in (
        "assets/expressions/complete-expressions/manifest.json",
        "assets/expressions/reviewed-garments/manifest.json",
        "assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json",
        "assets/pose-atlas/v5-garment-visibility/manifest.json",
        "assets/expressions/source-bound-exasperated/receipt.json",
    ):
        assert "read_text" in by_path[name]["readers"][0]["text"], name
    row = by_path["assets/pose-atlas/v5-base-layered/complete-expressions/frames/minus015-a-closed.rgba.png"]
    evidence = row["readers"][0]
    source = by_path[evidence["path"]]
    resolver = next(symbol for symbol in source["symbols"] if symbol["name"] == "_resolve_complete_expression_asset")
    assert resolver["line"] < evidence["line"] <= resolver["end_line"]
    assert "read_bytes" in evidence["text"]
    assert any(location["text"].startswith("CANONICAL_YAWS =") for location in by_path["domain/pose_pack.py"]["content_locations"])


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
    assert decisions["pack_visibility"] == "private_repository"
    for key in ("character_asset_license", "dlc_relationship"):
        assert decisions[key] == "owner_decision_pending"
    for row in inventory["files"]:
        if row["scope"] == "embedded_code":
            assert row["migration"] == builder.EMBEDDED
            assert row["symbols"]
