"""Product-neutral Huapu package and compatibility-facade contracts."""

from __future__ import annotations

lazy import ast
lazy import json
lazy import zipfile
lazy from pathlib import Path

lazy from domain.character_pack.models import ValidationLimits
lazy from domain.character_pack.validation import SCHEMA
lazy from huapu import approved_install, character_pack_lock, pose_audit, pose_release, rendering
lazy from huapu.character_pack_builder import (
    BUILD_SOURCE_SCHEMA,
    CharacterPackBuildSettings,
    build_character_pack,
)
lazy from huapu.hashing import digest_file
lazy from huapu.inventory import (
    AssetInventoryConfig,
    AssetSpec,
    build_asset_inventory,
    classify_character_asset_path,
)
lazy from huapu.licenses import LicenseClaim, LicensePolicy, check_license_allowlist
lazy from huapu.receipts import RECEIPT_SCHEMA_VERSION, receipt_for_files, render_receipt
lazy from huapu.schema import SchemaVersion

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
MIB = 1024 * 1024


def _imports(path: Path) -> tuple[tuple[str, int], ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, node.lineno))
    return tuple(found)


def test_huapu_has_no_product_or_private_runtime_imports() -> None:
    violations: list[str] = []
    forbidden_roots = {"application", "infrastructure", "integrations", "presentation", "tools"}
    for path in sorted((ROOT / "huapu").rglob("*.py")):
        for target, line in _imports(path):
            target_root = target.partition(".")[0]
            forbidden_domain = target_root == "domain" and not target.startswith("domain.character_pack")
            if target_root in forbidden_roots or forbidden_domain:
                violations.append(f"{path.relative_to(ROOT).as_posix()}:{line} -> {target}")
    assert not violations, "Huapu imports product-private modules:\n" + "\n".join(violations)


def test_huapu_public_modules_resolve_without_product_ui() -> None:
    modules = (approved_install, character_pack_lock, pose_audit, pose_release, rendering)
    assert tuple(module.__name__ for module in modules) == (
        "huapu.approved_install",
        "huapu.character_pack_lock",
        "huapu.pose_audit",
        "huapu.pose_release",
        "huapu.rendering",
    )


def test_existing_huapu_commands_are_thin_compatibility_entries() -> None:
    limits = {
        "tools/build_character_inventory.py": 120,
        "tools/build_character_pack.py": 180,
        "tools/verify_character_pack_lock.py": 170,
        "tools/art_pipeline/approved_asset_install.py": 90,
        "tools/audit_pose_atlas_working.py": 110,
        "tools/check_pose_atlas_release.py": 100,
    }
    measured = {
        relative: len((ROOT / relative).read_text(encoding="utf-8").splitlines())
        for relative in limits
    }
    assert all(measured[path] <= limit for path, limit in limits.items()), measured


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _fake_character(root: Path) -> tuple[list[AssetSpec], dict[str, object]]:
    profile_path = "characters/aria/persona/profile.json"
    persona_paths = {
        language: f"characters/aria/persona/{language}.json"
        for language in LANGUAGES
    }
    rig_path = "characters/aria/rig/manifest.json"
    source_path = "characters/aria/evidence/source.json"
    approval_path = "characters/aria/evidence/approval.json"
    foreign_path = "characters/bea/persona/profile.json"
    _write_json(
        root / profile_path,
        {
            "schema": "example.identity.v1",
            "schema_version": 1,
            "defaults": {"assistant_name": "Aria"},
            "personalization": {"assistant_tokens": ["Aria", "Ari"]},
        },
    )
    for language, path in persona_paths.items():
        _write_json(
            root / path,
            {
                "schema": "example.persona.v1",
                "schema_version": 1,
                "identity": {
                    "display_name": f"Aria {language}",
                    "assistant_alias": f"Ari-{language}",
                },
            },
        )
    body_profile = {"id": "aria-body-v1", "version": 1}
    _write_json(
        root / rig_path,
        {"schema": "example.rig.v1", "schema_version": 1, "body_profile": body_profile},
    )
    _write_json(root / source_path, {"schema": "example.source.v1"})
    _write_json(root / approval_path, {"schema": "example.approval.v1"})
    _write_json(root / foreign_path, {"schema": "example.identity.v1"})
    paths = [
        profile_path,
        *persona_paths.values(),
        rig_path,
        source_path,
        approval_path,
        foreign_path,
    ]
    specs = [AssetSpec(path, "fixture_data", "runtime_data") for path in paths]
    source = {
        "schema": BUILD_SOURCE_SCHEMA,
        "schema_version": 1,
        "pack_id": "example.aria",
        "pack_version": "1.0.0",
        "character_id": "aria",
        "identity": {"profile": profile_path, "personas": persona_paths},
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "1.2.3",
            "max_engine_version_exclusive": "2.0.0",
            "required_features": [],
        },
        "distribution": {
            "standalone_downloadable": True,
            "access": "owner_decision_pending",
            "redistribution": "owner_decision_pending",
        },
        "licenses": _pending_licenses(),
        "source_refs": [{"path": source_path, "scope": "Synthetic fixture source only."}],
        "approval_refs": [{"path": approval_path, "scope": "Synthetic fixture approval only."}],
        "components": [
            {
                "id": "aria.rig",
                "kind": "fullbody_rig",
                "schema": "example.rig.v1",
                "path": rig_path,
                "required": True,
                "body_profile": body_profile,
            }
        ],
        "dependencies": [
            {
                "id": "example.aria-outfit",
                "kind": "outfit_pack",
                "min_version": "1.0.0",
                "max_version_exclusive": "2.0.0",
                "required": False,
            }
        ],
        "validation_limits": _validation_limits(),
    }
    return specs, source


