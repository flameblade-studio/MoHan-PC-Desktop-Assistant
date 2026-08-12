from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from itertools import pairwise, product
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication, QLabel

lazy from app import CompanionWindow, QueuedSpeech
lazy from db import StudioDB

COMPLETION_PATHS = ("general", "realtime")
SCALE_PERCENTAGES = (75, 100, 180)
POSES = ("front", "lean", "cheek")
FINAL_KINDS = ("idle", "emotion")
POSE_SUFFIXES = {
    "front": "_front",
    "lean": "_lean",
    "cheek": "",
}
IDLE_EXPRESSIONS = {
    "front": "idle_front",
    "lean": "idle_lean",
    "cheek": "idle",
}
EMOTIONS = {
    "front": "protective_front",
    "lean": "proud_front",
    "cheek": "happy",
}
MAX_RELEASE_TICKS = 16
MAX_AMBIENT_SETTLE_TICKS = 32
MAX_FRAME_DELTA_PIXELS = 2


@dataclass(frozen=True, slots=True)
class MotionSample:
    x: int
    y: int


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
    _stop_all_timers(window)
    return app, window


def _stop_all_timers(window: CompanionWindow) -> None:
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


def _sample(window: CompanionWindow) -> MotionSample:
    layers = _character_layers(window)
    body_position = window.character.pos()
    assert all(layer.pos() == body_position for layer in layers), (
        "every layered character surface must share one composed coordinate"
    )
    return MotionSample(body_position.x(), body_position.y())


def _reset_scenario(
    window: CompanionWindow,
    scale_percent: int,
    pose: str,
) -> None:
    _stop_all_timers(window)
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
    window.after_speech_state = "idle"
    window.realtime_after_speech_state = "idle"
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
    window.gaze_target_x = 0.0
    window.gaze_target_y = 0.0
    window.motion_base_x = 0
    window.motion_base_y = window.character_base_y
    window.idle_pose = pose
    idle_expression = IDLE_EXPRESSIONS[pose]
    window.speech_closed_expression = idle_expression
    window.speech_mid_expression = f"mouth_mid{POSE_SUFFIXES[pose]}"
    window.speech_open_expression = f"speaking{POSE_SUFFIXES[pose]}"
    window._stop_mouth_animation()
    window.state = "idle"
    window.expression_arbiter.request("idle", force=True)
    window._apply_character_scale(scale_percent, preserve_anchor=False)
    window._set_expression(idle_expression, fade=False)
    window.last_composed_body_position = None
    window._compose_character_position()
    _stop_all_timers(window)
    assert window.character_scale_percent == scale_percent
    assert _sample(window).y == window.character_base_y


def _begin_general_speech(
    window: CompanionWindow,
    final_state: str,
) -> None:
    window._begin_speech_presentation(
        QueuedSpeech("一般語音完成流程", "speaking")
    )
    window.after_speech_state = final_state
    window.after_speech_intensity = 0.8
    window._start_mouth_animation(audio_driven=True)


def _begin_realtime_speech(
    window: CompanionWindow,
    final_state: str,
) -> None:
    window._realtime_speaking(True)
    window.realtime_after_speech_state = final_state
    window.realtime_after_speech_intensity = 0.8


def _drive_strong_visemes(window: CompanionWindow) -> None:
    for _ in range(8):
        window._audio_viseme_cue(0.95, "A")
        _sample(window)
    assert window.state == "speaking"
    assert window.audio_driven_mouth
    assert window.speech_motion_y < -2.0
    assert window.current_expression != window.speech_closed_expression


def _completion_is_active(window: CompanionWindow, path: str) -> bool:
    if path == "general":
        return window.speech_playing
    return window.state == "speaking" and window.audio_driven_mouth


def _begin_completion(window: CompanionWindow, path: str) -> None:
    if path == "general":
        window._speech_audio_finished()
    else:
        window._realtime_speaking(False)


def _advance_completion(window: CompanionWindow, path: str) -> None:
    if path == "general":
        window._complete_speech_audio_finished()
    else:
        window._complete_realtime_speaking_stop()


def _motion_steps(samples: list[MotionSample]) -> list[int]:
    return [
        current.y - previous.y
        for previous, current in pairwise(samples)
    ]


def _assert_smooth_upward_release(
    samples: list[MotionSample],
    context: str,
) -> None:
    assert all(sample.x == samples[0].x for sample in samples), (
        f"{context}: speech completion introduced horizontal movement"
    )
    steps = _motion_steps(samples)
    assert all(step >= 0 for step in steps), (
        f"{context}: motion reversed during release; trace={samples!r}"
    )
    assert max(steps, default=0) <= MAX_FRAME_DELTA_PIXELS, (
        f"{context}: release snapped by more than "
        f"{MAX_FRAME_DELTA_PIXELS}px; trace={samples!r}"
    )


