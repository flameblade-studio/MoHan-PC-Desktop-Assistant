"""Reproducible MoHan character-pack builder contracts."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from pathlib import Path

lazy import pytest

lazy from domain.character_pack.validation import validate_character_pack
lazy from domain.version_info import FALLBACK_VERSION
lazy from tools import build_character_pack as builder

ROOT = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024
PACK_SCOPES = frozenset({"runtime_data", "product_validation_data"})


def _write_json(path: Path, value: object) -> bytes:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def _inventory_row(path: str, data: bytes, category: str, scope: str = "runtime_data") -> dict[str, object]:
    return {
        "path": path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "category": category,
        "scope": scope,
    }


def _synthetic_inputs(root: Path) -> tuple[Path, Path, dict[str, bytes]]:
    profile = {
        "schema": "flameblade.character-identity-profile.v1",
        "schema_version": 1,
        "defaults": {"assistant_name": "墨寒"},
        "personalization": {"assistant_tokens": ["墨寒", "MoHan"]},
    }
    payloads: dict[str, bytes] = {}
    profile_path = "assets/characters/mohan/persona/profile.json"
    payloads[profile_path] = _write_json(root / profile_path, profile)
    names = {"zh-TW": ("墨寒", "寒"), "zh-CN": ("墨寒", "寒"), "en": ("MoHan", "Han"), "ja-JP": ("墨寒", "寒")}
    persona_paths: dict[str, str] = {}
    for language, (display_name, alias) in names.items():
        relative = f"assets/characters/mohan/persona/{language}.json"
        persona_paths[language] = relative
        payloads[relative] = _write_json(
            root / relative,
            {
                "schema": "flameblade.character-persona.v1",
                "schema_version": 1,
                "identity": {"display_name": display_name, "assistant_alias": alias},
            },
        )
    body_profile = {"id": "mohan-body-v2", "version": 2}
    rig_path = "assets/characters/mohan/rig/rig-manifest.json"
    payloads[rig_path] = _write_json(
        root / rig_path,
        {"schema": "example.rig.v1", "schema_version": 1, "body_profile": body_profile},
    )
    source_ref = "assets/evidence/source.json"
    approval_ref = "assets/evidence/approval.json"
    payloads[source_ref] = _write_json(root / source_ref, {"schema": "example.source.v1"})
    payloads[approval_ref] = _write_json(root / approval_ref, {"schema": "example.approval.v1"})
    rows = [
        _inventory_row(path, data, "character_persona_data")
        for path, data in payloads.items()
    ]
    rows.append({
        **_inventory_row("assets/archive.mohan-outfit!manifest.json", b"ignored", "appearance_pack_member"),
        "path": "assets/archive.mohan-outfit!manifest.json",
    })
    excluded = _write_json(root / "assets/excluded.json", {"excluded": True})
    rows.append(_inventory_row("assets/excluded.json", excluded, "archive_or_support", "excluded_support"))
    inventory = root / "inventory.json"
    _write_json(inventory, {"files": rows})
    major = int(FALLBACK_VERSION.split(".", maxsplit=1)[0])
    pending_license = {
        "status": "owner_decision_pending",
        "rights_holder": "CHOU MING HUA",
        "license_expression": None,
        "notice_path": None,
    }
    source = root / "pack-source.json"
    _write_json(
        source,
        {
            "schema": builder.BUILD_SOURCE_SCHEMA,
            "schema_version": 1,
            "pack_id": "flameblade.mohan",
            "pack_version": "1.0.0",
            "character_id": "mohan",
            "identity": {"profile": profile_path, "personas": persona_paths},
            "engine_compatibility": {
                "api_version": 1,
                "min_engine_version": FALLBACK_VERSION,
                "max_engine_version_exclusive": f"{major + 1}.0.0",
                "required_features": [],
            },
            "distribution": {
                "standalone_downloadable": True,
                "access": "private",
                "redistribution": "owner_decision_pending",
            },
            "licenses": {
                "program_data": pending_license,
                "character_art": pending_license,
                "persona_dialogue": pending_license,
                "voice": pending_license,
            },
            "source_refs": [{"path": source_ref, "scope": "Synthetic source fixture only."}],
            "approval_refs": [{"path": approval_ref, "scope": "Synthetic approval fixture only."}],
            "components": [{
                "id": "mohan.rig",
                "kind": "fullbody_rig",
                "schema": "example.rig.v1",
                "path": rig_path,
                "required": True,
                "body_profile": body_profile,
            }],
            "validation_limits": {
                "max_archive_bytes": 8 * MIB,
                "max_zip_directory_bytes": MIB,
                "max_manifest_bytes": MIB,
                "max_file_bytes": MIB,
                "max_total_bytes": 8 * MIB,
                "max_files": 128,
                "max_compression_ratio": 100,
            },
        },
    )
    return inventory, source, payloads


def _manifest_from_zip(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("manifest.json"))


def test_zip_build_is_byte_for_byte_deterministic_and_valid(tmp_path: Path) -> None:
    inventory, source, payloads = _synthetic_inputs(tmp_path / "repo")
    first_path = tmp_path / "first.zip"
    second_path = tmp_path / "second.zip"
    first = builder.build_character_pack(
        first_path,
        output_format="zip",
        repo_root=tmp_path / "repo",
        inventory_path=inventory,
        source_path=source,
    )
    second = builder.build_character_pack(
        second_path,
        output_format="zip",
        repo_root=tmp_path / "repo",
        inventory_path=inventory,
        source_path=source,
    )
    assert first.package_hash == second.package_hash
    assert first_path.read_bytes() == second_path.read_bytes()
    manifest = _manifest_from_zip(first_path)
    assert manifest["package_hash"] == first.package_hash
    result = validate_character_pack(
        first_path,
        engine_version=FALLBACK_VERSION,
        limits=first.validation_limits,
    )
    assert result.valid, result.issues
    assert result.package_hash == first.package_hash
    with zipfile.ZipFile(first_path) as archive:
        expected_names = ["manifest.json", *sorted(payloads)]
        assert archive.namelist() == expected_names
        for info in archive.infolist():
            assert info.date_time == builder.FIXED_ZIP_TIME
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.extra == b""
            assert info.comment == b""
        for path, data in payloads.items():
            assert archive.read(path) == data


def test_manifest_projects_identity_rights_components_and_original_paths(tmp_path: Path) -> None:
    inventory, source, payloads = _synthetic_inputs(tmp_path / "repo")
    output = tmp_path / "character"
    built = builder.build_character_pack(
        output,
        output_format="directory",
        repo_root=tmp_path / "repo",
        inventory_path=inventory,
        source_path=source,
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["display_names"] == {"zh-TW": "墨寒", "zh-CN": "墨寒", "en": "MoHan", "ja-JP": "墨寒"}
    assert manifest["character"] == {
        "id": "mohan",
        "canonical_name": "墨寒",
        "aliases": ["MoHan", "寒", "Han"],
    }
    assert manifest["distribution"] == {
        "standalone_downloadable": True,
        "access": "private",
        "redistribution": "owner_decision_pending",
    }
    assert {entry["status"] for entry in manifest["licenses"].values()} == {"owner_decision_pending"}
    assert {entry["rights_holder"] for entry in manifest["licenses"].values()} == {"CHOU MING HUA"}
    assert manifest["components"][0]["body_profile"] == {"id": "mohan-body-v2", "version": 2}
    assert "dependencies" not in manifest
    assert [entry["path"] for entry in manifest["files"]] == sorted(payloads)
    assert all((output / path).read_bytes() == data for path, data in payloads.items())
    manifest_text = (output / "manifest.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in manifest_text
    assert "timestamp" not in manifest_text
    result = validate_character_pack(
        output,
        engine_version=FALLBACK_VERSION,
        limits=built.validation_limits,
    )
    assert result.valid, result.issues


def test_stale_inventory_fails_before_creating_output(tmp_path: Path) -> None:
    inventory, source, _payloads = _synthetic_inputs(tmp_path / "repo")
    document = json.loads(inventory.read_text(encoding="utf-8"))
    document["files"][0]["sha256"] = "0" * 64
    _write_json(inventory, document)
    output = tmp_path / "rejected"
    with pytest.raises(builder.CharacterPackBuildError, match="stale"):
        builder.build_character_pack(
            output,
            output_format="directory",
            repo_root=tmp_path / "repo",
            inventory_path=inventory,
            source_path=source,
        )
    assert not output.exists()


def test_repository_mohan_pack_builds_and_validates(tmp_path: Path) -> None:
    output = tmp_path / "flameblade.mohan"
    expected_files, expected_bytes = _repository_payload_totals()
    built = builder.build_character_pack(output, output_format="directory")
    assert built.payload_files == expected_files
    assert built.payload_bytes == expected_bytes
    assert built.validation_limits.max_archive_bytes == 768 * MIB
    assert built.validation_limits.max_total_bytes == 768 * MIB
    result = validate_character_pack(
        output,
        engine_version=FALLBACK_VERSION,
        limits=built.validation_limits,
    )
    assert result.valid, result.issues
    assert result.checked_files == expected_files
    assert result.checked_bytes == expected_bytes
    assert result.package_hash == built.package_hash
    manifest = _manifest_from_directory(output)
    assert manifest["pack_id"] == "flameblade.mohan"
    assert manifest["character"]["id"] == "mohan"
    assert manifest["distribution"]["access"] == "private"
    assert builder.DEFAULT_SOURCE.as_posix() not in {
        str(entry["path"]) for entry in manifest["files"]
    }


def _manifest_from_directory(path: Path) -> dict[str, object]:
    return json.loads((path / "manifest.json").read_text(encoding="utf-8"))


def _repository_payload_totals(character_id: str = "mohan") -> tuple[int, int]:
    inventory = json.loads(
        (ROOT / builder.DEFAULT_INVENTORY).read_text(encoding="utf-8")
    )
    selected = [
        row
        for row in inventory["files"]
        if row["scope"] in PACK_SCOPES and "!" not in row["path"]
        and (
            not row["path"].startswith("assets/characters/")
            or row["path"].startswith(f"assets/characters/{character_id}/")
        )
    ]
    return len(selected), sum(row["bytes"] for row in selected)


def test_character_data_categories_map_to_explicit_license_components() -> None:
    assert builder._license_component("assets/characters/mohan/dialogue/runtime.json", "character_runtime_dialogue_data") == "persona_dialogue"
    assert builder._license_component("assets/characters/mohan/persona/ui-identifiers.json", "character_ui_identifier_data") == "persona_dialogue"
    assert builder._license_component("assets/characters/mohan/voice/profile.json", "character_voice_data") == "voice"
    assert builder._license_component("assets/characters/mohan/rig/rig-manifest.json", "character_rig_data") == "program_data"
    with pytest.raises(builder.CharacterPackBuildError, match="no license component"):
        builder._license_component("assets/characters/mohan/new/unknown.json", "character_unregistered_data")
