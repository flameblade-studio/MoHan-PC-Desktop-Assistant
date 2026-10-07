from __future__ import annotations

"""Shared chronicle (共同創作錄), the historian of shared achievements.

A real girl remembers the milestones you reached together.  MoHan quietly
records the first time the tests all passed, the first merged PR, and other
shared achievements.  On anniversaries (e.g. the project's first month) she
surfaces a tender recollection of those moments — the strongest weapon for
building emotional bonds.

This is pure domain logic with Qt outside the domain boundary.  It stores a small, bounded
list of milestone records and produces a four-language recollection line.
"""

lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.character_pack.character_data import (
    canonical_character_locale,
    load_mohan_character_data,
)

_DIALOGUES = load_mohan_character_data().dialogues


class MilestoneKind(StrEnum):
    FIRST_TESTS_PASSED = "first_tests_passed"
    FIRST_PR_MERGED = "first_pr_merged"
    FIRST_RELEASE = "first_release"


@dataclass(frozen=True, slots=True)
class Milestone:
    kind: MilestoneKind
    day: int  # days since the project began

    def __post_init__(self) -> None:
        if self.day < 0:
            raise ValueError("Milestone day accepts zero or greater.")


class Chronicle:
    """Record and recall shared milestones in a bounded, ordered list."""

    def __init__(self, milestones: tuple[Milestone, ...] = ()) -> None:
        self._milestones = tuple(milestones)

    @property
    def milestones(self) -> tuple[Milestone, ...]:
        return self._milestones

    def record(self, kind: MilestoneKind, day: int) -> Chronicle:
        """Record a milestone, deduplicating by kind (first occurrence wins)."""
        if any(m.kind is kind for m in self._milestones):
            return self
        return Chronicle((*self._milestones, Milestone(kind, day)))

    def recollection(self, language: str, day: int) -> str:
        """Return a four-language recollection for the most recent milestone."""
        if not self._milestones:
            return ""
        latest = self._milestones[-1]
        locale = canonical_character_locale(language)
        key = f"chronicle.{latest.kind.value}"
        return _DIALOGUES[locale].templates[key]
