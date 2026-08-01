from __future__ import annotations


DEFAULT_UI_LANGUAGE = "zh-TW"
ENGLISH_UI_LANGUAGES = {"en", "en-US", "en-GB"}

ENGLISH_REMINDER_LINES = {
    "work": (
        "Commander, today's campaign begins. Start when ready; I will keep "
        "the time."
    ),
    "lunch": (
        "It is time to eat. The work can wait; your health should not."
    ),
    "dinner": (
        "Commander, have dinner first. No sound strategy is made on an empty "
        "stomach."
    ),
    "offwork": (
        "That is enough for today. You no longer need to prove your worth by "
        "working late."
    ),
    "overwork": (
        "You have worked too long. Step away, drink some water, and stretch. "
        "We resume in ten minutes."
    ),
}


def is_english(language: str) -> bool:
    return str(language or "").strip() in ENGLISH_UI_LANGUAGES


def transcription_language_for_ui(language: str) -> str:
    return "en" if is_english(language) else "zh"


def localized_reminder_line(language: str, kind: str, chinese: str) -> str:
    if is_english(language):
        return ENGLISH_REMINDER_LINES.get(kind, chinese)
    return chinese


def migrate_builtin_reminder_line(
    current: str,
    language: str,
    kind: str,
    chinese: str,
) -> str:
    """Translate an untouched built-in reminder without replacing user text."""
    normalized = str(current or "").strip()
    known_defaults = {
        str(chinese).strip(),
        str(ENGLISH_REMINDER_LINES.get(kind, chinese)).strip(),
    }
    if normalized not in known_defaults:
        return current
    return localized_reminder_line(language, kind, chinese)


def response_language_instruction(language: str) -> str:
    if not is_english(language):
        return "使用自然的台灣繁體中文回覆。"
    return (
        "Reply in natural English. Preserve MoHan's poised sword-spirit "
        "personality, intelligence, restrained warmth, and subtle tsundere "
        "edge. Do not force Chinese first-person pronouns or honorifics into "
        "English sentences; use the configured user title naturally."
    )


def english_voice_instructions() -> str:
    return (
        "Speak natural international English with the clear, calm voice of a "
        "woman in her twenties. Keep a poised, classical, intelligent tone "
        "with restrained warmth and a subtle tsundere edge. Avoid a childlike, "
        "overly sweet, theatrical, or exaggerated delivery."
    )
