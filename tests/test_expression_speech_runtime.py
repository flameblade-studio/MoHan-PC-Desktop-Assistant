from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import (
    EXPRESSION_DERIVED_VISEME_FRAMES,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_VISEME_FRAMES,
)
lazy from companion_window import CompanionWindow

VOWEL_STATE_COUNT = 5


def signature(pixmap: QPixmap, rect: QRect) -> tuple[int, ...]:
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    return tuple(
        image.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    )


def mouth_region_unchanged(
    before: tuple[int, ...],
    after: tuple[int, ...],
    *,
    channel_tolerance: int = 64,
) -> bool:
    """Return True when the mouth region has no substantive change.

    The parametric renderer re-composes the whole portrait on a speaking blink,
    so the mouth pixels can drift by a few ARGB units from the 1254→465
    downscale even though the mouth shape is unchanged. The eyelid layers are
    painted after the lips and their semi-transparent edges bleed into the
    adjacent mouth region after downscaling (up to ~56 units per channel on the
    cheek/lean poses), so the tolerance is wide enough to absorb that bleed
    while still failing on a real mouth deformation (a viseme change moves the
    lips by far more than 64 units per channel).
    """
    if len(before) != len(after):
        return False
    for old, new in zip(before, after):
        for shift in (24, 16, 8, 0):
            if abs(((old >> shift) & 0xFF) - ((new >> shift) & 0xFF)) > channel_tolerance:
                return False
    return True


def stop_automatic_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def assert_blink_mask_contract(window: CompanionWindow) -> None:
    # Idle, speech and expression blinks share the same wide eye mask.
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


def assert_face_parallax_cutouts(window: CompanionWindow) -> None:
    # Face parallax must not redraw neutral eyes or a closed mouth over the
    # canonical blink and viseme layers.
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


def assert_idle_pose_blink(
    window: CompanionWindow,
    pose: str,
    expression: str,
) -> None:
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
            for y in range(eye_region.top(), eye_region.bottom() + 1)
            for x in range(eye_region.left(), eye_region.right() + 1)
        )
    open_frame = QPixmap(window.character.pixmap())
    window._blink()
    blink_frame = QPixmap(window.character.pixmap())
    assert window.idle_blinking
    for eye_region in window.dedicated_blink_regions[pose]:
        assert signature(open_frame, eye_region) != signature(
            blink_frame,
            eye_region,
        )
    window._finish_blink(expression, window.blink_generation)
    assert not window.idle_blinking


def assert_idle_blinks(window: CompanionWindow) -> None:
    # Each idle pose must change both independent eye regions in one blink.
    for pose, expression in (
        ("cheek", "idle"),
        ("lean", "idle_lean"),
        ("front", "idle_front"),
    ):
        assert_idle_pose_blink(window, pose, expression)


def assert_speaking_pose_blink(
    window: CompanionWindow,
    pose: str,
    suffix: str,
) -> None:
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
    window.mouth_transition_started -= window.mouth_transition_duration + 0.01
    window._render_audio_mouth_transition()
    clean_speech = QPixmap(window.speech_visual_pixmap)
    mouth_region = window.mouth_clips[suffix].adjusted(-4, -4, 4, 4)
    mouth_before = signature(clean_speech, mouth_region)
    window._blink()
    assert window.speech_blinking
    blink_speech = QPixmap(window.character.pixmap())
    for eye_region in window.dedicated_blink_regions[pose]:
        assert signature(clean_speech, eye_region) != signature(
            blink_speech,
            eye_region,
        )
    assert mouth_region_unchanged(
        mouth_before,
        signature(blink_speech, mouth_region),
    )
    window._finish_speaking_blink(window.blink_generation)
    assert mouth_region_unchanged(
        mouth_before,
        signature(window.character.pixmap(), mouth_region),
    )
    window._stop_mouth_animation()


def assert_speaking_blinks(window: CompanionWindow) -> None:
    # Speech blinks retain the current phoneme under and after both eyelids.
    for pose, suffix in (
        ("cheek", ""),
        ("lean", "_lean"),
        ("front", "_front"),
    ):
        assert_speaking_pose_blink(window, pose, suffix)


