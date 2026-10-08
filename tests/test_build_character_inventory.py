"""Measured inventory completeness, reproducibility and source-evidence contracts."""

from __future__ import annotations

lazy import ast
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
MIN_WORK_PACKAGE_COUNT = 3
MAX_WORK_PACKAGE_COUNT = 5
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


@pytest.fixture(scope="module")
def worklist(inventory: dict[str, Any]) -> dict[str, Any]:
    return builder.build_extraction_worklist(inventory)


def test_inventory_rebuild_matches_committed_bytes(inventory: dict[str, Any]) -> None:
    expected = builder.render_inventory(inventory)
    assert builder.render_inventory(builder.build_inventory(ROOT)) == expected
    assert (ROOT / "docs/character-pack/mohan-inventory.json").read_text(encoding="utf-8") == expected
    assert (ROOT / "docs/character-pack/mohan-inventory-summary.md").read_text(encoding="utf-8") == builder.render_summary(inventory)
    paths = [row["path"] for row in inventory["files"]]
    assert paths == sorted(set(paths))
    assert str(ROOT) not in expected
    assert "timestamp" not in inventory


def test_worklist_rebuild_matches_committed_bytes(
    worklist: dict[str, Any],
) -> None:
    expected = builder.render_extraction_worklist(worklist)
    assert builder.render_extraction_worklist(worklist) == expected
    assert (
        ROOT / "docs/character-pack/extraction-worklist.json"
    ).read_text(encoding="utf-8") == expected
    assert (
        ROOT / "docs/character-pack/extraction-worklist.md"
    ).read_text(encoding="utf-8") == builder.render_extraction_summary(worklist)
    assert str(ROOT) not in expected
    assert "timestamp" not in worklist


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


CHARACTER_DATA_FILE_COUNT = 15  # 12 persona/dialogue/voice/UI files + rig manifest + runtime bindings + expression catalog


def test_character_data_files_are_runtime_data(inventory: dict[str, Any]) -> None:
    rows = {row["path"]: row for row in inventory["files"] if row["path"].startswith("assets/characters/mohan/")}
    build_only = {"assets/characters/mohan/README.md", "assets/characters/mohan/pack-source.json"}
    data_rows = {path: row for path, row in rows.items() if path.endswith(".json") and path not in build_only}
    assert len(data_rows) == CHARACTER_DATA_FILE_COUNT
    assert {row["scope"] for row in data_rows.values()} == {"runtime_data"}
    assert rows["assets/characters/mohan/rig/runtime-bindings.json"]["category"] == "character_runtime_binding_data"
    assert rows["assets/characters/mohan/persona/ui-identifiers.json"]["category"] == "character_ui_identifier_data"
    assert {rows[path]["scope"] for path in build_only} == {"excluded_support"}


def test_only_actual_embedded_content_is_counted(inventory: dict[str, Any]) -> None:
    rows = [row for row in inventory["files"] if row["scope"] == "embedded_code"]
    by_path = {row["path"]: row for row in rows}
    assert inventory["scope_counts"]["embedded_code"] == len(rows)
    assert set(inventory["embedded_code_classification_counts"]) <= {
        "engine_extract", "product_shell_allowed", "ui_text_reference",
    }
    assert {"engine_extract", "product_shell_allowed"} <= set(inventory["embedded_code_classification_counts"])
    assert {
        "domain/outfit_pack_official.py",
        "infrastructure/app_resources.py",
        "presentation/ui_localization.py",
    } <= set(by_path)
    assert "domain/expression_system.py" not in by_path
    assert by_path["domain/constants.py"]["classification"] == "product_shell_allowed"
    for row in rows:
        assert row["migration"] == builder.EMBEDDED
        assert row["classification"] in builder.CLASSIFICATION_REASONS
        assert row["classification_reason"].strip()
        assert row["content_locations"]
        assert row["suggested_data_targets"]
        line_count = len((ROOT / row["path"]).read_text(encoding="utf-8").splitlines())
        for evidence in row["content_locations"]:
            assert evidence["rule"].strip()
            assert evidence["matched"]
            assert evidence["description"].strip()
            assert evidence["suggested_data_target"] in row["suggested_data_targets"]
            assert 1 <= evidence["line"] <= line_count
        assert all(
            1 <= symbol["line"] <= symbol["end_line"] <= line_count
            for symbol in row["symbols"]
        )


def test_moved_content_and_hint_only_files_are_not_counted(
    inventory: dict[str, Any],
) -> None:
    embedded = {
        row["path"] for row in inventory["files"]
        if row["scope"] == "embedded_code"
    }
    moved = {
        "application/companion_phrasebook.py",
        "application/special_occasion.py",
        "application/wellbeing_reminder.py",
        "application/wellbeing_runtime.py",
        "domain/app_profile.py",
        "domain/character_body_profile.py",
        "domain/character_pose.py",
        "domain/companion_animation_contract.py",
        "domain/persona_defaults.py",
        "domain/speech_configuration.py",
        "infrastructure/db.py",
        "integrations/azure_voice_catalog.py",
        "integrations/speech_voice_catalog.py",
    }
    assert not moved & embedded
    hints = {row["path"]: row for row in inventory["manual_review_hints"]}
    assert moved <= set(hints)
    assert {hints[path]["status"] for path in moved} == {"review_hint_only"}
    assert all(not hints[path]["evidence_rules"] for path in moved)