def _settle_ambient_motion(
    window: CompanionWindow,
    context: str,
) -> tuple[MotionSample, ...]:
    samples = [_sample(window)]
    window.ambient_motion_target_x = 0.0
    window.ambient_motion_target_y = 0.0
    for _ in range(MAX_AMBIENT_SETTLE_TICKS):
        if (
            window.ambient_motion_x == 0.0
            and window.ambient_motion_y == 0.0
        ):
            break
        window._motion_tick()
        samples.append(_sample(window))
    _assert_smooth_upward_release(samples, f"{context}/ambient")
    assert samples[-1].y == window.character_base_y, (
        f"{context}: ambient ownership did not settle at the base line; "
        f"trace={samples!r}; ambient={window.ambient_motion_y}"
    )
    settled = _sample(window)
    window._motion_tick()
    assert _sample(window) == settled, (
        f"{context}: body moved again after ambient motion had settled"
    )
    return tuple(samples)


def _assert_release_trace(
    window: CompanionWindow,
    path: str,
    final_state: str,
    context: str,
) -> tuple[MotionSample, ...]:
    samples = [_sample(window)]
    assert samples[0].y < window.character_base_y
    _begin_completion(window, path)
    samples.append(_sample(window))
    assert window.head_motion_y == 0.0
    assert window.speech_motion_target_y == 0.0
    assert _completion_is_active(window, path)
    assert window.state == "speaking"

    for _ in range(MAX_RELEASE_TICKS):
        if not _completion_is_active(window, path):
            break
        window._motion_tick()
        samples.append(_sample(window))
        position_before_handoff = samples[-1]
        _advance_completion(window, path)
        samples.append(_sample(window))
        if not _completion_is_active(window, path):
            assert samples[-1] == position_before_handoff, (
                f"{context}: state hand-off changed the composed coordinate"
            )
        if _completion_is_active(window, path):
            assert window.state == "speaking", (
                "state hand-off occurred before speech motion was centred"
            )

    assert not _completion_is_active(window, path)
    assert window.state == final_state
    assert window.speech_motion_y == 0.0
    assert window.speech_motion_target_y == 0.0
    assert not window.speech_finish_timer.isActive()
    assert not window.realtime_finish_timer.isActive()
    assert not window.mouth_timer.isActive()
    assert not window.mouth_visual_timer.isActive()
    assert not window.audio_driven_mouth
    _assert_smooth_upward_release(samples, f"{context}/speech")

    completed = _sample(window)
    _begin_completion(window, path)
    assert _sample(window) == completed, (
        "a duplicate completion signal changed the body coordinate"
    )
    _settle_ambient_motion(window, context)
    return tuple(samples)


def _run_completion_matrix(window: CompanionWindow) -> None:
    scenarios = product(
        COMPLETION_PATHS,
        SCALE_PERCENTAGES,
        POSES,
        FINAL_KINDS,
    )
    for path, scale_percent, pose, final_kind in scenarios:
        _reset_scenario(window, scale_percent, pose)
        final_state = (
            "idle" if final_kind == "idle" else EMOTIONS[pose]
        )
        if path == "general":
            _begin_general_speech(window, final_state)
        else:
            _begin_realtime_speech(window, final_state)
        assert window.speech_pose_suffix == POSE_SUFFIXES[pose]
        _drive_strong_visemes(window)
        _assert_release_trace(
            window,
            path,
            final_state,
            f"{path}/{scale_percent}/{pose}/{final_kind}",
        )


def _run_queued_speech_matrix(window: CompanionWindow) -> None:
    for scale_percent, pose in product(SCALE_PERCENTAGES, POSES):
        _reset_scenario(window, scale_percent, pose)
        _begin_general_speech(window, "idle")
        _drive_strong_visemes(window)
        window.speech_queue.append(
            QueuedSpeech("排隊中的下一句", "speaking")
        )
        _assert_release_trace(
            window,
            "general",
            "idle",
            f"queued-first/{scale_percent}/{pose}",
        )
        assert len(window.speech_queue) == 1

        handoff_position = _sample(window)
        window._start_next_speech()
        assert window.speech_playing
        assert window.active_speech_text == "排隊中的下一句"
        assert not window.speech_queue
        assert _sample(window) == handoff_position
        assert window.speech_motion_y == 0.0
        window.mouth_timer.stop()
        window.audio_driven_mouth = True
        _drive_strong_visemes(window)
        _assert_release_trace(
            window,
            "general",
            "idle",
            f"queued-second/{scale_percent}/{pose}",
        )


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app, window = _create_window(temp_dir)
        try:
            with patch.object(
                window,
                "_start_speech_provider",
                side_effect=AssertionError(
                    "provider matrix must remain fully offline"
                ),
            ):
                _run_completion_matrix(window)
                _run_queued_speech_matrix(window)
        finally:
            window.speech_queue.clear()
            window.speech_playing = False
            window.close()
            app.processEvents()
    print("POST_SPEECH_MOTION_PROVIDER_MATRIX_OK")


if __name__ == "__main__":
    run()