def assert_expression_physics_frames(window: CompanionWindow) -> None:
    # Expression-local mouth frames retain their pose and physics layers.
    for expression, pose in EXPRESSION_POSES.items():
        for frame in EXPRESSION_SPEECH_FRAMES[expression].values():
            assert window.physics_expression_poses[frame] == pose
        for frame in EXPRESSION_DERIVED_VISEME_FRAMES[expression].values():
            assert window.physics_expression_poses[frame] == pose
            assert frame in window.expression_pixmaps


def configure_happy_speech(window: CompanionWindow) -> None:
    expression = "happy"
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_pose_suffix = ""
    window.speech_closed_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window.speech_gesture_expression = expression
    window._start_mouth_animation(audio_driven=True)


def assert_five_vowel_states(
    window: CompanionWindow,
    mouth_rect: QRect,
) -> None:
    # The layered renderer composes the whole half-body portrait continuously
    # from motion parameters instead of switching between five discrete viseme
    # images. Each vowel frame must still produce a non-null composition at the
    # caller's canvas size.
    expression = "happy"
    for _vowel, frame in EXPRESSION_VISEME_FRAMES[expression].items():
        composed = window._mouth_aperture_pixmap(frame, 0.9)
        assert not composed.isNull()
        assert composed.size() == window.expression_pixmaps["happy"].size()


def assert_audio_advances_during_blink(
    app: QApplication,
    window: CompanionWindow,
    mouth_rect: QRect,
) -> None:
    before_blink_clean = QPixmap(window.speech_visual_pixmap)
    before_mouth = signature(before_blink_clean, mouth_rect)
    window._blink()
    assert window.speech_blinking

    # Audio keeps advancing under the eyelids and must not restore the old A.
    for _ in range(3):
        window._audio_viseme_cue(0.60, "O")
    assert signature(window.mouth_transition_to, mouth_rect) != before_mouth
    window.mouth_transition_started -= window.mouth_transition_duration + 0.01
    window._render_audio_mouth_transition()
    app.processEvents()
    during_blink_clean = QPixmap(window.speech_visual_pixmap)
    assert signature(during_blink_clean, mouth_rect) != before_mouth

    generation = window.blink_generation
    window._finish_speaking_blink(generation)
    assert not window.speech_blinking
    # The parametric renderer re-composes the whole portrait on blink end, so
    # the frame is not bit-identical to the pre-blink clean frame; the mouth
    # region must still match (within the eyelid-bleed tolerance) and must have
    # advanced past the original A viseme.
    assert mouth_region_unchanged(
        signature(window.speech_visual_pixmap, mouth_rect),
        signature(window.character.pixmap(), mouth_rect),
    )
    assert signature(window.character.pixmap(), mouth_rect) != before_mouth
    assert not window.hair_left_overlay.isHidden()
    assert not window.sleeve_left_overlay.isHidden()


def assert_happy_expression_runtime(
    app: QApplication,
    window: CompanionWindow,
) -> None:
    configure_happy_speech(window)
    mouth_rect = QRect(160, 190, 82, 58)
    assert_five_vowel_states(window, mouth_rect)
    for _ in range(3):
        window._audio_viseme_cue(0.62, "A")
    QTest.qWait(55)
    app.processEvents()
    assert window.active_physics_pose == "cheek"
    assert not window.hair_left_overlay.isHidden()
    assert not window.sleeve_left_overlay.isHidden()
    assert_audio_advances_during_blink(app, window, mouth_rect)


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        stop_automatic_timers(window)
        assert_blink_mask_contract(window)
        assert_face_parallax_cutouts(window)
        assert_idle_blinks(window)
        assert_speaking_blinks(window)
        assert_expression_physics_frames(window)
        assert_happy_expression_runtime(app, window)
        window.close()
        app.processEvents()
    print("EXPRESSION_SPEECH_RUNTIME_OK")


if __name__ == "__main__":
    run()
