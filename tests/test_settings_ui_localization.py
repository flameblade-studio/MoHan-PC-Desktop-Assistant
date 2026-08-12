from __future__ import annotations

lazy import re
lazy import sys
lazy from pathlib import Path
lazy from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from settings_ui_localization import (
    LANGUAGE_ORDER,
    PHYSICS_TEXT_KEYS,
    PROACTIVE_MODE_KEYS,
    TOPMOST_MODE_KEYS,
    TRANSLATIONS,
    SettingsText,
    settings_text,
)

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
TRADITIONAL_PHRASES = (
    "設定",
    "資料夾",
    "程式",
    "開啟",
    "啟用",
    "關閉",
    "顯示",
    "瀏覽",
    "實機驗證",
    "請先",
    "髮飾",
    "滑鼠",
)


def format_fields(template: str) -> tuple[str, ...]:
    return tuple(
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(
            template
        )
        if field_name is not None
    )


def assert_complete_translation_contract() -> None:
    expected_keys = frozenset(SettingsText)
    assert LANGUAGE_ORDER == ("zh-TW", "zh-CN", "en", "ja-JP")
    assert tuple(TRANSLATIONS) == LANGUAGE_ORDER
    for language in LANGUAGE_ORDER:
        assert frozenset(TRANSLATIONS[language]) == expected_keys
        assert all(TRANSLATIONS[language].values())
    for key in SettingsText:
        expected_fields = format_fields(TRANSLATIONS["zh-TW"][key])
        assert all(
            format_fields(TRANSLATIONS[language][key]) == expected_fields
            for language in LANGUAGE_ORDER
        ), key
        values = {field: f"<{field}>" for field in expected_fields}
        for language in LANGUAGE_ORDER:
            TRANSLATIONS[language][key].format(**values)


def assert_ordered_integration_contracts() -> None:
    assert TOPMOST_MODE_KEYS == (
        SettingsText.TOPMOST_SMART,
        SettingsText.TOPMOST_ALWAYS,
        SettingsText.TOPMOST_NEVER,
    )
    assert PROACTIVE_MODE_KEYS == (
        SettingsText.PROACTIVE_QUIET,
        SettingsText.PROACTIVE_BALANCED,
        SettingsText.PROACTIVE_ACTIVE,
    )
    assert tuple(PHYSICS_TEXT_KEYS) == (
        "physics_sleeves",
        "physics_hair",
        "physics_ornament",
        "physics_eye_tracking",
        "physics_face_parallax",
    )
    assert all(
        name_key.name.endswith("_NAME")
        and description_key.name.endswith("_DESCRIPTION")
        for name_key, description_key in PHYSICS_TEXT_KEYS.values()
    )


def assert_english_contains_no_cjk() -> None:
    english = "\n".join(TRANSLATIONS["en"].values())
    assert not CJK.search(english), english
    assert settings_text("en", SettingsText.TOPMOST_ALWAYS) == "Always on top"
    assert settings_text("en", SettingsText.WORK_FOLDER_OPEN) == (
        "Open work folder"
    )


def assert_simplified_chinese_contains_no_traditional_phrases() -> None:
    simplified = "\n".join(TRANSLATIONS["zh-CN"].values())
    for phrase in TRADITIONAL_PHRASES:
        assert phrase not in simplified, phrase
    assert settings_text("zh-CN", SettingsText.TOPMOST_SMART) == (
        "智能置顶（推荐）"
    )
    assert settings_text("zh-CN", SettingsText.WORK_FOLDER_BROWSE) == (
        "浏览…"
    )


def assert_natural_japanese_key_items() -> None:
    assert settings_text("ja-JP", SettingsText.AUTOSTART_WINDOWS) == (
        "Windows サインイン後に自動起動"
    )
    assert settings_text("ja-JP", SettingsText.PROACTIVE_BALANCED) == (
        "バランス（推奨）"
    )
    assert settings_text("ja-JP", SettingsText.PHYSICS_EYE_TRACKING_NAME) == (
        "視線のマウス追従"
    )
    assert settings_text("ja-JP", SettingsText.WORK_FOLDER_OPEN) == (
        "作業フォルダーを開く"
    )
    assert settings_text("ja-JP", SettingsText.AI_CORE_LABEL) == "AI コア"
    assert "入力してください" in settings_text(
        "ja-JP",
        SettingsText.PROFILE_REQUIRED_MESSAGE,
    )


def assert_formatting_aliases_and_fallback() -> None:
    assert settings_text(
        "en-US",
        SettingsText.AUTOSTART_UNAVAILABLE,
        platform="Linux",
    ) == "Autostart on Linux has not been verified on a physical device"
    assert settings_text(
        "zh-Hans",
        SettingsText.CHARACTER_SCALE_LABEL,
        assistant="墨寒",
    ) == "桌面墨寒显示大小"
    assert settings_text(
        "ja",
        SettingsText.AUTOSTART_ERROR,
        reason="権限不足",
    ) == "自動起動を更新できませんでした：権限不足"
    assert settings_text(
        "unsupported",
        SettingsText.CHARACTER_SCALE_RESET_TOOLTIP,
        assistant="墨寒",
    ) == "將桌面墨寒恢復為原始顯示大小"


def run() -> None:
    assert_complete_translation_contract()
    assert_ordered_integration_contracts()
    assert_english_contains_no_cjk()
    assert_simplified_chinese_contains_no_traditional_phrases()
    assert_natural_japanese_key_items()
    assert_formatting_aliases_and_fallback()
    print("SETTINGS_UI_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
