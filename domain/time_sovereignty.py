from __future__ import annotations

"""Time sovereignty (時間主權), inspired by "A・I ga Tomaranai!".

A real girl has her own rhythm.  When the user keeps coding deep into the
night, MoHan does not simply stay alert — she grows drowsy, her blinks lengthen,
and she quietly keeps the user company while fighting sleep.  This module
encodes that late-night drowsiness as pure domain logic with no Qt dependency.

The presentation layer samples it on its existing timer, so nothing here blocks
the Qt main thread.  The drowsiness level eases smoothly so the blink interval
lengthens gradually instead of snapping.

Key tuning, per the user's direction:

- The late-night window is 02:00–05:00 local time.
- Drowsiness eases in and out smoothly (exponential approach), never snapping.
- The blink interval lengthens within safe bounds so the companion looks sleepy,
  not broken.
"""

lazy import math
lazy import time

# The late-night window (local hour, inclusive start, exclusive end).
LATE_NIGHT_START_HOUR = 2
LATE_NIGHT_END_HOUR = 5

# Drowsiness eases toward its target with this per-second rate.
DROWSINESS_EASE_RATE = 0.05

# Blink interval (seconds) at rest and at full drowsiness.
BLINK_INTERVAL_ALERT = 4.0
BLINK_INTERVAL_DROWSY = 7.0


def is_late_night(hour: int) -> bool:
    """Return True when the local hour falls inside the late-night window."""
    return LATE_NIGHT_START_HOUR <= hour < LATE_NIGHT_END_HOUR


class TimeSovereigntyState:
    """Track a smooth drowsiness level from the current local hour."""

    def __init__(self, *, clock: object | None = None) -> None:
        self._clock = clock or time.monotonic
        self._drowsiness = 0.0
        self._last_update_at = self._clock()

    @property
    def drowsiness(self) -> float:
        """The current smoothed drowsiness level in [0, 1]."""
        return self._drowsiness

    def update(self, *, hour: int, now: float | None = None) -> float:
        """Advance drowsiness toward its target and return the new level."""
        current = self._clock() if now is None else float(now)
        elapsed = max(0.0, current - self._last_update_at)
        self._last_update_at = current

        target = 1.0 if is_late_night(hour) else 0.0
        alpha = 1.0 - math.exp(-DROWSINESS_EASE_RATE * elapsed)
        self._drowsiness += (target - self._drowsiness) * alpha
        return self._drowsiness

    def blink_interval(self) -> float:
        """The blink interval (seconds) for the current drowsiness."""
        return BLINK_INTERVAL_ALERT + (
            BLINK_INTERVAL_DROWSY - BLINK_INTERVAL_ALERT
        ) * self._drowsiness

    def reset(self) -> None:
        self._drowsiness = 0.0
        self._last_update_at = self._clock()
