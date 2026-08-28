from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import EXPRESSION_SPEECH_EXPRESSIONS
lazy from presentation.companion_window import CompanionWindow
lazy from domain.face_rig import FacePose, Viseme

SMILE_THRESHOLD = 0.5
BLUSH_THRESHOLD = 0.8


def configure(window: CompanionWindow, expression: str) -> None:
    window.state = "speaking"
    window.audio_driven_mouth = True
    window._configure_speech_frames(expression)
    window.face_motion_controller.reset(
        window.physics_expression_poses.get(expression, window.idle_pose),
        expression,
    )
    window.face_motion_frame = window.face_motion_controller.current


def assert_three_pose_articulation(window: CompanionWindow) -> None:
    expressions = {
        FacePose.CHEEK: "idle",
        FacePose.LEAN: "idle_lean",
        FacePose.FRONT: "idle_front",
    }
    for pose, expression in expressions.items():
        window.idle_pose = pose.value
        configure(window, expression)
        closed = window.expression_pixmaps[window.speech_closed_expression]
        closed_corner = closed.toImage().pixelColor(5, 5)
        for vowel in ("A", "I", "U", "E", "O", "CONSONANT"):
            for _ in range(3):
                window._audio_viseme_cue(0.72, vowel)
            window.mouth_transition_started -= (
                window.mouth_transition_duration + 0.001
            )
            window._render_audio_mouth_transition()
            assert window.face_motion_frame.pose is pose
            assert window.face_motion_frame.viseme in {
                Viseme.A,
                Viseme.I,
                Viseme.U,
                Viseme.E,
                Viseme.O,
                Viseme.CONSONANT,
            }
            rendered = window.speech_visual_pixmap
            assert not rendered.isNull()
            assert rendered.toImage().pixelColor(5, 5) == closed_corner
        window._stop_mouth_animation()
        assert window.face_motion_frame.viseme is Viseme.CLOSED


def assert_all_expression_layers(window: CompanionWindow) -> None:
    for expression in sorted(EXPRESSION_SPEECH_EXPRESSIONS):
        configure(window, expression)
        for vowel in ("A", "I", "U", "E", "O"):
            for _ in range(3):
                window._audio_viseme_cue(0.68, vowel)
            window.mouth_transition_started -= (
                window.mouth_transition_duration + 0.001
            )
            window._render_audio_mouth_transition()
            assert not window.speech_visual_pixmap.isNull(), expression
        if expression == "happy":
            assert window.face_motion_frame.expression_shape.eye_smile > SMILE_THRESHOLD
            assert window.face_motion_frame.mouth.corner_smile == 0.0
        if expression in {"shy_front", "shy_cute_front"}:
            assert window.face_motion_frame.expression_shape.blush > BLUSH_THRESHOLD
        window._stop_mouth_animation()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication.instance() or QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()
        assert_three_pose_articulation(window)
        assert_all_expression_layers(window)
        window.close()
        window.db.close()
        app.processEvents()
    print("PARAMETRIC_FACE_RUNTIME_OK")


if __name__ == "__main__":
    run()
