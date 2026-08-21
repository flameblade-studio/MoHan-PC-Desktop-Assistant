from __future__ import annotations

"""Shyness level state machine (害羞程度狀態機).

The shyness micro-expression chain (blush → lowered gaze → pursed lips) needs a
continuous ``shyness_level`` in [0, 1]. This module derives that level from
three drivers so the blush/gaze/lip cascade reads as a real emotional state
rather than a binary on/off:

1. **Gaze** (凝視): the longer the user stares, the more flustered MoHan grows.
2. **Favor** (親密): a devoted companion is more sensitive to being watched, so
   the same stare produces a stronger shyness response.
3. **Context** (情境): an explicit shy expression (``shy`` / ``shy_cute_front``)
   raises the baseline shyness.

The level eases toward its target with a bounded lerp so it never snaps, and it
decays back to zero when the drivers relax. This is pure domain logic with no
Qt dependency.
"""

# How strongly each driver contributes to the shyness target.
GAZE_WEIGHT = 0.5
FAVOR_WEIGHT = 0.3
CONTEXT_WEIGHT = 0.2

# The gaze-confidence floor above which the user is considered to be looking.
GAZE_CONFIDENCE_THRESHOLD = 0.35

# How quickly the level eases toward its target (per update).
EASE_RESPONSE = 0.18

# Expressions that signal an explicit shy context.
SHY_EXPRESSIONS = frozenset({"shy", "shy_cute_front", "shy_front"})


class ShynessState:
    """Derive a continuous shyness level from gaze, favor, and context."""

    def __init__(self) -> None:
        self._level = 0.0

    @property
    def level(self) -> float:
        return self._level

    def update(
        self,
        *,
        gaze_confidence: float,
        favor: float,
        expression: str,
    ) -> float:
        """Advance the level toward its target and return the new level.

        ``gaze_confidence`` is in [0, 1]; ``favor`` is in [0, 1]; ``expression``
        is the current expression name. The target is a weighted blend of the
        three drivers, then the level eases toward it with a bounded lerp.
        """
        looking = max(0.0, min(1.0, float(gaze_confidence)))
        gaze_component = (
            looking if looking >= GAZE_CONFIDENCE_THRESHOLD else 0.0
        )
        favor_component = max(0.0, min(1.0, float(favor)))
        context_component = 1.0 if expression in SHY_EXPRESSIONS else 0.0

        target = (
            GAZE_WEIGHT * gaze_component
            + FAVOR_WEIGHT * favor_component
            + CONTEXT_WEIGHT * context_component
        )
        target = max(0.0, min(1.0, target))
        self._level += (target - self._level) * EASE_RESPONSE
        self._level = max(0.0, min(1.0, self._level))
        return self._level
