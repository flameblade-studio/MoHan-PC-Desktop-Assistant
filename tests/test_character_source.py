from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from application import service_container
lazy from application.companion_phrasebook import (
    WARDROBE_REVEAL_QUESTION,
    public_companion_line,
)
lazy from domain.app_profile import DEFAULT_PROFILE, default_persona_for_language
lazy from domain.character_body_profile import body_profile_reference
lazy from domain.character_full_body_rig import compatible_yaws
lazy from domain.character_pack.validation import compute_package_hash
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAssets,
    CharacterPersona,
    CharacterSource,
)
lazy from domain.constants import (
    FULL_BODY_LAYER_Z_ORDER,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from domain.outfit_pack import MAKEUP_CANVASES
lazy from infrastructure.app_resources import resource_path
lazy from infrastructure.character_source_pack import (
    CharacterPackReadError,
    CharacterPackReader,
    DIALOGUE_SCHEMA,
    FULLBODY_RIG_SCHEMA,
    HALFBODY_RIG_SCHEMA,
    PERSONA_SCHEMA,
)

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_synthetic_pack(
    root: Path,
    *,
    persona_schema: str = PERSONA_SCHEMA,
) -> Path:
    payloads: dict[str, bytes] = {
        "provenance/source.json": _json_bytes(
            {"schema": "synthetic.character-source.v1", "created_for": "tests"}
        ),
        "persona/profile.json": _json_bytes(
            {
                "schema": persona_schema,
                "schema_version": 1,
                "default_user_titles": {
                    "zh-TW": "隊長",
                    "zh-CN": "队长",
                    "en": "Captain",
                    "ja-JP": "隊長",
                },
                "persona_prompts": {
                    language: f"synthetic persona {language}"
                    for language in LANGUAGES
                },
            }
        ),
        "dialogue/catalog.json": _json_bytes(
            {
                "schema": DIALOGUE_SCHEMA,
                "schema_version": 1,
                "locales": {
                    language: {
                        "welcome": [
                            f"welcome {language} zero",
                            f"welcome {language} one",
                        ]
                    }
                    for language in LANGUAGES
                },
            }
        ),
        "rig/fullbody.json": _json_bytes(
            {
                "schema": FULLBODY_RIG_SCHEMA,
                "schema_version": 1,
                "canvas": {"width": 640, "height": 960, "mode": "RGBA"},
                "views": ["front", "back"],
                "layers": ["body", "face", "hair"],
            }
        ),
        "rig/halfbody.json": _json_bytes(
            {
                "schema": HALFBODY_RIG_SCHEMA,
                "schema_version": 1,
                "canvas": {"width": 512, "height": 512, "mode": "RGBA"},
            }
        ),
        "rig/fullbody/front.rgba": b"synthetic-rgba-data",
    }
    for relative, data in payloads.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def digest(path: str) -> str:
        return hashlib.sha256(payloads[path]).hexdigest()

    components = [
        {
            "id": "synthetic-persona",
            "kind": "persona",
            "schema": persona_schema,
            "path": "persona/profile.json",
            "sha256": digest("persona/profile.json"),
            "required": True,
            "body_profile": None,
        },
        {
            "id": "synthetic-dialogue",
            "kind": "dialogue",
            "schema": DIALOGUE_SCHEMA,
            "path": "dialogue/catalog.json",
            "sha256": digest("dialogue/catalog.json"),
            "required": True,
            "body_profile": None,
        },
        {
            "id": "synthetic-fullbody",
            "kind": "fullbody_rig",
            "schema": FULLBODY_RIG_SCHEMA,
            "path": "rig/fullbody.json",
            "sha256": digest("rig/fullbody.json"),
            "required": True,
            "body_profile": {"id": "synthetic-body-v1", "version": 1},
        },
        {
            "id": "synthetic-halfbody",
            "kind": "halfbody_rig",
            "schema": HALFBODY_RIG_SCHEMA,
            "path": "rig/halfbody.json",
            "sha256": digest("rig/halfbody.json"),
            "required": True,
            "body_profile": {"id": "synthetic-body-v1", "version": 1},
        },
    ]
    files = [
        {
            "path": path,
            "sha256": digest(path),
            "bytes": len(data),
            "media_type": (
                "application/json" if path.endswith(".json") else "application/octet-stream"
            ),
            "license_component": (
                "persona_dialogue"
                if path.startswith(("persona/", "dialogue/"))
                else "character_art"
                if path.startswith("rig/")
                else "program_data"
            ),
        }
        for path, data in payloads.items()
    ]
    manifest: dict[str, object] = {
        "schema": "flameblade.character-pack.v1",
        "pack_id": "tests.synthetic-character",
        "pack_version": "1.0.0",
        "display_names": {
            "zh-TW": "合成測試角色",
            "zh-CN": "合成测试角色",
            "en": "Synthetic Test Character",
            "ja-JP": "合成テストキャラクター",
        },
        "character": {
            "id": "tests.synthetic-character",
            "canonical_name": "Aster",
            "aliases": ["Test Aster"],
        },
        "engine_compatibility": {
            "api_version": 1,
            "min_engine_version": "1.0.0",
            "max_engine_version_exclusive": "2.0.0",
            "required_features": ["character-source-v1"],
        },
        "distribution": {
            "standalone_downloadable": True,
            "access": "owner_decision_pending",
            "redistribution": "owner_decision_pending",
        },
        "licenses": {
            component: {
                "status": "owner_decision_pending",
                "rights_holder": "Synthetic test fixture",
                "license_expression": None,
                "notice_path": None,
            }
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
                "sha256": digest("provenance/source.json"),
                "scope": "Synthetic test data only.",
            }
        ],
        "approval_refs": [],
        "files": files,
        "components": components,
        "dependencies": [],
        "package_hash": "0" * 64,
    }
    manifest["package_hash"] = compute_package_hash(manifest)
    (root / "manifest.json").write_bytes(_json_bytes(manifest))
    return root


