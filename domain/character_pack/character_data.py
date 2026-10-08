"""Strict typed loader for built-in character persona, dialogue, and voice data."""

from __future__ import annotations

lazy import json
lazy from collections.abc import Mapping
lazy from functools import cache
lazy from pathlib import Path
lazy from domain.character_pack.appearance_data import load_character_appearance_defaults
lazy from domain.character_pack.character_data_models import (
    AzureVoicePreferences,
    canonical_character_locale as _canonical_character_locale,
    CharacterDataError,
    DialogueLocale,
    EventsProfile,
    IdentityProfile,
    MohanCharacterData,
    OccasionData,
    OfflineDialogue,
    OpenAIVoicePreferences,
    PersonaIdentity,
    PersonaLocale,
    SystemLocalVoicePreferences,
    TextReplacement,
    VoiceProfile,
)

SUPPORTED_LOCALES = ("zh-TW", "zh-CN", "en", "ja-JP")
MOHAN_CHARACTER_DATA_ROOT = Path(__file__).resolve().parents[2].joinpath("assets", "characters", "mohan")


canonical_character_locale = _canonical_character_locale


_PROFILE_DEFAULT_KEYS = frozenset(
    {
        "assistant_name",
        "user_title",
        "organization_name",
        "window_title",
        "work_type",
        "ui_language",
        "wake_word",
    }
)
_REMINDER_KEYS = frozenset({"work", "lunch", "dinner", "offwork", "overwork"})
_OFFLINE_TRIGGER_KEYS = frozenset(
    {
        "analysis",
        "exhausted",
        "tired",
        "romantic",
        "start_work_extra",
        "stop_work_extra",
    }
)
_OFFLINE_REPLY_KEYS = frozenset(
    {
        "analysis",
        "exhausted",
        "start_work",
        "tired",
        "stop_work",
        "romantic",
        "work",
        "companion",
    }
)
_WELLBEING_KINDS = ("meal", "hydration", "rest", "prolonged_sitting")
_WELLBEING_STAGES = ("initial", "restrained_reinforcement")
_OCCASION_KINDS = (
    "mohan_birthday",
    "valentines_day",
    "white_day",
    "qixi",
    "christmas_day",
)
_OCCASION_STAGES = ("subtle_hint", "restrained_grumble")
_PHRASEBOOK_KEYS = frozenset(
    {
        *(
            f"wellbeing.{kind}.{stage}"
            for kind in _WELLBEING_KINDS
            for stage in _WELLBEING_STAGES
        ),
        *(
            f"occasion.{kind}.{stage}"
            for kind in _OCCASION_KINDS
            for stage in _OCCASION_STAGES
        ),
        "wardrobe.reveal.question",
        "wardrobe.reveal.origin",
    }
)
_LINE_SET_KEYS = frozenset(
    {
        "welcome.warm",
        "welcome.general",
        "welcome.ceremonial",
        "welcome.morning",
        "welcome.late_night",
        "welcome.with_drink",
        "welcome.with_book",
        "interaction.gentle_check_in",
        "proactive.visual_activity",
        "somniloquy",
    }
)
_TEMPLATE_KEYS = frozenset(
    {
        "background.app_launched", "interaction.lighting_care",
        "proactive.memory_check_in", "voice.preview",
        "startup.first", "startup.returning",
        "caught_glance",
        "wardrobe.too_cold", "wardrobe.too_hot",
        "chronicle.first_tests_passed", "chronicle.first_pr_merged",
        "chronicle.first_release",
        *(f"ui.{name}" for name in (
            "all_platforms_saved_speech", "idea_added_speech",
            "memory_added_speech", "permission_saved_speech", "todo_added_speech",
        )),
    }
)
_LABEL_KEYS = frozenset(
    {
        *(f"welcome.{style}" for style in (
            "warm", "general", "ceremonial",
            "morning", "late_night", "with_drink",
            "with_book",
        )),
        "check_ins",
        *(f"wellbeing.{kind}" for kind in _WELLBEING_KINDS),
        *(f"stage.{stage}" for stage in _WELLBEING_STAGES),
        *(f"occasion.{kind}" for kind in _OCCASION_KINDS),
        *(f"occasion_stage.{stage}" for stage in _OCCASION_STAGES),
        "wardrobe.reveal.question", "wardrobe.reveal.origin",
        *(f"ui.{name}" for name in (
            "assistant_name_placeholder", "first_run_brand", "first_run_heading",
            "first_run_hero_tagline", "mohan_volume", "navigation_brand",
            "preview_voice", "reminder_message_placeholder", "user_title_placeholder",
            "wake_word_placeholder",
        )),
    }
)
_FIXED_OCCASION_KINDS = frozenset(
    {"mohan_birthday", "valentines_day", "white_day", "christmas_day"}
)
_PROVIDER_IDS = frozenset(
    {
        "openai-speech",
        "openai-realtime",
        "azure-speech",
        "azure-speech-hd",
        "system-local",
    }
)


