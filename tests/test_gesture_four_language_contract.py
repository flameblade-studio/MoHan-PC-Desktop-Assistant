from __future__ import annotations

lazy import re
lazy import string
lazy import sys
lazy from dataclasses import fields
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from presentation.flagship_ui_localization import FLAGSHIP_TRANSLATIONS, FlagshipTranslator
lazy from domain.gesture_configuration import (
    BUILTIN_GESTURE_LABELS,
    GESTURE_ACTION_LABELS,
    GestureAction,
    LocalizedLabel,
)

AUDITED_FILES = (
    ROOT / "domain" / "gesture_configuration.py",
    ROOT / "presentation" / "flagship_ui_localization.py",
    Path(__file__),
)
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
TRANSLATION_LANGUAGE_COUNT = 3
LABEL_FIELDS = (
    "traditional_chinese",
    "simplified_chinese",
    "english",
    "japanese",
)
BUILTIN_IDS = (
    "wave",
    "silence",
    "open-palm",
    "closed-fist",
    "thumbs-up",
    "thumbs-down",
    "point-left",
    "point-right",
)
GESTURE_UI_CONTROLS = (
    "<b>手勢互動</b>",
    "啟用手勢互動",
    "手勢列表",
    "手勢名稱",
    "辨識後動作",
    "自訂文字指令",
    "輸入一行交給墨寒安全命令流程的文字指令",
    "啟用此手勢",
    "錄製狀態",
    "新增自訂手勢",
    "重新命名",
    "刪除自訂手勢",
    "重設內建手勢",
    "錄製手部特徵",
)
GESTURE_UI_STATUS = (
    "內建",
    "自訂",
    "已停用",
    "內建手勢使用已稽核的偵測器，不需錄製。",
    "可錄製手部特徵；不保存照片或影像。",
    "目前沒有可用的手部 landmark 訊號，無法安全錄製。",
    "錄製已取消，沒有保存任何資料。",
    "已暫存手部特徵；全域保存後才會生效。",
)
GESTURE_UI_ERRORS = (
    "手勢設定尚未完成",
    "選擇自訂文字指令時，必須輸入一行指令後才能保存。",
)
GESTURE_UI_SAFETY = (
    "所有手勢變更只會先暫存，按下全域保存設定後才會生效。自訂文字指令會交由既有安全命令流程處理。",
    "輸入一行交給墨寒安全命令流程的文字指令",
    "可錄製手部特徵；不保存照片或影像。",
    "目前沒有可用的手部 landmark 訊號，無法安全錄製。",
    "錄製已取消，沒有保存任何資料。",
)
GESTURE_UI_SOURCES = tuple(
    dict.fromkeys(
        (
            *GESTURE_UI_CONTROLS,
            *GESTURE_UI_STATUS,
            *GESTURE_UI_ERRORS,
            *GESTURE_UI_SAFETY,
        )
    )
)

HAN = re.compile(r"[\u3400-\u9fff]")
KANA = re.compile(r"[\u3040-\u30ff]")
TRADITIONAL_ONLY = frozenset("勢動稱識後訂製態錄刪內徵儲檔與為這個閉開顯隱語聽啟對應擾")
SIMPLIFIED_ONLY = frozenset("势动称识后订态录删内征储档与为这个闭开显隐语听启对应扰")
SUSPICIOUS_MOJIBAKE = tuple(
    chr(codepoint)
    for codepoint in (
        0x875C,
        0x96FF,
        0x929D,
        0x6470,
        0x6498,
        0x977D,
        0xF172,
        0xEF3F,
        0xE6A4,
    )
)


def _format_fields(value: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(value)
        if field_name is not None
    }


