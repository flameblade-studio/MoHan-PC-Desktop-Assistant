from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QEvent, QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication

lazy from application.presentation_ports import PlatformCapabilities, PlatformPaths
lazy from application.service_container import create_presentation_ports
lazy from domain.app_profile import default_persona_for_language
lazy from domain.language_normalization import normalize_for_language
lazy from domain.language_support import (
    ENGLISH_REMINDER_LINES,
    SIMPLIFIED_CHINESE_REMINDER_LINES,
    english_voice_instructions,
    migrate_builtin_reminder_line,
    response_language_instruction,
    simplified_chinese_voice_instructions,
)
lazy from domain.speech_configuration import VOICE_ENGINE_WINDOWS
lazy from infrastructure.db import StudioDB
lazy from integrations.ai_client import offline_reply
lazy from integrations.speech import (
    WindowsTTS,
    _is_allowed_companion_voice,
    preferred_windows_voice,
)
lazy from presentation.companion_platform import REMINDER_LINES
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from presentation.ui_localization import _ENGLISH, _SIMPLIFIED_CHINESE


class FakeSecretStore:
    def load(self) -> str:
        return ""

    def save(self, _value: str) -> None:
        return None

    def clear(self) -> None:
        return None


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        return None


class StaticVoiceCatalog:
    def __init__(self, voices: list[tuple[str, str]]) -> None:
        self._voices = tuple(voices)

    def windows_voices(self) -> list[tuple[str, str]]:
        return list(self._voices)


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=True,
        native_window_management=True,
        published_installers=("portable-zip", "exe", "msi"),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(
            data=root / "data",
            config=root / "config",
            cache=root / "cache",
        )

    def set_autostart(
        self,
        _enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        raise AssertionError(
            f"Localization test attempted autostart: {application_id} {command}"
        )

    def open_path(self, path: Path) -> None:
        raise AssertionError(f"Localization test attempted external open: {path}")


def ignore_autostart(_enabled: bool, _platform: object) -> None:
    return None


def dashboard_dependencies(
    db: StudioDB,
    listener: FakeListener,
    voices: list[tuple[str, str]],
) -> DashboardDependencies:
    ports = replace(
        create_presentation_ports(),
        voice_catalog=StaticVoiceCatalog(voices),
        autostart_configurator=ignore_autostart,
    )
    return DashboardDependencies(
        listener=listener,
        secret_store=FakeSecretStore(),
        platform_services=OfflinePlatformServices(db.path.parent),
        presentation_ports=ports,
    )


def close_dashboard(app: QApplication, dashboard: Dashboard) -> None:
    """Destroy dashboard timers before its temporary database is closed."""
    for timer in dashboard.findChildren(QTimer):
        timer.stop()
    dashboard.close()
    dashboard.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def assert_language_tables_and_reminders() -> str:
    assert set(_SIMPLIFIED_CHINESE) == set(_ENGLISH)
    chinese_lunch = "午膳時辰到了。工作可以等，身體不可以。"
    assert migrate_builtin_reminder_line(
        chinese_lunch,
        "en",
        "lunch",
        chinese_lunch,
    ) == ENGLISH_REMINDER_LINES["lunch"]
    assert migrate_builtin_reminder_line(
        ENGLISH_REMINDER_LINES["lunch"],
        "zh-CN",
        "lunch",
        chinese_lunch,
    ) == SIMPLIFIED_CHINESE_REMINDER_LINES["lunch"]
    assert migrate_builtin_reminder_line(
        SIMPLIFIED_CHINESE_REMINDER_LINES["lunch"],
        "zh-TW",
        "lunch",
        chinese_lunch,
    ) == chinese_lunch
    custom_lunch = "Remember our custom lunch ritual."
    assert migrate_builtin_reminder_line(
        custom_lunch,
        "zh-TW",
        "lunch",
        chinese_lunch,
    ) == custom_lunch
    assert normalize_for_language("打开软件", "zh-CN") == "打开软件"
    assert normalize_for_language("打开软件", "zh-TW") == "開啟軟體"
    return custom_lunch


def assert_companion_voice_policy() -> list[tuple[str, str]]:
    # Gender is strict. Known legacy Taiwan voices remain compatible when an
    # older registry omits Gender, but an arbitrary unknown voice is hidden.
    assert _is_allowed_companion_voice("Microsoft Yating", "")
    assert _is_allowed_companion_voice("Microsoft Hanhan", "")
    assert _is_allowed_companion_voice("Microsoft Zira", "Female")
    assert _is_allowed_companion_voice("Microsoft Xiaoxiao", "Female")
    assert not _is_allowed_companion_voice("Microsoft David", "Male")
    assert not _is_allowed_companion_voice("Third-party Voice", "")
    assert not _is_allowed_companion_voice("Microsoft Zhiwei", "Female")

    female_voices = [
        ("OneCore::Microsoft Zira", "en-US"),
        ("OneCore::Microsoft Hanhan", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
        ("OneCore::Microsoft Xiaoxiao", "zh-CN"),
    ]
    assert preferred_windows_voice(
        female_voices,
        target_language="zh-TW",
    ) == "OneCore::Microsoft Yating"
    assert preferred_windows_voice(
        female_voices,
        target_language="en",
    ) == "OneCore::Microsoft Zira"
    assert preferred_windows_voice(
        female_voices,
        target_language="zh-CN",
    ) == "OneCore::Microsoft Xiaoxiao"
    assert preferred_windows_voice(
        female_voices,
        saved="OneCore::Microsoft Hanhan",
        target_language="en",
    ) == "OneCore::Microsoft Hanhan"
    assert preferred_windows_voice(
        female_voices,
        saved="OneCore::Microsoft Zira",
        target_language="zh-TW",
    ) == "OneCore::Microsoft Zira"
    return female_voices


def assert_empty_voice_selection_fails() -> None:
    # The runtime never lets an empty selection fall through to an arbitrary
    # Windows system default, which could be male.
    tts = WindowsTTS(language="en")
    failures: list[str] = []
    tts.failed.connect(failures.append)
    with patch("integrations.speech.windows_voices", return_value=[]):
        tts._run("Hello", "", 0)
    assert failures and "female" in failures[-1].casefold()
    assert "女性" not in failures[-1]


def assert_english_wizard(app: QApplication, db: StudioDB) -> None:
    wizard = FirstRunWizard(db)
    english_index = wizard.ui_language.findData("en")
    wizard.ui_language.setCurrentIndex(english_index)
    app.processEvents()
    assert wizard.windowTitle() == "First-run setup"
    assert "thousand-year-old" in wizard.hero_tagline.text()
    assert wizard.form_labels["assistant_name"].text() == "Assistant name"
    assert wizard.assistant_name.text() == "MoHan"
    assert wizard.user_title.text() == "Commander"
    chinese_index = wizard.ui_language.findData("zh-TW")
    wizard.ui_language.setCurrentIndex(chinese_index)
    app.processEvents()
    assert wizard.title_label.text() == "<b>歡迎使用墨寒桌面陪伴工作助理</b>"
    assert wizard.windowTitle() == "首次啟動設定"
    assert wizard.assistant_name.text() == "墨寒"
    assert wizard.user_title.text() == "主上"
    wizard.ui_language.setCurrentIndex(english_index)
    app.processEvents()
    wizard._save()
    assert db.setting("ui_language") == "en"
    assert db.setting("transcription_language") == "en"
    assert "Please transcribe accurately in English" in str(
        db.setting("transcription_prompt")
    )
    assert db.setting("voice_engine") == VOICE_ENGINE_WINDOWS
    assert db.setting("persona_prompt") == default_persona_for_language("en")
    assert db.setting("voice_instructions") == english_voice_instructions()
    assert "Reply in natural English" in response_language_instruction("en")
    assert "I am listening" in offline_reply("Hello", "陪伴", "en")
    wizard.close()


def assert_english_dashboard(
    app: QApplication,
    db: StudioDB,
    female_voices: list[tuple[str, str]],
    custom_lunch: str,
) -> None:
    listener = FakeListener()
    dashboard = Dashboard(
        db,
        dashboard_dependencies(db, listener, female_voices),
    )
    assert dashboard.tabs.tabText(0) == "Chat"
    assert dashboard.tabs.tabText(1) == "Today"
    assert dashboard.todo_input.placeholderText().startswith("Enter a task")
    assert dashboard.todo_category.itemText(0) == "Comic"
    assert dashboard.todo_category.itemData(0) == "漫畫"
    assert dashboard.today_add_button.text() == "＋ Add task"
    assert dashboard.today_save_idea_button.text() == "✦ Save idea"
    assert dashboard.today_tasks_heading.text() == "<b>Tasks for today</b>"
    assert dashboard.creative_ideas_heading.text() == "<b>Creative ideas</b>"
    assert dashboard.todo_count.text() == "0 open"
    assert dashboard.idea_count.text() == "0 saved"
    assert dashboard.work_label.text().startswith("Today ")
    assert dashboard.voice_engine.currentData() == VOICE_ENGINE_WINDOWS
    assert dashboard.windows_voice.currentData() == "OneCore::Microsoft Zira"
    assert dashboard.permission_controls["delete_files"].currentData() == "禁止"
    assert dashboard.permission_controls["delete_files"].currentText() == "Deny"
    assert dashboard.persona_prompt.toPlainText().strip() == (
        default_persona_for_language("en").strip()
    )
    spoken: list[str] = []
    dashboard.speak_requested.connect(
        lambda text, _expression: spoken.append(text)
    )
    dashboard._mode_changed("會議")
    assert spoken[-1].startswith("Meeting mode enabled")

    dashboard.reminder_message_controls["lunch"].setText(custom_lunch)
    zh_index = dashboard.profile_ui_language.findData("zh-TW")
    dashboard.profile_ui_language.setCurrentIndex(zh_index)
    assert dashboard.save_settings(silent=True)
    assert db.setting("reminder_message_work") == REMINDER_LINES["work"]
    assert db.setting("reminder_message_lunch") == custom_lunch
    stored_persona = str(db.setting("persona_prompt"))
    visible_persona = dashboard.persona_prompt.toPlainText()
    assert stored_persona.strip() == visible_persona.strip()

    en_index = dashboard.profile_ui_language.findData("en")
    dashboard.profile_ui_language.setCurrentIndex(en_index)
    assert dashboard.save_settings(silent=True)
    assert db.setting("reminder_message_work") == ENGLISH_REMINDER_LINES["work"]
    assert db.setting("reminder_message_lunch") == custom_lunch
    close_dashboard(app, dashboard)


def assert_english_profile(
    app: QApplication,
    female_voices: list[tuple[str, str]],
    custom_lunch: str,
) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan.db")
        assert_english_wizard(app, db)
        db.set_setting("onboarding_complete", True)
        assert_english_dashboard(app, db, female_voices, custom_lunch)
        db.close()


def assert_simplified_wizard(app: QApplication, db: StudioDB) -> None:
    wizard = FirstRunWizard(db)
    simplified_index = wizard.ui_language.findData("zh-CN")
    wizard.ui_language.setCurrentIndex(simplified_index)
    app.processEvents()
    assert wizard.windowTitle() == "首次启动设置"
    assert "千年女剑魂" in wizard.hero_tagline.text()
    assert wizard.form_labels["assistant_name"].text() == "助手名称"
    assert wizard.work_type.itemText(0) == "一般办公／行政"
    wizard._save()
    assert db.setting("ui_language") == "zh-CN"
    assert db.setting("transcription_language") == "zh"
    assert "请使用中国简体中文准确转录" in str(
        db.setting("transcription_prompt")
    )
    assert db.setting("voice_engine") == VOICE_ENGINE_WINDOWS
    assert db.setting("persona_prompt") == default_persona_for_language("zh-CN")
    assert db.setting("voice_instructions") == simplified_chinese_voice_instructions()
    assert "简体中文" in response_language_instruction("zh-CN")
    assert "妾在听" in offline_reply("你好", "陪伴", "zh-CN")
    wizard.close()


def assert_simplified_dashboard(
    app: QApplication,
    db: StudioDB,
    female_voices: list[tuple[str, str]],
) -> None:
    listener = FakeListener()
    dashboard = Dashboard(
        db,
        dashboard_dependencies(db, listener, female_voices),
    )
    assert dashboard.tabs.tabText(0) == "对话"
    assert dashboard.windows_voice.currentData() == "OneCore::Microsoft Xiaoxiao"
    assert dashboard.windows_voice.findData("OneCore::Microsoft Zira") == -1
    assert dashboard.windows_voice.findData("OneCore::Microsoft Yating") >= 0
    assert dashboard.permission_controls["delete_files"].currentText() == "禁止"
    assert dashboard.persona_prompt.toPlainText().strip() == (
        default_persona_for_language("zh-CN").strip()
    )
    simplified_spoken: list[str] = []
    dashboard.speak_requested.connect(
        lambda text, _expression: simplified_spoken.append(text)
    )
    dashboard._mode_changed("會議")
    assert simplified_spoken[-1].startswith("会议模式已启动")
    close_dashboard(app, dashboard)


def assert_simplified_profile(
    app: QApplication,
    female_voices: list[tuple[str, str]],
) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan-zh-cn.db")
        assert_simplified_wizard(app, db)
        db.set_setting("onboarding_complete", True)
        assert_simplified_dashboard(app, db, female_voices)
        db.close()


def assert_traditional_profile(
    app: QApplication,
    female_voices: list[tuple[str, str]],
) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan-zh.db")
        db.set_setting("onboarding_complete", True)
        db.set_setting("ui_language", "zh-TW")
        listener = FakeListener()
        dashboard = Dashboard(
            db,
            dashboard_dependencies(db, listener, female_voices),
        )
        assert dashboard.voice_engine.currentData() == VOICE_ENGINE_WINDOWS
        assert dashboard.windows_voice.currentData() == "OneCore::Microsoft Yating"
        assert dashboard.windows_voice.findData("OneCore::Microsoft Zira") == -1
        assert dashboard.windows_voice.findData("OneCore::Microsoft Xiaoxiao") >= 0
        close_dashboard(app, dashboard)

        dashboard = Dashboard(
            db,
            dashboard_dependencies(
                db,
                listener,
                [("OneCore::Microsoft Zira", "en-US")],
            ),
        )
        assert dashboard.windows_voice.findData("OneCore::Microsoft Zira") == -1
        assert str(dashboard.windows_voice.currentData() or "") == ""
        close_dashboard(app, dashboard)
        db.close()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    custom_lunch = assert_language_tables_and_reminders()
    female_voices = assert_companion_voice_policy()
    assert_empty_voice_selection_fails()
    assert_english_profile(app, female_voices, custom_lunch)
    assert_simplified_profile(app, female_voices)
    assert_traditional_profile(app, female_voices)
    app.processEvents()
    print("LANGUAGE_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
