from __future__ import annotations


DEFAULT_UI_LANGUAGE = "zh-TW"
ENGLISH_UI_LANGUAGES = {"en", "en-US", "en-GB"}
SIMPLIFIED_CHINESE_UI_LANGUAGES = {"zh-CN", "zh-SG", "zh-Hans"}

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

SIMPLIFIED_CHINESE_REMINDER_LINES = {
    "work": "主上，今日之局已开。准备好了便开始，妾替你守住时辰。",
    "lunch": "该用午膳了。工作可以等，身体不可以。",
    "dinner": "主上先用晚膳。空腹之时，难有稳妥的判断。",
    "offwork": "今日到此为止。你不必再以加班证明自己的价值。",
    "overwork": "主上已经连续工作太久。离席、饮水、伸展，十分钟后再战。",
}


def is_english(language: str) -> bool:
    return str(language or "").strip() in ENGLISH_UI_LANGUAGES


def is_simplified_chinese(language: str) -> bool:
    return (
        str(language or "").strip()
        in SIMPLIFIED_CHINESE_UI_LANGUAGES
    )


def transcription_language_for_ui(language: str) -> str:
    return "en" if is_english(language) else "zh"


def localized_reminder_line(language: str, kind: str, chinese: str) -> str:
    if is_english(language):
        return ENGLISH_REMINDER_LINES.get(kind, chinese)
    if is_simplified_chinese(language):
        return SIMPLIFIED_CHINESE_REMINDER_LINES.get(kind, chinese)
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
        str(
            SIMPLIFIED_CHINESE_REMINDER_LINES.get(kind, chinese)
        ).strip(),
    }
    if normalized not in known_defaults:
        return current
    return localized_reminder_line(language, kind, chinese)


def response_language_instruction(language: str) -> str:
    if is_english(language):
        return (
            "Reply in natural English. Preserve MoHan's poised sword-spirit "
            "personality, intelligence, restrained warmth, and subtle "
            "tsundere edge. Do not force Chinese first-person pronouns or "
            "honorifics into English sentences; use the configured user "
            "title naturally."
        )
    if is_simplified_chinese(language):
        return (
            "使用自然、清晰的简体中文回复。保留墨寒沉静聪慧、克制温柔、"
            "略带成熟傲娇的剑魂人格；使用“妾”自称，并自然称呼用户为其"
            "设定称谓。不要输出繁体中文或生硬的机械转换文字。"
        )
    return "使用自然的台灣繁體中文回覆。"


def english_voice_instructions() -> str:
    return (
        "Speak natural international English with the clear, calm voice of a "
        "woman in her twenties. Keep a poised, classical, intelligent tone "
        "with restrained warmth and a subtle tsundere edge. Avoid a childlike, "
        "overly sweet, theatrical, or exaggerated delivery."
    )


def simplified_chinese_voice_instructions() -> str:
    return (
        "请使用自然清晰的普通话，以二十多岁女性的沉静声线说话。保持聪慧、"
        "克制、略带古典气质与成熟傲娇感；避免儿童声、过度甜腻、夸张撒娇、"
        "机械播报或舞台式朗诵。"
    )


def localized_voice_instructions(language: str, traditional: str) -> str:
    if is_english(language):
        return english_voice_instructions()
    if is_simplified_chinese(language):
        return simplified_chinese_voice_instructions()
    return traditional