def load_mohan_character_data(root: Path | None = None) -> MohanCharacterData:
    """Load all required data, rejecting any schema or type drift."""
    if root is None:
        return _load_builtin_character_data()
    return _load_character_data(Path(root))


@cache
def _load_builtin_character_data() -> MohanCharacterData:
    return _load_character_data(MOHAN_CHARACTER_DATA_ROOT)


def _load_character_data(root: Path) -> MohanCharacterData:
    identity = _parse_identity(_read_json(root / "persona" / "profile.json"))
    personas = {
        locale: _parse_persona(
            _read_json(root / "persona" / f"{locale}.json"),
            locale,
        )
        for locale in SUPPORTED_LOCALES
    }
    dialogues = {
        locale: _parse_dialogue(
            _read_json(root / "dialogue" / f"{locale}.json"),
            locale,
        )
        for locale in SUPPORTED_LOCALES
    }
    events = _parse_events(_read_json(root / "dialogue" / "events.json"))
    voice = _parse_voice(_read_json(root / "voice" / "profile.json"))
    return MohanCharacterData(
        appearance_defaults=load_character_appearance_defaults(root / "appearance" / "defaults.json"),
        identity=identity,
        personas=frozendict(personas),
        dialogues=frozendict(dialogues),
        events=events,
        voice=voice,
    )


