from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB
lazy from speech_configuration import QueuedSpeech

BREATH_CHANGE_LIMIT = 0.22
EMOTION_INTENSITY = 0.86


def _process_after(app: QApplication, milliseconds: int) -> None:
    QTest.qWait(milliseconds)
    app.processEvents()


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


def _configure_front_speech(
    window: CompanionWindow,
    expression: str,
) -> None:
    window.state = "speaking"
    window.audio_driven_mouth = True
    window.speech_closed_expression = "idle_front"
    window.speech_mid_expression = "mouth_mid_front"
    window.speech_open_expression = "speaking_front"
    window.current_expression = expression
    window.character.setPixmap(window.expression_pixmaps[expression])


def _assert_local_speech_completion(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.idle_pose = "front"
    _configure_front_speech(window, "mouth_o_front")
    window.speech_playing = True
    window.after_speech_state = "idle"
    window._speech_audio_finished()
    assert window.speech_playing
    assert window.speech_finish_timer.isActive()
    assert window.mouth_visual_timer.isActive()
    assert window.current_expression == "idle_front"
    # Duplicate completion signals must not skip the natural mouth close.
    window._speech_audio_finished()
    assert window.speech_playing
    assert window.speech_finish_timer.isActive()
    _process_after(app, 165)
    assert not window.speech_playing
    assert not window.speech_finish_timer.isActive()
    assert not window.mouth_visual_timer.isActive()
    assert window.state == "idle"
    assert window.character.pixmap().toImage() == window._render_half_body_frame().toImage()


def _assert_completion_breath_is_continuous(window: CompanionWindow) -> None:
    window.state = "speaking"
    window.current_breath = 0.92
    window.idle_phase = 53
    window.set_state("idle", force=True)
    before_idle_tick = window.current_breath
    window._idle_tick()
    assert abs(window.current_breath - before_idle_tick) <= BREATH_CHANGE_LIMIT, (
        "the first idle breath frame snapped after speech completion"
    )


def _assert_realtime_natural_close(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    _configure_front_speech(window, "mouth_i_front")
    window.realtime_after_speech_state = "idle"
    window._realtime_speaking(False)
    assert window.realtime_finish_timer.isActive()
    assert window.mouth_visual_timer.isActive()
    assert window.mouth_closing
    closing_expression = window.current_expression
    closing_target = window.mouth_transition_to.cacheKey()
    for _ in range(4):
        window._audio_viseme_cue(0.8, "A")
    assert window.viseme_dynamics.current == "CLOSED"
    assert window.current_expression == closing_expression
    assert window.mouth_transition_to.cacheKey() == closing_target
    window._realtime_speaking(False)
    assert window.realtime_finish_timer.isActive()
    _process_after(app, 165)
    assert not window.realtime_finish_timer.isActive()
    assert not window.mouth_visual_timer.isActive()
    assert window.state == "idle"


def _assert_normal_realtime_answer(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    # "speaking" must never survive as a post-audio state.
    window._realtime_speaking(True)
    window._realtime_assistant_text("主上，妾已經聽明白了。")
    assert window.realtime_after_speech_state == "idle"
    window._audio_viseme_cue(0.42, "A")
    window._realtime_speaking(False)
    _process_after(app, 165)
    assert window.state == "idle"
    assert not window.mouth_timer.isActive()
    assert not window.mouth_visual_timer.isActive()
    _process_after(app, 180)
    assert window.state == "idle"
    assert not window.mouth_timer.isActive()


def _assert_emotion_metadata_hidden(window: CompanionWindow) -> None:
    window._realtime_speaking(True)
    window._realtime_assistant_text(
        "主上，妾會護著你。[[MOHAN_EMOTION:protective:0.86]]"
    )
    assert window.realtime_after_speech_state == "protective_front"
    assert window.realtime_after_speech_intensity == EMOTION_INTENSITY
    assert "MOHAN_EMOTION" not in window.bubble_text.text()
    assert "MOHAN_EMOTION" not in window.db.recent_chat(1)[0]["content"]
    window._realtime_speaking(False)
    window._complete_realtime_speaking_stop()


def _assert_answer_state_reset(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.realtime_after_speech_state = "mock_scold"
    window._realtime_speaking(True)
    assert window.realtime_after_speech_state == "idle"
    window._realtime_speaking(False)
    _process_after(app, 130)
    assert window.state == "idle"
    # A stale delayed idle callback cannot interrupt an active answer.
    window._realtime_speaking(True)
    window._return_to_idle()
    assert window.state == "speaking"
    window._realtime_speaking(False)
    _process_after(app, 130)
    assert window.state == "idle"


def _assert_unrelated_state_recovery(window: CompanionWindow) -> None:
    window.realtime_mouth_active = True
    window.state = "idle"
    window.audio_driven_mouth = True
    window.current_expression = "mouth_o_front"
    window.character.setPixmap(window.expression_pixmaps["mouth_o_front"])
    window.mouth_visual_timer.start()
    window.realtime_finish_timer.start(500)
    window._realtime_speaking(False)
    assert window.realtime_finish_timer.isActive()
    window._complete_realtime_speaking_stop()
    assert not window.realtime_finish_timer.isActive()
    assert not window.mouth_visual_timer.isActive()
    assert not window.audio_driven_mouth
    assert not window.realtime_mouth_active
    assert window.current_expression == "idle_front"


def _assert_queued_reply(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    _configure_front_speech(window, "mouth_o_front")
    window.speech_playing = True
    window.after_speech_state = "idle"
    window.speech_queue.append(QueuedSpeech("下一句", "idle"))
    window._speech_audio_finished()
    _process_after(app, 165)
    assert not window.speech_finish_timer.isActive()
    assert not window.speech_playing
    _process_after(app, 140)
    assert window.speech_playing
    assert window.state == "speaking"
    assert "下一句" in window.bubble_text.text()


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        app, window = _create_window(temp_dir)
        try:
            _assert_local_speech_completion(app, window)
            _assert_completion_breath_is_continuous(window)
            _assert_realtime_natural_close(app, window)
            _assert_normal_realtime_answer(app, window)
            _assert_emotion_metadata_hidden(window)
            _assert_answer_state_reset(app, window)
            _assert_unrelated_state_recovery(window)
            _assert_queued_reply(app, window)
        finally:
            window.close()
            app.processEvents()
    print("SPEECH_STATE_MACHINE_OK")


if __name__ == "__main__":
    run()
