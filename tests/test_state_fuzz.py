from __future__ import annotations

lazy import math
lazy import os
lazy import random
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB

ORNAMENT_ANGLE_LIMIT = 1.15
HAIR_LEFT_ANGLE_LIMIT = 0.34
HAIR_RIGHT_ANGLE_LIMIT = 0.32
SLEEVE_LEFT_ANGLE_LIMIT = 0.16
SLEEVE_RIGHT_ANGLE_LIMIT = 0.15
POSE_OPERATION_MAX = 2
IDLE_OPERATION = 3
SPEAKING_OPERATION = 4
PHYSICS_OPERATION = 5
FEATURES = (
    "physics_sleeves",
    "physics_hair",
    "physics_ornament",
    "physics_eye_tracking",
    "physics_face_parallax",
)
POSES = {
    "cheek": (
        "idle",
        "speaking",
        "mouth_mid",
        "mouth_wide",
        "mouth_round",
        "mouth_i",
        "mouth_o",
        "blink",
    ),
    "lean": (
        "idle_lean",
        "speaking_lean",
        "mouth_mid_lean",
        "mouth_wide_lean",
        "mouth_round_lean",
        "mouth_i_lean",
        "mouth_o_lean",
        "blink_lean",
    ),
    "front": (
        "idle_front",
        "speaking_front",
        "mouth_mid_front",
        "mouth_wide_front",
        "mouth_round_front",
        "mouth_i_front",
        "mouth_o_front",
        "blink_front",
    ),
}
SPECIAL = (
    "mock_scold",
    "shy_front",
    "thinking_front",
    "worried_front",
    "happy",
)


def stop_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def assert_motion_bounds(window: CompanionWindow) -> None:
    values = (
        window.ornament_angle,
        window.hair_left_angle,
        window.hair_right_angle,
        window.sleeve_left_angle,
        window.sleeve_right_angle,
    )
    assert all(math.isfinite(value) for value in values)
    assert abs(window.ornament_angle) <= ORNAMENT_ANGLE_LIMIT
    assert abs(window.hair_left_angle) <= HAIR_LEFT_ANGLE_LIMIT
    assert abs(window.hair_right_angle) <= HAIR_RIGHT_ANGLE_LIMIT
    assert abs(window.sleeve_left_angle) <= SLEEVE_LEFT_ANGLE_LIMIT
    assert abs(window.sleeve_right_angle) <= SLEEVE_RIGHT_ANGLE_LIMIT


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
    stop_timers(window)
    return app, window


def _apply_random_operation(window: CompanionWindow) -> None:
    operation = random.randrange(7)
    if operation <= POSE_OPERATION_MAX:
        pose = random.choice(tuple(POSES))
        window.idle_pose = pose
        expression = random.choice(POSES[pose])
        window.state = (
            "speaking"
            if "speaking" in expression or "mouth_" in expression
            else "idle"
        )
        window._set_expression(expression, fade=False)
    elif operation == IDLE_OPERATION:
        window.state = "idle"
        window._set_expression(random.choice(SPECIAL), fade=False)
    elif operation == SPEAKING_OPERATION:
        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_blinking = False
        window._audio_viseme_cue(
            random.random(),
            random.choice(("A", "I", "U", "E", "O", "CLOSED")),
        )
    elif operation == PHYSICS_OPERATION:
        feature = random.choice(FEATURES)
        window.physics_features[feature] = not window.physics_features[feature]
        window._apply_physics_visibility()
    else:
        window.gaze_target_x = random.uniform(-1.0, 1.0)
        window.gaze_target_y = random.uniform(-1.0, 1.0)
        window._attention_tick()


def _assert_render_state(window: CompanionWindow) -> None:
    window._physics_tick()
    assert_motion_bounds(window)
    assert 0.0 <= window.character_opacity.opacity() <= 1.0
    if window.current_expression not in window.physics_expression_poses:
        assert window.physics_overlay.isHidden()
        assert window.hair_left_overlay.isHidden()
        assert window.sleeve_left_overlay.isHidden()


def _run_fuzz_sequence(app: QApplication, window: CompanionWindow) -> None:
    for index in range(2400):
        _apply_random_operation(window)
        _assert_render_state(window)
        if index % 200 == 0:
            app.processEvents()


def _assert_idle_reset(window: CompanionWindow) -> None:
    window.physics_features.update(dict.fromkeys(FEATURES, True))
    window.state = "idle"
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=False)
    window._ensure_idle_mouth_closed()
    assert window.current_expression == "idle_front"
    assert not window.mouth_open


def _assert_reopen_lifecycle(app: QApplication) -> None:
    for _ in range(8):
        reopened = CompanionWindow(startup_speech=False)
        reopened.show()
        app.processEvents()
        stop_timers(reopened)
        assert reopened.character.pixmap() is not None
        reopened.close()
        app.processEvents()


def run() -> None:
    random.seed(20260729)
    with TemporaryDirectory() as temp_dir:
        app, window = _create_window(temp_dir)
        _run_fuzz_sequence(app, window)
        _assert_idle_reset(window)
        window.close()
        app.processEvents()
        _assert_reopen_lifecycle(app)
    print("STATE_FUZZ_AND_LIFECYCLE_OK")


if __name__ == "__main__":
    run()