def _pending_licenses() -> dict[str, object]:
    result: dict[str, object] = {}
    for component in ("program_data", "character_art", "persona_dialogue", "voice"):
        result[component] = {
            "status": "owner_decision_pending",
            "rights_holder": "Fixture Rights Holder",
            "license_expression": None,
            "notice_path": None,
        }
    return result


def _validation_limits() -> dict[str, int]:
    return {
        "max_archive_bytes": 8 * MIB,
        "max_zip_directory_bytes": MIB,
        "max_manifest_bytes": MIB,
        "max_file_bytes": MIB,
        "max_total_bytes": 8 * MIB,
        "max_files": 128,
        "max_compression_ratio": 100,
    }


def _license_component(_path: str, _category: str) -> str:
    return "program_data"


def _no_special_component(_path: Path, _schema: str) -> bool:
    return False


def test_fake_character_inventory_and_pack_build_are_product_neutral(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    specs, source = _fake_character(repository)
    inventory = build_asset_inventory(
        repository,
        AssetInventoryConfig(
            SchemaVersion("example.character-inventory", 1),
            "example.aria",
            {".json": "application/json"},
        ),
        specs,
    )
    inventory_path = repository / "inventory.json"
    source_path = repository / "pack-source.json"
    _write_json(inventory_path, inventory)
    _write_json(source_path, source)
    settings = CharacterPackBuildSettings(
        manifest_schema=SCHEMA,
        build_source_schema=BUILD_SOURCE_SCHEMA,
        characters_root="characters",
        engine_version="1.2.3",
        languages=LANGUAGES,
        pack_scopes=frozenset({"runtime_data"}),
        media_types={".json": "application/json"},
        identity_profile_schema="example.identity.v1",
        persona_schema="example.persona.v1",
        rig_schema="example.rig.v1",
        license_classifier=_license_component,
        special_component_validator=_no_special_component,
    )
    output = tmp_path / "aria-character.zip"
    result = build_character_pack(
        output,
        output_format="zip",
        repo_root=repository,
        inventory_path=inventory_path,
        source_path=source_path,
        settings=settings,
    )
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert result.package_hash == manifest["package_hash"]
    assert manifest["pack_id"] == "example.aria"
    assert manifest["character"]["canonical_name"] == "Aria"
    assert manifest["dependencies"] == source["dependencies"]
    assert "characters/bea/persona/profile.json" not in archive.namelist()
    assert all("mohan" not in name.casefold() for name in archive.namelist())


def test_character_asset_classification_uses_the_injected_root() -> None:
    expected = {
        "appearance/defaults.json": "character_appearance_defaults",
        "persona/ui-identifiers.json": "character_ui_identifier_data",
        "persona/en.json": "character_persona_data",
        "dialogue/runtime.json": "character_runtime_dialogue_data",
        "dialogue/en.json": "character_dialogue_data",
        "voice/profile.json": "character_voice_data",
        "rig/runtime-bindings.json": "character_runtime_binding_data",
        "rig/manifest.json": "character_rig_data",
        "expressions/states.json": "character_expression_catalog",
    }
    for relative, category in expected.items():
        assert classify_character_asset_path(
            f"characters/aria/{relative}",
            characters_root="characters",
        ) == category
    assert classify_character_asset_path(
        "assets/characters/aria/persona/en.json",
        characters_root="characters",
    ) is None


def test_hash_receipt_and_license_policy_are_explicit(tmp_path: Path) -> None:
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"huapu-fixture")
    measured = digest_file(tmp_path, "asset.bin")
    receipt = receipt_for_files("inventory", "accepted", "example.aria", (measured,))
    document = json.loads(render_receipt(receipt))
    assert document["schema_version"] == RECEIPT_SCHEMA_VERSION
    assert document["files"] == [measured.to_document()]
    pending = LicenseClaim("character_art", "owner_decision_pending", None)
    blocked = check_license_allowlist(
        (pending,),
        LicensePolicy(frozenset({"licensed"}), frozenset({"MIT"})),
    )
    allowed = check_license_allowlist(
        (pending,),
        LicensePolicy(frozenset({"owner_decision_pending"}), frozenset()),
    )
    assert not blocked.allowed
    assert allowed.allowed


def test_builder_result_keeps_public_validation_limits_type() -> None:
    assert CharacterPackBuildSettings.__module__ == "huapu.character_pack_builder"
    assert ValidationLimits.__module__ == "domain.character_pack.models"
