from __future__ import annotations

lazy from dataclasses import dataclass, replace

lazy from domain.constants import (
    FLOAT_COMPARISON_EPSILON,
    SHYNESS_BLUSH_WEIGHT,
    SHYNESS_GAZE_WEIGHT,
    SHYNESS_LIP_WEIGHT,
)
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    MouthShape,
    Viseme,
    blink_for_eye_state,
    eye_state_for_blink,
    parse_pose,
    parse_viseme,
)
lazy from domain.lip_sync import VisemeFrame

VISEME_MOUTH_TARGETS = frozendict(
    {
        Viseme.CLOSED: MouthShape(0.0, 0.48, 0.0, 0.0),
        Viseme.CONSONANT: MouthShape(0.12, 0.55, 0.04, 0.08),
        Viseme.A: MouthShape(0.92, 0.78, 0.08, 1.0),
        Viseme.I: MouthShape(0.42, 1.0, 0.0, 0.45),
        Viseme.U: MouthShape(0.46, 0.38, 1.0, 0.52, u_inward=1.0),
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
            u_inward=_approach(
                previous.mouth.u_inward,
                target.u_inward,
                self.shape_response,
            ),
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


def shyness_expression(shyness_level: float) -> ExpressionShape:
    """Map a shyness level onto a cascading micro-expression.

    The cascade is ordered so the most subtle cue appears first and the most
    deliberate cue last, mirroring how a real person blushes before lowering
    their gaze and finally pursing their lips:

    1. blush rises first (``SHYNESS_BLUSH_WEIGHT``),
    2. then the gaze lowers (``SHYNESS_GAZE_WEIGHT``),
    3. then the lips purse (``SHYNESS_LIP_WEIGHT``).

    ``shyness_level`` is clamped to ``[0, 1]``.
    """

    level = max(0.0, min(1.0, float(shyness_level)))
    return ExpressionShape(
        blink=0.0,
        eye_smile=level * SHYNESS_GAZE_WEIGHT,
        brow_lift=0.0,
        brow_tension=0.0,
        blush=level * SHYNESS_BLUSH_WEIGHT,
    )


def shyness_mouth(shyness_level: float) -> MouthShape:
    """Return the lip-purse component of the shyness cascade."""

    level = max(0.0, min(1.0, float(shyness_level)))
    return MouthShape(
        aperture=0.0,
        width=0.5,
        rounding=0.0,
        jaw=0.0,
        corner_smile=level * SHYNESS_LIP_WEIGHT,
        u_inward=0.0,
    )


def blend_shyness(
    frame: FaceMotionFrame,
    shyness_level: float,
) -> FaceMotionFrame:
    """Blend the shyness cascade into an existing face frame.

    The shyness micro-expression (blush → lowered gaze → pursed lips) is mixed
    with the frame's existing expression by ``shyness_level`` so the companion's
    current emotion never vanishes — she grows shy *on top of* whatever she was
    already feeling. At ``shyness_level == 0`` the frame is returned unchanged;
    at ``1`` the shyness cascade fully dominates the blush/gaze/lip controls.
    """

    level = max(0.0, min(1.0, float(shyness_level)))
    if level < FLOAT_COMPARISON_EPSILON:
        return frame
    shy_expression = shyness_expression(level)
    shy_mouth = shyness_mouth(level)
    existing = frame.expression_shape
    existing_mouth = frame.mouth
    blended_expression = ExpressionShape(
        blink=existing.blink,
        eye_smile=_lerp(existing.eye_smile, shy_expression.eye_smile, level),
        brow_lift=existing.brow_lift,
        brow_tension=existing.brow_tension,
        blush=_lerp(existing.blush, shy_expression.blush, level),
    )
    blended_mouth = MouthShape(
        aperture=existing_mouth.aperture,
        width=existing_mouth.width,
        rounding=existing_mouth.rounding,
        jaw=existing_mouth.jaw,
        corner_smile=_lerp(
            existing_mouth.corner_smile,
            shy_mouth.corner_smile,
            level,
        ),
        u_inward=existing_mouth.u_inward,
    )
    return replace(
        frame,
        mouth=blended_mouth,
        expression_shape=blended_expression,
    ).clamped()


def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between two scalar controls."""
    bounded = max(0.0, min(1.0, float(t)))
    return start + (end - start) * bounded


def interpolate_frame(
    start: FaceMotionFrame,
    end: FaceMotionFrame,
    t: float,
) -> FaceMotionFrame:
    """Interpolate one face state between two 50 Hz frames.

    The speech clock emits a new :class:`FaceMotionFrame` every 20 ms. Instead
    of snapping the renderer to each discrete frame (a "cut"), the renderer can
    call this with ``t`` in ``[0, 1]`` to produce a sub-frame blend so every
    deformation lands precisely within the 20 ms window. Pose, expression and
    viseme are taken from ``end`` (they are discrete labels, not continuous
    controls); the continuous mouth and expression shapes are lerped. Blink is
    the deliberate exception: it selects a complete authority state only at
    the next 20 ms frame boundary, preventing open and closed eyes from being
    visible in the same alpha-blended frame.
    """

    mouth = MouthShape(
        aperture=_lerp(start.mouth.aperture, end.mouth.aperture, t),
        width=_lerp(start.mouth.width, end.mouth.width, t),
        rounding=_lerp(start.mouth.rounding, end.mouth.rounding, t),
        jaw=_lerp(start.mouth.jaw, end.mouth.jaw, t),
        corner_smile=_lerp(start.mouth.corner_smile, end.mouth.corner_smile, t),
        u_inward=_lerp(start.mouth.u_inward, end.mouth.u_inward, t),
    )
    bounded_t = max(0.0, min(1.0, float(t)))
    blink_source = (
        start.expression_shape.blink
        if bounded_t < 1.0
        else end.expression_shape.blink
    )
    expression_shape = ExpressionShape(
        blink=blink_for_eye_state(eye_state_for_blink(blink_source)),
        eye_smile=_lerp(
            start.expression_shape.eye_smile,
            end.expression_shape.eye_smile,
            t,
        ),
        brow_lift=_lerp(
            start.expression_shape.brow_lift,
            end.expression_shape.brow_lift,
            t,
        ),
        brow_tension=_lerp(
            start.expression_shape.brow_tension,
            end.expression_shape.brow_tension,
            t,
        ),
        blush=_lerp(start.expression_shape.blush, end.expression_shape.blush, t),
    )
    return FaceMotionFrame(
        pose=end.pose,
        expression=end.expression,
        viseme=end.viseme,
        mouth=mouth,
        expression_shape=expression_shape,
        gaze_x=_lerp(start.gaze_x, end.gaze_x, t),
        gaze_y=_lerp(start.gaze_y, end.gaze_y, t),
        breath=_lerp(start.breath, end.breath, t),
    ).clamped()
