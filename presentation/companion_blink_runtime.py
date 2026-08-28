"""Blink lifecycle shared by the half- and full-body face renderers."""

from __future__ import annotations

lazy from dataclasses import replace
lazy import random

lazy from PySide6.QtCore import QTimer

lazy from domain.face_microtiming import (
    BLINK_CLOSED_TIMES_MS,
    BLINK_HALF_CLOSE_TIMES_MS,
    BLINK_HALF_OPEN_TIMES_MS,
    BLINK_REST_AT_MS,
)
lazy from domain.face_rig import blink_for_eye_state, eye_state_for_blink

BLINK_PROBABILITY = 0.16


class CompanionBlinkRuntimeMixin:
    """Drive discrete blink states without replacing the active character view."""

    def _full_body_blink(self) -> None:
        """Blink through discrete full-body eye states on the 50 Hz clock."""
        self.blink_generation = getattr(self, "blink_generation", 0) + 1
        generation = self.blink_generation
        self._set_full_body_blink(generation, 0.5)
        for delay in BLINK_HALF_CLOSE_TIMES_MS[1:]:
            QTimer.singleShot(
                delay,
                lambda generation=generation: self._set_full_body_blink(
                    generation, 0.5
                ),
            )
        for delay in BLINK_CLOSED_TIMES_MS:
            QTimer.singleShot(
                delay,
                lambda generation=generation: self._set_full_body_blink(
                    generation, 1.0
                ),
            )
        for delay in BLINK_HALF_OPEN_TIMES_MS:
            QTimer.singleShot(
                delay,
                lambda generation=generation: self._set_full_body_blink(
                    generation, 0.5
                ),
            )
        QTimer.singleShot(
            BLINK_REST_AT_MS,
            lambda: self._set_full_body_blink(generation, 0.0),
        )

    def _set_full_body_blink(self, generation: int, opacity: float) -> None:
        if generation != self.blink_generation:
            return
        self.blink_opacity = blink_for_eye_state(eye_state_for_blink(opacity))
        self._refresh_full_body()

    def _set_half_body_blink(self, generation: int, opacity: float) -> None:
        """Blink via the parametric half-body renderer (mutate ``blink`` only)."""
        if generation != self.blink_generation:
            return
        self.blink_opacity = blink_for_eye_state(eye_state_for_blink(opacity))
        motion = self.face_motion_frame
        if motion is None:
            return
        self.face_motion_frame = replace(
            motion,
            expression_shape=replace(
                motion.expression_shape,
                blink=self.blink_opacity,
            ),
        )
        self.character.setPixmap(
            self._render_masked_blink_frame(self.blink_opacity)
        )

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
        self.blink_opacity = blink_for_eye_state(eye_state_for_blink(opacity))
        self.character.setPixmap(
            self._blink_composite(
                self.blink_restore_pixmap,
                base_expression,
                self.blink_opacity,
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
        self.blink_opacity = blink_for_eye_state(eye_state_for_blink(opacity))
        self._set_half_body_blink(generation, self.blink_opacity)

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
            # A newer blink cycle owns the shared ``blink_opacity`` now; only
            # retire this cycle's own flag instead of zeroing the live value.
            self.idle_blinking = False
            return
        self._set_half_body_blink(generation, 0.0)
        self.idle_blinking = False
        self.blink_opacity = 0.0
        self._render_attention_layers(force=True)
        self._attention_tick()
        if random.random() < BLINK_PROBABILITY:
            QTimer.singleShot(
                170,
                lambda: self._reblink_if_current(generation),
            )

    def _reblink_if_current(self, generation: int) -> None:
        """Run the follow-up blink only while its owner window is still live."""
        if getattr(self, "_closing", False) or generation != self.blink_generation:
            return
        self._blink()

    def _finish_speaking_blink(
        self,
        generation: int,
    ) -> None:
        if self.state != "speaking" or generation != self.blink_generation:
            # Do not clear the shared ``blink_opacity`` for a superseded cycle.
            self.speech_blinking = False
            return
        self.speech_blinking = False
        self.blink_opacity = 0.0
        self._set_half_body_blink(generation, 0.0)
        self._render_attention_layers(force=True)
        self._attention_tick()


__all__ = ("CompanionBlinkRuntimeMixin",)
