from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from ai_client import ENGLISH_PERSONA, offline_reply
from app import (
    Dashboard,
    FirstRunWizard,
    REMINDER_LINES,
    VOICE_ENGINE_WINDOWS,
)
from db import StudioDB
from language_support import (
    ENGLISH_REMINDER_LINES,
    english_voice_instructions,
    migrate_builtin_reminder_line,
    response_language_instruction,
)
from speech import (
    WindowsTTS,
    _is_allowed_companion_voice,
    preferred_windows_voice,
)


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


def run() -> None:
    app = QApplication.instance() or QApplication([])

    chinese_lunch = "午膳時辰到了。工作可以等，身體不可以。"
    assert migrate_builtin_reminder_line(
        chinese_lunch,
        "en",
        "lunch",
        chinese_lunch,
    ) == ENGLISH_REMINDER_LINES["lunch"]
    assert migrate_builtin_reminder_line(
        ENGLISH_REMINDER_LINES["lunch"],
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

    # Gender is strict. Known legacy Taiwan voices remain compatible when an
    # older registry omits Gender, but an arbitrary unknown voice is hidden.
    assert _is_allowed_companion_voice("Microsoft Yating", "")
    assert _is_allowed_companion_voice("Microsoft Hanhan", "")
    assert _is_allowed_companion_voice("Microsoft Zira", "Female")
    assert not _is_allowed_companion_voice("Microsoft David", "Male")
    assert not _is_allowed_companion_voice("Third-party Voice", "")
    assert not _is_allowed_companion_voice("Microsoft Zhiwei", "Female")

    female_voices = [
        ("OneCore::Microsoft Zira", "en-US"),
        ("OneCore::Microsoft Hanhan", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
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
        saved="OneCore::Microsoft Hanhan",
        target_language="en",
    ) == "OneCore::Microsoft Hanhan"
    assert preferred_windows_voice(
        female_voices,
        saved="OneCore::Microsoft Zira",
        target_language="zh-TW",
    ) == "OneCore::Microsoft Zira"

    # The runtime never lets an empty selection fall through to an arbitrary
    # Windows system default, which could be male.
    tts = WindowsTTS()
    failures: list[str] = []
    tts.failed.connect(failures.append)
    with patch("speech.windows_voices", return_value=[]):
        tts._run("Hello", "", 0)
    assert failures and "女性" in failures[-1]

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan.db")
        wizard = FirstRunWizard(db)
        english_index = wizard.ui_language.findData("en")
        wizard.ui_language.setCurrentIndex(english_index)
        app.processEvents()
        assert wizard.windowTitle() == "First-run setup"
        assert wizard.form_labels["assistant_name"].text() == "Assistant name"
        assert wizard.assistant_name.text() == "MoHan"
        assert wizard.user_title.text() == "Commander"
        chinese_index = wizard.ui_language.findData("zh-TW")
        wizard.ui_language.setCurrentIndex(chinese_index)
        app.processEvents()
        assert wizard.windowTitle() == "首次啟動設定"
        assert wizard.assistant_name.text() == "墨寒"
        assert wizard.user_title.text() == "主上"
        wizard.ui_language.setCurrentIndex(english_index)
        app.processEvents()
        wizard._save()
        assert db.setting("ui_language") == "en"
        assert db.setting("transcription_language") == "en"
        assert db.setting("voice_engine") == VOICE_ENGINE_WINDOWS
        assert db.setting("persona_prompt") == ENGLISH_PERSONA
        assert db.setting("voice_instructions") == english_voice_instructions()
        assert "Reply in natural English" in response_language_instruction("en")
        assert "I am listening" in offline_reply("Hello", "陪伴", "en")
        wizard.close()

        db.set_setting("onboarding_complete", True)
        listener = FakeListener()
        with patch("app.windows_voices", return_value=female_voices):
            dashboard = Dashboard(db, listener, FakeSecretStore())
        assert dashboard.tabs.tabText(0) == "Chat"
        assert dashboard.voice_engine.currentData() == VOICE_ENGINE_WINDOWS
        assert (
            dashboard.windows_voice.currentData()
            == "OneCore::Microsoft Zira"
        )
        assert dashboard.permission_controls["delete_files"].currentData() == "禁止"
        assert dashboard.permission_controls["delete_files"].currentText() == "Deny"
        assert dashboard.persona_prompt.toPlainText().strip() == ENGLISH_PERSONA.strip()
        spoken: list[str] = []
        dashboard.speak_requested.connect(
            lambda text, _expression: spoken.append(text)
        )
        dashboard._mode_changed("會議")
        assert spoken[-1].startswith("Meeting mode enabled")

        dashboard.reminder_message_controls["lunch"].setText(custom_lunch)
        zh_index = dashboard.profile_ui_language.findData("zh-TW")
        dashboard.profile_ui_language.setCurrentIndex(zh_index)
        with patch("app.set_autostart"):
            assert dashboard.save_settings(silent=True)
        assert db.setting("reminder_message_work") == REMINDER_LINES["work"]
        assert db.setting("reminder_message_lunch") == custom_lunch
        stored_persona = str(db.setting("persona_prompt"))
        visible_persona = dashboard.persona_prompt.toPlainText()
        assert stored_persona.strip() == visible_persona.strip()

        en_index = dashboard.profile_ui_language.findData("en")
        dashboard.profile_ui_language.setCurrentIndex(en_index)
        with patch("app.set_autostart"):
            assert dashboard.save_settings(silent=True)
        assert (
            db.setting("reminder_message_work")
            == ENGLISH_REMINDER_LINES["work"]
        )
        assert db.setting("reminder_message_lunch") == custom_lunch
        dashboard.close()
        db.close()

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan-zh.db")
        db.set_setting("onboarding_complete", True)
        db.set_setting("ui_language", "zh-TW")
        listener = FakeListener()
        with patch("app.windows_voices", return_value=female_voices):
            dashboard = Dashboard(db, listener, FakeSecretStore())
        assert dashboard.voice_engine.currentData() == VOICE_ENGINE_WINDOWS
        assert (
            dashboard.windows_voice.currentData()
            == "OneCore::Microsoft Yating"
        )
        dashboard.close()
        db.close()
    app.processEvents()
    print("ENGLISH_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
