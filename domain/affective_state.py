from __future__ import annotations

"""Emotional continuity: a decaying affective residue between expressions.

A real person does not snap from one feeling to a neutral face the instant a
sentence ends.  A compliment leaves a lingering shyness, a worry leaves a
softened gaze, and joy fades gradually instead of vanishing.  This module
tracks the most recent expressive state and exposes an exponentially decaying
residue so the companion can ease back toward idle instead of jumping there.

The module is pure domain logic with no Qt or speech-provider dependency, so
it can be unit-tested deterministically and reused by any presentation owner.
"""

lazy import math
lazy import time
lazy from dataclasses import dataclass

# Each expressive state maps to the "softer" expression that should linger
# after the primary expression ends.  The residue is always a gentler variant
# so the companion never looks stuck on a strong emotion.
RESIDUAL_EXPRESSION = frozendict({
    "happy": "gentle_smile_front",
    "proud": "gentle_smile_front",
    "proud_front": "gentle_smile_front",
    "relieved": "gentle_smile_front",
    "relieved_front": "gentle_smile_front",
    "shy": "shy_cute_front",
    "shy_front": "shy_cute_front",
    "shy_cute_front": "shy_cute_front",
    "amused": "restrained_amused_front",
    "restrained_amused_front": "restrained_amused_front",
    "worried": "worried_front",
    "worried_front": "worried_front",
    "gentle": "gentle_smile_front",
    "gentle_smile_front": "gentle_smile_front",
    "surprised": "attentive_front",
    "surprised_front": "attentive_front",
    "eureka": "attentive_front",
    "eureka_front": "attentive_front",
    "thinking": "attentive_front",
    "thinking_front": "attentive_front",
    "attentive": "attentive_front",
    "attentive_front": "attentive_front",
    "caught": "shy_cute_front",
    "protective": "determined_front",
    "protective_front": "determined_front",
})

# How long (seconds) a residue remains visible before fully fading.  Stronger
# emotions linger longer; the decay is exponential so the tail is soft.
DEFAULT_RESIDUE_HALF_LIFE_SECONDS = 6.0
MINIMUM_RESIDUAL_STRENGTH = 0.12


@dataclass(frozen=True, slots=True)
class AffectiveResidue:
    """One decaying emotional afterglow."""

    expression: str
    strength: float
    half_life_seconds: float
    started_at: float

    def strength_at(self, now: float) -> float:
        elapsed = max(0.0, now - self.started_at)
        if self.half_life_seconds <= 0.0:
            return 0.0
        return self.strength * math.exp(
            -math.log(2.0) * elapsed / self.half_life_seconds
        )


class AffectiveState:
    """Track the most recent expressive state and expose its decaying residue."""

    def __init__(
        self,
        *,
        clock: object | None = None,
        half_life_seconds: float = DEFAULT_RESIDUE_HALF_LIFE_SECONDS,
    ) -> None:
        if not math.isfinite(half_life_seconds) or half_life_seconds <= 0.0:
            raise ValueError("Affective half-life must be a positive finite value.")
        self._clock = clock or time.monotonic
        self._half_life_seconds = half_life_seconds
        self._residue: AffectiveResidue | None = None

    @property
    def residue(self) -> AffectiveResidue | None:
        return self._residue

    def note_expression(
        self,
        expression: str,
        *,
        intensity: float = 0.5,
        now: float | None = None,
    ) -> None:
        """Record an expressive state so its afterglow can linger afterward."""
        residual = RESIDUAL_EXPRESSION.get(str(expression))
        if residual is None:
            return
        strength = max(0.0, min(1.0, float(intensity)))
        if strength < MINIMUM_RESIDUAL_STRENGTH:
            return
        self._residue = AffectiveResidue(
            residual,
            strength,
            self._half_life_seconds,
            self._clock() if now is None else float(now),
        )

    def residual_expression(self, now: float | None = None) -> str | None:
        """Return the lingering expression, or None once it has fully faded."""
        residue = self._residue
        if residue is None:
            return None
        current = self._clock() if now is None else float(now)
        if residue.strength_at(current) < MINIMUM_RESIDUAL_STRENGTH:
            self._residue = None
            return None
        return residue.expression

    def clear(self) -> None:
        self._residue = None
