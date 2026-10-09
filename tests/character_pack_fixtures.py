"""Synthetic standalone character-pack fixtures built below pytest ``tmp_path``."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import shutil
lazy import zipfile
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from typing import Any

lazy from domain.character_pack.validation import compute_package_hash
lazy from tools import build_character_pack as builder

ROOT = Path(__file__).resolve().parents[1]
FAKE_CHARACTER_ID = "test-sentinel"
FAKE_CANONICAL_NAME = "Test Sentinel"
FAKE_OUTFIT_PACK_ID = "tests.sentinel.missing-outfit"
FAKE_OUTFIT_ENSEMBLE_ID = "missing-outfit"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
CHARACTER_FILES = (
    "appearance/defaults.json",
    "dialogue/en.json",
    "dialogue/events.json",
    "dialogue/ja-JP.json",
    "dialogue/zh-CN.json",
    "dialogue/zh-TW.json",
    "expressions/state-catalog.json",
    "persona/en.json",
    "persona/ja-JP.json",
    "persona/profile.json",
    "persona/zh-CN.json",
    "persona/zh-TW.json",
    "rig/rig-manifest.json",
    "voice/profile.json",
)
CATEGORIES = {
    "appearance/defaults.json": "character_appearance_defaults",
    "expressions/state-catalog.json": "character_expression_catalog",
    "persona/profile.json": "character_persona_data",
    "rig/rig-manifest.json": "character_rig_data",
    "voice/profile.json": "character_voice_data",
}


def build_fake_character_pack(tmp_path: Path) -> Path:
    """Build a complete non-product character ZIP through the real Huapu builder."""

    repository = tmp_path / "fake-character-repository"
    character_root = repository / "assets" / "characters" / FAKE_CHARACTER_ID
    source_root = ROOT / "assets" / "characters" / "mohan"
    for relative in CHARACTER_FILES:
        source = source_root / relative
        target = character_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    _rewrite_character_data(character_root)

    provenance = repository / "provenance" / "source.json"
    provenance.parent.mkdir(parents=True)
    _write_json(
        provenance,
        {
            "schema": "tests.synthetic-character-source.v1",
            "schema_version": 1,
            "character_id": FAKE_CHARACTER_ID,
        },
    )
    inventory = repository / "inventory.json"
    rows = [
        _inventory_row(
            repository,
            f"assets/characters/{FAKE_CHARACTER_ID}/{relative}",
            _category(relative),
        )
        for relative in CHARACTER_FILES
    ]
    rows.append(_inventory_row(repository, "provenance/source.json", "provenance"))
    _write_json(inventory, {"files": rows})

    build_source = character_root / "pack-source.json"
    _write_json(build_source, _pack_source())
    archive = tmp_path / f"flameblade.{FAKE_CHARACTER_ID}.zip"
    builder.build_character_pack(
        archive,
        output_format="zip",
        repo_root=repository,
        inventory_path=inventory,
        source_path=build_source,
    )
    return archive


def rewrite_character_pack_manifest(
    source: Path,
    destination: Path,
    transform: Callable[[dict[str, Any]], None],
) -> Path:
    """Create a validly hashed variant for negative compatibility tests."""

    with zipfile.ZipFile(source) as archive:
        payloads = {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }
    manifest = json.loads(payloads["manifest.json"].decode("utf-8"))
    transform(manifest)
    manifest["package_hash"] = compute_package_hash(manifest)
    payloads["manifest.json"] = _json_bytes(manifest)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
    return destination


def tamper_character_pack_payload(source: Path, destination: Path) -> Path:
    """Copy a ZIP while changing one declared payload byte without its manifest."""

    with zipfile.ZipFile(source) as archive:
        payloads = {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }
    target = next(name for name in sorted(payloads) if name != "manifest.json")
    payloads[target] = payloads[target] + b"tampered"
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
    return destination


def _rewrite_character_data(character_root: Path) -> None:
    profile_path = character_root / "persona" / "profile.json"
    profile = _read_json(profile_path)
    profile["defaults"]["assistant_name"] = FAKE_CANONICAL_NAME
    profile["defaults"]["wake_word"] = FAKE_CANONICAL_NAME
    profile["legacy_profile_defaults"]["assistant_name"] = FAKE_CANONICAL_NAME
    profile["legacy_profile_defaults"]["wake_word"] = FAKE_CANONICAL_NAME
    profile["personalization"]["assistant_tokens"] = [FAKE_CANONICAL_NAME]
    _write_json(profile_path, profile)

    for language in LANGUAGES:
        persona_path = character_root / "persona" / f"{language}.json"
        persona = _read_json(persona_path)
        persona["identity"]["assistant_alias"] = FAKE_CANONICAL_NAME
        persona["identity"]["default_wake_word"] = FAKE_CANONICAL_NAME
        persona["identity"]["display_name"] = FAKE_CANONICAL_NAME
        persona["system_prompt"] = (
            f"You are {FAKE_CANONICAL_NAME}, a synthetic test character."
        )
        _write_json(persona_path, persona)

    appearance_path = character_root / "appearance" / "defaults.json"
    appearance = _read_json(appearance_path)
    appearance["outfit"]["pack_id"] = FAKE_OUTFIT_PACK_ID
    appearance["outfit"]["ensemble_id"] = FAKE_OUTFIT_ENSEMBLE_ID
    appearance["outfit"]["native_headwear"] = None
    _write_json(appearance_path, appearance)

    rig_path = character_root / "rig" / "rig-manifest.json"
    rig = _read_json(rig_path)
    rig["character_id"] = f"flameblade.{FAKE_CHARACTER_ID}"
    _write_json(rig_path, rig)

    expressions_path = character_root / "expressions" / "state-catalog.json"
    expressions = _read_json(expressions_path)
    expressions["character_id"] = f"flameblade.{FAKE_CHARACTER_ID}"
    _write_json(expressions_path, expressions)


def _pack_source() -> dict[str, object]:
    components: list[dict[str, object]] = [
        _component(
            "appearance-defaults",
            "appearance_defaults",
            "flameblade.character-appearance-defaults.v1",
            "appearance/defaults.json",
        ),
        _component(
            "rig",
            "fullbody_rig",
            "flameblade.character-rig.v1",
            "rig/rig-manifest.json",
            body_profile=True,
        ),
        _component(
            "expression-states",
            "expression_manifest",
            "flameblade.expression-state-catalog.v1",
            "expressions/state-catalog.json",
            body_profile=True,
        ),
        _component(
            "identity",
            "persona",
            "flameblade.character-identity-profile.v1",
            "persona/profile.json",
        ),
    ]
    for language in LANGUAGES:
        slug = language.lower()
        components.append(
            _component(
                f"persona.{slug}",
                "persona",
                "flameblade.character-persona.v1",
                f"persona/{language}.json",
            )
        )
        components.append(
            _component(
                f"dialogue.{slug}",
                "dialogue",
                "flameblade.character-dialogue.v1",
                f"dialogue/{language}.json",
            )
        )
    components.extend(
        (
            _component(
                "dialogue.events",
                "dialogue",
                "flameblade.character-events.v1",
                "dialogue/events.json",
            ),
            _component(
                "voice",
                "voice_profile",
                "flameblade.character-voice-profile.v1",
                "voice/profile.json",
            ),
        )
    )
    pending_license = {
        "status": "owner_decision_pending",
        "rights_holder": "Synthetic test fixture",
        "license_expression": None,
        "notice_path": None,
    }
    return {
        "schema": "flameblade.character-pack-build-source.v1",
        "schema_version": 1,
        "pack_id": f"tests.{FAKE_CHARACTER_ID}",
        "pack_version": "1.0.0",
        "character_id": FAKE_CHARACTER_ID,
        "identity": {
            "profile": f"assets/characters/{FAKE_CHARACTER_ID}/persona/profile.json",
            "personas": {
                language: (
                    f"assets/characters/{FAKE_CHARACTER_ID}/persona/{language}.json"
                )
                for language in LANGUAGES
            },
        },
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "4.6.0",
            "max_engine_version_exclusive": "5.0.0",
            "required_features": [],
        },
        "distribution": {
            "standalone_downloadable": True,
            "access": "owner_decision_pending",
            "redistribution": "owner_decision_pending",
        },
        "licenses": {
            component: dict(pending_license)
            for component in (
                "program_data",
                "character_art",
                "persona_dialogue",
                "voice",
            )
        },
        "source_refs": [
            {
                "path": "provenance/source.json",
                "scope": "Synthetic test fixture only.",
            }
        ],
        "approval_refs": [],
        "components": components,
        "dependencies": [
            {
                "id": FAKE_OUTFIT_PACK_ID,
                "kind": "outfit_pack",
                "min_version": "1.0.0",
                "max_version_exclusive": "2.0.0",
                "required": True,
            }
        ],
        "validation_limits": {
            "max_archive_bytes": 64 * 1024 * 1024,
            "max_zip_directory_bytes": 1024 * 1024,
            "max_manifest_bytes": 1024 * 1024,
            "max_file_bytes": 16 * 1024 * 1024,
            "max_total_bytes": 64 * 1024 * 1024,
            "max_files": 128,
            "max_compression_ratio": 100,
        },
    }


def _component(
    component_id: str,
    kind: str,
    schema: str,
    relative: str,
    *,
    body_profile: bool = False,
) -> dict[str, object]:
    return {
        "id": f"{FAKE_CHARACTER_ID}.{component_id}",
        "kind": kind,
        "schema": schema,
        "path": f"assets/characters/{FAKE_CHARACTER_ID}/{relative}",
        "required": True,
        "body_profile": (
            {"id": "mohan-body-v2", "version": 2} if body_profile else None
        ),
    }


def _category(relative: str) -> str:
    if relative in CATEGORIES:
        return CATEGORIES[relative]
    if relative.startswith("persona/"):
        return "character_persona_data"
    if relative.startswith("dialogue/"):
        return "character_dialogue_data"
    raise AssertionError(relative)


def _inventory_row(repository: Path, relative: str, category: str) -> dict[str, object]:
    payload = (repository / relative).read_bytes()
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "category": category,
        "scope": "runtime_data",
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object fixture at {path}.")
    return value


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


__all__ = (
    "FAKE_CANONICAL_NAME",
    "FAKE_CHARACTER_ID",
    "FAKE_OUTFIT_ENSEMBLE_ID",
    "FAKE_OUTFIT_PACK_ID",
    "build_fake_character_pack",
    "rewrite_character_pack_manifest",
    "tamper_character_pack_payload",
)
