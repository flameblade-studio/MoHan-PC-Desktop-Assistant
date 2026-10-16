from __future__ import annotations

lazy import json
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy from domain import safe_error_localization, service_status_localization
lazy from domain.service_status_localization import (
    character_ui_values,
    render_character_ui_template,
)
lazy from integrations import realtime_contracts, remote_control
lazy from presentation import ui_localization
lazy from presentation.flagship_ui_localization import FlagshipTranslator

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "tests/data/ui-name-parameterization-before.json"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _snapshot() -> dict[str, object]:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _parameterized_source(source: str) -> str:
    values = character_ui_values("zh-TW")
    result = source
    for key in sorted(values, key=lambda item: len(values[item]), reverse=True):
        result = result.replace(values[key], "{" + key + "}")
    return result


def test_character_ui_identifiers_are_complete_utf8_data() -> None:
    values = {language: character_ui_values(language) for language in LANGUAGES}

    assert values == {
        "zh-TW": {
            "character_name": "墨寒",
            "user_title": "主上",
            "self_reference": "妾",
            "signature_weapon_theme_label": "赤焰劍光",
        },
        "zh-CN": {
            "character_name": "墨寒",
            "user_title": "主上",
            "self_reference": "妾",
            "signature_weapon_theme_label": "赤焰剑光",
        },
        "en": {
            "character_name": "MoHan",
            "user_title": "Commander",
            "self_reference": "I",
            "signature_weapon_theme_label": "Crimson Swordlight",
        },
        "ja-JP": {
            "character_name": "墨寒",
            "user_title": "主様",
            "self_reference": "妾",
            "signature_weapon_theme_label": "赤焔剣光",
        },
    }


def test_character_name_and_user_title_come_from_character_data(monkeypatch) -> None:
    identity = SimpleNamespace(
        display_name="測試角色",
        default_user_title="隊長",
    )
    character_data = SimpleNamespace(
        personas={language: SimpleNamespace(identity=identity) for language in LANGUAGES}
    )
    monkeypatch.setattr(
        service_status_localization,
        "active_character_data",
        lambda: character_data,
    )

    assert render_character_ui_template(
        "zh-TW",
        "{character_name}會向{user_title}回報。",
    ) == "測試角色會向隊長回報。"


def test_four_language_catalogs_match_the_pre_change_snapshot() -> None:
    snapshot = _snapshot()

    for diagnostic, translations in snapshot["safe_errors"].items():
        key = safe_error_localization.SafeDiagnostic(diagnostic)
        for language, expected in translations.items():
            assert render_character_ui_template(
                language,
                safe_error_localization._MESSAGES[key][language],
            ) == expected

    for status, translations in snapshot["service_status"].items():
        key = service_status_localization.ServiceStatus(status)
        for language, expected in translations.items():
            assert render_character_ui_template(
                language,
                service_status_localization._TEXT[key][language],
            ) == expected

    for language, catalog in snapshot["realtime"].items():
        for key, expected in catalog.items():
            assert realtime_contracts._realtime_message(language, key) == expected

    for language, catalog in snapshot["ui_catalogs"].items():
        for key, expected in catalog.items():
            assert ui_localization.ui_text(language, key, "") == expected

    language_order = ("zh-CN", "en", "ja-JP")
    for source, translations in snapshot["flagship"].items():
        parameterized = _parameterized_source(source)
        assert FlagshipTranslator("zh-TW").text(parameterized) == source
        for language, expected in zip(language_order, translations, strict=True):
            assert FlagshipTranslator(language).text(parameterized) == expected


def test_remote_page_keeps_the_existing_default_character_text() -> None:
    assert "<title>墨寒遠端</title>" in remote_control.MOBILE_PAGE
    assert "<h1>墨寒遠端</h1>" in remote_control.MOBILE_PAGE
    assert "<label>傳給墨寒</label>" in remote_control.MOBILE_PAGE
    assert "{character_name}" not in remote_control.MOBILE_PAGE


def test_runtime_system_messages_keep_character_named_data_verbatim() -> None:
    from presentation.flagship_ui_localization import FlagshipTranslator

    for language in ("zh-TW", "zh-CN", "en", "ja"):
        translator = FlagshipTranslator(language)
        opened = translator.system_message("已開啟資料夾：D:/墨寒")
        assert opened.endswith("D:/墨寒")
        assert "{character_name}" not in opened
        unknown = "含有墨寒字樣的未知執行期訊息"
        assert translator.system_message(unknown) == unknown
