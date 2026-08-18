from __future__ import annotations

"""Crimson Flame resonance (赤焰劍意), inspired by "A・I ga Tomaranai!".

When the user is tense — brows furrowed, typing furiously, or voice full of
anxiety — MoHan's idle breathing quickens and her blink rate rises, as if she
senses the user's agitation through the sword.  This is a quiet, non-verbal act
of empathy: "主上，妾感受到您的殺氣/焦慮了".

This module is pure domain logic with no Qt dependency.  It only computes a
smooth, bounded resonance level from cheap scalar inputs (brow tension and a
typing-rate estimate); the presentation layer samples it on its existing timer,
so nothing here ever blocks the Qt main thread.

The key tuning concerns, per the user's direction:

- The resonance level must ease smoothly (exponential approach), never snap, so
  the breathing period shortens gradually instead of jittering frame to frame.
- The breathing period and blink interval must stay within safe bounds so the
  companion never looks like a twitching zombie.
"""

lazy import math
lazy import time

# How strongly brow tension and typing rate each contribute to resonance.
BROW_TENSION_WEIGHT = 0.6
TYPING_RATE_WEIGHT = 0.4

# The brow-tension threshold above which the user is considered "furrowed".
BROW_TENSION_THRESHOLD = 0.55

# Typing rate (keystrokes per second) that maps to full typing-driven resonance.
TYPING_RATE_FULL_KPS = 6.0

# Resonance eases toward its target with this per-second rate.  A smaller value
# means a slower, smoother transition (no snapping).
RESONANCE_EASE_RATE = 0.8

# Breathing period (in idle-phase ticks) at rest and at full resonance.
BREATH_PERIOD_REST = 72.0
BREATH_PERIOD_AGITATED = 44.0

# Blink interval (seconds) at rest and at full resonance.
BLINK_INTERVAL_REST = 4.0
BLINK_INTERVAL_AGITATED = 2.2


class EmotionalResonanceState:
    """Track a smooth resonance level from brow tension and typing rate."""

    def __init__(self, *, clock: object | None = None) -> None:
        self._clock = clock or time.monotonic
        self._resonance = 0.0
        self._last_update_at = self._clock()

    @property
    def resonance(self) -> float:
        """The current smoothed resonance level in [0, 1]."""
        return self._resonance

    def update(
        self,
        *,
        brow_tension: float,
        typing_rate_kps: float,
        now: float | None = None,
    ) -> float:
        """Advance the resonance toward its target and return the new level."""
        current = self._clock() if now is None else float(now)
        elapsed = max(0.0, current - self._last_update_at)
        self._last_update_at = current

        brow_component = _clamp01(
            (brow_tension - BROW_TENSION_THRESHOLD) / (1.0 - BROW_TENSION_THRESHOLD)
        )
        typing_component = _clamp01(typing_rate_kps / TYPING_RATE_FULL_KPS)
        target = _clamp01(
            BROW_TENSION_WEIGHT * brow_component
            + TYPING_RATE_WEIGHT * typing_component
        )

        # Exponential ease toward the target so the transition is always smooth.
        alpha = 1.0 - math.exp(-RESONANCE_EASE_RATE * elapsed)
        self._resonance += (target - self._resonance) * alpha
        return self._resonance

    def breath_period(self) -> float:
        """The breathing period (idle-phase ticks) for the current resonance."""
        return _lerp(
            BREATH_PERIOD_REST,
            BREATH_PERIOD_AGITATED,
            self._resonance,
        )

    def blink_interval(self) -> float:
        """The blink interval (seconds) for the current resonance."""
        return _lerp(
            BLINK_INTERVAL_REST,
            BLINK_INTERVAL_AGITATED,
            self._resonance,
        )

    def reset(self) -> None:
        self._resonance = 0.0
        self._last_update_at = self._clock()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount
