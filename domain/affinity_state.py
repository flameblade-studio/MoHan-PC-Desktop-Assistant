from __future__ import annotations

"""Companion growth arc and jealousy, inspired by "A・I ga Tomaranai!".

The manga's heroine grows from a cold program into a girl who learns affection,
jealousy, and devotion.  This module tracks two slow-changing dimensions so
MoHan can do the same:

- ``affinity``: how close the companion has grown to the user over time.  It
  rises with interaction and decays very slowly, so a long relationship feels
  warmer than a first meeting.
- ``jealousy``: a short-lived spike when the user mentions another assistant or
  ignores the companion for a long stretch.  It fades quickly so it reads as a
  playful, restrained sulk rather than possessiveness.

Both are pure domain logic with no Qt or speech-provider dependency.
"""

lazy import math
lazy import time
lazy from dataclasses import dataclass

# Affinity grows toward 1.0 with each interaction and decays very slowly, so a
# long relationship stays warm across sessions.
AFFINITY_GROWTH_PER_INTERACTION = 0.02
AFFECTION_BOOST_PER_GESTURE = 0.15
AFFINITY_DECAY_HALF_LIFE_SECONDS = 7.0 * 24.0 * 60.0 * 60.0  # one week

# Jealousy spikes and fades slowly so it reads as a lingering, restrained sulk
# rather than a flash that vanishes in a second.  A tsundere's pout should hold
# for several minutes, not evaporate the moment the user looks away.
JEALOUSY_SPIKE = 0.7
JEALOUSY_DECAY_HALF_LIFE_SECONDS = 600.0  # ten minutes

# Affinity thresholds that change the companion's tone.
AFFINITY_STRANGER = 0.0
AFFINITY_ACQUAINTED = 0.25
AFFINITY_CLOSE = 0.55
AFFINITY_DEVOTED = 0.8


@dataclass(frozen=True, slots=True)
class AffinitySnapshot:
    affinity: float
    jealousy: float
    interaction_count: int

    @property
    def stage(self) -> str:
        if self.affinity >= AFFINITY_DEVOTED:
            return "devoted"
        if self.affinity >= AFFINITY_CLOSE:
            return "close"
        if self.affinity >= AFFINITY_ACQUAINTED:
            return "acquainted"
        return "stranger"


class AffinityState:
    """Track the companion's slow-growing closeness and short-lived jealousy."""

    def __init__(
        self,
        *,
        clock: object | None = None,
        affinity: float = 0.0,
        jealousy: float = 0.0,
        interaction_count: int = 0,
    ) -> None:
        if not 0.0 <= affinity <= 1.0:
            raise ValueError("Affinity must be within 0..1.")
        if not 0.0 <= jealousy <= 1.0:
            raise ValueError("Jealousy must be within 0..1.")
        if interaction_count < 0:
            raise ValueError("Interaction count must not be negative.")
        self._clock = clock or time.monotonic
        self._affinity = float(affinity)
        self._jealousy = float(jealousy)
        self._interaction_count = int(interaction_count)
        self._last_interaction_at = self._clock()
        self._jealousy_at = self._clock()

    @property
    def affinity(self) -> float:
        return self._affinity

    @property
    def jealousy(self) -> float:
        return self._jealousy

    @property
    def interaction_count(self) -> int:
        return self._interaction_count

    def note_interaction(self, now: float | None = None) -> AffinitySnapshot:
        """Record one user interaction, growing affinity and decaying jealousy."""
        current = self._clock() if now is None else float(now)
        self._decay_affinity(current)
        self._affinity = min(
            1.0,
            self._affinity + AFFINITY_GROWTH_PER_INTERACTION,
        )
        self._interaction_count += 1
        self._last_interaction_at = current
        self._decay_jealousy(current)
        return self.snapshot(current)

    def note_jealousy(self, now: float | None = None) -> AffinitySnapshot:
        """Spike jealousy when the user mentions another assistant."""
        current = self._clock() if now is None else float(now)
        self._decay_jealousy(current)
        self._jealousy = min(1.0, self._jealousy + JEALOUSY_SPIKE)
        self._jealousy_at = current
        return self.snapshot(current)

    def note_affection_boost(self, now: float | None = None) -> AffinitySnapshot:
        """A larger affinity jump for a warm gesture (a fed treat, a high-five).

        This is a deliberate, bounded boost — bigger than a routine interaction
        but still capped at 1.0 — so a playful cross-dimensional gesture reads
        as a real moment of closeness rather than a routine tick.
        """
        current = self._clock() if now is None else float(now)
        self._decay_affinity(current)
        self._affinity = min(
            1.0,
            self._affinity + AFFECTION_BOOST_PER_GESTURE,
        )
        self._interaction_count += 1
        self._last_interaction_at = current
        self._decay_jealousy(current)
        return self.snapshot(current)

    def snapshot(self, now: float | None = None) -> AffinitySnapshot:
        current = self._clock() if now is None else float(now)
        self._decay_affinity(current)
        self._decay_jealousy(current)
        return AffinitySnapshot(
            self._affinity,
            self._jealousy,
            self._interaction_count,
        )

    def _decay_affinity(self, now: float) -> None:
        elapsed = max(0.0, now - self._last_interaction_at)
        if AFFINITY_DECAY_HALF_LIFE_SECONDS <= 0.0:
            return
        self._affinity *= math.exp(
            -math.log(2.0) * elapsed / AFFINITY_DECAY_HALF_LIFE_SECONDS
        )
        # Advance the anchor after applying decay.  Without this, every
        # snapshot() re-applies the full since-last-interaction factor and the
        # decay compounds with each read (a per-frame policy read emptied a
        # one-week half-life in minutes).  Mirrors satiety._decay.
        self._last_interaction_at = now

    def _decay_jealousy(self, now: float) -> None:
        elapsed = max(0.0, now - self._jealousy_at)
        if JEALOUSY_DECAY_HALF_LIFE_SECONDS <= 0.0:
            return
        self._jealousy *= math.exp(
            -math.log(2.0) * elapsed / JEALOUSY_DECAY_HALF_LIFE_SECONDS
        )
        self._jealousy_at = now
