from __future__ import annotations

"""Shy gaze aversion (羞澀視線迴避), inspired by "A・I ga Tomaranai!".

When the user stares at MoHan on screen for a sustained stretch, a real girl
would grow flustered and glance away.  This module encodes the precise timing
and iris offset so the aversion reads as a shy, restrained look-away — never a
sudden eye-roll.

The key tuning concerns, per the user's direction:

- The stare threshold must be long enough (not a hair-trigger) so the companion
  does not flinch the instant the user glances at her.
- The iris offset must be small and directed downward (left-down or right-down),
  never a large lateral jump that would look like rolling the eyes.
- The aversion must hold for a few seconds, then release smoothly.

This is pure domain logic with no Qt dependency, so the timing and offsets can
be unit-tested independently of the renderer.
"""

lazy import time

# How long the user must keep their gaze on the companion before she grows shy.
STARE_THRESHOLD_SECONDS = 5.0

# How long the shy look-away holds before the gaze returns.
AVERSION_HOLD_SECONDS = 3.0

# The iris offset applied during aversion.  Kept small and downward so it reads
# as a bashful glance to the lower-left or lower-right, not an eye-roll.  The
# x component is modest; the y component points down (negative in screen space
# where +y is down, so we use a positive downward value here and let the caller
# map it to its own coordinate convention).
AVERSION_OFFSET_X = 0.35
AVERSION_OFFSET_Y = 0.25

# The gaze-confidence floor above which we consider the user to be looking at
# the screen (and therefore potentially at the companion).
GAZE_CONFIDENCE_THRESHOLD = 0.35


class ShyGazeState:
    """Track sustained staring and produce a shy look-away when it persists."""

    def __init__(self, *, clock: object | None = None) -> None:
        self._clock = clock or time.monotonic
        self._stare_started_at: float | None = None
        self._aversion_until: float | None = None
        self._aversion_side = 1.0  # +1 = look right-down, -1 = look left-down

    def update(
        self,
        *,
        gaze_confidence: float,
        now: float | None = None,
    ) -> tuple[float, float] | None:
        """Advance the state machine and return the iris offset, or None.

        Returns ``(offset_x, offset_y)`` while the companion is averting her
        gaze, and ``None`` when she is looking normally.
        """
        current = self._clock() if now is None else float(now)

        # If we are currently averting, keep holding until the timer expires.
        if self._aversion_until is not None:
            if current < self._aversion_until:
                return (
                    self._aversion_side * AVERSION_OFFSET_X,
                    AVERSION_OFFSET_Y,
                )
            self._aversion_until = None

        looking = gaze_confidence >= GAZE_CONFIDENCE_THRESHOLD
        if looking:
            if self._stare_started_at is None:
                self._stare_started_at = current
            elif current - self._stare_started_at >= STARE_THRESHOLD_SECONDS:
                # The user has stared long enough: trigger a shy look-away.
                self._stare_started_at = None
                self._aversion_until = current + AVERSION_HOLD_SECONDS
                self._aversion_side = -self._aversion_side
                return (
                    self._aversion_side * AVERSION_OFFSET_X,
                    AVERSION_OFFSET_Y,
                )
        else:
            self._stare_started_at = None

        return None

    def reset(self) -> None:
        self._stare_started_at = None
        self._aversion_until = None
