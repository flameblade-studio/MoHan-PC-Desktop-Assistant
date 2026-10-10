from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application import service_container
lazy from application.companion_phrasebook import (
    WARDROBE_REVEAL_QUESTION,
    public_companion_line,
)
lazy from domain.app_profile import DEFAULT_PROFILE, default_persona_for_language
lazy from domain.character_body_profile import body_profile_reference
lazy from domain.character_full_body_rig import compatible_yaws
lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.character_pack.validation import compute_package_hash
lazy from domain.character_pose import canonical_view_id
lazy from domain.character_source import (
    CharacterAppearanceContract,
    CharacterAssets,
    CharacterPersona,
    CharacterSource,
    CharacterVoice,
)
lazy from domain.constants import (
    FULL_BODY_LAYER_Z_ORDER,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from domain.outfit_pack import MAKEUP_CANVASES
lazy from domain.version_info import FALLBACK_VERSION
lazy from infrastructure.app_resources import resource_path
lazy from infrastructure.character_source_pack import (
    APPEARANCE_DEFAULTS_SCHEMA,
    CharacterPackReadError,
    CharacterPackReader,
    DIALOGUE_SCHEMA,
    EVENTS_SCHEMA,
    EXPRESSION_STATE_SCHEMA,
    FULLBODY_RIG_SCHEMA,
    IDENTITY_SCHEMA,
    PERSONA_SCHEMA,
    VOICE_SCHEMA,
)
lazy from tools import build_character_pack as builder

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _component_specs() -> list[dict[str, object]]:
    body_profile = {"id": "synthetic-body-v1", "version": 1}
    specs: list[dict[str, object]] = [
        {
            "id": "synthetic.appearance-defaults",
            "kind": "appearance_defaults",
            "schema": APPEARANCE_DEFAULTS_SCHEMA,
            "path": "character/appearance/defaults.json",
            "body_profile": None,
        },
        {
            "id": "synthetic.identity",
            "kind": "persona",
            "schema": IDENTITY_SCHEMA,
            "path": "character/persona/profile.json",
            "body_profile": None,
        },
        {
            "id": "synthetic.events",
            "kind": "dialogue",
            "schema": EVENTS_SCHEMA,
            "path": "character/dialogue/events.json",
            "body_profile": None,
        },
        {
            "id": "synthetic.voice",
            "kind": "voice_profile",
            "schema": VOICE_SCHEMA,
            "path": "character/voice/profile.json",
            "body_profile": None,
        },
        {
            "id": "synthetic.rig",
            "kind": "fullbody_rig",
            "schema": FULLBODY_RIG_SCHEMA,
            "path": "character/rig/rig-manifest.json",
            "body_profile": body_profile,
        },
        {
            "id": "synthetic.expression-states",
            "kind": "expression_manifest",
            "schema": EXPRESSION_STATE_SCHEMA,
            "path": "character/expressions/state-catalog.json",
            "body_profile": body_profile,
        },
    ]
    for language in LANGUAGES:
        slug = language.lower()
        specs.extend(
            (
                {
                    "id": f"synthetic.persona.{slug}",
                    "kind": "persona",
                    "schema": PERSONA_SCHEMA,
                    "path": f"character/persona/{language}.json",
                    "body_profile": None,
                },
                {
                    "id": f"synthetic.dialogue.{slug}",
                    "kind": "dialogue",
                    "schema": DIALOGUE_SCHEMA,
                    "path": f"character/dialogue/{language}.json",
                    "body_profile": None,
                },
            )
        )
    return specs


def _write_synthetic_contract_pack(
    root: Path,
    *,
    missing_id: str | None = None,
    duplicate_voice: bool = False,
    rig_schema: str = FULLBODY_RIG_SCHEMA,
) -> Path:
    specs = _component_specs()
    for spec in specs:
        if spec["id"] == "synthetic.rig":
            spec["schema"] = rig_schema
    if missing_id is not None:
        specs = [spec for spec in specs if spec["id"] != missing_id]
    if duplicate_voice:
        specs.append(
            {
                "id": "synthetic.voice.duplicate",
                "kind": "voice_profile",
                "schema": VOICE_SCHEMA,
                "path": "character/voice/duplicate-profile.json",
                "body_profile": None,
            }
        )

    payloads = {
        "provenance/source.json": _json_bytes(
            {"schema": "synthetic.character-source.v1", "created_for": "tests"}
        )
    }
    for spec in specs:
        path = str(spec["path"])
        payloads[path] = _json_bytes(
            {"schema": spec["schema"], "schema_version": 1}
        )
    for relative, data in payloads.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def digest(path: str) -> str:
        return hashlib.sha256(payloads[path]).hexdigest()

    components: list[dict[str, object]] = []
    for spec in specs:
        path = str(spec["path"])
        components.append(
            {
                **spec,
                "sha256": digest(path),
                "required": True,
            }
        )
    files = []
    for path, data in payloads.items():
        files.append(
            {
                "path": path,
                "sha256": digest(path),
                "bytes": len(data),
                "media_type": "application/json",
                "license_component": "persona_dialogue",
            }
        )
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
            "aliases": [],
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


def test_character_pack_reader_rejects_missing_component(tmp_path: Path) -> None:
    pack = _write_synthetic_contract_pack(
        tmp_path / "missing.character",
        missing_id="synthetic.voice",
    )
    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code == "missing_component"


def test_character_pack_reader_rejects_duplicate_component(tmp_path: Path) -> None:
    pack = _write_synthetic_contract_pack(
        tmp_path / "duplicate.character",
        duplicate_voice=True,
    )
    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code == "duplicate_component"


def test_character_pack_reader_rejects_wrong_component_schema(tmp_path: Path) -> None:
    pack = _write_synthetic_contract_pack(
        tmp_path / "unsupported.character",
        rig_schema="tests.unknown-rig.v1",
    )
    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code == "unsupported_component_schema"


def test_character_pack_reader_rejects_invalid_real_component_content(
    tmp_path: Path,
) -> None:
    pack = _write_synthetic_contract_pack(tmp_path / "invalid-content.character")
    with pytest.raises(CharacterPackReadError) as captured:
        CharacterPackReader(
            pack,
            engine_version="1.0.0",
            engine_features={"character-source-v1"},
        )
    assert captured.value.code == "invalid_component"


def _assert_appearance_data_fails_closed(
    pack: Path,
    built: builder.CharacterPackBuildResult,
) -> None:
    appearance_path = "assets/characters/mohan/appearance/defaults.json"
    appearance_file = pack / appearance_path
    manifest_path = pack / "manifest.json"
    original_appearance = appearance_file.read_bytes()
    original_manifest = manifest_path.read_bytes()
    manifest = json.loads(original_manifest)
    try:
        missing = dict(manifest)
        missing["components"] = [
            component
            for component in manifest["components"]
            if component["kind"] != "appearance_defaults"
        ]
        missing["package_hash"] = compute_package_hash(missing)
        manifest_path.write_bytes(_json_bytes(missing))
        with pytest.raises(CharacterPackReadError) as captured:
            CharacterPackReader(
                pack,
                engine_version=FALLBACK_VERSION,
                limits=built.validation_limits,
            )
        assert captured.value.code == "missing_component"

        malformed = b"{}\n"
        appearance_file.write_bytes(malformed)
        malformed_hash = hashlib.sha256(malformed).hexdigest()
        malformed_manifest = json.loads(original_manifest)
        for record in malformed_manifest["files"]:
            if record["path"] == appearance_path:
                record["bytes"] = len(malformed)
                record["sha256"] = malformed_hash
        for component in malformed_manifest["components"]:
            if component["path"] == appearance_path:
                component["sha256"] = malformed_hash
        malformed_manifest["package_hash"] = compute_package_hash(
            malformed_manifest
        )
        manifest_path.write_bytes(_json_bytes(malformed_manifest))
        with pytest.raises(CharacterPackReadError) as captured:
            CharacterPackReader(
                pack,
                engine_version=FALLBACK_VERSION,
                limits=built.validation_limits,
            )
        assert captured.value.code == "invalid_component"
        assert captured.value.path == "assets/characters/mohan"
    finally:
        appearance_file.write_bytes(original_appearance)
        manifest_path.write_bytes(original_manifest)


def test_built_mohan_pack_reader_matches_legacy_source(tmp_path: Path) -> None:
    pack = tmp_path / "flameblade.mohan"
    built = builder.build_character_pack(pack, output_format="directory")
    source = CharacterPackReader(
        pack,
        engine_version=FALLBACK_VERSION,
        limits=built.validation_limits,
    )
    legacy = service_container.create_default_character_source()

    assert isinstance(source, CharacterSource)
    assert isinstance(source.assets, CharacterAssets)
    assert isinstance(source.persona, CharacterPersona)
    assert isinstance(source.appearance, CharacterAppearanceContract)
    assert isinstance(source.voice, CharacterVoice)
    assert source.validation_result.valid
    assert source.canonical_name == legacy.canonical_name
    assert source.aliases == legacy.aliases
    assert source.body_profile == legacy.body_profile
    assert source.appearance_defaults == legacy.appearance_defaults
    assert source.voice_profile == legacy.voice_profile
    assert source.view_ids == legacy.view_ids
    assert source.fullbody_canvas == legacy.fullbody_canvas
    assert source.halfbody_canvas == legacy.halfbody_canvas
    assert source.layer_order == legacy.layer_order
    for language in LANGUAGES:
        assert source.display_name(language) == legacy.display_name(language)
        assert source.default_user_title(language) == legacy.default_user_title(language)
        assert source.persona_prompt(language) == legacy.persona_prompt(language)
        for variation_index in (0, 1):
            assert source.dialogue_line(
                language,
                WARDROBE_REVEAL_QUESTION,
                variation_index=variation_index,
            ) == legacy.dialogue_line(
                language,
                WARDROBE_REVEAL_QUESTION,
                variation_index=variation_index,
            )

    profile_path = "assets/characters/mohan/persona/profile.json"
    profile = source.resolve_path(profile_path)
    original = profile.read_bytes()
    try:
        profile.write_bytes(b"changed-character-data")
        with pytest.raises(CharacterPackReadError) as captured:
            source.resolve_path(profile_path)
        assert captured.value.code in {"size_mismatch", "file_hash_mismatch"}
    finally:
        profile.write_bytes(original)
    with pytest.raises(CharacterPackReadError, match="unsafe_path"):
        source.resolve_path("../outside")
    with pytest.raises(CharacterPackReadError, match="undeclared_path"):
        source.resolve_path("assets/characters/mohan/unknown.json")

    _assert_appearance_data_fails_closed(pack, built)


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
    assert source.appearance_defaults == load_mohan_character_data().appearance_defaults
    assert source.voice_profile == load_mohan_character_data().voice
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
    source = SimpleNamespace(
        assets=SimpleNamespace(
            asset_root=root,
            resolve_path=lambda relative: root / relative,
        ),
    )
    monkeypatch.setattr(
        service_container,
        "active_character_source",
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


def test_preview_packager_includes_complete_character_directory() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "tools" / "build_preview_package.py"
    ).read_text(encoding="utf-8")
    assert "ROOT / 'assets' / 'characters'" in source
    assert "assets/characters" in source
