from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from db import StudioDB


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

        # A stale cross-fade must never overwrite a newer immediate frame.
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

        # Speech may interrupt a large-pose transition without a late swap.
        window.idle_pose = "cheek"
        window._set_expression("idle", fade=False)
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=True)
        assert window.pose_transition_active
        QTest.qWait(25)
        window.state = "speaking"
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window._start_mouth_animation(audio_driven=True)
        window._audio_viseme_cue(0.65, "O")
        window._audio_viseme_cue(0.65, "O")
        window._audio_viseme_cue(0.65, "O")
        QTest.qWait(250)
        app.processEvents()
        assert not window.pose_transition_active
        assert window.current_expression == "mouth_o_front"
        assert window.character_opacity.opacity() == 1.0

        # Emotional gestures must move the complete layered character as one
        # unit.  Moving only the body sprite creates a visible twitch/ghost.
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
            for layer in (
                window.expression_overlay,
                window.sleeve_left_overlay,
                window.sleeve_right_overlay,
                window.hair_left_overlay,
                window.hair_right_overlay,
                window.physics_overlay,
                window.face_overlay,
                window.eye_overlay,
            ):
                assert layer.pos() == body_position
        assert max(
            abs(current.x() - previous.x())
            + abs(current.y() - previous.y())
            for previous, current in zip(positions, positions[1:])
        ) <= 3
        assert window.gesture_motion_x == 0.0
        assert window.gesture_motion_y == 0.0

        # Interrupting a gesture or pose fade may not leave a late callback
        # that moves the body away from its overlays.
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
                for layer in (
                    window.expression_overlay,
                    window.sleeve_left_overlay,
                    window.sleeve_right_overlay,
                    window.hair_left_overlay,
                    window.hair_right_overlay,
                    window.physics_overlay,
                    window.face_overlay,
                    window.eye_overlay,
                )
            )

        # A delayed blink callback from a prior utterance must be ignored.
        window.state = "speaking"
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window._start_mouth_animation(audio_driven=True)
        window._blink()
        old_generation = window.blink_generation
        assert window.speech_blinking
        window._start_mouth_animation(audio_driven=True)
        assert window.blink_generation > old_generation
        window._audio_viseme_cue(0.70, "I")
        window._audio_viseme_cue(0.70, "I")
        window._audio_viseme_cue(0.70, "I")
        QTest.qWait(180)
        app.processEvents()
        assert window.current_expression == "mouth_i_front"
        assert not window.speech_blinking

        # Closing while every animation family is active must be harmless.
        window.idle_pose = "cheek"
        window._set_expression("idle", fade=False)
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=True)
        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window._queue_audio_mouth_transition("speaking_front")
        window.close()
        QTest.qWait(260)
        app.processEvents()
        assert not window.pose_transition_active
        assert not window.mouth_visual_timer.isActive()

    print("ANIMATION_RACE_AND_CLOSE_OK")


if __name__ == "__main__":
    run()
