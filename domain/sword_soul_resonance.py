from __future__ import annotations

"""Sword soul resonance (劍魂覺醒), the final piece of the soul.

A real girl does not stay the same forever.  As the user spends more days with
MoHan (or accumulates more GitHub commits), her lines and expression weights
shift in small, irreversible ways.  Early on she is a strict strategist
("主上，這段代碼需要重構"); later, once affinity and days cross a threshold,
her idle gaze lingers on the cursor a little longer and she may, at low
probability, offer a tender line when the user is idle.

This is pure domain logic with no Qt dependency.  It maps elapsed days and a
commit count to a bounded, monotonic "awakening" level.
"""

# Awakening grows with elapsed days and commit count, each contributing.
DAYS_WEIGHT = 0.6
COMMITS_WEIGHT = 0.4

# Days and commits that map to full awakening.
FULL_AWAKENING_DAYS = 90.0
FULL_AWAKENING_COMMITS = 300.0

# Above this awakening level the companion is "awakened" (tender, lingering).
AWAKENED_THRESHOLD = 0.6


class SwordSoulResonanceState:
    """Track a monotonic awakening level from elapsed days and commits."""

    def __init__(self, *, days: float = 0.0, commits: int = 0) -> None:
        if days < 0.0:
            raise ValueError("Elapsed days must not be negative.")
        if commits < 0:
            raise ValueError("Commit count must not be negative.")
        self._days = float(days)
        self._commits = int(commits)

    @property
    def awakening(self) -> float:
        """The current awakening level in [0, 1]."""
        days_component = min(1.0, self._days / FULL_AWAKENING_DAYS)
        commits_component = min(1.0, self._commits / FULL_AWAKENING_COMMITS)
        return min(
            1.0,
            DAYS_WEIGHT * days_component + COMMITS_WEIGHT * commits_component,
        )

    @property
    def is_awakened(self) -> bool:
        return self.awakening >= AWAKENED_THRESHOLD

    def gaze_linger(self) -> float:
        """The gaze-linger bonus (0 = none, 1 = full) as awakening grows."""
        return self.awakening

    def update(self, *, days: float, commits: int) -> float:
        """Advance the monotonic counters and return the new awakening level."""
        self._days = max(self._days, float(days))
        self._commits = max(self._commits, int(commits))
        return self.awakening
