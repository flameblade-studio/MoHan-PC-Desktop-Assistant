from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum


class ObservableFacialCue(StrEnum):
    SMILE_LIKE = "smile-like"
    EYES_CLOSED_LIKE = "eyes-closed-like"
    BROW_TENSION_LIKE = "brow-tension-like"
    FATIGUE_CANDIDATE = "fatigue-candidate"
    UNKNOWN = "unknown"


class GazeHeadDirection(StrEnum):
    SCREEN_LIKE = "screen-like"
    AWAY = "away"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FacialCueMeasurements:
    """Normalized, observable measurements; never a claim about emotion."""

    smile_like: float | None = None
    eyes_closed_like: float | None = None
    brow_tension_like: float | None = None
    fatigue_candidate: float | None = None
    screen_alignment: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("smile_like", self.smile_like),
            ("eyes_closed_like", self.eyes_closed_like),
            ("brow_tension_like", self.brow_tension_like),
            ("fatigue_candidate", self.fatigue_candidate),
            ("screen_alignment", self.screen_alignment),
        ):
            if value is not None and (
                not math.isfinite(value) or not 0.0 <= value <= 1.0
            ):
                raise ValueError(f"{name} must be finite and normalized.")


@dataclass(frozen=True, slots=True)
class VisualSocialCueObservation:
    facial_cues: tuple[ObservableFacialCue, ...]
    gaze_head_direction: GazeHeadDirection
    confidence: float
    uncertainty: float

    def __post_init__(self) -> None:
        if not self.facial_cues:
            raise ValueError("At least one observable facial cue is required.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be normalized.")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("Uncertainty must be normalized.")


def observe_social_cues(
    measurements: FacialCueMeasurements,
    *,
    cue_threshold: float = 0.68,
    direction_threshold: float = 0.65,
) -> VisualSocialCueObservation:
    """Describe visible candidates conservatively without inferring feelings."""

    _validate_threshold(cue_threshold, "cue_threshold")
    _validate_threshold(direction_threshold, "direction_threshold")
    candidates = (
        (ObservableFacialCue.SMILE_LIKE, measurements.smile_like),
        (ObservableFacialCue.EYES_CLOSED_LIKE, measurements.eyes_closed_like),
        (ObservableFacialCue.BROW_TENSION_LIKE, measurements.brow_tension_like),
        (ObservableFacialCue.FATIGUE_CANDIDATE, measurements.fatigue_candidate),
    )
    cues = tuple(cue for cue, score in candidates if score is not None and score >= cue_threshold)
    known_scores = tuple(score for _, score in candidates if score is not None)
    if not cues:
        cues = (ObservableFacialCue.UNKNOWN,)

    alignment = measurements.screen_alignment
    if alignment is None:
        direction = GazeHeadDirection.UNKNOWN
    elif alignment >= direction_threshold:
        direction = GazeHeadDirection.SCREEN_LIKE
    elif alignment <= 1.0 - direction_threshold:
        direction = GazeHeadDirection.AWAY
    else:
        direction = GazeHeadDirection.UNKNOWN

    evidence = (*known_scores, *((alignment,) if alignment is not None else ()))
    confidence = max(evidence, default=0.0)
    if cues == (ObservableFacialCue.UNKNOWN,) and direction is GazeHeadDirection.UNKNOWN:
        confidence = min(confidence, 0.49)
    return VisualSocialCueObservation(
        cues,
        direction,
        confidence,
        1.0 - confidence,
    )


def _validate_threshold(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.5 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and between 0.5 and 1.0.")
