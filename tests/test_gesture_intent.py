from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.gesture_intent import LipRegion as OwnerLipRegion
lazy from domain.gesture_intent import NormalizedPoint as OwnerNormalizedPoint
lazy from gesture_intent import (
    GestureFrame,
    GestureIntent,
    GestureState,
    HandLandmarks,
    HandSide,
    NormalizedPoint,
    SilenceGestureDetector,
)

LIPS = OwnerLipRegion(
    OwnerNormalizedPoint(0.5, 0.45),
    0.12,
    0.08,
)


def hand(side: HandSide, *, valid: bool = True, mirrored: bool = False) -> HandLandmarks:
    points = [NormalizedPoint(0.5, 0.82) for _ in range(21)]
    points[6] = NormalizedPoint(0.5, 0.59)
    points[8] = NormalizedPoint(0.5, 0.46 if valid else 0.2)
    for pip, tip in ((10, 12), (14, 16), (18, 20)):
        points[pip] = NormalizedPoint(0.52, 0.68)
        points[tip] = NormalizedPoint(0.51, 0.74)
    if mirrored:
        points = [NormalizedPoint(1.0 - point.x, point.y) for point in points]
    return HandLandmarks(side, tuple(points))


def frame(at: float, *hands: HandLandmarks, tracked: bool = True) -> GestureFrame:
    return GestureFrame(at, LIPS if tracked else None, tuple(hands), tracked)


def assert_multiframe_duration_and_cooldown_are_deterministic() -> None:
    detector = SilenceGestureDetector(minimum_frames=3, minimum_duration=0.2, cooldown=1.0)
    right = hand(HandSide.RIGHT)
    assert detector.update(frame(0.0, right)).state is GestureState.CANDIDATE
    assert detector.update(frame(0.1, right)).state is GestureState.CANDIDATE
    triggered = detector.update(frame(0.2, right))
    assert triggered.state is GestureState.TRIGGERED
    assert triggered.intent is GestureIntent.SILENCE_REQUEST
    assert triggered.hand is HandSide.RIGHT
    assert detector.update(frame(0.3, right)).state is GestureState.COOLDOWN
    assert detector.update(frame(1.2, right)).state is GestureState.CANDIDATE


def assert_false_positive_shapes_do_not_trigger() -> None:
    detector = SilenceGestureDetector(minimum_frames=2, minimum_duration=0.1)
    invalid = hand(HandSide.LEFT, valid=False)
    for at in (0.0, 0.2, 0.4):
        decision = detector.update(frame(at, invalid))
        assert decision.state is GestureState.IDLE
        assert decision.intent is None
    open_hand = list(hand(HandSide.LEFT).points)
    open_hand[12] = NormalizedPoint(0.4, 0.3)
    assert detector.update(
        frame(0.6, HandLandmarks(HandSide.LEFT, tuple(open_hand)))
    ).state is GestureState.IDLE


def assert_tracking_loss_cancel_and_side_change_reset_evidence() -> None:
    detector = SilenceGestureDetector(minimum_frames=3, minimum_duration=0.2)
    left = hand(HandSide.LEFT)
    right = hand(HandSide.RIGHT)
    detector.update(frame(0.0, left))
    assert detector.update(frame(0.1, tracked=False)).state is GestureState.IDLE
    assert detector.update(frame(0.2, left)).state is GestureState.CANDIDATE
    assert detector.update(frame(0.3, right)).state is GestureState.CANDIDATE
    assert detector.update(frame(0.4, right)).state is GestureState.CANDIDATE
    assert detector.update(frame(0.5, right)).intent is GestureIntent.SILENCE_REQUEST


def assert_left_right_and_mirror_are_geometry_equivalent() -> None:
    for side, mirrored in (
        (HandSide.LEFT, False),
        (HandSide.RIGHT, True),
    ):
        detector = SilenceGestureDetector(minimum_frames=2, minimum_duration=0.1)
        observed = hand(side, mirrored=mirrored)
        detector.update(frame(0.0, observed))
        result = detector.update(frame(0.1, observed))
        assert result.intent is GestureIntent.SILENCE_REQUEST
        assert result.hand is side


def assert_cancel_and_invalid_input_are_explicit() -> None:
    detector = SilenceGestureDetector(minimum_frames=2, minimum_duration=0.1)
    detector.update(frame(1.0, hand(HandSide.LEFT)))
    detector.cancel()
    assert detector.update(frame(1.1, hand(HandSide.LEFT))).state is GestureState.CANDIDATE
    try:
        detector.update(frame(1.0, hand(HandSide.LEFT)))
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-order frames must fail explicitly.")


def run() -> None:
    assert_multiframe_duration_and_cooldown_are_deterministic()
    assert_false_positive_shapes_do_not_trigger()
    assert_tracking_loss_cancel_and_side_change_reset_evidence()
    assert_left_right_and_mirror_are_geometry_equivalent()
    assert_cancel_and_invalid_input_are_explicit()
    print("GESTURE_INTENT_OK")


if __name__ == "__main__":
    run()
