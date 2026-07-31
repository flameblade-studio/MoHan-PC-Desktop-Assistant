from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from db import StudioDB
from service_container import CompanionServices


class FakeSecretStore:
    def __init__(self) -> None:
        self.value = "test-key"

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class FakeSpeechEngine(QObject):
    finished = Signal()
    failed = Signal(str)
    viseme_cue = Signal(str, float)

    def __init__(self) -> None:
        super().__init__()
        self.volume_calls: list[tuple[int, bool]] = []
        self.speak_calls: list[tuple[tuple, dict]] = []

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))

    def speak(self, *args, **kwargs) -> None:
        self.speak_calls.append((args, kwargs))


class FakeRealtime(QObject):
    status_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    speaking_changed = Signal(bool)
    viseme_cue = Signal(str, float)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.stop_calls = 0
        self.volume_calls: list[tuple[int, bool]] = []

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_calls.append((volume_percent, muted))

    def start(self, *args, **kwargs) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.stop_calls += 1


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.is_recording = False
        self.toggle_calls = 0

    def toggle_listening(self) -> None:
        self.toggle_calls += 1


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        app = QApplication.instance() or QApplication([])
        db = StudioDB(Path(temp) / "mohan.db")
        db.set_setting("onboarding_complete", True)
        db.set_setting("tts_enabled", False)
        db.set_setting("voice_volume_percent", 137)
        db.set_setting("voice_muted", False)
        secret_store = FakeSecretStore()
        local_tts = FakeSpeechEngine()
        cloud_tts = FakeSpeechEngine()
        realtime = FakeRealtime()
        listener = FakeListener()
        services = CompanionServices(
            db=db,
            secret_store=secret_store,
            local_tts=local_tts,
            cloud_tts=cloud_tts,
            realtime=realtime,
            listener=listener,
        )
        window = CompanionWindow(
            startup_speech=False,
            services=services,
        )
        assert window.db is db
        assert window.secret_store is secret_store
        assert window.tts is local_tts
        assert window.cloud_tts is cloud_tts
        assert window.realtime is realtime
        assert window.listener is listener
        assert local_tts.volume_calls[-1] == (137, False)
        assert cloud_tts.volume_calls[-1] == (137, False)
        assert realtime.volume_calls[-1] == (137, False)
        db.set_setting("tts_enabled", True)
        db.set_setting("voice_engine", "OpenAI 自然語音")
        db.set_setting("windows_voice", "OneCore::Microsoft Yating")
        window.speak("主上，妾在。", "speaking")
        assert cloud_tts.speak_calls
        assert not local_tts.speak_calls
        cloud_tts.failed.emit("模擬雲端播放失敗")
        app.processEvents()
        assert local_tts.speak_calls[-1][0] == (
            "主上，妾在。",
            "OneCore::Microsoft Yating",
            -1,
        )
        assert window.cloud_fallback_active
        window.dashboard.mic_btn.click()
        assert listener.toggle_calls == 1
        window.close()
        app.processEvents()
        assert realtime.stop_calls == 1
    print("DEPENDENCY_INJECTION_OK")


if __name__ == "__main__":
    run()
