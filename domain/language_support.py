from __future__ import annotations

lazy from domain.character_pack.character_data import (
    canonical_character_locale,
    load_mohan_character_data,
)

_CHARACTER_DATA = load_mohan_character_data()

DEFAULT_UI_LANGUAGE = "zh-TW"
ENGLISH_UI_LANGUAGES = frozenset({"en", "en-US", "en-GB"})
SIMPLIFIED_CHINESE_UI_LANGUAGES = frozenset({"zh-CN", "zh-SG", "zh-Hans"})
JAPANESE_UI_LANGUAGES = frozenset({"ja", "ja-JP"})

LEGACY_TRANSCRIPTION_PROMPT = _CHARACTER_DATA.identity.legacy_transcription_prompt

# This value belonged to the original author's private profile.  It may be
# present in databases created before the public onboarding flow existed, but
# it stays scoped to its original user's built-in transcription hints.
LEGACY_AUTHOR_ORGANIZATION = _CHARACTER_DATA.identity.legacy_author_organization

TRANSCRIPTION_PROMPT_BASES = frozendict(
    {
        locale: persona.transcription_prompt_base
        for locale, persona in _CHARACTER_DATA.personas.items()
    }
)

ENGLISH_REMINDER_LINES = _CHARACTER_DATA.dialogues["en"].reminder_lines
SIMPLIFIED_CHINESE_REMINDER_LINES = _CHARACTER_DATA.dialogues["zh-CN"].reminder_lines
JAPANESE_REMINDER_LINES = _CHARACTER_DATA.dialogues["ja-JP"].reminder_lines


def is_english(language: str) -> bool:
    return str(language or "").strip() in ENGLISH_UI_LANGUAGES


def is_simplified_chinese(language: str) -> bool:
    return (
        str(language or "").strip()
        in SIMPLIFIED_CHINESE_UI_LANGUAGES
    )


def is_japanese(language: str) -> bool:
    return str(language or "").strip() in JAPANESE_UI_LANGUAGES


def transcription_language_for_ui(language: str) -> str:
    if is_english(language):
        return "en"
    if is_japanese(language):
        return "ja"
    return "zh"


def canonical_ui_language(language: str) -> str:
    return canonical_character_locale(language)


def transcription_terms(
    assistant_name: str = "",
    user_title: str = "",
    organization_name: str = "",
    wake_word: str = "",
) -> tuple[str, ...]:
    """Return short, user-owned ASR hints in everyday language."""
    terms: list[str] = []
    for value in (
        assistant_name,
        wake_word,
        user_title,
        organization_name,
    ):
        normalized = str(value or "").strip()
        if normalized and normalized not in terms:
            terms.append(normalized)
    return tuple(terms)


def localized_transcription_prompt(
    language: str,
    *,
    assistant_name: str = "",
    user_title: str = "",
    organization_name: str = "",
    wake_word: str = "",
) -> str:
    locale = canonical_ui_language(language)
    prompt = TRANSCRIPTION_PROMPT_BASES[locale]
    terms = transcription_terms(
        assistant_name,
        user_title,
        organization_name,
        wake_word,
    )
    if not terms:
        return prompt
    joined = "、".join(terms)
    if locale == "zh-CN":
        return f"{prompt} 常用词：{joined}。"
    if locale == "en":
        return f"{prompt} Common terms: {', '.join(terms)}."
    if locale == "ja-JP":
        return f"{prompt} よく使う語句：{joined}。"
    return f"{prompt} 常用詞：{joined}。"


def is_builtin_transcription_prompt(
    current: str,
    language: str,
    **profile: str,
) -> bool:
    normalized = str(current or "").strip()
    return normalized in {
        LEGACY_TRANSCRIPTION_PROMPT,
        localized_transcription_prompt(language, **profile),
    }


def localized_reminder_line(language: str, kind: str, chinese: str) -> str:
    if is_english(language):
        return ENGLISH_REMINDER_LINES.get(kind, chinese)
    if is_simplified_chinese(language):
        return SIMPLIFIED_CHINESE_REMINDER_LINES.get(kind, chinese)
    if is_japanese(language):
        return JAPANESE_REMINDER_LINES.get(kind, chinese)
    return chinese


def migrate_builtin_reminder_line(
    current: str,
    language: str,
    kind: str,
    chinese: str,
) -> str:
    """Translate an untouched built-in reminder while preserving user text."""
    normalized = str(current or "").strip()
    known_defaults = {
        str(chinese).strip(),
        str(ENGLISH_REMINDER_LINES.get(kind, chinese)).strip(),
        str(
            SIMPLIFIED_CHINESE_REMINDER_LINES.get(kind, chinese)
        ).strip(),
        str(JAPANESE_REMINDER_LINES.get(kind, chinese)).strip(),
    }
    if normalized not in known_defaults:
        return current
    return localized_reminder_line(language, kind, chinese)


def response_language_instruction(language: str) -> str:
    locale = canonical_ui_language(language)
    return _CHARACTER_DATA.personas[locale].response_language_instruction


def english_voice_instructions() -> str:
    return _CHARACTER_DATA.voice.instructions["en"]


def simplified_chinese_voice_instructions() -> str:
    return _CHARACTER_DATA.voice.instructions["zh-CN"]


def japanese_voice_instructions() -> str:
    return _CHARACTER_DATA.voice.instructions["ja-JP"]


def localized_voice_instructions(language: str, traditional: str) -> str:
    if is_english(language):
        return english_voice_instructions()
    if is_simplified_chinese(language):
        return simplified_chinese_voice_instructions()
    if is_japanese(language):
        return japanese_voice_instructions()
    return traditional
