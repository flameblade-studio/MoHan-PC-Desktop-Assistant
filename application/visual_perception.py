from __future__ import annotations

lazy import time
lazy from collections.abc import Sequence
lazy from dataclasses import dataclass
lazy from enum import StrEnum


class PresenceState(StrEnum):
    UNKNOWN = "unknown"
    AWAY = "away"
    PRESENT = "present"


class LightingState(StrEnum):
    DARK = "dark"
    DIM = "dim"
    COMFORTABLE = "comfortable"
    BRIGHT = "bright"


class ActivityState(StrEnum):
    STILL = "still"
    ACTIVE = "active"


DARK_THRESHOLD = 8.0
DIM_THRESHOLD = 42.0
COMFORTABLE_THRESHOLD = 205.0


@dataclass(frozen=True, slots=True)
class VisualObservation:
    """Non-identifying measurements derived from one local camera sample."""

    observed_at: float
    presence: PresenceState
    lighting: LightingState
    activity: ActivityState
    brightness: float
    motion: float


class LocalVisualAnalyzer:
    """Turn tiny grayscale samples into coarse, ephemeral observations.

    The analyzer receives numbers rather than images so storage, networking,
    identity recognition, and UI concerns remain outside this pure core.
    """

    def __init__(
        self,
        *,
        motion_threshold: float = 5.5,
        presence_hold_seconds: float = 45.0,
        clock=time.monotonic,
    ) -> None:
        self._motion_threshold = max(0.1, float(motion_threshold))
        self._presence_hold_seconds = max(1.0, float(presence_hold_seconds))
        self._clock = clock
        self._previous: tuple[int, ...] | None = None
        self._last_motion: float | None = None

    @staticmethod
    def lighting_for(brightness: float) -> LightingState:
        if brightness < DARK_THRESHOLD:
            return LightingState.DARK
        if brightness < DIM_THRESHOLD:
            return LightingState.DIM
        if brightness < COMFORTABLE_THRESHOLD:
            return LightingState.COMFORTABLE
        return LightingState.BRIGHT

    def analyze(
        self,
        sample: Sequence[int],
        *,
        observed_at: float | None = None,
    ) -> VisualObservation:
        if not sample:
            raise ValueError("camera sample must not be empty")
        normalized = tuple(max(0, min(255, int(value))) for value in sample)
        now = self._clock() if observed_at is None else float(observed_at)
        brightness = sum(normalized) / len(normalized)
        motion = self._motion(normalized)
        lighting = self.lighting_for(brightness)
        meaningful_motion = (
            motion >= self._motion_threshold and lighting is not LightingState.DARK
        )
        if meaningful_motion:
            self._last_motion = now
        present = (
            self._last_motion is not None
            and lighting is not LightingState.DARK
            and now - self._last_motion <= self._presence_hold_seconds
        )
        self._previous = normalized
        return VisualObservation(
            observed_at=now,
            presence=PresenceState.PRESENT if present else PresenceState.AWAY,
            lighting=lighting,
            activity=(
                ActivityState.ACTIVE if meaningful_motion else ActivityState.STILL
            ),
            brightness=brightness,
            motion=motion,
        )

    def reset(self) -> None:
        self._previous = None
        self._last_motion = None

    def _motion(self, sample: tuple[int, ...]) -> float:
        if self._previous is None or len(self._previous) != len(sample):
            return 0.0
        return sum(
            abs(current - previous)
            for current, previous in zip(sample, self._previous, strict=True)
        ) / len(sample)