def test_character_pack_reader_exposes_validated_synthetic_data(tmp_path: Path) -> None:
    pack = _write_synthetic_pack(tmp_path / "synthetic.character")
    source = CharacterPackReader(
        pack,
        engine_version="1.0.0",
        engine_features={"character-source-v1"},
    )

    assert isinstance(source, CharacterSource)
    assert isinstance(source.assets, CharacterAssets)
    assert isinstance(source.persona, CharacterPersona)
    assert isinstance(source.appearance, CharacterAppearanceContract)
    assert source.validation_result.valid
    assert source.canonical_name == "Aster"
    assert source.aliases == ("Test Aster",)
    assert source.display_name("en-US") == "Synthetic Test Character"
    assert source.default_user_title("zh-CN") == "队长"
    assert source.persona_prompt("ja") == "synthetic persona ja-JP"
    assert source.dialogue_line("en", "welcome", variation_index=3) == "welcome en one"
    assert source.dialogue_line("en", "missing") == ""
    assert source.body_profile.profile_id == "synthetic-body-v1"
    assert source.body_profile.version == 1
    assert (source.fullbody_canvas.width, source.fullbody_canvas.height) == (640, 960)
    assert (source.halfbody_canvas.width, source.halfbody_canvas.height) == (512, 512)
    assert source.view_ids == ("front", "back")
    assert source.layer_order == ("body", "face", "hair")
    assert source.resolve_path("rig/fullbody/front.rgba").read_bytes() == b"synthetic-rgba-data"
    assert source.resolve_path("rig/fullbody").is_dir()
    with pytest.raises(CharacterPackReadError, match="unsafe_path"):
        source.resolve_path("../outside")
    with pytest.raises(CharacterPackReadError, match="undeclared_path"):
        source.resolve_path("rig/unknown.rgba")


def test_character_pack_reader_fails_closed_without_partial_data(tmp_path: Path) -> None:
    pack = _write_synthetic_pack(tmp_path / "tampered.character")
    (pack / "dialogue" / "catalog.json").write_text("{}", encoding="utf-8")

    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code in {"size_mismatch", "file_hash_mismatch"}
    assert "dialogue/catalog.json" in str(captured.value)


