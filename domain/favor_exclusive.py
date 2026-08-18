from __future__ import annotations

"""Exclusive favor (主上專屬寵溺), the hidden weighting field.

This is the finishing touch.  The higher this hidden coefficient, the more
tolerant MoHan is of disturbances (being ignored, other AI services) and the
sweeter her response to the user's cross-dimensional gestures.  It is a slow,
bounded value that grows with genuine closeness and never resets on a whim.

This is pure domain logic with no Qt dependency.
"""

lazy import math
lazy import time

# Favor grows by this much per warm gesture (a fed treat, a high-five).
FAVOR_GROWTH_PER_GESTURE = 0.01

# Favor decays with this half-life (seconds) — about one month, so it is a
# long-term bond, not a transient mood.
FAVOR_DECAY_HALF_LIFE_SECONDS = 30.0 * 24.0 * 60.0 * 60.0

# Above this threshold the companion is "devoted" and highly tolerant.
FAVOR_DEVOTED_THRESHOLD = 0.7


class FavorExclusiveState:
    """Track the hidden exclusive-favor coefficient in [0, 1]."""

    def __init__(
        self,
        *,
        clock: object | None = None,
        favor: float = 0.0,
    ) -> None:
        if not 0.0 <= favor <= 1.0:
            raise ValueError("Favor must be within 0..1.")
        self._clock = clock or time.monotonic
        self._favor = float(favor)
        self._last_update_at = self._clock()

    @property
    def favor(self) -> float:
        return self._favor

    @property
    def is_devoted(self) -> bool:
        return self._favor >= FAVOR_DEVOTED_THRESHOLD

    def note_gesture(self, now: float | None = None) -> float:
        """Record a warm gesture, growing favor (bounded at 1.0)."""
        current = self._clock() if now is None else float(now)
        self._decay(current)
        self._favor = min(1.0, self._favor + FAVOR_GROWTH_PER_GESTURE)
        self._last_update_at = current
        return self._favor

    def snapshot(self, now: float | None = None) -> float:
        """Return the current favor after applying decay."""
        current = self._clock() if now is None else float(now)
        self._decay(current)
        return self._favor

    def tolerance(self, now: float | None = None) -> float:
        """The disturbance tolerance derived from favor (0 = none, 1 = full)."""
        return self.snapshot(now)

    def _decay(self, now: float) -> None:
        elapsed = max(0.0, now - self._last_update_at)
        if FAVOR_DECAY_HALF_LIFE_SECONDS <= 0.0:
            return
        self._favor *= math.exp(
            -math.log(2.0) * elapsed / FAVOR_DECAY_HALF_LIFE_SECONDS
        )
        self._last_update_at = now