def _assert_language_purity(language: str, value: str) -> None:
    assert value.strip()
    assert "\ufffd" not in value
    assert "?" * 2 not in value
    assert not any(marker in value for marker in SUSPICIOUS_MOJIBAKE)
    if language == "zh-TW":
        assert not SIMPLIFIED_ONLY.intersection(value)
    elif language == "zh-CN":
        assert not TRADITIONAL_ONLY.intersection(value)
    elif language == "en":
        assert HAN.search(value) is None
        assert KANA.search(value) is None
    else:
        assert HAN.search(value) or KANA.search(value)


def _localized_values(label: LocalizedLabel) -> tuple[str, ...]:
    return tuple(getattr(label, field_name) for field_name in LABEL_FIELDS)


def test_source_files_are_strict_utf8_without_corruption() -> None:
    for path in AUDITED_FILES:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        assert text.encode("utf-8") == raw
        assert not raw.startswith(bytes((0xEF, 0xBB, 0xBF)))
        assert "\ufffd" not in text
        assert "\x00" not in text
        assert "?" * 2 not in text
        assert not any(marker in text for marker in SUSPICIOUS_MOJIBAKE)


def test_localized_label_field_order_is_canonical() -> None:
    assert tuple(field.name for field in fields(LocalizedLabel)) == LABEL_FIELDS
    assert LANGUAGES == ("zh-TW", "zh-CN", "en", "ja-JP")


def test_all_eight_builtin_gestures_have_clean_four_language_names() -> None:
    assert tuple(BUILTIN_GESTURE_LABELS) == BUILTIN_IDS
    for label in BUILTIN_GESTURE_LABELS.values():
        values = _localized_values(label)
        assert len(values) == len(LANGUAGES)
        for language, value in zip(LANGUAGES, values, strict=True):
            _assert_language_purity(language, value)


def test_every_gesture_action_is_present_in_every_language_ui() -> None:
    assert set(GESTURE_ACTION_LABELS) == set(GestureAction)
    for action in GestureAction:
        values = _localized_values(GESTURE_ACTION_LABELS[action])
        assert len(values) == len(LANGUAGES)
        for language, value in zip(LANGUAGES, values, strict=True):
            _assert_language_purity(language, value)


def test_every_gesture_ui_control_status_error_and_safety_text_is_translated() -> None:
    translators = {
        language: FlagshipTranslator(language)
        for language in LANGUAGES
    }
    for source in GESTURE_UI_SOURCES:
        assert source in FLAGSHIP_TRANSLATIONS
        translated_tuple = FLAGSHIP_TRANSLATIONS[source]
        assert len(translated_tuple) == TRANSLATION_LANGUAGE_COUNT
        assert _format_fields(source) == _format_fields(translated_tuple[0])
        assert _format_fields(source) == _format_fields(translated_tuple[1])
        assert _format_fields(source) == _format_fields(translated_tuple[2])
        for language, translator in translators.items():
            translated = translator.text(source)
            _assert_language_purity(language, translated)
            if language in {"en", "ja-JP"}:
                assert translated != source


def test_every_language_ui_catalog_contains_all_builtins_and_actions() -> None:
    for index, language in enumerate(LANGUAGES):
        builtin_names = {
            _localized_values(label)[index]
            for label in BUILTIN_GESTURE_LABELS.values()
        }
        action_names = {
            _localized_values(label)[index]
            for label in GESTURE_ACTION_LABELS.values()
        }
        assert len(builtin_names) == len(BUILTIN_IDS), language
        assert len(action_names) == len(GestureAction), language
        assert all(name.strip() for name in (*builtin_names, *action_names))


if __name__ == "__main__":
    test_source_files_are_strict_utf8_without_corruption()
    test_localized_label_field_order_is_canonical()
    test_all_eight_builtin_gestures_have_clean_four_language_names()
    test_every_gesture_action_is_present_in_every_language_ui()
    test_every_gesture_ui_control_status_error_and_safety_text_is_translated()
    test_every_language_ui_catalog_contains_all_builtins_and_actions()
    print("GESTURE_FOUR_LANGUAGE_CONTRACT_OK")
