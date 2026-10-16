"""MoHan product compatibility facade over the neutral character-data loader."""

from __future__ import annotations

lazy from functools import cache
lazy from pathlib import Path

lazy from domain.character_pack.character_data_loader import (
    SUPPORTED_LOCALES,
    load_character_data,
)
lazy from domain.character_pack.character_data_models import (
    AzureVoicePreferences,
    canonical_character_locale,
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

MOHAN_CHARACTER_DATA_ROOT = Path(__file__).resolve().parents[2].joinpath(
    "assets",
    "characters",
    "mohan",
)


def load_mohan_character_data(root: Path | None = None) -> MohanCharacterData:
    """Preserve the established product loader and optional explicit root."""

    if root is not None:
        return load_character_data(Path(root))
    return _load_builtin_character_data()


@cache
def _load_builtin_character_data() -> MohanCharacterData:
    return load_character_data(MOHAN_CHARACTER_DATA_ROOT)


__all__ = (
    "MOHAN_CHARACTER_DATA_ROOT",
    "SUPPORTED_LOCALES",
    "AzureVoicePreferences",
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
    "load_mohan_character_data",
)
