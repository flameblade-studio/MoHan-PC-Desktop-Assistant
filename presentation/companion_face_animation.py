from __future__ import annotations

lazy import math
lazy import random
lazy import time

lazy from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QTimer,
    QVariantAnimation,
)
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from domain.companion_animation_contract import (
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    EXPRESSION_SPEECH_MOUTH_RECTS,
    EXPRESSION_VISEME_FRAMES,
    NEUTRAL_VISEME_ASSET_STEMS,
    NEW_EXPRESSION_ASSETS,
)
lazy from domain.lip_sync import (
    VISEME_CHANGE_TRANSITION_SECONDS,
    VISEME_CLOSE_TRANSITION_SECONDS,
    VISEME_OPEN_TRANSITION_SECONDS,
    VisemeFrame,
)
lazy from presentation.companion_face_assets import CompanionFaceAssetMethods
lazy from presentation.presentation_resources import FaceRenderLayers

__all__ = ("CompanionFaceAnimationMixin",)


class CompanionFaceAnimationMixin:
    _idle_expression = CompanionFaceAssetMethods._idle_expression
    _speaking_expression = CompanionFaceAssetMethods._speaking_expression
    _mouth_mid_expression = CompanionFaceAssetMethods._mouth_mid_expression
    _closed_speech_expression = CompanionFaceAssetMethods._closed_speech_expression
    _build_mouth_frames = CompanionFaceAssetMethods._build_mouth_frames
    _mouth_clip_regions = staticmethod(CompanionFaceAssetMethods._mouth_clip_regions)
    _soft_rounded_mask = staticmethod(CompanionFaceAssetMethods._soft_rounded_mask)
    _build_speech_mouth_masks = CompanionFaceAssetMethods._build_speech_mouth_masks
    _build_cheek_neutral_speech_frame = (
        CompanionFaceAssetMethods._build_cheek_neutral_speech_frame
    )
    _build_gesture_mouth_masks = CompanionFaceAssetMethods._build_gesture_mouth_masks
    _build_derived_expression_visemes = (
        CompanionFaceAssetMethods._build_derived_expression_visemes
    )
    _blink_regions = staticmethod(CompanionFaceAssetMethods._blink_regions)
    _build_blink_masks = CompanionFaceAssetMethods._build_blink_masks
    _build_face_parallax_cutouts = (
        CompanionFaceAssetMethods._build_face_parallax_cutouts
    )
    _normalize_base_speech_frames = (
        CompanionFaceAssetMethods._normalize_base_speech_frames
    )
    _compose_mouth_only = CompanionFaceAssetMethods._compose_mouth_only
    _build_pose_viseme_frames = CompanionFaceAssetMethods._build_pose_viseme_frames
    _build_happy_neutral_speech_frames = (
        CompanionFaceAssetMethods._build_happy_neutral_speech_frames
    )
    _build_blink_viseme_frames = CompanionFaceAssetMethods._build_blink_viseme_frames
    _masked_mouth_patch = CompanionFaceAssetMethods._masked_mouth_patch
    _build_expression_anchor_profiles = (
        CompanionFaceAssetMethods._build_expression_anchor_profiles
    )
    _estimate_face_offset = staticmethod(
        CompanionFaceAssetMethods._estimate_face_offset
    )
    _face_offset_candidate_score = staticmethod(
        CompanionFaceAssetMethods._face_offset_candidate_score
    )
    _opaque_pixel_difference = staticmethod(
        CompanionFaceAssetMethods._opaque_pixel_difference
    )
    _expression_face_offset = CompanionFaceAssetMethods._expression_face_offset
    _expression_eye_offset = CompanionFaceAssetMethods._expression_eye_offset
    _expression_mouth_offset = CompanionFaceAssetMethods._expression_mouth_offset
    _translated_pixmap = staticmethod(CompanionFaceAssetMethods._translated_pixmap)
    _build_expression_eye_layers = (
        CompanionFaceAssetMethods._build_expression_eye_layers
    )
    _masked_region = staticmethod(CompanionFaceAssetMethods._masked_region)
    _render_base_expression = CompanionFaceAssetMethods._render_base_expression
    _local_physics_source = CompanionFaceAssetMethods._local_physics_source
    _blink_expression = CompanionFaceAssetMethods._blink_expression
    _speaking_blink_expression = CompanionFaceAssetMethods._speaking_blink_expression
    _pose_suffix = staticmethod(CompanionFaceAssetMethods._pose_suffix)
    _blink_composite = CompanionFaceAssetMethods._blink_composite
    _wink_composite = CompanionFaceAssetMethods._wink_composite
    _masked_eye_patch = CompanionFaceAssetMethods._masked_eye_patch
    _active_speech_pose_suffix = CompanionFaceAssetMethods._active_speech_pose_suffix

    def _schedule_pose_change(self) -> None:
        delay = (
            random.randint(5_000, 9_000)
            if self.idle_pose == "front"
            else random.randint(16_000, 29_000)
        )
        self.pose_timer.start(delay)

    def _rotate_idle_pose(self) -> None:
        if self.state == "idle":
            if self.idle_pose == "cheek":
                self.idle_pose = random.choice(["lean", "front"])
            elif self.idle_pose == "lean" and random.random() < 0.55:
                self.idle_pose = "front"
            else:
                self.idle_pose = "cheek"
            self._set_expression(self._idle_expression())
        self._schedule_pose_change()

    def _schedule_blink(self) -> None:
        self.blink_timer.start(random.randint(2_800, 6_200))

    def _blink(self) -> None:
        if getattr(self, "pose_transition_active", False):
            self._schedule_blink()
            return
        self.blink_generation += 1
        generation = self.blink_generation
        render_base = self._render_base_expression()
        can_idle_blink = (
            self.state != "speaking"
            and render_base in self.physics_expression_poses
            and not self.idle_blinking
        )
        if can_idle_blink:
            base_expression = self.current_expression
            current = self.character.pixmap()
            if current is None or current.isNull():
                current = self.expression_pixmaps[base_expression]
            self.blink_restore_pixmap = QPixmap(current)
            self.idle_blinking = True
            self.blink_opacity = 0.45
            self.eye_overlay.hide()
            self.character.setPixmap(
                self._blink_composite(
                    current,
                    render_base,
                    self.blink_opacity,
                )
            )
            QTimer.singleShot(
                32,
                lambda: self._advance_idle_blink(
                    base_expression,
                    generation,
                    1.0,
                ),
            )
            QTimer.singleShot(
                92,
                lambda: self._advance_idle_blink(
                    base_expression,
                    generation,
                    0.42,
                ),
            )
            QTimer.singleShot(
                random.randint(118, 145),
                lambda: self._finish_blink(base_expression, generation),
            )
        elif self.state == "speaking" and not self.speech_blinking:
            current = self.speech_visual_pixmap
            if current.isNull():
                visible = self.character.pixmap()
                current = (
                    QPixmap(visible)
                    if visible is not None and not visible.isNull()
                    else QPixmap(self.expression_pixmaps[self.speech_closed_expression])
                )
            self.speech_blink_restore_pixmap = QPixmap(current)
            self.speech_blinking = True
            self.blink_opacity = 0.45
            self.eye_overlay.hide()
            self._render_speech_pixmap(current)
            QTimer.singleShot(
                32,
                lambda: self._advance_speaking_blink(generation, 1.0),
            )
            QTimer.singleShot(
                92,
                lambda: self._advance_speaking_blink(generation, 0.42),
            )
            QTimer.singleShot(
                random.randint(118, 145),
                lambda: self._finish_speaking_blink(generation),
            )
        self._schedule_blink()

    def _advance_idle_blink(
        self,
        base_expression: str,
        generation: int,
        opacity: float,
    ) -> None:
        if (
            not self.idle_blinking
            or generation != self.blink_generation
            or self.state == "speaking"
            or self.current_expression != base_expression
            or self.blink_restore_pixmap.isNull()
        ):
            return
        self.blink_opacity = opacity
        self.character.setPixmap(
            self._blink_composite(
                self.blink_restore_pixmap,
                base_expression,
                opacity,
            )
        )

    def _advance_speaking_blink(
        self,
        generation: int,
        opacity: float,
    ) -> None:
        if (
            not self.speech_blinking
            or generation != self.blink_generation
            or self.state != "speaking"
        ):
            return
        self.blink_opacity = opacity
        current = self.speech_visual_pixmap
        if current.isNull():
            current = self.speech_blink_restore_pixmap
        if not current.isNull():
            self._render_speech_pixmap(current)

    def _finish_blink(
        self,
        base_expression: str,
        generation: int,
    ) -> None:
        if (
            generation != self.blink_generation
            or self.state == "speaking"
            or self.current_expression != base_expression
        ):
            self.idle_blinking = False
            self.blink_opacity = 0.0
            return
        if not self.blink_restore_pixmap.isNull():
            self.character.setPixmap(self.blink_restore_pixmap)
        self.idle_blinking = False
        self.blink_opacity = 0.0
        self._render_attention_layers(force=True)
        self._attention_tick()
        if random.random() < 0.16:
            QTimer.singleShot(170, self._blink)

    def _finish_speaking_blink(
        self,
        generation: int,
    ) -> None:
        if self.state != "speaking" or generation != self.blink_generation:
            self.speech_blinking = False
            self.blink_opacity = 0.0
            return
        self.speech_blinking = False
        self.blink_opacity = 0.0
        if not self.speech_visual_pixmap.isNull():
            self.character.setPixmap(self.speech_visual_pixmap)
        self._render_attention_layers(force=True)
        self._attention_tick()

    def _wink_once(self) -> bool:
        """Play one deliberate, expression-preserving wink when idle."""
        if (
            self.speech_playing
            or self.state == "speaking"
            or self.idle_blinking
            or self.speech_blinking
        ):
            return False
        base_expression = self.current_expression
        render_base = self._render_base_expression()
        if render_base not in self.physics_expression_poses:
            return False
        current = self.character.pixmap()
        if current is None or current.isNull():
            current = self.expression_pixmaps[base_expression]
        restore = QPixmap(current)
        self.blink_generation += 1
        generation = self.blink_generation

        def render(opacity: float) -> None:
            if (
                generation != self.blink_generation
                or self.speech_playing
                or self.current_expression != base_expression
            ):
                return
            self.character.setPixmap(
                self._wink_composite(
                    restore,
                    render_base,
                    opacity,
                )
            )

        def finish() -> None:
            if generation != self.blink_generation:
                return
            if self.current_expression == base_expression:
                self.character.setPixmap(restore)
                self._render_attention_layers(force=True)
                self._attention_tick()

        render(0.5)
        QTimer.singleShot(45, lambda: render(1.0))
        QTimer.singleShot(165, lambda: render(0.45))
        QTimer.singleShot(235, finish)
        return True

    def _schedule_attention_glance(self) -> None:
        self.gaze_timer.start(random.randint(38_000, 78_000))

    def _schedule_ambient_expression(self) -> None:
        self.ambient_timer.start(random.randint(42_000, 88_000))

    def _show_ambient_expression(self) -> None:
        # Emotional expressions require conversational or event context.
        # Context-free idle variation is limited to pose, breath, gaze and
        # blinking so an unrelated smile, worry or scold can never appear.
        self._schedule_ambient_expression()

    def _start_attention_glance(self) -> None:
        if self.conservative_idle:
            self._schedule_attention_glance()
            return
        if self.state == "idle" and self.idle_pose == "cheek":
            self.set_state("glance", source="ambient")
            QTimer.singleShot(random.randint(2_600, 4_100), self._end_attention_glance)
        self._schedule_attention_glance()

    def _end_attention_glance(self) -> None:
        if self.state == "glance":
            self.set_state("idle")

    def _character_clicked(self) -> None:
        if self.state == "glance":
            self._show_caught_reaction()
            QTimer.singleShot(1_700, self.open_dashboard)
            return
        self.open_dashboard()

    def _show_caught_reaction(self) -> None:
        self.set_state("caught", source="user_direct")
        self._show_bubble("????????????????????????????????????")
        self._schedule_return_to_idle(2_800, "caught")
        QTimer.singleShot(3_400, self.bubble.hide)

    def _set_expression(self, expression: str, fade: bool = True) -> None:
        # Legacy expression rendering resumes ownership of the canvas, so the
        # half-body overlays suppressed by a v4 full-body publish may return.
        self._adaptive_full_body_active = False
        if expression not in self.expression_pixmaps:
            expression = "idle"
        self._cancel_expression_transition()
        if self._active_pose_transition_owns(expression):
            return
        if self._needs_pose_transition(expression, fade):
            target_pose = self.physics_expression_poses[expression]
            self._start_pose_transition(expression, target_pose)
            return
        self._prepare_expression_layers(expression, fade)
        if expression == self.current_expression:
            return
        if not fade:
            self.character.setPixmap(self.expression_pixmaps[expression])
            self.current_expression = expression
            return
        self._start_expression_crossfade(expression)

    def _active_pose_transition_owns(self, expression: str) -> bool:
        """Keep one in-flight pose transition or cancel it before replacement."""
        if not getattr(self, "pose_transition_active", False):
            return False
        # Timers for idle motion, blinking, and speech can all request the
        # same frame while a large-pose fade is already in flight. Restarting
        # that fade creates a visible flash although the target is unchanged.
        if expression == getattr(self, "pose_transition_expression", None):
            return True
        self._cancel_pose_transition()
        return False

    def _needs_pose_transition(self, expression: str, fade: bool) -> bool:
        current_pose = self.physics_expression_poses.get(self.current_expression)
        target_pose = self.physics_expression_poses.get(expression)
        return (
            fade
            and current_pose is not None
            and target_pose is not None
            and current_pose != target_pose
        )

    def _prepare_expression_layers(self, expression: str, fade: bool) -> None:
        if hasattr(self, "face_overlay") and expression != self._idle_expression():
            self.face_overlay.hide()
            self.eye_overlay.hide()
        current_has_physics = self.current_expression in self.physics_expression_poses
        target_has_physics = expression in self.physics_expression_poses
        if not target_has_physics:
            # Hide local overlays before cross-fading to a special expression;
            # otherwise an idle sleeve/face can briefly float over that frame.
            self._update_physics_pose(expression)
        elif not fade or current_has_physics:
            self._update_physics_pose(expression)

    def _start_expression_crossfade(self, expression: str) -> None:
        pixmap = self.expression_pixmaps[expression]
        self.expression_overlay.setPixmap(pixmap)
        self.expression_overlay.show()
        self.expression_overlay.raise_()
        if not self.physics_overlay.isHidden():
            self.sleeve_left_overlay.raise_()
            self.sleeve_right_overlay.raise_()
            self.hair_left_overlay.raise_()
            self.hair_right_overlay.raise_()
            self.physics_overlay.raise_()
        self.bubble.raise_()
        self.overlay_opacity.setOpacity(0.0)
        self.character_opacity.setOpacity(1.0)
        fade_in = QPropertyAnimation(self.overlay_opacity, b"opacity", self)
        fade_out = QPropertyAnimation(self.character_opacity, b"opacity", self)
        for animation, start, end in (
            (fade_in, 0.0, 1.0),
            (fade_out, 1.0, 0.0),
        ):
            animation.setDuration(180)
            animation.setStartValue(start)
            animation.setEndValue(end)
            animation.setEasingCurve(QEasingCurve.InOutSine)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade_in)
        group.addAnimation(fade_out)
        group.finished.connect(lambda: self._finish_expression_change(expression))
        group.start()
        self.expression_animation = group

    def _cancel_expression_transition(self) -> None:
        animation = getattr(self, "expression_animation", None)
        if animation is not None and animation.state():
            animation.stop()
        if hasattr(self, "expression_overlay"):
            self.expression_overlay.hide()
        if hasattr(self, "character_opacity"):
            self.character_opacity.setOpacity(1.0)

    def _cancel_pose_transition(self) -> None:
        # Invalidate callbacks that may already be queued by Qt.  A boolean is
        # insufficient because an old animation can finish after a new
        # transition has set the boolean back to True.
        self.pose_transition_generation = (
            getattr(self, "pose_transition_generation", 0) + 1
        )
        for animation_name in (
            "pose_transition_out",
            "pose_transition_in",
        ):
            animation = getattr(self, animation_name, None)
            if animation is not None:
                animation.stop()
            setattr(self, animation_name, None)
        self.pose_transition_active = False
        self.pose_transition_expression = None
        self.pose_transition_target_pose = None
        self.character_opacity.setOpacity(1.0)

    def _start_pose_transition(
        self,
        expression: str,
        target_pose: str,
    ) -> None:
        """Switch large pose sprites without ever drawing both simultaneously."""
        self.pose_transition_generation = (
            getattr(self, "pose_transition_generation", 0) + 1
        )
        generation = self.pose_transition_generation
        self.pose_transition_active = True
        self.pose_transition_expression = expression
        self.pose_transition_target_pose = target_pose
        self.expression_overlay.hide()
        self.face_overlay.hide()
        self.eye_overlay.hide()
        for overlay in (
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
        ):
            overlay.hide()
        fade_out = QPropertyAnimation(
            self.character_opacity,
            b"opacity",
            self,
        )
        fade_out.setDuration(75)
        fade_out.setStartValue(self.character_opacity.opacity())
        # The sprite must be fully transparent before its pixmap is replaced.
        # Swapping at partial opacity leaves both poses in visual persistence
        # and can also expose a stale QGraphicsOpacityEffect cache for a frame.
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InOutSine)
        fade_out.finished.connect(
            lambda: self._pose_transition_midpoint(
                expression,
                target_pose,
                generation,
            )
        )
        self.pose_transition_out = fade_out
        fade_out.start()

    def _pose_transition_midpoint(
        self,
        expression: str,
        target_pose: str,
        generation: int,
    ) -> None:
        if (
            not getattr(self, "pose_transition_active", False)
            or generation != getattr(self, "pose_transition_generation", -1)
            or expression != getattr(self, "pose_transition_expression", None)
            or target_pose != getattr(self, "pose_transition_target_pose", None)
        ):
            return
        self.character_opacity.setOpacity(0.0)
        self.character.setPixmap(self.expression_pixmaps[expression])
        self.current_expression = expression
        self.active_physics_pose = target_pose
        self._render_sleeve_layers(force=True)
        self._render_hair_layers(force=True)
        self._render_physics_layer(force=True)
        self.character.update()
        fade_in = QPropertyAnimation(
            self.character_opacity,
            b"opacity",
            self,
        )
        fade_in.setDuration(105)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InOutSine)
        fade_in.finished.connect(
            lambda: self._finish_pose_transition(expression, generation)
        )
        self.pose_transition_in = fade_in
        fade_in.start()

    def _finish_pose_transition(
        self,
        expression: str,
        generation: int,
    ) -> None:
        if (
            not getattr(self, "pose_transition_active", False)
            or generation != getattr(self, "pose_transition_generation", -1)
            or expression != getattr(self, "pose_transition_expression", None)
        ):
            return
        self.pose_transition_active = False
        self.pose_transition_expression = None
        self.pose_transition_target_pose = None
        self.pose_transition_out = None
        self.pose_transition_in = None
        self.character_opacity.setOpacity(1.0)
        self._update_physics_pose(expression)
        self._render_attention_layers(force=True)
        self._attention_tick()

    def _finish_expression_change(self, expression: str) -> None:
        self.character.setPixmap(self.expression_pixmaps[expression])
        self.character_opacity.setOpacity(1.0)
        self.expression_overlay.hide()
        self.current_expression = expression
        self._update_physics_pose(expression)

    def _ensure_idle_mouth_closed(self) -> None:
        if self.state != "idle":
            return
        speaking_frame = self.current_expression.startswith((
            "speaking",
            "mouth_",
            "viseme_",
            "blink_mid",
            "blink_open",
            "blink_wide",
            "blink_round",
            "blink_i",
            "blink_o",
        ))
        if not self.mouth_open and not speaking_frame:
            return
        self.mouth_timer.stop()
        self.speech_blinking = False
        self.audio_driven_mouth = False
        self.viseme_dynamics.reset()
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self._idle_expression()
        self._set_expression(self._idle_expression(), fade=False)

    def _mouth_tick(self) -> None:
        if self.state != "speaking" or self.audio_driven_mouth:
            return
        if self.mouth_frame_index == 0:
            self.mouth_frame_index = 1
        elif self.mouth_frame_index == 1:
            self.mouth_frame_index = random.choices((0, 2), weights=(0.28, 0.72), k=1)[
                0
            ]
        else:
            self.mouth_frame_index = 1
        self.mouth_open = self.mouth_frame_index > 0
        expression = (
            self.speech_closed_expression,
            self.speech_mid_expression,
            self.speech_open_expression,
        )[self.mouth_frame_index]
        self.speech_current_expression = expression
        aperture = (0.0, 0.48, 0.9)[self.mouth_frame_index]
        self._show_speech_frame(expression, aperture)
        delay_range = (
            (125, 235)
            if self.mouth_frame_index == 0
            else (75, 145)
            if self.mouth_frame_index == 1
            else (85, 165)
        )
        self.mouth_timer.start(random.randint(*delay_range))

    def _start_mouth_animation(self, audio_driven: bool = False) -> None:
        self.blink_generation += 1
        # Speech owns the visible character frame from its first sample.
        # A pending expression/pose cross-fade can otherwise leave the prior
        # pose above the new closed-mouth frame for one or two audio cues.
        self._cancel_expression_transition()
        self._cancel_pose_transition()
        self._stop_gesture_animation()
        self.expression_overlay.hide()
        self.mouth_timer.stop()
        self.mouth_visual_timer.stop()
        self.mouth_transition_from = QPixmap()
        self.mouth_transition_to = QPixmap()
        self.mouth_transition_started = 0.0
        self.speech_blinking = False
        self.blink_opacity = 0.0
        self.audio_driven_mouth = audio_driven
        self.mouth_closing = False
        self.viseme_dynamics.reset()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.speech_motion_release_attempts = 0
        self.realtime_motion_release_attempts = 0
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self.speech_closed_expression
        if getattr(self, "_adaptive_full_body_active", False):
            # The v4 full-body composition owns the canvas and renders its own
            # speech mouth frames from speech-performance events. Legacy
            # half-body mouth rendering must not overwrite the full-body frame
            # or resume ownership of the suppressed overlays (the startup
            # full/half-body double image).
            return
        self._set_expression(self.speech_closed_expression, fade=False)
        closed_frame = self._mouth_aperture_pixmap(
            self.speech_closed_expression,
            0.0,
        )
        self._render_speech_pixmap(closed_frame)
        if self.speech_gesture_expression is not None:
            self._update_physics_pose(self.speech_gesture_expression)
        if not audio_driven:
            self.mouth_timer.start(random.randint(70, 120))

    def _show_speech_frame(
        self,
        expression: str,
        aperture: float,
    ) -> None:
        """Render speech over its emotional base without a full-sprite swap."""
        if expression not in self.expression_pixmaps:
            expression = self.speech_mid_expression
        self._render_speech_pixmap(
            self._mouth_aperture_pixmap(
                expression,
                aperture,
            )
        )
        self.current_expression = expression
        self._update_physics_pose(expression)
        self._render_attention_layers(force=True)

    def _render_speech_pixmap(self, clean_pixmap: QPixmap) -> None:
        """Display the latest mouth frame with blink as an independent layer.

        Mouth animation keeps advancing while the eyelids are closed.  The
        clean frame is retained separately so ending a blink never restores a
        stale viseme from before the blink began.
        """
        # Legacy mouth rendering resumes ownership of the canvas, so the
        # half-body overlays suppressed by a v4 full-body publish may return.
        self._adaptive_full_body_active = False
        self.speech_visual_pixmap = QPixmap(clean_pixmap)
        visible = (
            self._blink_composite(
                clean_pixmap,
                self.speech_gesture_expression or self.speech_closed_expression,
                self.blink_opacity,
            )
            if self.speech_blinking
            else clean_pixmap
        )
        self.character.setPixmap(visible)

    def _stop_mouth_animation(self) -> None:
        self.blink_generation += 1
        self.mouth_timer.stop()
        self.mouth_visual_timer.stop()
        self.speech_blinking = False
        self.blink_opacity = 0.0
        self.audio_driven_mouth = False
        self.mouth_closing = False
        self.viseme_dynamics.reset()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self.speech_closed_expression
        motion_expression = (
            self.speech_gesture_expression or self.speech_closed_expression
        )
        motion_pose = self.physics_expression_poses.get(
            motion_expression,
            getattr(self, "idle_pose", "front"),
        )
        self.face_motion_frame = self.face_motion_controller.close(
            pose=motion_pose,
            expression=motion_expression,
        )
        closed_frame = self._mouth_aperture_pixmap(
            self.speech_closed_expression,
            0.0,
        )
        self._set_expression(self.speech_closed_expression, fade=False)
        self._render_speech_pixmap(closed_frame)
        self.current_expression = self.speech_closed_expression
        self._compose_character_position()

    def _audio_viseme_cue(self, level: float, vowel: str) -> None:
        if getattr(self, "_adaptive_full_body_active", False):
            # The v4 full-body composition renders its own speech mouth from
            # speech-performance events.  The legacy viseme path must not run
            # in parallel: it would reset the ownership flag and let the
            # suppressed half-body overlays return, stacking a second body over
            # the full-body frame (the reported double image).
            return
        if (
            self.state != "speaking"
            or not self.audio_driven_mouth
            or self.mouth_closing
        ):
            return
        # A live viseme owns the full photographed face. Remove any gaze
        # overlay left by the preceding idle frame before drawing the mouth.
        self.eye_overlay.hide()
        frame: VisemeFrame = self.viseme_dynamics.advance(level, vowel)
        expression = self._viseme_expression(frame.selected)
        motion_expression = (
            self.speech_gesture_expression or self.speech_closed_expression
        )
        motion_pose = self.physics_expression_poses.get(
            motion_expression,
            getattr(self, "idle_pose", "front"),
        )
        self.face_motion_frame = self.face_motion_controller.advance(
            frame,
            pose=motion_pose,
            expression=motion_expression,
            blink=1.0 if self.speech_blinking else 0.0,
        )
        self.mouth_frame_index = frame.frame_index
        self.mouth_open = frame.mouth_open
        self.speech_current_expression = expression
        if frame.selected != frame.previous or self.mouth_transition_to.isNull():
            self._queue_audio_mouth_transition(
                expression,
                frame.jaw_aperture,
            )
        target_motion = min(
            4.0,
            self.viseme_dynamics.smoothed_level * 3.0 + frame.jaw_weight,
        )
        self.head_motion_y = self.head_motion_y * 0.62 + target_motion * 0.38
        self.speech_motion_target_y = -self.head_motion_y
        self._motion_tick()

    def _viseme_expression(self, viseme: str) -> str:
        if viseme == "CLOSED":
            expression = self.speech_closed_expression
        elif viseme == "CONSONANT":
            expression = self.speech_mid_expression
        elif self.speech_gesture_expression is not None:
            expression = EXPRESSION_VISEME_FRAMES[self.speech_gesture_expression].get(
                viseme, self.speech_mid_expression
            )
        else:
            stem = NEUTRAL_VISEME_ASSET_STEMS.get(viseme)
            expression = (
                self.speech_mid_expression
                if stem is None
                else f"{stem}{self._active_speech_pose_suffix()}"
            )
        return expression

    def _mouth_aperture_pixmap(
        self,
        expression: str,
        aperture: float,
    ) -> QPixmap:
        closed = self.expression_pixmaps[self.speech_closed_expression]
        if expression == self.speech_closed_expression or aperture <= 0.01:
            return QPixmap(closed)
        source = self.expression_pixmaps[expression]
        suffix = self._active_speech_pose_suffix()
        return self.face_renderer.render(
            closed,
            self.face_motion_frame,
            self._face_render_layers(source, suffix),
            aperture=aperture,
        )

    def _face_render_layers(
        self,
        mouth_source: QPixmap,
        suffix: str,
    ) -> FaceRenderLayers:
        if self.speech_gesture_expression is not None:
            expression = self.speech_gesture_expression
            return FaceRenderLayers(
                mouth_source=mouth_source,
                mouth_mask=self.gesture_mouth_masks[expression],
                mouth_rect=EXPRESSION_SPEECH_MOUTH_RECTS[expression],
            )
        return FaceRenderLayers(
            mouth_source=mouth_source,
            mouth_mask=self.mouth_masks[suffix],
            mouth_rect=self.mouth_clips[suffix],
        )

    def _speech_mouth_patch(
        self,
        source: QPixmap,
        suffix: str,
        source_already_aligned: bool = False,
    ) -> QPixmap:
        """Use one mask path for target frames and in-between transitions."""
        if self.speech_gesture_expression is not None:
            return self._masked_region(
                source,
                self.gesture_mouth_masks[self.speech_gesture_expression],
            )
        if (
            suffix == ""
            and self.speech_closed_expression == CHEEK_SPEECH_CLOSED_EXPRESSION
        ):
            return self._masked_region(
                source,
                self.viseme_mouth_masks[""],
            )
        return self._masked_mouth_patch(
            source,
            suffix,
            self.speech_closed_expression,
            source_already_aligned=source_already_aligned,
        )

    def _queue_audio_mouth_transition(
        self,
        expression: str,
        aperture: float | None = None,
    ) -> None:
        if expression not in self.expression_pixmaps:
            expression = self.speech_mid_expression
        previous_aperture = getattr(
            self,
            "mouth_aperture_target",
            0.0,
        )
        # If a new phoneme arrives mid-transition, continue from the latest
        # clean rendered frame. Jumping from the previous target would skip
        # several visual milliseconds and make the lips appear to teleport.
        normalized_current = (
            QPixmap(self.speech_visual_pixmap)
            if (
                self.mouth_visual_timer.isActive()
                and not self.speech_visual_pixmap.isNull()
            )
            else self._mouth_aperture_pixmap(
                self.current_expression,
                previous_aperture,
            )
        )
        self.mouth_transition_from = normalized_current
        next_aperture = (
            0.0
            if expression == self.speech_closed_expression
            else 1.0
            if aperture is None
            else max(0.0, min(1.0, float(aperture)))
        )
        self.mouth_transition_to = self._mouth_aperture_pixmap(
            expression,
            next_aperture,
        )
        opening = previous_aperture <= 0.05 < next_aperture
        closing = next_aperture <= 0.05 < previous_aperture
        self.mouth_transition_duration = (
            VISEME_OPEN_TRANSITION_SECONDS
            if opening
            else VISEME_CLOSE_TRANSITION_SECONDS
            if closing
            else VISEME_CHANGE_TRANSITION_SECONDS
        )
        self.mouth_aperture_target = next_aperture
        self.mouth_transition_started = time.perf_counter()
        self._update_physics_pose(expression)
        self.current_expression = expression
        self.expression_overlay.hide()
        if not self.mouth_visual_timer.isActive():
            self.mouth_visual_timer.start()

    def _render_audio_mouth_transition(self) -> None:
        if (
            self.state != "speaking"
            or not self.audio_driven_mouth
            or self.mouth_transition_from.isNull()
            or self.mouth_transition_to.isNull()
        ):
            self.mouth_visual_timer.stop()
            return
        elapsed = time.perf_counter() - self.mouth_transition_started
        progress = max(
            0.0,
            min(1.0, elapsed / self.mouth_transition_duration),
        )
        eased = 0.5 - 0.5 * math.cos(progress * math.pi)
        suffix = self._active_speech_pose_suffix()
        blended = QPixmap(self.mouth_transition_from)
        painter = QPainter(blended)
        painter.setOpacity(eased)
        painter.drawPixmap(
            0,
            0,
            self._speech_mouth_patch(
                self.mouth_transition_to,
                suffix,
                source_already_aligned=True,
            ),
        )
        painter.end()
        self._render_speech_pixmap(blended)
        if progress >= 1.0:
            self._render_speech_pixmap(self.mouth_transition_to)
            self.mouth_visual_timer.stop()

    def set_state(
        self,
        state: str,
        *,
        source: str = "conversation",
        intensity: float = 0.5,
        force: bool = False,
        animate_gesture: bool = True,
    ) -> bool:
        decision = self.expression_arbiter.request(
            state,
            source=source,
            intensity=intensity,
            force=force or state in {"idle", "speaking"},
        )
        if not decision.accepted:
            return False
        self._stop_gesture_animation()
        self.expression_generation += 1
        self.state = state
        self.dashboard.set_desktop_companion_status(
            "expression",
            state.replace("_", " "),
        )
        if state == "idle":
            expression = self._idle_expression()
        elif state == "speaking":
            expression = self._speaking_expression()
        else:
            expression = state
        self._set_expression(expression)
        expressive_states = {
            "happy",
            "reminder",
            "worried",
            "thinking_front",
            "caught",
            "gentle_smile_front",
            "worried_front",
            "shy_front",
            "mock_scold",
            "surprised_front",
            "relieved_front",
            "tired_front",
            "proud_front",
            *NEW_EXPRESSION_ASSETS,
        }
        if state in expressive_states and animate_gesture:
            animation = QVariantAnimation(self)
            animation.setDuration(
                720
                if state in {"mock_scold", "mock_hit_front"}
                else 620
                if state
                in {
                    "thinking_front",
                    "shy_front",
                    "shy_cute_front",
                    "tired_front",
                    "exasperated_front",
                }
                else 500
            )
            animation.setStartValue(QPoint(0, 0))
            animation.setKeyValueAt(
                0.35,
                QPoint(
                    -5 if state in {"caught", "shy_front", "shy_cute_front"} else 0,
                    -7
                    if state == "happy"
                    else -9
                    if state in {"mock_scold", "mock_hit_front"}
                    else -3
                    if state
                    in {
                        "reminder",
                        "thinking_front",
                        "surprised_front",
                        "proud_front",
                        "eureka_front",
                    }
                    else 0,
                ),
            )
            animation.setKeyValueAt(
                0.62,
                QPoint(
                    5
                    if state in {"worried", "worried_front", "caught"}
                    else 2
                    if state in {"mock_scold", "mock_hit_front"}
                    else 0,
                    -5
                    if state == "mock_scold"
                    else -2
                    if state in {"thinking_front", "proud_front"}
                    else 0,
                ),
            )
            animation.setEndValue(QPoint(0, 0))
            animation.valueChanged.connect(self._apply_gesture_motion)
            animation.finished.connect(self._finish_gesture_motion)
            animation.setEasingCurve(QEasingCurve.OutBack)
            animation.start()
            self.state_animation = animation
        return True
