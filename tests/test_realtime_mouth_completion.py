from __future__ import annotations

lazy import os
lazy import random
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from app import CompanionWindow
lazy from db import StudioDB

COMPLETION_EVENTS = (
    "response.output_audio.done",
    "response.audio.done",
    "response.done",
    "response.cancelled",
    "response.failed",
    "input_audio_buffer.speech_started",
)


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = (
            Path(temp_dir)
            / "YanJianStudio"
            / "MoHan"
            / "mohan.db"
        )
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(type(window.idle_timer)):
            timer.stop()

        rng = random.Random(1205)
        with patch.object(
            window.realtime,
            "_assistant_audio_watchdog",
        ):
            for _ in range(40):
                window.idle_pose = rng.choice(("cheek", "lean", "front"))
                window.realtime._begin_assistant_audio()
                window._audio_viseme_cue(
                    rng.uniform(0.08, 0.42),
                    rng.choice(("A", "I", "E", "O", "U")),
                )
                event_type = rng.choice(COMPLETION_EVENTS)
                window.realtime._handle_server_event(
                    {"type": event_type}
                )
                if rng.random() < 0.35:
                    # Duplicate and out-of-order completion events are legal
                    # cleanup noise and must remain harmless.
                    window.realtime._handle_server_event(
                        {"type": rng.choice(COMPLETION_EVENTS)}
                    )
                QTest.qWait(160)
                app.processEvents()
                assert not window.realtime._assistant_audio_active.is_set()
                assert not window.realtime_mouth_active
                assert not window.realtime_finish_timer.isActive()
                assert not window.mouth_timer.isActive()
                assert not window.mouth_visual_timer.isActive()
                assert not window.audio_driven_mouth
                assert not window.mouth_open
                assert window.viseme_dynamics.current == "CLOSED"
                assert window.state != "speaking"

        window.close()
        app.processEvents()
    print("REALTIME_MOUTH_COMPLETION_OK")


if __name__ == "__main__":
    run()