def _read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CharacterDataError(f"{path}: UTF-8 character data is required") from exc

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise CharacterDataError(f"{path}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=lambda value: (_raise_nonfinite(path, value)),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CharacterDataError(f"{path}: valid UTF-8 JSON is required") from exc


def _raise_nonfinite(path: Path, value: str) -> None:
    raise CharacterDataError(f"{path}: non-finite number {value!r} is not allowed")


def _object(value: object, path: str, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict:
        raise CharacterDataError(f"{path}: object required")
    actual = frozenset(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise CharacterDataError(f"{path}: fields differ; missing={missing}, extra={extra}")
    return value


def _text(value: object, path: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        requirement = "text" if allow_empty else "non-empty text"
        raise CharacterDataError(f"{path}: {requirement} required")
    return value


def _integer(value: object, path: str) -> int:
    if type(value) is not int:
        raise CharacterDataError(f"{path}: integer required")
    return value


def _number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CharacterDataError(f"{path}: number required")
    return float(value)


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise CharacterDataError(f"{path}: boolean required")
    return value


def _strings(
    value: object,
    path: str,
    *,
    allow_empty: bool = False,
    allow_empty_items: bool = False,
) -> tuple[str, ...]:
    if type(value) is not list or (not allow_empty and not value):
        raise CharacterDataError(f"{path}: string array required")
    result = tuple(
        _text(item, f"{path}[{index}]", allow_empty=allow_empty_items)
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise CharacterDataError(f"{path}: duplicate values are not allowed")
    return result


def _text_map(
    value: object,
    path: str,
    keys: frozenset[str],
    *,
    allow_empty: bool = False,
) -> Mapping[str, str]:
    source = _object(value, path, keys)
    return frozendict(
        {
            key: _text(source[key], f"{path}.{key}", allow_empty=allow_empty)
            for key in sorted(keys)
        }
    )


def _string_array_map(
    value: object,
    path: str,
    keys: frozenset[str],
    *,
    allow_empty: bool = False,
) -> Mapping[str, tuple[str, ...]]:
    source = _object(value, path, keys)
    return frozendict(
        {
            key: _strings(
                source[key],
                f"{path}.{key}",
                allow_empty=allow_empty,
            )
            for key in sorted(keys)
        }
    )


def _schema(value: object, path: str, expected: str) -> dict[str, object]:
    source = value if type(value) is dict else {}
    if source.get("schema") != expected or source.get("schema_version") != 1:
        raise CharacterDataError(f"{path}: expected {expected} schema version 1")
    return source


def _parse_identity(value: object) -> IdentityProfile:
    path = "persona/profile.json"
    source = _object(
        _schema(value, path, "flameblade.character-identity-profile.v1"),
        path,
        frozenset(
            {
                "schema",
                "schema_version",
                "default_locale",
                "defaults",
                "legacy_profile_defaults",
                "personalization",
                "legacy",
                "command_phrases",
            }
        ),
    )
    default_locale = _text(source["default_locale"], f"{path}.default_locale")
    if default_locale not in SUPPORTED_LOCALES:
        raise CharacterDataError(f"{path}.default_locale: unsupported locale")
    defaults = _text_map(
        source["defaults"],
        f"{path}.defaults",
        _PROFILE_DEFAULT_KEYS,
        allow_empty=True,
    )
    legacy_defaults = _text_map(
        source["legacy_profile_defaults"],
        f"{path}.legacy_profile_defaults",
        _PROFILE_DEFAULT_KEYS,
        allow_empty=True,
    )
    personalization = _object(
        source["personalization"],
        f"{path}.personalization",
        frozenset(
            {
                "assistant_tokens",
                "user_title_tokens",
                "organization_token",
                "organization_neutralizations",
                "organization_context_templates",
            }
        ),
    )
    replacements_value = personalization["organization_neutralizations"]
    if type(replacements_value) is not list or not replacements_value:
        raise CharacterDataError(f"{path}.personalization.organization_neutralizations: array required")
    replacements = tuple(
        TextReplacement(
            source=_text(
                replacement["source"],
                f"{path}.personalization.organization_neutralizations[{index}].source",
            ),
            target=_text(
                replacement["target"],
                f"{path}.personalization.organization_neutralizations[{index}].target",
            ),
        )
        for index, item in enumerate(replacements_value)
        for replacement in (
            _object(
                item,
                f"{path}.personalization.organization_neutralizations[{index}]",
                frozenset({"source", "target"}),
            ),
        )
    )
    legacy = _object(
        source["legacy"],
        f"{path}.legacy",
        frozenset({"author_organization", "transcription_prompt"}),
    )
    commands = _object(
        source["command_phrases"],
        f"{path}.command_phrases",
        frozenset({"start_work", "stop_work"}),
    )
    return IdentityProfile(
        default_locale=default_locale,
        defaults=defaults,
        legacy_defaults=legacy_defaults,
        assistant_tokens=_strings(
            personalization["assistant_tokens"],
            f"{path}.personalization.assistant_tokens",
        ),
        user_title_tokens=_strings(
            personalization["user_title_tokens"],
            f"{path}.personalization.user_title_tokens",
        ),
        organization_token=_text(
            personalization["organization_token"],
            f"{path}.personalization.organization_token",
        ),
        organization_neutralizations=replacements,
        organization_context_templates=_text_map(
            personalization["organization_context_templates"],
            f"{path}.personalization.organization_context_templates",
            frozenset(SUPPORTED_LOCALES),
        ),
        legacy_author_organization=_text(
            legacy["author_organization"],
            f"{path}.legacy.author_organization",
        ),
        legacy_transcription_prompt=_text(
            legacy["transcription_prompt"],
            f"{path}.legacy.transcription_prompt",
        ),
        start_work_phrases=_strings(
            commands["start_work"],
            f"{path}.command_phrases.start_work",
        ),
        stop_work_phrases=_strings(
            commands["stop_work"],
            f"{path}.command_phrases.stop_work",
        ),
    )


def _parse_persona(value: object, locale: str) -> PersonaLocale:
    path = f"persona/{locale}.json"
    source = _object(
        _schema(value, path, "flameblade.character-persona.v1"),
        path,
        frozenset(
            {
                "schema",
                "schema_version",
                "locale",
                "identity",
                "system_prompt",
                "response_language_instruction",
                "transcription_prompt_base",
            }
        ),
    )
    loaded_locale = _text(source["locale"], f"{path}.locale")
    if loaded_locale != locale:
        raise CharacterDataError(f"{path}.locale: expected {locale}")
    identity = _object(
        source["identity"],
        f"{path}.identity",
        frozenset(
            {"display_name", "assistant_alias", "default_user_title", "default_wake_word"}
        ),
    )
    return PersonaLocale(
        locale=locale,
        identity=PersonaIdentity(
            display_name=_text(identity["display_name"], f"{path}.identity.display_name"),
            assistant_alias=_text(identity["assistant_alias"], f"{path}.identity.assistant_alias"),
            default_user_title=_text(
                identity["default_user_title"],
                f"{path}.identity.default_user_title",
            ),
            default_wake_word=_text(
                identity["default_wake_word"],
                f"{path}.identity.default_wake_word",
            ),
        ),
        system_prompt=_text(source["system_prompt"], f"{path}.system_prompt"),
        response_language_instruction=_text(
            source["response_language_instruction"],
            f"{path}.response_language_instruction",
        ),
        transcription_prompt_base=_text(
            source["transcription_prompt_base"],
            f"{path}.transcription_prompt_base",
        ),
    )


def _parse_dialogue(value: object, locale: str) -> DialogueLocale:
    path = f"dialogue/{locale}.json"
    source = _object(
        _schema(value, path, "flameblade.character-dialogue.v1"),
        path,
        frozenset(
            {
                "schema",
                "schema_version",
                "locale",
                "reminder_lines",
                "offline",
                "phrasebook",
                "line_sets",
                "templates",
                "labels",
            }
        ),
    )
    if _text(source["locale"], f"{path}.locale") != locale:
        raise CharacterDataError(f"{path}.locale: expected {locale}")
    offline = _object(
        source["offline"],
        f"{path}.offline",
        frozenset({"notice", "work_mode_value", "triggers", "replies"}),
    )
    return DialogueLocale(
        locale=locale,
        reminder_lines=_text_map(
            source["reminder_lines"],
            f"{path}.reminder_lines",
            _REMINDER_KEYS,
        ),
        offline=OfflineDialogue(
            notice=_text(offline["notice"], f"{path}.offline.notice"),
            work_mode_value=_text(
                offline["work_mode_value"],
                f"{path}.offline.work_mode_value",
            ),
            triggers=_string_array_map(
                offline["triggers"],
                f"{path}.offline.triggers",
                _OFFLINE_TRIGGER_KEYS,
                allow_empty=True,
            ),
            replies=_text_map(
                offline["replies"],
                f"{path}.offline.replies",
                _OFFLINE_REPLY_KEYS,
            ),
        ),
        phrasebook=_string_array_map(
            source["phrasebook"],
            f"{path}.phrasebook",
            _PHRASEBOOK_KEYS,
        ),
        line_sets=_string_array_map(
            source["line_sets"],
            f"{path}.line_sets",
            _LINE_SET_KEYS,
        ),
        templates=_text_map(source["templates"], f"{path}.templates", _TEMPLATE_KEYS),
        labels=_text_map(source["labels"], f"{path}.labels", _LABEL_KEYS),
    )


def _occasion(value: object, path: str) -> OccasionData:
    source = _object(
        value,
        path,
        frozenset(
            {
                "kind",
                "month",
                "day",
                "hint_hour",
                "grumble_hour",
                "minimum_grumble_delay_seconds",
            }
        ),
    )
    return OccasionData(
        kind=_text(source["kind"], f"{path}.kind"),
        month=_integer(source["month"], f"{path}.month"),
        day=_integer(source["day"], f"{path}.day"),
        hint_hour=_integer(source["hint_hour"], f"{path}.hint_hour"),
        grumble_hour=_integer(source["grumble_hour"], f"{path}.grumble_hour"),
        minimum_grumble_delay_seconds=_number(
            source["minimum_grumble_delay_seconds"],
            f"{path}.minimum_grumble_delay_seconds",
        ),
    )


def _parse_events(value: object) -> EventsProfile:
    path = "dialogue/events.json"
    source = _object(
        _schema(value, path, "flameblade.character-events.v1"),
        path,
        frozenset({"schema", "schema_version", "zodiac", "fixed_occasions", "qixi"}),
    )
    occasions_value = source["fixed_occasions"]
    if type(occasions_value) is not list:
        raise CharacterDataError(f"{path}.fixed_occasions: array required")
    occasions = tuple(
        _occasion(item, f"{path}.fixed_occasions[{index}]")
        for index, item in enumerate(occasions_value)
    )
    kinds = frozenset(occasion.kind for occasion in occasions)
    if kinds != _FIXED_OCCASION_KINDS or len(kinds) != len(occasions):
        raise CharacterDataError(f"{path}.fixed_occasions: exact unique event set required")
    qixi = _object(
        source["qixi"],
        f"{path}.qixi",
        frozenset({"hint_hour", "grumble_hour", "minimum_grumble_delay_seconds"}),
    )
    return EventsProfile(
        zodiac=_text(source["zodiac"], f"{path}.zodiac"),
        fixed_occasions=occasions,
        qixi_hint_hour=_integer(qixi["hint_hour"], f"{path}.qixi.hint_hour"),
        qixi_grumble_hour=_integer(
            qixi["grumble_hour"],
            f"{path}.qixi.grumble_hour",
        ),
        qixi_minimum_grumble_delay_seconds=_number(
            qixi["minimum_grumble_delay_seconds"],
            f"{path}.qixi.minimum_grumble_delay_seconds",
        ),
    )


def _parse_voice(value: object) -> VoiceProfile:
    path = "voice/profile.json"
    source = _object(
        _schema(value, path, "flameblade.character-voice-profile.v1"),
        path,
        frozenset(
            {
                "schema",
                "schema_version",
                "user_selection_wins",
                "defaults",
                "instructions",
                "preview_text",
                "providers",
                "fallback_provider_order",
            }
        ),
    )
    if not _boolean(source["user_selection_wins"], f"{path}.user_selection_wins"):
        raise CharacterDataError(f"{path}.user_selection_wins: must remain true")
    defaults = _object(
        source["defaults"],
        f"{path}.defaults",
        frozenset(
            {"provider", "rate", "volume_percent", "tts_voice", "cloud_voice", "realtime_voice"}
        ),
    )
    providers = _object(
        source["providers"],
        f"{path}.providers",
        frozenset({"openai", "azure", "system_local"}),
    )
    openai = _object(
        providers["openai"],
        f"{path}.providers.openai",
        frozenset({"voice_order", "realtime_unsupported"}),
    )
    azure = _object(
        providers["azure"],
        f"{path}.providers.azure",
        frozenset({"voices", "hd_voices"}),
    )
    system_local = _object(
        providers["system_local"],
        f"{path}.providers.system_local",
        frozenset(
            {
                "onecore_prefix",
                "preferred_voice_ids",
                "preferred_name_markers",
                "female_compatibility_markers",
                "male_markers",
                "excluded_name_markers",
            }
        ),
    )
    preferred_ids_source = _object(
        system_local["preferred_voice_ids"],
        f"{path}.providers.system_local.preferred_voice_ids",
        frozenset(SUPPORTED_LOCALES),
    )
    preferred_ids = frozendict(
        {
            locale: _text(
                preferred_ids_source[locale],
                f"{path}.providers.system_local.preferred_voice_ids.{locale}",
                allow_empty=True,
            )
            for locale in SUPPORTED_LOCALES
        }
    )
    fallback_order = _string_array_map(
        source["fallback_provider_order"],
        f"{path}.fallback_provider_order",
        _PROVIDER_IDS,
        allow_empty=True,
    )
    if any(
        provider not in _PROVIDER_IDS
        for order in fallback_order.values()
        for provider in order
    ):
        raise CharacterDataError(f"{path}.fallback_provider_order: unknown provider")
    return VoiceProfile(
        default_provider=_text(defaults["provider"], f"{path}.defaults.provider"),
        default_rate=_integer(defaults["rate"], f"{path}.defaults.rate"),
        default_volume_percent=_integer(
            defaults["volume_percent"],
            f"{path}.defaults.volume_percent",
        ),
        default_tts_voice=_text(defaults["tts_voice"], f"{path}.defaults.tts_voice"),
        default_cloud_voice=_text(
            defaults["cloud_voice"],
            f"{path}.defaults.cloud_voice",
        ),
        default_realtime_voice=_text(
            defaults["realtime_voice"],
            f"{path}.defaults.realtime_voice",
        ),
        instructions=_text_map(
            source["instructions"],
            f"{path}.instructions",
            frozenset(SUPPORTED_LOCALES),
        ),
        preview_text=_text_map(
            source["preview_text"],
            f"{path}.preview_text",
            frozenset(SUPPORTED_LOCALES),
        ),
        openai=OpenAIVoicePreferences(
            voice_order=_strings(
                openai["voice_order"],
                f"{path}.providers.openai.voice_order",
            ),
            realtime_unsupported=frozenset(
                _strings(
                    openai["realtime_unsupported"],
                    f"{path}.providers.openai.realtime_unsupported",
                )
            ),
        ),
        azure=AzureVoicePreferences(
            voices=_string_array_map(
                azure["voices"],
                f"{path}.providers.azure.voices",
                frozenset(SUPPORTED_LOCALES),
            ),
            hd_voices=_string_array_map(
                azure["hd_voices"],
                f"{path}.providers.azure.hd_voices",
                frozenset(SUPPORTED_LOCALES),
            ),
        ),
        system_local=SystemLocalVoicePreferences(
            onecore_prefix=_text(
                system_local["onecore_prefix"],
                f"{path}.providers.system_local.onecore_prefix",
            ),
            preferred_voice_ids=preferred_ids,
            preferred_name_markers=_string_array_map(
                system_local["preferred_name_markers"],
                f"{path}.providers.system_local.preferred_name_markers",
                frozenset(SUPPORTED_LOCALES),
                allow_empty=True,
            ),
            female_compatibility_markers=_strings(
                system_local["female_compatibility_markers"],
                f"{path}.providers.system_local.female_compatibility_markers",
            ),
            male_markers=_strings(
                system_local["male_markers"],
                f"{path}.providers.system_local.male_markers",
            ),
            excluded_name_markers=_strings(
                system_local["excluded_name_markers"],
                f"{path}.providers.system_local.excluded_name_markers",
            ),
        ),
        fallback_provider_order=fallback_order,
        user_selection_wins=True,
    )


__all__ = (
    "MOHAN_CHARACTER_DATA_ROOT",
    "SUPPORTED_LOCALES",
    "CharacterDataError", "DialogueLocale",
    "EventsProfile", "IdentityProfile",
    "MohanCharacterData", "PersonaLocale",
    "VoiceProfile",
    "canonical_character_locale",
    "load_mohan_character_data",
)
