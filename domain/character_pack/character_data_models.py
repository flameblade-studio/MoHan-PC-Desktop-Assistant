"""Immutable contracts returned by the strict built-in character-data loader."""

from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass


class CharacterDataError(ValueError):
    """Built-in character data violates its versioned schema."""


def canonical_character_locale(language: str) -> str:
    normalized = str(language or "").strip()
    if normalized in {"en", "en-US", "en-GB"}:
        return "en"
    if normalized in {"zh-CN", "zh-SG", "zh-Hans"}:
        return "zh-CN"
    if normalized in {"ja", "ja-JP"}:
        return "ja-JP"
    return "zh-TW"


@dataclass(frozen=True, slots=True)
class PersonaIdentity:
    display_name: str
    assistant_alias: str
    default_user_title: str
    default_wake_word: str


@dataclass(frozen=True, slots=True)
class AppearanceItemSelection:
    item_id: str
    variant_id: str


@dataclass(frozen=True, slots=True)
class CharacterAppearanceDefaults:
    makeup_pack_id: str
    makeup_item_id: str
    makeup_variants: tuple[str, ...]
    makeup_menu_variants: tuple[str, ...]
    makeup_always_visible_variants: tuple[str, ...]
    outfit_pack_id: str
    outfit_ensemble_id: str
    native_hair: AppearanceItemSelection
    native_headwear: AppearanceItemSelection


@dataclass(frozen=True, slots=True)
class PersonaLocale:
    locale: str
    identity: PersonaIdentity
    system_prompt: str
    response_language_instruction: str
    transcription_prompt_base: str


@dataclass(frozen=True, slots=True)
class TextReplacement:
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class IdentityProfile:
    default_locale: str
    defaults: Mapping[str, str]
    legacy_defaults: Mapping[str, str]
    assistant_tokens: tuple[str, ...]
    user_title_tokens: tuple[str, ...]
    organization_token: str
    organization_neutralizations: tuple[TextReplacement, ...]
    organization_context_templates: Mapping[str, str]
    legacy_author_organization: str
    legacy_transcription_prompt: str
    start_work_phrases: tuple[str, ...]
    stop_work_phrases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OfflineDialogue:
    notice: str
    work_mode_value: str
    triggers: Mapping[str, tuple[str, ...]]
    replies: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class DialogueLocale:
    locale: str
    reminder_lines: Mapping[str, str]
    offline: OfflineDialogue
    phrasebook: Mapping[str, tuple[str, ...]]
    line_sets: Mapping[str, tuple[str, ...]]
    templates: Mapping[str, str]
    labels: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class OccasionData:
    kind: str
    month: int
    day: int
    hint_hour: int
    grumble_hour: int
    minimum_grumble_delay_seconds: float


@dataclass(frozen=True, slots=True)
class EventsProfile:
    zodiac: str
    fixed_occasions: tuple[OccasionData, ...]
    qixi_hint_hour: int
    qixi_grumble_hour: int
    qixi_minimum_grumble_delay_seconds: float


@dataclass(frozen=True, slots=True)
class OpenAIVoicePreferences:
    voice_order: tuple[str, ...]
    realtime_unsupported: frozenset[str]


@dataclass(frozen=True, slots=True)
class AzureVoicePreferences:
    voices: Mapping[str, tuple[str, ...]]
    hd_voices: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class SystemLocalVoicePreferences:
    onecore_prefix: str
    preferred_voice_ids: Mapping[str, str]
    preferred_name_markers: Mapping[str, tuple[str, ...]]
    female_compatibility_markers: tuple[str, ...]
    male_markers: tuple[str, ...]
    excluded_name_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    default_provider: str
    default_rate: int
    default_volume_percent: int
    default_tts_voice: str
    default_cloud_voice: str
    default_realtime_voice: str
    instructions: Mapping[str, str]
    preview_text: Mapping[str, str]
    openai: OpenAIVoicePreferences
    azure: AzureVoicePreferences
    system_local: SystemLocalVoicePreferences
    fallback_provider_order: Mapping[str, tuple[str, ...]]
    user_selection_wins: bool


@dataclass(frozen=True, slots=True)
class MohanCharacterData:
    appearance_defaults: CharacterAppearanceDefaults
    identity: IdentityProfile
    personas: Mapping[str, PersonaLocale]
    dialogues: Mapping[str, DialogueLocale]
    events: EventsProfile
    voice: VoiceProfile


__all__ = (
    "AppearanceItemSelection",
    "AzureVoicePreferences",
    "CharacterAppearanceDefaults",
    "CharacterDataError",
    "DialogueLocale",
    "EventsProfile",
    "IdentityProfile",
    "MohanCharacterData",
    "OccasionData",
    "OfflineDialogue",
    "OpenAIVoicePreferences",
    "PersonaIdentity",
    "PersonaLocale",
    "SystemLocalVoicePreferences",
    "TextReplacement",
    "VoiceProfile",
    "canonical_character_locale",
)
