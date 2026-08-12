from __future__ import annotations

lazy import os
lazy import sys
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QAbstractAnimation, QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from app import CompanionWindow
lazy from db import StudioDB


def _create_window(temp_dir: str) -> tuple[QApplication, CompanionWindow]:
    os.environ["LOCALAPPDATA"] = temp_dir
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    preflight = StudioDB(db_path)
    preflight.set_setting("tts_enabled", False)
    preflight.close()
    app = QApplication([])
    window = CompanionWindow(startup_speech=False)
    window.show()
    app.processEvents()
    for timer in window.findChildren(QTimer):
        timer.stop()
    return app, window


def _configure_speech_completion(
    window: CompanionWindow,
    final_state: str,
) -> None:
    window.state = "speaking"
    window.speech_playing = True
    window.audio_driven_mouth = True
    window.speech_closed_expression = "idle_front"
    window.speech_mid_expression = "mouth_mid_front"
    window.speech_open_expression = "speaking_front"
    window.current_expression = "mouth_o_front"
    window.after_speech_state = final_state
    window.after_speech_intensity = 0.8
    window.ambient_motion_y = 0.75
    window.ambient_motion_target_y = 0.0
    window.speech_motion_y = -3.5
    window.speech_motion_target_y = -3.5
    window.gesture_motion_y = 0.0
    window._compose_character_position()


def _assert_completion_has_one_motion_owner(
    window: CompanionWindow,
) -> None:
    _configure_speech_completion(window, "happy")
    window.current_expression = window.speech_closed_expression
    window._speech_audio_finished()

    assert window.speech_playing
    assert window.speech_motion_target_y == 0.0
    assert window.head_motion_y == 0.0
    positions = [window.character.pos().y()]
    for _ in range(8):
        window._motion_tick()
        positions.append(window.character.pos().y())
    position_before_handoff = window.character.pos()
    window._complete_speech_audio_finished()

    assert not window.speech_playing
    assert window.character.pos() == position_before_handoff
    assert window.speech_motion_y == 0.0
    assert max(
        abs(current - previous)
        for previous, current in pairwise(positions)
    ) <= 1
    animation = getattr(window, "state_animation", None)
    assert animation is None or animation.state() == QAbstractAnimation.Stopped


def _assert_release_is_gradual(window: CompanionWindow) -> None:
    for scale_percent in (75, 100, 180):
        window.character_scale_percent = scale_percent
        window.character_scale = scale_percent / 100.0
        _configure_speech_completion(window, "idle")
        window._begin_speech_motion_release()
        positions = [window.character.pos().y()]
        for _ in range(12):
            window._motion_tick()
            positions.append(window.character.pos().y())
        deltas = [
            current - previous
            for previous, current in pairwise(positions)
        ]
        assert all(delta >= 0 for delta in deltas)
        assert max(deltas, default=0) <= 2
        assert round(window.speech_motion_y * window.character_scale) == 0


def _assert_late_viseme_cannot_restart_motion(
    window: CompanionWindow,
) -> None:
    _configure_speech_completion(window, "idle")
    window._begin_speech_motion_release()
    position_before = window.character.pos()

    window._audio_viseme_cue(1.0, "A")

    assert window.character.pos() == position_before
    assert window.speech_motion_target_y == 0.0
    assert window.mouth_closing


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        app, window = _create_window(temp_dir)
        try:
            _assert_completion_has_one_motion_owner(window)
            _assert_release_is_gradual(window)
            _assert_late_viseme_cannot_restart_motion(window)
        finally:
            window.close()
            app.processEvents()
    print("POST_SPEECH_MOTION_CONTINUITY_OK")


if __name__ == "__main__":
    run()
