from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QEvent, QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication

lazy from application.presentation_ports import PlatformCapabilities, PlatformPaths
lazy from application.service_container import create_presentation_ports
lazy from domain.app_profile import default_persona_for_language
lazy from domain.language_normalization import normalize_for_language
lazy from domain.language_support import (
    JAPANESE_REMINDER_LINES,
    is_japanese,
    japanese_voice_instructions,
    migrate_builtin_reminder_line,
    response_language_instruction,
    transcription_language_for_ui,
)
lazy from domain.speech_configuration import VOICE_ENGINE_WINDOWS
lazy from infrastructure.db import StudioDB
lazy from integrations.ai_client import offline_reply
lazy from integrations.azure_speech import azure_female_voices
lazy from integrations.speech import preferred_windows_voice
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from presentation.ui_localization import _ENGLISH, _JAPANESE


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


def dashboard_dependencies(
    db: StudioDB,
    listener: FakeListener,
    voices: list[tuple[str, str]],
) -> DashboardDependencies:
    ports = replace(
        create_presentation_ports(),
        voice_catalog=StaticVoiceCatalog(voices),
        autostart_configurator=lambda _enabled, _platform: None,
    )
    return DashboardDependencies(
        listener=listener,
        secret_store=FakeSecretStore(),
        platform_services=OfflinePlatformServices(db.path.parent),
        presentation_ports=ports,
    )


def close_dashboard(app: QApplication, dashboard: Dashboard) -> None:
    for timer in dashboard.findChildren(QTimer):
        timer.stop()
    dashboard.close()
    dashboard.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def assert_japanese_language_contracts() -> list[tuple[str, str]]:
    assert set(_JAPANESE) == set(_ENGLISH)
    assert is_japanese("ja-JP")
    assert transcription_language_for_ui("ja-JP") == "ja"
    assert "自然で明瞭な日本語" in response_language_instruction("ja-JP")
    assert "二十代女性" in japanese_voice_instructions()
    assert "妾はここにおります" in offline_reply("こんにちは", "陪伴", "ja-JP")
    assert normalize_for_language("予定を確認します", "ja-JP") == "予定を確認します"

    traditional_lunch = "到吃飯時間了。工作可以稍候，主上的身體不能。"
    assert migrate_builtin_reminder_line(
        traditional_lunch,
        "ja-JP",
        "lunch",
        traditional_lunch,
    ) == JAPANESE_REMINDER_LINES["lunch"]
    assert migrate_builtin_reminder_line(
        "私だけの昼食メッセージ",
        "zh-TW",
        "lunch",
        traditional_lunch,
    ) == "私だけの昼食メッセージ"

    azure_voices = azure_female_voices("ja-JP")
    assert azure_voices == (
        "ja-JP-NanamiNeural",
        "ja-JP-AoiNeural",
        "ja-JP-MayuNeural",
        "ja-JP-ShioriNeural",
    )
    windows_voices = [
        ("OneCore::Microsoft Zira", "en-US"),
        ("OneCore::Microsoft Yating", "zh-TW"),
        ("OneCore::Microsoft Ayumi", "ja-JP"),
    ]
    assert preferred_windows_voice(
        windows_voices,
        target_language="ja-JP",
    ) == "OneCore::Microsoft Ayumi"
    return windows_voices


def assert_japanese_wizard(app: QApplication, db: StudioDB) -> None:
    wizard = FirstRunWizard(db)
    japanese_index = wizard.ui_language.findData("ja-JP")
    assert japanese_index >= 0
    wizard.ui_language.setCurrentIndex(japanese_index)
    app.processEvents()
    assert wizard.windowTitle() == "初回セットアップ"
    assert "千年の女剣魂" in wizard.hero_tagline.text()
    assert wizard.form_labels["assistant_name"].text() == "アシスタント名"
    assert wizard.work_type.itemText(0) == "一般事務／管理"
    assert wizard.assistant_name.text() == "墨寒"
    assert wizard.user_title.text() == "主様"
    wizard._save()
    assert db.setting("ui_language") == "ja-JP"
    assert db.setting("transcription_language") == "ja"
    assert "日本語で正確に文字起こししてください" in str(
        db.setting("transcription_prompt")
    )
    assert db.setting("voice_engine") == VOICE_ENGINE_WINDOWS
    assert db.setting("persona_prompt") == default_persona_for_language("ja-JP")
    assert db.setting("voice_instructions") == japanese_voice_instructions()
    wizard.close()


def assert_japanese_dashboard(
    app: QApplication,
    db: StudioDB,
    windows_voices: list[tuple[str, str]],
) -> None:
    listener = FakeListener()
    dashboard = Dashboard(
        db,
        dashboard_dependencies(db, listener, windows_voices),
    )
    assert dashboard.tabs.tabText(0) == "会話"
    assert dashboard.windows_voice.currentData() == "OneCore::Microsoft Ayumi"
    assert dashboard.permission_controls["delete_files"].currentText() == "禁止"
    assert dashboard.persona_prompt.toPlainText().strip() == (
        default_persona_for_language("ja-JP").strip()
    )
    spoken: list[str] = []
    dashboard.speak_requested.connect(
        lambda text, _expression: spoken.append(text)
    )
    dashboard._mode_changed("會議")
    assert spoken[-1].startswith("会議モードを開始")
    close_dashboard(app, dashboard)


def assert_japanese_profile(
    app: QApplication,
    windows_voices: list[tuple[str, str]],
) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan-ja.db")
        assert_japanese_wizard(app, db)
        db.set_setting("onboarding_complete", True)
        assert_japanese_dashboard(app, db, windows_voices)
        db.close()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    windows_voices = assert_japanese_language_contracts()
    assert_japanese_profile(app, windows_voices)
    app.processEvents()
    print("JAPANESE_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
