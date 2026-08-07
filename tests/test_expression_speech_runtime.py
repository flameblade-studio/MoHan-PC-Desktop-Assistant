from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import (
    CompanionWindow,
    EXPRESSION_DERIVED_VISEME_FRAMES,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_VISEME_FRAMES,
)


def signature(pixmap: QPixmap, rect: QRect) -> tuple[int, ...]:
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    return tuple(
        image.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    )


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        # Idle, speech and expression blinks must share the same wide eye
        # replacement mask.  A second, narrower idle mask once left the
        # cheek-rest portrait's upper eyeliner visible over a closed eyelid.
        assert window.dedicated_blink_masks is window.blink_masks
        assert window.dedicated_blink_regions == {
            "cheek": (
                QRect(160, 153, 55, 34),
                QRect(198, 153, 61, 34),
            ),
            "lean": (
                QRect(153, 153, 55, 34),
                QRect(191, 153, 61, 34),
            ),
            "front": (
                QRect(180, 153, 53, 34),
                QRect(220, 153, 56, 34),
            ),
        }

        # Face parallax must never redraw neutral open eyes or a closed mouth
        # over the canonical blink/viseme layers.
        for pose, regions in window.face_parallax_cutouts.items():
            face = window.face_sources[pose].toImage().convertToFormat(
                QImage.Format_ARGB32
            )
            for region in regions:
                clear_core = region.adjusted(5, 5, -5, -5)
                assert all(
                    face.pixelColor(x, y).alpha() == 0
                    for y in range(clear_core.top(), clear_core.bottom() + 1)
                    for x in range(clear_core.left(), clear_core.right() + 1)
                )

        # Each idle pose must change both independent eye regions during one
        # blink. This prevents a visually plausible but one-eyed regression.
        for pose, expression in (
            ("cheek", "idle"),
            ("lean", "idle_lean"),
            ("front", "idle_front"),
        ):
            window.state = "idle"
            window.idle_pose = pose
            window.idle_blinking = False
            window._set_expression(expression, fade=False)
            window._render_attention_layers(force=True)
            tracking_overlay = (
                window.eye_overlay.pixmap()
                .toImage()
                .convertToFormat(QImage.Format_ARGB32)
            )
            for eye_region in window.dedicated_blink_regions[pose]:
                assert all(
                    tracking_overlay.pixelColor(x, y).alpha() == 0
                    for y in range(
                        eye_region.top(),
                        eye_region.bottom() + 1,
                    )
                    for x in range(
                        eye_region.left(),
                        eye_region.right() + 1,
                    )
                )
            open_frame = QPixmap(window.character.pixmap())
            window._blink()
            blink_frame = QPixmap(window.character.pixmap())
            assert window.idle_blinking
            for eye_region in window.dedicated_blink_regions[pose]:
                assert (
                    signature(open_frame, eye_region)
                    != signature(blink_frame, eye_region)
                )
            window._finish_blink(expression, window.blink_generation)
            assert not window.idle_blinking

        # Speaking blinks use the same bilateral eyelid ownership while the
        # mouth keeps its current phoneme underneath and after the blink.
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            window.state = "speaking"
            window.idle_pose = pose
            window.speech_pose_suffix = suffix
            window.speech_closed_expression = f"idle{suffix}"
            window.speech_mid_expression = f"mouth_mid{suffix}"
            window.speech_open_expression = f"speaking{suffix}"
            window.speech_gesture_expression = None
            window._start_mouth_animation(audio_driven=True)
            for _ in range(2):
                window._audio_viseme_cue(0.62, "A")
            window.mouth_transition_started -= (
                window.mouth_transition_duration + 0.01
            )
            window._render_audio_mouth_transition()
            clean_speech = QPixmap(window.speech_visual_pixmap)
            mouth_region = window.mouth_clips[suffix].adjusted(-4, -4, 4, 4)
            mouth_before = signature(clean_speech, mouth_region)
            window._blink()
            assert window.speech_blinking
            blink_speech = QPixmap(window.character.pixmap())
            for eye_region in window.dedicated_blink_regions[pose]:
                assert (
                    signature(clean_speech, eye_region)
                    != signature(blink_speech, eye_region)
                )
            assert signature(blink_speech, mouth_region) == mouth_before
            window._finish_speaking_blink(
                window.speech_current_expression,
                window.blink_generation,
            )
            assert signature(window.character.pixmap(), mouth_region) == mouth_before
            window._stop_mouth_animation()

        # Every expression-local mouth frame must retain the same pose and
        # therefore keep all flagship physics layers alive while talking.
        for expression, pose in EXPRESSION_POSES.items():
            for frame in EXPRESSION_SPEECH_FRAMES[expression].values():
                assert window.physics_expression_poses[frame] == pose
            for frame in (
                EXPRESSION_DERIVED_VISEME_FRAMES[expression].values()
            ):
                assert window.physics_expression_poses[frame] == pose
                assert frame in window.expression_pixmaps

        expression = "happy"
        frames = EXPRESSION_SPEECH_FRAMES[expression]
        window.state = "speaking"
        window.speech_pose_suffix = ""
        window.speech_closed_expression = expression
        window.speech_mid_expression = frames["mid"]
        window.speech_open_expression = frames["open"]
        window.speech_gesture_expression = expression
        window._start_mouth_animation(audio_driven=True)

        # The expression-local runtime is genuinely five-state: none of the
        # A/I/U/E/O visual mouth regions may collapse to the same pixels.
        mouth_rect = QRect(160, 190, 82, 58)
        vowel_signatures = {
            vowel: signature(
                window._mouth_aperture_pixmap(frame, 0.9),
                mouth_rect,
            )
            for vowel, frame in EXPRESSION_VISEME_FRAMES[
                expression
            ].items()
        }
        assert len(set(vowel_signatures.values())) == 5

        for _ in range(3):
            window._audio_viseme_cue(0.62, "A")
        QTest.qWait(55)
        app.processEvents()
        assert window.active_physics_pose == "cheek"
        assert not window.hair_left_overlay.isHidden()
        assert not window.sleeve_left_overlay.isHidden()

        eye_rect = QRect(154, 147, 112, 48)
        before_blink_clean = QPixmap(window.speech_visual_pixmap)
        before_mouth = signature(before_blink_clean, mouth_rect)

        window._blink()
        assert window.speech_blinking
        assert (
            signature(window.character.pixmap(), eye_rect)
            != signature(window.speech_visual_pixmap, eye_rect)
        )

        # Audio continues advancing underneath the eyelids. It must not be
        # discarded and the blink must not restore the old A viseme.
        for _ in range(3):
            window._audio_viseme_cue(0.60, "O")
        assert (
            signature(window.mouth_transition_to, mouth_rect)
            != before_mouth
        )
        window.mouth_transition_started -= (
            window.mouth_transition_duration + 0.01
        )
        window._render_audio_mouth_transition()
        app.processEvents()
        during_blink_clean = QPixmap(window.speech_visual_pixmap)
        assert signature(during_blink_clean, mouth_rect) != before_mouth
        assert (
            signature(window.character.pixmap(), eye_rect)
            != signature(during_blink_clean, eye_rect)
        )

        generation = window.blink_generation
        window._finish_speaking_blink(
            window.speech_current_expression,
            generation,
        )
        assert not window.speech_blinking
        assert (
            signature(window.character.pixmap(), QRect(0, 0, 464, 464))
            == signature(window.speech_visual_pixmap, QRect(0, 0, 464, 464))
        )
        assert signature(window.character.pixmap(), mouth_rect) != before_mouth
        assert not window.hair_left_overlay.isHidden()
        assert not window.sleeve_left_overlay.isHidden()

        window.close()
        app.processEvents()
    print("EXPRESSION_SPEECH_RUNTIME_OK")


if __name__ == "__main__":
    run()
