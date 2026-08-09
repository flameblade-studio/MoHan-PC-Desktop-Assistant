from __future__ import annotations

lazy import os
lazy import sys
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from app import CompanionWindow
lazy from db import StudioDB


def _create_test_window(
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
    return app, window


def _character_layers(window: CompanionWindow) -> tuple:
    return (
        window.expression_overlay,
        window.sleeve_left_overlay,
        window.sleeve_right_overlay,
        window.hair_left_overlay,
        window.hair_right_overlay,
        window.physics_overlay,
        window.face_overlay,
        window.eye_overlay,
    )


def _set_front_speech_expressions(window: CompanionWindow) -> None:
    window.speech_closed_expression = "idle_front"
    window.speech_mid_expression = "mouth_mid_front"
    window.speech_open_expression = "speaking_front"


def _assert_stale_crossfade_is_ignored(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window._set_expression("happy", fade=True)
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=False)
    QTest.qWait(230)
    app.processEvents()
    assert window.current_expression == "idle_front"
    assert window.character.pixmap().cacheKey() == (
        window.expression_pixmaps["idle_front"].cacheKey()
    )
    assert window.expression_overlay.isHidden()
    assert window.character_opacity.opacity() == 1.0


def _assert_large_pose_transition_race(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.idle_pose = "cheek"
    window._set_expression("idle", fade=False)
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=True)
    first_generation = window.pose_transition_generation
    first_animation = window.pose_transition_out
    assert first_animation.endValue() == 0.0
    window._set_expression("idle_front", fade=True)
    assert window.pose_transition_generation == first_generation
    assert window.pose_transition_out is first_animation

    window.idle_pose = "lean"
    window._set_expression("idle_lean", fade=True)
    latest_generation = window.pose_transition_generation
    assert latest_generation > first_generation
    assert window.pose_transition_expression == "idle_lean"
    window._pose_transition_midpoint("idle_front", "front", first_generation)
    assert window.current_expression == "idle"
    assert window.pose_transition_expression == "idle_lean"
    window.pose_transition_out.stop()
    window._pose_transition_midpoint("idle_lean", "lean", latest_generation)
    assert window.current_expression == "idle_lean"
    assert window.character_opacity.opacity() == 0.0
    window._finish_pose_transition("idle_front", first_generation)
    assert window.pose_transition_active
    assert window.pose_transition_expression == "idle_lean"
    QTest.qWait(140)
    app.processEvents()
    assert not window.pose_transition_active
    assert window.current_expression == "idle_lean"
    assert window.character_opacity.opacity() == 1.0


def _assert_speech_interrupts_pose_transition(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.idle_pose = "cheek"
    window._set_expression("idle", fade=False)
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=True)
    assert window.pose_transition_active
    QTest.qWait(25)
    window.state = "speaking"
    _set_front_speech_expressions(window)
    window._start_mouth_animation(audio_driven=True)
    for _ in range(5):
        window._audio_viseme_cue(0.65, "O")
    QTest.qWait(250)
    app.processEvents()
    assert not window.pose_transition_active
    assert window.current_expression == "mouth_o_front"
    assert window.character_opacity.opacity() == 1.0


def _assert_layered_gesture_motion(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.state = "idle"
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=False)
    window.gaze_x = 0.0
    window.gaze_y = 0.0
    positions = []
    assert window.set_state(
        "thinking_front",
        source="user_direct",
        force=True,
    )
    for _ in range(48):
        QTest.qWait(16)
        app.processEvents()
        body_position = window.character.pos()
        positions.append(body_position)
        for layer in _character_layers(window):
            assert layer.pos() == body_position
    assert max(
        abs(current.x() - previous.x())
        + abs(current.y() - previous.y())
        for previous, current in pairwise(positions)
    ) <= 3
    assert window.gesture_motion_x == 0.0
    assert window.gesture_motion_y == 0.0


def _assert_interrupted_gesture_alignment(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    assert window.set_state(
        "mock_scold",
        source="user_direct",
        force=True,
    )
    QTest.qWait(70)
    window.set_state("idle", force=True)
    for _ in range(16):
        QTest.qWait(16)
        app.processEvents()
        body_position = window.character.pos()
        assert all(
            layer.pos() == body_position
            for layer in _character_layers(window)
        )


def _assert_delayed_blink_is_ignored(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.state = "speaking"
    _set_front_speech_expressions(window)
    window._start_mouth_animation(audio_driven=True)
    window._blink()
    old_generation = window.blink_generation
    assert window.speech_blinking
    window._start_mouth_animation(audio_driven=True)
    assert window.blink_generation > old_generation
    for _ in range(5):
        window._audio_viseme_cue(0.70, "I")
    QTest.qWait(180)
    app.processEvents()
    assert window.current_expression == "mouth_i_front"
    assert not window.speech_blinking


def _assert_close_cancels_active_animations(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    window.idle_pose = "cheek"
    window._set_expression("idle", fade=False)
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=True)
    window.state = "speaking"
    window.audio_driven_mouth = True
    _set_front_speech_expressions(window)
    window._queue_audio_mouth_transition("speaking_front")
    window.close()
    QTest.qWait(260)
    app.processEvents()
    assert not window.pose_transition_active
    assert not window.mouth_visual_timer.isActive()


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        app, window = _create_test_window(temp_dir)

        # A stale cross-fade must not overwrite a newer immediate frame.
        _assert_stale_crossfade_is_ignored(app, window)
        # Coalescing and stale callbacks must preserve the newest large pose.
        _assert_large_pose_transition_race(app, window)
        # Speech may interrupt a large-pose transition without a late swap.
        _assert_speech_interrupts_pose_transition(app, window)
        # Every visual layer must follow emotional gesture motion as one unit.
        _assert_layered_gesture_motion(app, window)
        # Interrupting a gesture must not leave a late misalignment callback.
        _assert_interrupted_gesture_alignment(app, window)
        # A delayed blink callback from a prior utterance must be ignored.
        _assert_delayed_blink_is_ignored(app, window)
        # Closing with every animation family active must be harmless.
        _assert_close_cancels_active_animations(app, window)

    print("ANIMATION_RACE_AND_CLOSE_OK")


if __name__ == "__main__":
    run()
