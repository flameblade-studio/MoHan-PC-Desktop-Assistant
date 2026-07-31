from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from db import StudioDB


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
    assert abs(window.ornament_angle) <= 1.15
    assert abs(window.hair_left_angle) <= 0.34
    assert abs(window.hair_right_angle) <= 0.32
    assert abs(window.sleeve_left_angle) <= 0.16
    assert abs(window.sleeve_right_angle) <= 0.15


def run() -> None:
    random.seed(20260729)
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
        stop_timers(window)

        for index in range(2400):
            operation = random.randrange(7)
            if operation <= 2:
                pose = random.choice(tuple(POSES))
                window.idle_pose = pose
                expression = random.choice(POSES[pose])
                window.state = (
                    "speaking"
                    if "speaking" in expression
                    or "mouth_" in expression
                    else "idle"
                )
                window._set_expression(expression, fade=False)
            elif operation == 3:
                window.state = "idle"
                window._set_expression(random.choice(SPECIAL), fade=False)
            elif operation == 4:
                window.state = "speaking"
                window.audio_driven_mouth = True
                window.speech_blinking = False
                window._audio_viseme_cue(
                    random.random(),
                    random.choice(("A", "I", "U", "E", "O", "CLOSED")),
                )
            elif operation == 5:
                feature = random.choice(FEATURES)
                window.physics_features[feature] = not window.physics_features[
                    feature
                ]
                window._apply_physics_visibility()
            else:
                window.gaze_target_x = random.uniform(-1.0, 1.0)
                window.gaze_target_y = random.uniform(-1.0, 1.0)
                window._attention_tick()
            window._physics_tick()
            assert_motion_bounds(window)
            assert window.character_opacity.opacity() >= 0.0
            assert window.character_opacity.opacity() <= 1.0
            if window.current_expression not in window.physics_expression_poses:
                assert window.physics_overlay.isHidden()
                assert window.hair_left_overlay.isHidden()
                assert window.sleeve_left_overlay.isHidden()
            if index % 200 == 0:
                app.processEvents()

        window.physics_features.update({key: True for key in FEATURES})
        window.state = "idle"
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=False)
        window._ensure_idle_mouth_closed()
        assert window.current_expression == "idle_front"
        assert not window.mouth_open
        window.close()
        app.processEvents()

        for _ in range(8):
            reopened = CompanionWindow(startup_speech=False)
            reopened.show()
            app.processEvents()
            stop_timers(reopened)
            assert reopened.character.pixmap() is not None
            reopened.close()
            app.processEvents()
    print("STATE_FUZZ_AND_LIFECYCLE_OK")


if __name__ == "__main__":
    run()
