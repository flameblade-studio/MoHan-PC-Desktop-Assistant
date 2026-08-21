from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.face_motion import blend_shyness
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from domain.shyness import ShynessState

FLOAT_EPSILON = 1e-6
SHYNESS_MIDPOINT = 0.5


def _frame(
    *,
    blush: float = 0.0,
    eye_smile: float = 0.0,
    corner_smile: float = 0.0,
) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(corner_smile=corner_smile),
        ExpressionShape(blush=blush, eye_smile=eye_smile),
    )


def test_shyness_starts_neutral() -> None:
    state = ShynessState()
    assert state.level == 0.0


def test_shyness_rises_with_gaze_favor_context() -> None:
    state = ShynessState()
    for _ in range(50):
        state.update(
            gaze_confidence=1.0,
            favor=1.0,
            expression="shy_cute_front",
        )
    assert state.level > SHYNESS_MIDPOINT


def test_shyness_decays_when_drivers_relax() -> None:
    state = ShynessState()
    for _ in range(50):
        state.update(gaze_confidence=1.0, favor=1.0, expression="shy")
    peak = state.level
    for _ in range(50):
        state.update(gaze_confidence=0.0, favor=0.0, expression="idle")
    assert state.level < peak


def test_blend_shyness_is_identity_at_zero() -> None:
    frame = _frame(blush=0.4, eye_smile=0.3, corner_smile=0.2)
    blended = blend_shyness(frame, 0.0)
    assert blended.expression_shape.blush == frame.expression_shape.blush
    assert blended.expression_shape.eye_smile == frame.expression_shape.eye_smile
    assert blended.mouth.corner_smile == frame.mouth.corner_smile


def test_blend_shyness_moves_toward_cascade() -> None:
    frame = _frame(blush=0.0, eye_smile=0.0, corner_smile=0.0)
    blended = blend_shyness(frame, 1.0)
    assert blended.expression_shape.blush > 0.0
    assert blended.expression_shape.eye_smile > 0.0
    assert blended.mouth.corner_smile > 0.0


def test_blend_shyness_preserves_existing_emotion() -> None:
    # A happy companion (blush already high) should keep some of that blush
    # even when shy, rather than snapping to the shy cascade alone.
    frame = _frame(blush=0.8, eye_smile=0.7, corner_smile=0.6)
    blended = blend_shyness(frame, 0.5)
    assert blended.expression_shape.blush > 0.0
    assert blended.expression_shape.eye_smile > 0.0
    assert blended.mouth.corner_smile > 0.0


def run() -> None:
    test_shyness_starts_neutral()
    test_shyness_rises_with_gaze_favor_context()
    test_shyness_decays_when_drivers_relax()
    test_blend_shyness_is_identity_at_zero()
    test_blend_shyness_moves_toward_cascade()
    test_blend_shyness_preserves_existing_emotion()
    print("SHYNESS_OK")


if __name__ == "__main__":
    run()