def test_literal_rules_ignore_comments_docstrings_and_manual_hints() -> None:
    source = '''"""墨寒、主上、coral and 1024x1536 are documentation only."""
# 墨寒的 v5-base 備忘
VALUE = "generic"
'''
    assert builder._content_evidence("domain/example.py", source) == []
    evidence = builder._content_evidence(
        "domain/example.py",
        'VALUE = "主上，墨寒自赤焰劍歸來。"\n',
    )
    assert {row["rule"] for row in evidence} == {
        "character_name_literal", "character_title_or_dialogue_literal",
    }


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
    source = (ROOT / evidence["path"]).read_text(encoding="utf-8")
    tree = builder._parsed_python(source)
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_resolve_complete_expression_asset"
    )
    assert resolver.lineno < evidence["line"] <= resolver.end_lineno
    assert "read_bytes" in evidence["text"]


def test_cli_checks_both_outputs_and_detects_stale_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inventory: dict[str, Any]) -> None:
    monkeypatch.setattr(builder, "build_inventory", lambda: inventory)
    args = ["--output-dir", str(tmp_path)]
    assert builder.main(args) == 0
    assert builder.main([*args, "--check"]) == 0
    assert (tmp_path / "extraction-worklist.json").is_file()
    assert (tmp_path / "extraction-worklist.md").is_file()
    (tmp_path / "extraction-worklist.md").write_text("過期摘要", encoding="utf-8")
    assert builder.main([*args, "--check"]) == 1


def test_work_packages_are_exclusive_and_product_shell_is_reasoned(
    inventory: dict[str, Any],
    worklist: dict[str, Any],
) -> None:
    counts = worklist["counts"]
    assert MIN_WORK_PACKAGE_COUNT <= counts["work_packages"] <= MAX_WORK_PACKAGE_COUNT
    assert counts["true_extraction_files"] == (
        counts["engine_extract_files"] + counts["ui_text_reference_files"]
    )
    package_paths = []
    for package in worklist["work_packages"]:
        assert package["file_count"] == len(package["exclusive_files"])
        assert package["objective"].strip()
        assert package["exclusions"].strip()
        package_paths.extend(package["exclusive_files"])
    pending_paths = [row["path"] for row in worklist["extraction_items"]]
    assert sorted(package_paths) == sorted(pending_paths)
    assert len(package_paths) == len(set(package_paths))
    assert all(row["work_package"] for row in worklist["extraction_items"])
    allowlist = inventory["product_shell_allowlist"]
    assert len({row["path"] for row in allowlist}) == len(allowlist)
    assert all(row["reason"].strip() for row in allowlist)
    allowed_paths = {row["path"] for row in worklist["product_shell_allowed"]}
    classified_allowed = {
        row["path"] for row in inventory["files"]
        if row.get("classification") == "product_shell_allowed"
    }
    assert allowed_paths == classified_allowed


def test_summary_fragment_and_owner_boundaries(
    inventory: dict[str, Any],
    worklist: dict[str, Any],
) -> None:
    assert not audit_text(builder.render_summary(inventory), require_h1=True)
    assert not audit_text(builder.render_extraction_summary(worklist), require_h1=True)
    fragment = (
        ROOT / "changelog.d/honest-character-extraction-measure.md"
    ).read_text(encoding="utf-8")
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
            assert row["content_locations"]


def test_appearance_pack_identifiers_are_detected() -> None:
    source = 'PACK = "mohan.official.blue-white-hanfu"\nLOOK = "mohan-signature"\nSCHEMA = "mohan.makeup-safe-regions.v2"\n'
    evidence = builder._content_evidence("domain/example.py", source)
    matched = {row["matched"] for row in evidence if row["rule"] == "character_appearance_pack_identifier"}
    assert matched == {"mohan.official.blue-white-hanfu", "mohan-signature"}


def test_multiline_literal_evidence_points_at_the_matching_line() -> None:
    source = 'TEXT = (\n    "first line "\n    "主上 second line"\n)\n'
    evidence = builder._content_evidence("domain/example.py", source)
    row = next(row for row in evidence if row["matched"] == "主上")
    assert row["line"] == source.splitlines().index('    "主上 second line"') + 1
    assert "主上" in row["text"]


def test_inventory_test_is_mapped_to_every_scanned_source() -> None:
    from tools import generate_test_impact_map as impact

    rules = json.loads((ROOT / "tests/impact_map.json").read_text(encoding="utf-8"))["rules"]
    test_names = frozenset(path.name for path in (ROOT / "tests").glob("test_*.py"))
    for path in builder._python_sources(ROOT):
        assert "test_build_character_inventory.py" in impact.mapped_tests_for_path(path, rules, test_names), path


def test_product_identity_literals_are_product_shell_not_extraction() -> None:
    source = (
        'NAME = "墨寒桌面助理 v{version}"\n'
        'AGENT = "MoHan-Desktop-Assistant/2.0"\n'
        'LABEL = f"MoHan {provider_id} OAuth token"\n'
    )
    evidence = builder._content_evidence("presentation/example.py", source)
    assert evidence
    assert {row["rule"] for row in evidence} == {"product_identity_literal"}
    assert builder._source_classification("presentation/example.py", evidence) == "product_shell_allowed"
    mixed = builder._content_evidence("presentation/example.py", source + 'GREETING = "主上，墨寒在此。"\n')
    assert builder._source_classification("presentation/example.py", mixed) != "product_shell_allowed"


def test_product_identity_exempts_only_its_own_span() -> None:
    source = 'LABEL = f"MoHan {provider_id} OAuth token — 墨寒會回覆主上"\n'
    evidence = builder._content_evidence("presentation/example.py", source)
    rules = {(row["matched"], row["rule"]) for row in evidence}
    assert ("MoHan", "product_identity_literal") in rules
    assert ("墨寒", "character_name_literal") in rules
    assert builder._source_classification("presentation/example.py", evidence) != "product_shell_allowed"