def test_character_pack_reader_rejects_unknown_child_schema(tmp_path: Path) -> None:
    pack = _write_synthetic_pack(
        tmp_path / "unsupported.character",
        persona_schema="tests.unknown-persona.v1",
    )
    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code == "unsupported_component_schema"
    assert "persona/profile.json" in str(captured.value)


def test_character_pack_reader_rechecks_assets_after_validation(tmp_path: Path) -> None:
    pack = _write_synthetic_pack(tmp_path / "mutable.character")
    source = CharacterPackReader(
        pack,
        engine_version="1.0.0",
        engine_features={"character-source-v1"},
    )
    (pack / "rig" / "fullbody" / "front.rgba").write_bytes(b"changed-synthetic-data")
    with pytest.raises(CharacterPackReadError) as captured:
        source.resolve_path("rig/fullbody/front.rgba")
    assert captured.value.code in {"size_mismatch", "file_hash_mismatch"}


def test_default_source_matches_every_existing_public_contract_field() -> None:
    source = service_container.create_default_character_source()
    assert isinstance(source, service_container.LegacyMohanCharacterSource)
    assert isinstance(source, CharacterSource)
    assert source.asset_root == resource_path(".")
    assert source.resolve_path(POSE_ATLAS_RELATIVE_ROOT) == resource_path(
        POSE_ATLAS_RELATIVE_ROOT
    )
    assert source.canonical_name == DEFAULT_PROFILE["assistant_name"]
    assert source.aliases == ()
    reference = body_profile_reference()
    assert source.body_profile.profile_id == reference["id"]
    assert source.body_profile.version == reference["version"]
    assert (source.fullbody_canvas.width, source.fullbody_canvas.height) == MAKEUP_CANVASES[
        "full-body"
    ]
    assert (source.halfbody_canvas.width, source.halfbody_canvas.height) == MAKEUP_CANVASES[
        "half-body"
    ]
    assert source.fullbody_canvas.mode == source.halfbody_canvas.mode == "RGBA"
    assert source.view_ids == tuple(
        canonical_view_id(yaw) for yaw in compatible_yaws()
    )
    assert source.layer_order == FULL_BODY_LAYER_Z_ORDER
    for language in LANGUAGES:
        assert source.display_name(language) == DEFAULT_PROFILE["assistant_name"]
        assert source.default_user_title(language) == DEFAULT_PROFILE["user_title"]
        assert source.persona_prompt(language) == default_persona_for_language(language)
        for variation_index in (0, 1):
            assert source.dialogue_line(
                language,
                WARDROBE_REVEAL_QUESTION,
                variation_index=variation_index,
            ) == public_companion_line(
                language,
                WARDROBE_REVEAL_QUESTION,
                variation_index=variation_index,
            )


def test_presentation_composition_uses_injected_character_asset_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "packaged-root"
    (root / "assets" / "official-packs").mkdir(parents=True)
    expected_atlas = root / POSE_ATLAS_RELATIVE_ROOT
    expected_atlas.mkdir(parents=True)
    source = service_container.LegacyMohanCharacterSource(root)
    monkeypatch.setattr(
        service_container,
        "create_default_character_source",
        lambda: source,
    )
    monkeypatch.setattr(
        service_container,
        "load_full_body_display_placement",
        lambda path: path,
    )
    monkeypatch.setattr(
        service_container,
        "LayeredFullBodyRenderer",
        lambda **values: values,
    )

    ports = service_container.create_presentation_ports()
    renderer = ports.full_body_renderer_factory()
    assert renderer["display_placement"] == expected_atlas


def test_preview_packager_includes_complete_mohan_character_directory() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "tools" / "build_preview_package.py"
    ).read_text(encoding="utf-8")
    assert "ROOT / 'assets' / 'characters' / 'mohan'" in source
    assert "assets/characters/mohan" in source
