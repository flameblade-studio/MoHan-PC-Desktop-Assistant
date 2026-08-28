"""Audio-driven viseme cue application, extracted from the face-animation mixin.

The 1200-line layered-module gate forced ``companion_face_animation`` to shed
its audio-viseme block after the golden-batch and UI audit waves both grew the
file; the logic is unchanged and the mixin keeps thin forwarding methods.
"""

from __future__ import annotations

lazy from domain.companion_animation_contract import (
    EXPRESSION_VISEME_FRAMES, NEUTRAL_VISEME_ASSET_STEMS,
)
lazy from domain.lip_sync import VisemeFrame

__all__ = ("apply_audio_viseme_cue", "viseme_expression")


def viseme_expression(window, viseme: str) -> str:
    if viseme == "CLOSED":
        expression = window.speech_closed_expression
    elif viseme == "CONSONANT":
        expression = window.speech_mid_expression
    elif window.speech_gesture_expression is not None:
        expression = EXPRESSION_VISEME_FRAMES[window.speech_gesture_expression].get(
            viseme, window.speech_mid_expression
        )
    else:
        stem = NEUTRAL_VISEME_ASSET_STEMS.get(viseme)
        expression = (
            window.speech_mid_expression
            if stem is None
            else f"{stem}{window._active_speech_pose_suffix()}"
        )
    return expression


def apply_audio_viseme_cue(window, level: float, vowel: str) -> None:
    if (
        window.state != "speaking"
        or not window.audio_driven_mouth
        or getattr(window, "mouth_closing", False)
        or getattr(window, "viseme_dynamics", None) is None
    ):
        return
    # A live viseme owns the full photographed face. Remove any gaze
    # overlay left by the preceding idle frame before drawing the mouth.
    window.eye_overlay.hide()
    frame: VisemeFrame = window.viseme_dynamics.advance(level, vowel)
    expression = viseme_expression(window, frame.selected)
    motion_expression = (
        window.speech_gesture_expression or window.speech_closed_expression
    )
    motion_pose = window.physics_expression_poses.get(
        motion_expression,
        getattr(window, "idle_pose", "front"),
    )
    window.face_motion_frame = window.face_motion_controller.advance(
        frame,
        pose=motion_pose,
        expression=motion_expression,
        blink=1.0 if window.speech_blinking else 0.0,
    )
    # The adaptive full-body renderer is driven by the provider-neutral
    # speech-performance bridge, not by the legacy half-body pixmap path.
    # Publish every accepted audio cue before the ownership guard below;
    # otherwise full-body speech keeps the canvas but never receives a
    # changing viseme, which presents as "text only, mouth not moving".
    window._record_speech_performance(
        window.speech_performance.viseme(level, frame.selected)
    )
    if getattr(window, "_adaptive_full_body_active", False):
        # The v4 full-body composition renders its own speech mouth from
        # the continuous ``face_motion_frame`` produced above.  The legacy
        # half-body mouth patch and head-motion path must not run in
        # parallel: it would reset the ownership flag and let the
        # suppressed half-body overlays return, stacking a second body over
        # the full-body frame (the reported double image).
        return
    window.mouth_frame_index = frame.frame_index
    window.mouth_open = frame.mouth_open
    window.speech_current_expression = expression
    if frame.selected != frame.previous or window.mouth_transition_to.isNull():
        window._queue_audio_mouth_transition(
            expression,
            frame.jaw_aperture,
        )
    target_motion = min(
        4.0,
        window.viseme_dynamics.smoothed_level * 3.0 + frame.jaw_weight,
    )
    window.head_motion_y = window.head_motion_y * 0.62 + target_motion * 0.38
    window.speech_motion_target_y = -window.head_motion_y
    window._motion_tick()
