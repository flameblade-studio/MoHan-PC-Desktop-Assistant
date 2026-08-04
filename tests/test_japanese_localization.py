from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ai_client import JAPANESE_PERSONA, offline_reply
from app import Dashboard, FirstRunWizard, VOICE_ENGINE_WINDOWS, normalize_for_language
from azure_speech import azure_female_voices
from db import StudioDB
from language_support import (
    JAPANESE_REMINDER_LINES,
    is_japanese,
    japanese_voice_instructions,
    migrate_builtin_reminder_line,
    response_language_instruction,
    transcription_language_for_ui,
)
from speech import preferred_windows_voice
from ui_localization import _ENGLISH
from ui_localization_ja import JAPANESE_UI


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


def close_dashboard(app: QApplication, dashboard: Dashboard) -> None:
    for timer in dashboard.findChildren(QTimer):
        timer.stop()
    dashboard.close()
    dashboard.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    assert set(JAPANESE_UI) == set(_ENGLISH)
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

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan-ja.db")
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
        assert db.setting("voice_engine") == VOICE_ENGINE_WINDOWS
        assert db.setting("persona_prompt") == JAPANESE_PERSONA
        assert db.setting("voice_instructions") == japanese_voice_instructions()
        wizard.close()

        db.set_setting("onboarding_complete", True)
        listener = FakeListener()
        with patch("app.windows_voices", return_value=windows_voices):
            dashboard = Dashboard(db, listener, FakeSecretStore())
        assert dashboard.tabs.tabText(0) == "会話"
        assert dashboard.windows_voice.currentData() == (
            "OneCore::Microsoft Ayumi"
        )
        assert dashboard.permission_controls["delete_files"].currentText() == "禁止"
        assert dashboard.persona_prompt.toPlainText().strip() == (
            JAPANESE_PERSONA.strip()
        )
        spoken: list[str] = []
        dashboard.speak_requested.connect(
            lambda text, _expression: spoken.append(text)
        )
        dashboard._mode_changed("會議")
        assert spoken[-1].startswith("会議モードを開始")
        close_dashboard(app, dashboard)
        db.close()

    app.processEvents()
    print("JAPANESE_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
