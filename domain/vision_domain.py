from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.constants import FLOAT_COMPARISON_EPSILON


class IdentityState(StrEnum):
    NO_FACE = "no_face"
    UNKNOWN = "unknown"
    RECOGNIZED = "recognized"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)


@dataclass(frozen=True, slots=True)
class ObjectDetection:
    label: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True, slots=True)
class IdentityObservation:
    state: IdentityState
    profile_id: str = ""
    display_name: str = ""
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class SceneUnderstanding:
    identity: IdentityObservation
    objects: tuple[ObjectDetection, ...]
    activities: tuple[str, ...]
    uncertainty: tuple[str, ...]


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    if not all(math.isfinite(value) for value in (*left, *right)):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm < FLOAT_COMPARISON_EPSILON or right_norm < FLOAT_COMPARISON_EPSILON:
        return 0.0
    return numerator / (left_norm * right_norm)
