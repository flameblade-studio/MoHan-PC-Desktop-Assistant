from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.constants import (
    FULL_BODY_LAYER_COUNT,
    FULL_BODY_LAYER_Z_ORDER,
    SHYNESS_BLUSH_WEIGHT,
    SHYNESS_GAZE_WEIGHT,
    SHYNESS_LIP_WEIGHT,
)
lazy from domain.face_motion import (
    interpolate_frame,
    shyness_expression,
    shyness_mouth,
)
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)

FLOAT_EPSILON = 1e-6


def _frame(
    *,
    aperture: float = 0.0,
    blush: float = 0.0,
    blink: float = 0.0,
) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(aperture=aperture),
        ExpressionShape(blush=blush, blink=blink),
    )


def test_interpolate_frame_midpoint_halves_continuous_controls() -> None:
    start = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(aperture=0.0),
        ExpressionShape(blush=0.0),
        gaze_x=-0.5,
        gaze_y=0.0,
        breath=0.2,
    )
    end = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(aperture=0.9),
        ExpressionShape(blush=0.6),
        gaze_x=0.5,
        gaze_y=0.5,
        breath=0.8,
    )
    mid = interpolate_frame(start, end, 0.5)
    assert abs(mid.mouth.aperture - 0.45) < FLOAT_EPSILON
    assert abs(mid.expression_shape.blush - 0.3) < FLOAT_EPSILON
    assert abs(mid.gaze_x - 0.0) < FLOAT_EPSILON
    assert abs(mid.gaze_y - 0.25) < FLOAT_EPSILON
    assert abs(mid.breath - 0.5) < FLOAT_EPSILON


def test_interpolate_frame_endpoint_returns_end_labels() -> None:
    start = _frame()
    end = FaceMotionFrame(
        FacePose.LEAN,
        "idle_lean",
        Viseme.A,
        MouthShape(aperture=0.9),
        ExpressionShape(),
    )
    result = interpolate_frame(start, end, 1.0)
    assert result.pose is FacePose.LEAN
    assert result.viseme is Viseme.A
    assert abs(result.mouth.aperture - 0.9) < FLOAT_EPSILON


def test_shyness_cascade_weights_match_constants() -> None:
    expression = shyness_expression(1.0)
    mouth = shyness_mouth(1.0)
    assert abs(expression.blush - SHYNESS_BLUSH_WEIGHT) < FLOAT_EPSILON
    assert abs(expression.eye_smile - SHYNESS_GAZE_WEIGHT) < FLOAT_EPSILON
    assert abs(mouth.corner_smile - SHYNESS_LIP_WEIGHT) < FLOAT_EPSILON


def test_shyness_cascade_is_zero_at_neutral() -> None:
    expression = shyness_expression(0.0)
    mouth = shyness_mouth(0.0)
    assert expression.blush == 0.0
    assert expression.eye_smile == 0.0
    assert mouth.corner_smile == 0.0


def test_full_body_z_order_has_twenty_five_layers() -> None:
    assert len(FULL_BODY_LAYER_Z_ORDER) == FULL_BODY_LAYER_COUNT
    assert len(set(FULL_BODY_LAYER_Z_ORDER)) == FULL_BODY_LAYER_COUNT


def test_full_body_z_order_prevents_clothing_clipping() -> None:
    # Back hair must stay behind the face; front hair and sleeves must stay in
    # front of the torso so turning never clips clothing through the body.
    order = FULL_BODY_LAYER_Z_ORDER
    assert order.index("hair_back") < order.index("base")
    assert order.index("base") < order.index("hair_left")
    assert order.index("base") < order.index("hair_right")
    assert order.index("body") < order.index("sleeve_left")
    assert order.index("body") < order.index("sleeve_right")
    assert order.index("hair_right") < order.index("ornament")


def run() -> None:
    test_interpolate_frame_midpoint_halves_continuous_controls()
    test_interpolate_frame_endpoint_returns_end_labels()
    test_shyness_cascade_weights_match_constants()
    test_shyness_cascade_is_zero_at_neutral()
    test_full_body_z_order_has_twenty_five_layers()
    test_full_body_z_order_prevents_clothing_clipping()
    print("FACE_MOTION_INTERPOLATION_OK")


if __name__ == "__main__":
    run()
