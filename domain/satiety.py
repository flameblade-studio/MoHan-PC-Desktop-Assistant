from __future__ import annotations

"""Military ration satiety (軍糧飽食度), inspired by "A・I ga Tomaranai!".

MoHan also needs to "eat".  The user can send her a ration (送軍糧), which
raises her satiety.  When satiety runs low, her Live 2.5D motion grows sluggish
— she is too hungry to blink energetically — and her speech turns listless.
This ties the Ko-fi sponsorship gesture to the character's vitality.

This module is pure domain logic with no Qt dependency.  Satiety decays slowly
over time and rises with each ration, always bounded within [0, 1].
"""

lazy import math
lazy import time

# Satiety rises by this much per ration.
SATIETY_GAIN_PER_RATION = 0.25

# Satiety decays with this half-life (seconds) — about one day.
SATIETY_DECAY_HALF_LIFE_SECONDS = 24.0 * 60.0 * 60.0

# Below this threshold the companion is visibly hungry (sluggish motion).
SATIETY_HUNGRY_THRESHOLD = 0.3

# Blink interval (seconds) at full satiety and when starving.
BLINK_INTERVAL_FULL = 4.0
BLINK_INTERVAL_STARVING = 7.5


class SatietyState:
    """Track the companion's slowly-decaying satiety level."""

    def __init__(
        self,
        *,
        clock: object | None = None,
        satiety: float = 1.0,
    ) -> None:
        if not 0.0 <= satiety <= 1.0:
            raise ValueError("Satiety must be within 0..1.")
        self._clock = clock or time.monotonic
        self._satiety = float(satiety)
        self._last_update_at = self._clock()

    @property
    def satiety(self) -> float:
        return self._satiety

    @property
    def is_hungry(self) -> bool:
        return self._satiety < SATIETY_HUNGRY_THRESHOLD

    def feed(self, now: float | None = None) -> float:
        """Feed one ration, raising satiety (bounded at 1.0)."""
        current = self._clock() if now is None else float(now)
        self._decay(current)
        self._satiety = min(1.0, self._satiety + SATIETY_GAIN_PER_RATION)
        self._last_update_at = current
        return self._satiety

    def snapshot(self, now: float | None = None) -> float:
        """Return the current satiety after applying decay."""
        current = self._clock() if now is None else float(now)
        self._decay(current)
        return self._satiety

    def blink_interval(self, now: float | None = None) -> float:
        """The blink interval (seconds) for the current satiety."""
        level = self.snapshot(now)
        return BLINK_INTERVAL_FULL + (
            BLINK_INTERVAL_STARVING - BLINK_INTERVAL_FULL
        ) * (1.0 - level)

    def _decay(self, now: float) -> None:
        elapsed = max(0.0, now - self._last_update_at)
        if SATIETY_DECAY_HALF_LIFE_SECONDS <= 0.0:
            return
        self._satiety *= math.exp(
            -math.log(2.0) * elapsed / SATIETY_DECAY_HALF_LIFE_SECONDS
        )
        self._last_update_at = now
