from __future__ import annotations

lazy from dataclasses import dataclass

lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.character_pack.character_data_models import canonical_character_locale
lazy from domain.contracts import ProfileDatabasePort
lazy from domain.language_support import is_english, is_japanese, is_simplified_chinese
lazy from domain.persona_defaults import (
    ENGLISH_PERSONA,
    JAPANESE_PERSONA,
    PERSONA,
    SIMPLIFIED_CHINESE_PERSONA,
)

_IDENTITY = load_mohan_character_data().identity
DEFAULT_PROFILE = frozendict(_IDENTITY.defaults)


@dataclass(frozen=True, slots=True)
class ProfileLocalizationContext:
    assistant_name: str
    user_title: str
    organization_name: str
    wake_word: str
    ui_language: str


@dataclass(frozen=True, slots=True)
class ProfileSettingsValues:
    assistant_name: str
    user_title: str
    organization_name: str
    window_title: str
    work_type: str
    ui_language: str
    wake_word: str

    @property
    def localization(self) -> ProfileLocalizationContext:
        return ProfileLocalizationContext(
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=self.wake_word,
            ui_language=self.ui_language,
        )

    def setting_items(self) -> tuple[tuple[str, object], ...]:
        return (
            ("assistant_name", self.assistant_name),
            ("user_title", self.user_title),
            ("organization_name", self.organization_name),
            ("window_title", self.window_title),
            ("work_type", self.work_type),
            ("ui_language", self.ui_language),
            ("wake_word", self.wake_word),
            ("onboarding_complete", True),
        )


def default_persona_for_language(language: str) -> str:
    if is_english(language):
        return ENGLISH_PERSONA
    if is_simplified_chinese(language):
        return SIMPLIFIED_CHINESE_PERSONA
    if is_japanese(language):
        return JAPANESE_PERSONA
    return PERSONA


def profile_setting(db: ProfileDatabasePort, key: str) -> str:
    return str(db.setting(key, DEFAULT_PROFILE[key])).strip()


def profile_window_title(db: ProfileDatabasePort) -> str:
    custom = profile_setting(db, "window_title")
    if custom:
        return custom
    assistant = profile_setting(db, "assistant_name")
    organization = profile_setting(db, "organization_name")
    return "．".join(part for part in (assistant, organization) if part)


def persona_for_profile(db: ProfileDatabasePort) -> str:
    """Apply editable identity fields while preserving stored user prompts."""
    language = profile_setting(db, "ui_language")
    default_persona = default_persona_for_language(language)
    persona = (
        str(db.setting("persona_prompt", default_persona)).strip()
        or default_persona
    )
    assistant = profile_setting(db, "assistant_name")
    user_title = profile_setting(db, "user_title")
    organization = profile_setting(db, "organization_name")
    for token in _IDENTITY.assistant_tokens:
        persona = persona.replace(token, assistant)
    for token in _IDENTITY.user_title_tokens:
        persona = persona.replace(token, user_title)
    if organization:
        persona = persona.replace(_IDENTITY.organization_token, organization)
        locale = canonical_character_locale(language)
        persona += _IDENTITY.organization_context_templates[locale].format(
            organization=organization,
        )
    else:
        for replacement in _IDENTITY.organization_neutralizations:
            persona = persona.replace(replacement.source, replacement.target)
    return persona


def personalize_text(db: ProfileDatabasePort, text: str) -> str:
    """Apply editable identity fields to built-in fallback copy."""
    replacements = {
        **{
            token: profile_setting(db, "assistant_name")
            for token in _IDENTITY.assistant_tokens
        },
        **{
            token: profile_setting(db, "user_title")
            for token in _IDENTITY.user_title_tokens
        },
    }
    organization = profile_setting(db, "organization_name")
    if organization:
        replacements[_IDENTITY.organization_token] = organization
    result = text
    for source, target in replacements.items():
        if target:
            result = result.replace(source, target)
    return result
