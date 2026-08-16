from __future__ import annotations

lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum


class FacePose(StrEnum):
    CHEEK = "cheek"
    LEAN = "lean"
    FRONT = "front"


class Viseme(StrEnum):
    CLOSED = "CLOSED"
    CONSONANT = "CONSONANT"
    A = "A"
    I = "I"
    U = "U"
    E = "E"
    O = "O"


@dataclass(frozen=True, slots=True)
class MouthShape:
    """Continuous, renderer-independent articulation controls."""

    aperture: float = 0.0
    width: float = 0.5
    rounding: float = 0.0
    jaw: float = 0.0
    corner_smile: float = 0.0

    def clamped(self) -> MouthShape:
        return replace(
            self,
            aperture=_unit(self.aperture),
            width=_unit(self.width),
            rounding=_unit(self.rounding),
            jaw=_unit(self.jaw),
            corner_smile=_signed_unit(self.corner_smile),
        )


@dataclass(frozen=True, slots=True)
class ExpressionShape:
    """Facial expression controls that remain independent of articulation."""

    blink: float = 0.0
    eye_smile: float = 0.0
    brow_lift: float = 0.0
    brow_tension: float = 0.0
    blush: float = 0.0

    def clamped(self) -> ExpressionShape:
        return replace(
            self,
            blink=_unit(self.blink),
            eye_smile=_unit(self.eye_smile),
            brow_lift=_signed_unit(self.brow_lift),
            brow_tension=_unit(self.brow_tension),
            blush=_unit(self.blush),
        )


@dataclass(frozen=True, slots=True)
class FaceMotionFrame:
    """One complete 2.5D face state consumed by every renderer."""

    pose: FacePose
    expression: str
    viseme: Viseme
    mouth: MouthShape
    expression_shape: ExpressionShape

    def clamped(self) -> FaceMotionFrame:
        return replace(
            self,
            mouth=self.mouth.clamped(),
            expression_shape=self.expression_shape.clamped(),
        )


def parse_pose(value: str) -> FacePose:
    try:
        return FacePose(str(value))
    except ValueError:
        return FacePose.FRONT


def parse_viseme(value: str) -> Viseme:
    try:
        return Viseme(str(value).upper())
    except ValueError:
        return Viseme.E


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _signed_unit(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))
