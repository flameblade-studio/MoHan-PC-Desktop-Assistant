from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow


FEATURES = (
    "physics_sleeves",
    "physics_hair",
    "physics_ornament",
    "physics_eye_tracking",
    "physics_face_parallax",
)


def stop_automatic_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def wait_until(app: QApplication, predicate, timeout_ms: int = 500) -> bool:
    elapsed = 0
    while elapsed < timeout_ms:
        if predicate():
            return True
        QTest.qWait(10)
        app.processEvents()
        elapsed += 10
    return predicate()


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        stop_automatic_timers(window)

        assert all(window._physics_enabled(key) for key in FEATURES)
        assert window.safe_layer_rendering
        assert {
            "idle",
            "speaking",
            "mouth_mid",
            "mouth_wide",
            "mouth_round",
            "mouth_i",
            "mouth_o",
        }.issubset(window.expression_eye_sources)
        for suffix in ("", "_lean", "_front"):
            idle_eye = window.expression_eye_sources[
                f"idle{suffix}"
            ].toImage()
            for expression_prefix in (
                "speaking",
                "mouth_mid",
                "mouth_wide",
                "mouth_round",
                "mouth_i",
                "mouth_o",
            ):
                assert (
                    window.expression_eye_sources[
                        f"{expression_prefix}{suffix}"
                    ].toImage()
                    == idle_eye
                ), f"eye pixels changed in {expression_prefix}{suffix}"
        pose_expressions = (
            ("cheek", "idle", "speaking", "blink"),
            ("lean", "idle_lean", "speaking_lean", "blink_lean"),
            ("front", "idle_front", "speaking_front", "blink_front"),
        )
        for pose, idle, speaking, blink in pose_expressions:
            window.idle_pose = pose
            for expression in (idle, speaking, blink):
                window._set_expression(expression, fade=False)
                assert window.active_physics_pose == pose
                assert window.physics_overlay.isVisible()
                assert window.hair_left_overlay.isVisible()
                assert window.hair_right_overlay.isVisible()
                assert window.sleeve_left_overlay.isVisible()
                assert window.sleeve_right_overlay.isVisible()

            window.state = "idle"
            window._set_expression(idle, fade=False)
            window.gaze_x = 0.8
            window.gaze_y = -0.5
            window._render_attention_layers(force=True)
            window._attention_tick()
            assert window.face_overlay.isVisible()
            assert window.eye_overlay.isVisible()
            window.idle_blinking = True
            window._attention_tick()
            assert window.eye_overlay.isHidden()
            window.idle_blinking = False
            window.current_expression = idle

        window.idle_pose = "cheek"
        window.state = "speaking"
        eye_frame_keys = []
        for expression in (
            "idle",
            "mouth_mid",
            "speaking",
            "mouth_i",
            "mouth_o",
            "mouth_round",
        ):
            window._set_expression(expression, fade=False)
            window._render_attention_layers(force=True)
            eye_frame_keys.append(window.eye_overlay.pixmap().cacheKey())
            assert (
                window.attention_render_state[1]
                == window.current_expression
            )
        assert len(set(eye_frame_keys)) == len(eye_frame_keys)

        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_blinking = False
        window.current_viseme = "A"
        window.viseme_candidate = "A"
        window.viseme_candidate_frames = 0
        window.viseme_hold_frames = 0
        for _ in range(3):
            window._audio_viseme_cue(0.55, "O")
            assert window.current_viseme == "A"
        assert window.mouth_visual_timer.isActive()
        window._audio_viseme_cue(0.55, "O")
        assert window.current_viseme == "O"
        assert window.speech_current_expression == "mouth_o"
        assert 0.16 <= window.mouth_aperture_target < 1.0
        assert window.character.pixmap().cacheKey() != (
            window.expression_pixmaps["mouth_o"].cacheKey()
        )
        target_key = window.mouth_transition_to.cacheKey()
        QTest.qWait(130)
        app.processEvents()
        assert not window.mouth_visual_timer.isActive()
        assert window.character.pixmap().cacheKey() == target_key

        window.idle_pose = "front"
        window.state = "idle"
        window._set_expression("idle_front", fade=False)
        visibility = {
            "physics_sleeves": (
                window.sleeve_left_overlay,
                window.sleeve_right_overlay,
            ),
            "physics_hair": (
                window.hair_left_overlay,
                window.hair_right_overlay,
            ),
            "physics_ornament": (window.physics_overlay,),
            "physics_eye_tracking": (window.eye_overlay,),
            "physics_face_parallax": (window.face_overlay,),
        }
        for key in FEATURES:
            window.db.set_setting(key, False)
            window._reload_physics_settings()
            window._attention_tick()
            assert all(widget.isHidden() for widget in visibility[key])
            for other_key, widgets in visibility.items():
                if other_key != key:
                    assert any(widget.isVisible() for widget in widgets), (
                        key,
                        other_key,
                    )
            window.db.set_setting(key, True)
            window._reload_physics_settings()
            window._attention_tick()
            assert all(widget.isVisible() for widget in visibility[key])

        for _ in range(3600):
            window._physics_tick()
            assert math.isfinite(window.ornament_angle)
            assert math.isfinite(window.hair_left_angle)
            assert math.isfinite(window.hair_right_angle)
            assert math.isfinite(window.sleeve_left_angle)
            assert math.isfinite(window.sleeve_right_angle)
            assert abs(window.ornament_angle) <= 1.15
            assert abs(window.hair_left_angle) <= 0.34
            assert abs(window.hair_right_angle) <= 0.32
            assert abs(window.sleeve_left_angle) <= 0.16
            assert abs(window.sleeve_right_angle) <= 0.15

        window.current_expression = "speaking_front"
        window.mouth_open = True
        window.mouth_timer.start(500)
        window.state = "idle"
        window._idle_tick()
        assert window.current_expression == "idle_front"
        assert not window.mouth_open
        assert not window.mouth_timer.isActive()

        window._attention_tick()
        assert window.face_overlay.isVisible()
        window._set_expression("mock_scold", fade=True)
        assert window.physics_overlay.isVisible()
        assert window.hair_left_overlay.isVisible()
        assert window.sleeve_left_overlay.isVisible()
        assert window.face_overlay.isHidden()
        assert window.eye_overlay.isHidden()
        QTest.qWait(240)
        app.processEvents()
        assert window.current_expression == "mock_scold"
        window._attention_tick()
        assert window.face_overlay.isVisible()
        assert window.eye_overlay.isVisible()

        window.state = "idle"
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=False)
        window.idle_pose = "cheek"
        window._set_expression("idle", fade=True)
        assert window.pose_transition_active
        assert window.current_expression == "idle_front"
        assert window.expression_overlay.isHidden()
        assert window.physics_overlay.isHidden()
        assert window.face_overlay.isHidden()
        assert window.eye_overlay.isHidden()
        assert wait_until(
            app,
            lambda: window.current_expression == "idle",
        )
        assert window.current_expression == "idle"
        assert window.pose_transition_active
        assert window.expression_overlay.isHidden()
        assert window.physics_overlay.isHidden()
        assert wait_until(
            app,
            lambda: not window.pose_transition_active,
        )
        assert not window.pose_transition_active
        assert window.character_opacity.opacity() == 1.0
        assert window.physics_overlay.isVisible()
        assert window.hair_left_overlay.isVisible()
        assert window.sleeve_left_overlay.isVisible()

        window.close()
        app.processEvents()

        reopened = CompanionWindow(startup_speech=False)
        reopened.show()
        app.processEvents()
        stop_automatic_timers(reopened)
        assert all(reopened._physics_enabled(key) for key in FEATURES)
        assert all(
            reopened.dashboard.physics_controls[key].isChecked()
            for key in FEATURES
        )
        reopened.close()
        app.processEvents()
    print("FLAGSHIP_PHYSICS_OK")


if __name__ == "__main__":
    run()
