from __future__ import annotations

lazy import json
lazy import re
lazy from collections.abc import Iterable, Mapping
lazy from pathlib import Path
lazy from typing import Any

lazy from domain.character_pack.appearance_data import load_character_appearance_defaults
lazy from domain.version_info import FALLBACK_VERSION
lazy from infrastructure.character_source_pack import CharacterPackReader
lazy from tools import build_character_pack as builder


ROOT = Path(__file__).resolve().parents[1]
MOHAN_ROOT = ROOT / "assets" / "characters" / "mohan"
LIN_KEYUN_ROOT = ROOT / "assets" / "characters" / "lin-keyun"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
APPEARANCE_DEFAULTS_PATH = "appearance/defaults.json"
APPEARANCE_DEFAULTS_REPOSITORY_PATH = (
    "assets/characters/lin-keyun/appearance/defaults.json"
)
RUNTIME_JSON_FILES = (
    "dialogue/en.json",
    "dialogue/events.json",
    "dialogue/ja-JP.json",
    "dialogue/runtime.json",
    "dialogue/zh-CN.json",
    "dialogue/zh-TW.json",
    "expressions/state-catalog.json",
    "persona/en.json",
    "persona/ja-JP.json",
    "persona/profile.json",
    "persona/ui-identifiers.json",
    "persona/zh-CN.json",
    "persona/zh-TW.json",
    "rig/rig-manifest.json",
    "rig/runtime-bindings.json",
    "voice/profile.json",
)
EXPECTED_FILES = frozenset(
    {
        *RUNTIME_JSON_FILES,
        APPEARANCE_DEFAULTS_PATH,
        "pack-source.json",
        "README.md",
    }
)
EXPECTED_FILE_COUNT = len(EXPECTED_FILES)
EXPECTED_DIALOGUE_LABEL_COUNT = 33
EXPECTED_LINE_SET_LINE_COUNT = 37
EXPECTED_PHRASEBOOK_COUNT = 20
EXPECTED_PHRASEBOOK_LINE_COUNT = 40
EXPECTED_TEMPLATE_COUNT = 17
EXPECTED_README_LOCALE_COUNT = len(LANGUAGES)
LEGACY_VISIBLE_CONTENT = re.compile(
    r"墨寒|主上|主様|妾|MoHan|Mohan|Commander|My lord|my lord|"
    r"北宋|汴京|赤焰|赤焔|Chiyan|Crimson Flame|千年|"
    r"劍魂|剑魂|剣魂|sword spirit",
)


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _shape(value: object, path: str = "$") -> frozenset[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            result.add(child_path)
            result.update(_shape(child, child_path))
    elif isinstance(value, list):
        result.add(f"{path}#len={len(value)}")
        for child in value:
            result.update(_shape(child, f"{path}[]"))
    return frozenset(result)


def _key_paths(value: object, path: str = "$") -> frozenset[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            result.add(child_path)
            result.update(_key_paths(child, child_path))
    elif isinstance(value, list):
        for child in value:
            result.update(_key_paths(child, f"{path}[]"))
    return frozenset(result)


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def test_linkeyun_directory_matches_the_character_data_contract() -> None:
    files = {
        path.relative_to(LIN_KEYUN_ROOT).as_posix()
        for path in LIN_KEYUN_ROOT.rglob("*")
        if path.is_file()
    }
    assert files == EXPECTED_FILES
    assert len(files) == EXPECTED_FILE_COUNT
    for relative in EXPECTED_FILES:
        data = (LIN_KEYUN_ROOT / relative).read_bytes()
        assert data.endswith(b"\n"), relative
        assert b"\r\n" not in data, relative


def test_linkeyun_runtime_json_shapes_match_mohan() -> None:
    for relative in RUNTIME_JSON_FILES:
        assert _shape(_load(LIN_KEYUN_ROOT, relative)) == _shape(
            _load(MOHAN_ROOT, relative)
        ), relative

    reference = _key_paths(_load(MOHAN_ROOT, "dialogue/zh-TW.json"))
    for language in LANGUAGES:
        dialogue = _load(LIN_KEYUN_ROOT, f"dialogue/{language}.json")
        assert _key_paths(dialogue) == reference
        assert dialogue["locale"] == language
        assert len(dialogue["labels"]) == EXPECTED_DIALOGUE_LABEL_COUNT
        assert (
            sum(len(lines) for lines in dialogue["line_sets"].values())
            == EXPECTED_LINE_SET_LINE_COUNT
        )
        assert len(dialogue["phrasebook"]) == EXPECTED_PHRASEBOOK_COUNT
        assert (
            sum(len(lines) for lines in dialogue["phrasebook"].values())
            == EXPECTED_PHRASEBOOK_LINE_COUNT
        )
        assert len(dialogue["templates"]) == EXPECTED_TEMPLATE_COUNT


def test_linkeyun_four_languages_are_complete_and_character_specific() -> None:
    expected_identity = {
        "zh-TW": ("林可芸", "可芸", "劍主"),
        "zh-CN": ("林可芸", "可芸", "剑主"),
        "en": ("Lin Keyun", "Keyun", "Swordmaster"),
        "ja-JP": ("林可芸", "可芸", "剣主"),
    }
    for language, (name, alias, title) in expected_identity.items():
        persona = _load(LIN_KEYUN_ROOT, f"persona/{language}.json")
        assert persona["identity"] == {
            "assistant_alias": alias,
            "default_user_title": title,
            "default_wake_word": name,
            "display_name": name,
        }
        assert persona["system_prompt"].strip()
        dialogue = _load(LIN_KEYUN_ROOT, f"dialogue/{language}.json")
        assert all(value.strip() for value in _strings(persona))
        assert all(value.strip() for value in _strings(dialogue))
        assert dialogue["line_sets"]["somniloquy"]
        assert all(line.strip() for line in dialogue["line_sets"]["somniloquy"])


def test_linkeyun_human_facing_content_has_no_legacy_identity_leak() -> None:
    for path in LIN_KEYUN_ROOT.rglob("*"):
        if path.is_file():
            assert "墨寒" not in path.read_text(encoding="utf-8"), path

    inspected = (
        *(f"persona/{language}.json" for language in LANGUAGES),
        "persona/profile.json",
        "persona/ui-identifiers.json",
        *(f"dialogue/{language}.json" for language in LANGUAGES),
        "dialogue/runtime.json",
        "voice/profile.json",
    )
    for relative in inspected:
        for value in _strings(_load(LIN_KEYUN_ROOT, relative)):
            assert LEGACY_VISIBLE_CONTENT.search(value) is None, (relative, value)
    readme = (LIN_KEYUN_ROOT / "README.md").read_text(encoding="utf-8")
    assert LEGACY_VISIBLE_CONTENT.search(readme) is None

    memories = {
        language: _load(LIN_KEYUN_ROOT, f"dialogue/{language}.json")["line_sets"][
            "somniloquy"
        ]
        for language in LANGUAGES
    }
    assert any("前世" in line for line in memories["zh-TW"])
    assert any("前世" in line for line in memories["zh-CN"])
    assert any("past life" in line for line in memories["en"])
    assert any("前世" in line for line in memories["ja-JP"])


def test_linkeyun_voice_and_shared_v5_body_match_the_approved_contract() -> None:
    voice = _load(LIN_KEYUN_ROOT, "voice/profile.json")
    mohan_voice = _load(MOHAN_ROOT, "voice/profile.json")
    for field in (
        "defaults",
        "fallback_provider_order",
        "providers",
        "schema",
        "schema_version",
        "user_selection_wins",
    ):
        assert voice[field] == mohan_voice[field]
    assert voice["defaults"]["rate"] == -1
    assert voice["providers"]["system_local"]["preferred_voice_ids"]["zh-TW"] == (
        "OneCore::Microsoft Yating"
    )

    rig = _load(LIN_KEYUN_ROOT, "rig/rig-manifest.json")
    mohan_rig = _load(MOHAN_ROOT, "rig/rig-manifest.json")
    expressions = _load(LIN_KEYUN_ROOT, "expressions/state-catalog.json")
    assert rig["character_id"] == expressions["character_id"] == "flameblade.lin-keyun"
    assert rig["body_profile"] == mohan_rig["body_profile"]
    assert rig["body_profile"]["id"] == "mohan-body-v2"
    assert rig["body_profile"]["measurements"] == {
        "height_cm": 168,
        "weight_kg": 54,
        "bust_cm": 86,
        "underbust_cm": 71,
        "waist_cm": 62,
        "hips_cm": 90,
    }


def test_linkeyun_appearance_defaults_load_with_explicitly_no_headwear() -> None:
    source = _load(LIN_KEYUN_ROOT, APPEARANCE_DEFAULTS_PATH)
    defaults = load_character_appearance_defaults(
        LIN_KEYUN_ROOT / APPEARANCE_DEFAULTS_PATH
    )
    mohan = _load(MOHAN_ROOT, APPEARANCE_DEFAULTS_PATH)

    assert source["makeup"] == mohan["makeup"]
    assert defaults.makeup_pack_id == "mohan.makeup.builtin"
    assert defaults.makeup_item_id == "mohan-signature"
    assert defaults.outfit_pack_id == "linkeyun.official.modern-office"
    assert defaults.outfit_ensemble_id == "modern-office"
    assert (defaults.native_hair.item_id, defaults.native_hair.variant_id) == (
        "long-hair",
        "dark-brown",
    )
    assert source["outfit"]["native_headwear"] is None
    assert defaults.native_headwear is None


def test_linkeyun_pack_source_declares_public_access_and_default_outfit() -> None:
    source = _load(LIN_KEYUN_ROOT, "pack-source.json")
    mohan_source = _load(MOHAN_ROOT, "pack-source.json")
    assert source["pack_id"] == "flameblade.lin-keyun"
    assert source["character_id"] == "lin-keyun"
    assert source["pack_version"] == "1.0.0"
    assert source["distribution"]["access"] == "public"
    assert source["licenses"] == mohan_source["licenses"]
    assert source["dependencies"] == [
        {
            "id": "linkeyun.official.modern-office",
            "kind": "outfit_pack",
            "min_version": "1.0.0",
            "max_version_exclusive": "2.0.0",
            "required": True,
        }
    ]
    component_ids = {component["id"] for component in source["components"]}
    assert "linkeyun.appearance-defaults" in component_ids
    assert "mohan.makeup.builtin" in component_ids
    assert "mohan.official.blue-white-hanfu" not in component_ids

    readme = (LIN_KEYUN_ROOT / "README.md").read_text(encoding="utf-8")
    for identifier in (
        "linkeyun.official.modern-office",
        "long-hair",
        "dark-brown",
    ):
        assert readme.count(identifier) == EXPECTED_README_LOCALE_COUNT


def test_linkeyun_pack_builds_validates_and_reads_without_mohan_data(
    tmp_path: Path,
) -> None:
    output = tmp_path / "flameblade.lin-keyun"
    built = builder.build_character_pack(
        output,
        output_format="directory",
        source_path="assets/characters/lin-keyun/pack-source.json",
    )
    reader = CharacterPackReader(
        output,
        engine_version=FALLBACK_VERSION,
        limits=built.validation_limits,
    )
    assert reader.validation_result.valid
    assert reader.manifest.pack_id == "flameblade.lin-keyun"
    assert reader.manifest.character_id == "lin-keyun"
    assert reader.manifest.access == "public"
    assert reader.manifest.dependencies[0].dependency_id == (
        "linkeyun.official.modern-office"
    )
    declared = {record.path for record in reader.manifest.files}
    assert any(path.startswith("assets/characters/lin-keyun/") for path in declared)
    assert not any(path.startswith("assets/characters/mohan/") for path in declared)
    assert APPEARANCE_DEFAULTS_REPOSITORY_PATH in declared
    appearance_record = next(
        record for record in reader.manifest.files
        if record.path == APPEARANCE_DEFAULTS_REPOSITORY_PATH
    )
    assert appearance_record.license_component == "program_data"
    for relative in RUNTIME_JSON_FILES:
        assert f"assets/characters/lin-keyun/{relative}" in declared
    assert reader.appearance_defaults.native_headwear is None
    for language in LANGUAGES:
        assert reader.persona_prompt(language).strip()
        assert reader.dialogue_line(language, "wardrobe.reveal.question").strip()
