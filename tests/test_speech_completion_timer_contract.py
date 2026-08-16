from __future__ import annotations

lazy import os
lazy import sys
lazy from collections.abc import Callable
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QAbstractAnimation, QPoint, QTimer
lazy from PySide6.QtWidgets import QApplication, QLabel

lazy from companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB
lazy from speech_configuration import QueuedSpeech

FINAL_STATE = "proud_front"
FINAL_STATE_SOURCE = "ai_tag"
MAX_COMPLETION_CYCLES = 20
MAX_VISIBLE_FRAME_DELTA_PIXELS = 2
TIMER_ORDERS = {
    "mouth-motion-finish": ("mouth", "motion", "finish"),
    "finish-motion-mouth": ("finish", "motion", "mouth"),
    "motion-duplicate-finish": (
        "motion",
        "finish",
        "finish",
        "mouth",
    ),
}


def _create_window(
    temp_dir: str,
) -> tuple[QApplication, CompanionWindow]:
    os.environ["LOCALAPPDATA"] = temp_dir
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    preflight = StudioDB(db_path)
    preflight.set_setting("tts_enabled", False)
    preflight.close()
    app = QApplication([])
    window = CompanionWindow(startup_speech=False)
    window.show()
    app.processEvents()
    _stop_timers(window)
    return app, window


def _stop_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def _character_layers(window: CompanionWindow) -> tuple[QLabel, ...]:
    return (
        window.character,
        window.expression_overlay,
        window.sleeve_left_overlay,
        window.sleeve_right_overlay,
        window.hair_left_overlay,
        window.hair_right_overlay,
        window.physics_overlay,
        window.face_overlay,
        window.eye_overlay,
    )


def _sample_position(window: CompanionWindow) -> QPoint:
    body_position = window.character.pos()
    assert all(
        layer.pos() == body_position for layer in _character_layers(window)
    ), "speech completion split the layered character coordinates"
    return QPoint(body_position)


def _reset_window(window: CompanionWindow) -> None:
    _stop_timers(window)
    window._cancel_expression_transition()
    window._cancel_pose_transition()
    window._stop_gesture_animation()
    window.speech_queue.clear()
    window.speech_playing = False
    window.active_speech_text = ""
    window.realtime_mouth_active = False
    window.audio_driven_mouth = False
    window.mouth_closing = False
    window.speech_gesture_expression = None
    window.speech_motion_release_attempts = 0
    window.realtime_motion_release_attempts = 0
    window.head_motion_y = 0.0
    window.ambient_motion_x = 0.0
    window.ambient_motion_y = 0.0
    window.ambient_motion_target_x = 0.0
    window.ambient_motion_target_y = 0.0
    window.speech_motion_y = 0.0
    window.speech_motion_target_y = 0.0
    window.gesture_motion_x = 0.0
    window.gesture_motion_y = 0.0
    window.gaze_x = 0.0
    window.gaze_y = 0.0
    window.idle_pose = "front"
    window.speech_closed_expression = "idle_front"
    window.speech_mid_expression = "mouth_mid_front"
    window.speech_open_expression = "speaking_front"
    window.after_speech_state = "idle"
    window.realtime_after_speech_state = "idle"
    window.state = "idle"
    window.expression_arbiter.request("idle", force=True)
    window._stop_mouth_animation()
    window._set_expression("idle_front", fade=False)
    window.last_composed_body_position = None
    window._compose_character_position()
    _stop_timers(window)
    assert _sample_position(window).y() == window.character_base_y


def _begin_speech(window: CompanionWindow, path: str) -> None:
    if path == "general":
        window._begin_speech_presentation(
            QueuedSpeech(
                "計時器完成契約",
                FINAL_STATE,
                0.8,
                FINAL_STATE_SOURCE,
            )
        )
        window.after_speech_state = FINAL_STATE
        window.after_speech_intensity = 0.8
        window._start_mouth_animation(audio_driven=True)
        assert window.after_speech_state == FINAL_STATE
    else:
        window._realtime_speaking(True)
        window.realtime_after_speech_state = FINAL_STATE
        window.realtime_after_speech_intensity = 0.8
        assert window.realtime_after_speech_state == FINAL_STATE
    for vowel in ("A", "A", "A", "O", "O", "O", "E", "E"):
        window._audio_viseme_cue(0.95, vowel)
    assert window.state == "speaking"
    assert window.audio_driven_mouth
    assert window.speech_motion_y < -1.0
    assert window.current_expression != window.speech_closed_expression


def _completion_is_active(window: CompanionWindow, path: str) -> bool:
    if path == "general":
        return window.speech_playing
    return (
        window.state == "speaking"
        and window.audio_driven_mouth
        and not window.speech_playing
    )


