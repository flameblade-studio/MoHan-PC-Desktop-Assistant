from __future__ import annotations

lazy from dataclasses import dataclass

lazy from domain.contracts import ProfileDatabasePort
lazy from domain.language_support import is_english, is_japanese, is_simplified_chinese
lazy from domain.persona_defaults import (
    ENGLISH_PERSONA,
    JAPANESE_PERSONA,
    PERSONA,
    SIMPLIFIED_CHINESE_PERSONA,
)

DEFAULT_PROFILE = frozendict(
    {
        "assistant_name": "墨寒",
        "user_title": "主上",
        "organization_name": "",
        "window_title": "",
        "work_type": "一般辦公／行政",
        "ui_language": "zh-TW",
        "wake_word": "墨寒",
    }
)


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
    """Apply editable identity fields without changing stored user prompts."""
    language = profile_setting(db, "ui_language")
    default_persona = default_persona_for_language(language)
    persona = (
        str(db.setting("persona_prompt", default_persona)).strip()
        or default_persona
    )
    assistant = profile_setting(db, "assistant_name")
    user_title = profile_setting(db, "user_title")
    organization = profile_setting(db, "organization_name")
    persona = (
        persona.replace("墨寒", assistant)
        .replace("MoHan", assistant)
        .replace("主上", user_title)
    )
    if organization:
        persona = persona.replace("炎劍文化工作室", organization)
        if is_english(language):
            persona += (
                "\nThe user's configured organization or team is "
                f'"{organization}". Use that context for work assistance.'
            )
        elif is_simplified_chinese(language):
            persona += (
                f"\n用户当前设置的组织／团队名称是“{organization}”。"
                "处理工作事务时，请结合此组织背景提供协助。"
            )
        elif is_japanese(language):
            persona += (
                f"\nユーザーが設定した組織／チーム名は「{organization}」です。"
                "仕事を支援する際は、この組織の文脈を踏まえてください。"
            )
        else:
            persona += (
                f"\n使用者目前設定的組織／團隊名稱是「{organization}」。"
                "處理工作事務時，請依此組織背景提供協助。"
            )
    else:
        persona = persona.replace(
            "炎劍文化工作室的虛擬執行長、文膽與策士",
            "使用者身邊的虛擬執行長、文膽與策士",
        ).replace(
            "炎劍文化工作室首席文膽與策士",
            "首席文膽與策士",
        )
    return persona


def personalize_text(db: ProfileDatabasePort, text: str) -> str:
    """Apply editable identity fields to built-in fallback copy."""
    replacements = {
        "墨寒": profile_setting(db, "assistant_name"),
        "主上": profile_setting(db, "user_title"),
    }
    organization = profile_setting(db, "organization_name")
    if organization:
        replacements["炎劍文化工作室"] = organization
    result = text
    for source, target in replacements.items():
        if target:
            result = result.replace(source, target)
    return result
