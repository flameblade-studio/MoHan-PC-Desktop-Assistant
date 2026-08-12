from __future__ import annotations

lazy from dataclasses import dataclass, replace

lazy from face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    MouthShape,
    Viseme,
    parse_pose,
    parse_viseme,
)
lazy from lip_sync import VisemeFrame

VISEME_MOUTH_TARGETS = frozendict(
    {
        Viseme.CLOSED: MouthShape(0.0, 0.48, 0.0, 0.0),
        Viseme.CONSONANT: MouthShape(0.12, 0.55, 0.04, 0.08),
        Viseme.A: MouthShape(0.92, 0.78, 0.08, 1.0),
        Viseme.I: MouthShape(0.42, 1.0, 0.0, 0.45),
        Viseme.U: MouthShape(0.46, 0.38, 1.0, 0.52),
        Viseme.E: MouthShape(0.50, 0.88, 0.05, 0.50),
        Viseme.O: MouthShape(0.78, 0.48, 0.90, 0.92),
    }
)

HAPPY_EXPRESSIONS = frozenset(
    {
        "happy",
        "gentle_smile_front",
        "proud_front",
        "relieved_front",
        "restrained_amused_front",
    }
)
BLUSH_EXPRESSIONS = frozenset({"shy_front", "shy_cute_front"})
LIFTED_BROW_EXPRESSIONS = frozenset(
    {"surprised_front", "eureka_front", "attentive_front"}
)
TENSE_BROW_EXPRESSIONS = frozenset(
    {
        "determined_front",
        "worried",
        "worried_front",
        "exasperated_front",
        "mock_scold",
        "mock_hit_front",
        "protective_front",
    }
)


@dataclass(slots=True)
class FaceMotionController:
    """Turn 50 Hz speech and expression state into continuous face controls."""

    current: FaceMotionFrame | None = None
    attack: float = 0.58
    release: float = 0.34
    shape_response: float = 0.52

    def reset(self, pose: str = "front", expression: str = "idle_front") -> None:
        self.current = self.neutral(pose, expression)

    @staticmethod
    def neutral(pose: str, expression: str) -> FaceMotionFrame:
        return FaceMotionFrame(
            pose=parse_pose(pose),
            expression=str(expression),
            viseme=Viseme.CLOSED,
            mouth=MouthShape(),
            expression_shape=_expression_target(expression),
        )

    def advance(
        self,
        viseme_frame: VisemeFrame,
        *,
        pose: str,
        expression: str,
        blink: float = 0.0,
    ) -> FaceMotionFrame:
        viseme = parse_viseme(viseme_frame.selected)
        target = VISEME_MOUTH_TARGETS[viseme]
        target = replace(
            target,
            aperture=max(target.aperture * 0.45, viseme_frame.jaw_aperture),
            jaw=max(target.jaw * viseme_frame.jaw_weight, viseme_frame.jaw_aperture),
            # Speech uses a neutral mouth. Smiling remains in the eyes and
            # returns to the corners only after the final CLOSED state.
            corner_smile=0.0,
        ).clamped()
        previous = self.current or self.neutral(pose, expression)
        aperture_response = (
            self.attack
            if target.aperture > previous.mouth.aperture
            else self.release
        )
        mouth = MouthShape(
            aperture=_approach(
                previous.mouth.aperture,
                target.aperture,
                aperture_response,
            ),
            width=_approach(
                previous.mouth.width,
                target.width,
                self.shape_response,
            ),
            rounding=_approach(
                previous.mouth.rounding,
                target.rounding,
                self.shape_response,
            ),
            jaw=_approach(
                previous.mouth.jaw,
                target.jaw,
                aperture_response,
            ),
            corner_smile=0.0,
        ).clamped()
        expression_shape = replace(
            _expression_target(expression),
            blink=blink,
        ).clamped()
        self.current = FaceMotionFrame(
            pose=parse_pose(pose),
            expression=str(expression),
            viseme=viseme,
            mouth=mouth,
            expression_shape=expression_shape,
        )
        return self.current

    def close(self, *, pose: str, expression: str) -> FaceMotionFrame:
        closed = self.neutral(pose, expression)
        expression_shape = _expression_target(expression)
        corner_smile = 0.62 if expression in HAPPY_EXPRESSIONS else 0.0
        self.current = replace(
            closed,
            mouth=replace(closed.mouth, corner_smile=corner_smile),
            expression_shape=expression_shape,
        ).clamped()
        return self.current


def _expression_target(expression: str) -> ExpressionShape:
    happy = expression in HAPPY_EXPRESSIONS
    return ExpressionShape(
        eye_smile=0.72 if happy else 0.0,
        brow_lift=0.58 if expression in LIFTED_BROW_EXPRESSIONS else 0.0,
        brow_tension=0.68 if expression in TENSE_BROW_EXPRESSIONS else 0.0,
        blush=0.82 if expression in BLUSH_EXPRESSIONS else 0.0,
    )


def _approach(current: float, target: float, response: float) -> float:
    bounded = max(0.0, min(1.0, float(response)))
    return current + (target - current) * bounded