def _completion_timer(window: CompanionWindow, path: str) -> QTimer:
    return (
        window.speech_finish_timer
        if path == "general"
        else window.realtime_finish_timer
    )


def _completion_callback(
    window: CompanionWindow,
    path: str,
) -> Callable[[], None]:
    return (
        window._complete_speech_audio_finished
        if path == "general"
        else window._complete_realtime_speaking_stop
    )


def _signal_audio_finished(window: CompanionWindow, path: str) -> None:
    if path == "general":
        window._speech_audio_finished()
    else:
        window._realtime_speaking(False)


def _final_state_calls(set_state: MagicMock) -> list:
    return [
        call
        for call in set_state.call_args_list
        if call.args and call.args[0] == FINAL_STATE
    ]


def _run_timer_action(
    window: CompanionWindow,
    callback: Callable[[], None],
    action: str,
    context: str,
) -> None:
    before = _sample_position(window)
    if action == "mouth":
        window._render_audio_mouth_transition()
    elif action == "motion":
        window._motion_tick()
    else:
        callback()
    after = _sample_position(window)
    if action in {"mouth", "finish"}:
        assert after == before, (
            f"{context}: {action} callback changed the visible pixel"
        )
        return
    assert abs(after.y() - before.y()) <= MAX_VISIBLE_FRAME_DELTA_PIXELS, (
        f"{context}: motion timer jumped from {before.y()} to {after.y()}"
    )


def _assert_timer_order_contract(
    window: CompanionWindow,
    path: str,
    order_name: str,
) -> None:
    _reset_window(window)
    _begin_speech(window, path)
    callback = _completion_callback(window, path)
    timer = _completion_timer(window, path)
    with patch.object(
        window,
        "set_state",
        wraps=window.set_state,
    ) as set_state:
        _signal_audio_finished(window, path)
        _signal_audio_finished(window, path)
        assert timer.isActive(), (
            f"{path}/{order_name}: duplicate end signal lost the timer"
        )
        assert window.mouth_closing
        assert window.speech_motion_target_y == 0.0

        position_before_late_viseme = _sample_position(window)
        window._audio_viseme_cue(1.0, "A")
        assert _sample_position(window) == position_before_late_viseme
        assert window.speech_motion_target_y == 0.0

        for cycle in range(MAX_COMPLETION_CYCLES):
            if not _completion_is_active(window, path):
                break
            context = f"{path}/{order_name}/cycle-{cycle}"
            for action in TIMER_ORDERS[order_name]:
                _run_timer_action(window, callback, action, context)

        assert not _completion_is_active(window, path), (
            f"{path}/{order_name}: completion did not converge"
        )
        assert not timer.isActive()
        assert window.state == FINAL_STATE, (
            f"{path}/{order_name}: final state was {window.state!r}"
        )
        handoff_calls = _final_state_calls(set_state)
        assert len(handoff_calls) == 1, (
            f"{path}/{order_name}: state handoff count was "
            f"{len(handoff_calls)}"
        )
        assert handoff_calls[0].kwargs["animate_gesture"] is False
        animation = getattr(window, "state_animation", None)
        assert animation is None or (
            animation.state() == QAbstractAnimation.Stopped
        ), f"{path}/{order_name}: post-speech gesture replayed"
        assert window.gesture_motion_x == 0.0
        assert window.gesture_motion_y == 0.0

        completed_position = _sample_position(window)
        completed_state = window.state
        completed_call_count = len(set_state.call_args_list)
        callback()
        callback()
        _signal_audio_finished(window, path)
        window._audio_viseme_cue(1.0, "O")
        assert _sample_position(window) == completed_position
        assert window.state == completed_state
        assert len(set_state.call_args_list) == completed_call_count
        assert len(_final_state_calls(set_state)) == 1

        release_positions = [_sample_position(window)]
        for _ in range(MAX_COMPLETION_CYCLES):
            window._motion_tick()
            release_positions.append(_sample_position(window))
            if release_positions[-1].y() == window.character_base_y:
                break
        assert release_positions[-1].y() == window.character_base_y
        assert max(
            (
                abs(current.y() - previous.y())
                for previous, current in pairwise(release_positions)
            ),
            default=0,
        ) <= MAX_VISIBLE_FRAME_DELTA_PIXELS


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app, window = _create_window(temp_dir)
        try:
            for path in ("general", "realtime"):
                for order_name in TIMER_ORDERS:
                    _assert_timer_order_contract(
                        window,
                        path,
                        order_name,
                    )
        finally:
            window.speech_queue.clear()
            window.speech_playing = False
            window.close()
            app.processEvents()
    print("SPEECH_COMPLETION_TIMER_CONTRACT_OK")


if __name__ == "__main__":
    run()
