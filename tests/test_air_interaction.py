from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from air_interaction import (
    AirHandPoint,
    AirHandSample,
    AirInteractionConfig,
    AirInteractionDetector,
    AirInteractionKind,
)
lazy from gesture_intent import HandSide


def hand(
    side: HandSide,
    *,
    center_x: float = 0.50,
    pinch: bool = False,
    confidence: float = 0.95,
) -> AirHandSample:
    points = [AirHandPoint(center_x, 0.80) for _ in range(21)]
    points[0] = AirHandPoint(center_x, 0.82)
    for mcp, pip, tip, offset in (
        (5, 6, 8, -0.12),
        (9, 10, 12, -0.04),
        (13, 14, 16, 0.04),
        (17, 18, 20, 0.12),
    ):
        points[mcp] = AirHandPoint(center_x + offset, 0.65)
        points[pip] = AirHandPoint(center_x + offset, 0.52)
        points[tip] = AirHandPoint(center_x + offset, 0.30)
    points[2] = AirHandPoint(center_x - 0.07, 0.70)
    points[4] = AirHandPoint(center_x - 0.20, 0.58)
    if pinch:
        points[4] = AirHandPoint(center_x - 0.02, 0.48)
        points[8] = AirHandPoint(center_x + 0.01, 0.48)
    return AirHandSample(side, confidence, tuple(points))


def detector() -> AirInteractionDetector:
    return AirInteractionDetector(
        AirInteractionConfig(
            minimum_stable_frames=2,
            cooldown_seconds=0.5,
        )
    )


def assert_pinch_is_stable_and_not_repeated() -> None:
    target = detector()
    sample = (hand(HandSide.RIGHT, pinch=True),)
    assert target.update(1.0, sample) is None
    event = target.update(1.1, sample)
    assert event is not None
    assert event.kind is AirInteractionKind.PINCH
    assert target.update(1.2, sample) is None
    target.update(1.3, (hand(HandSide.RIGHT),))
    target.update(1.4, sample)
    assert target.update(1.5, sample) is None


def assert_swipe_direction_is_deterministic() -> None:
    target = detector()
    assert target.update(2.0, (hand(HandSide.LEFT, center_x=0.20),)) is None
    event = target.update(2.2, (hand(HandSide.LEFT, center_x=0.45),))
    assert event is not None
    assert event.kind is AirInteractionKind.SWIPE_RIGHT
    assert event.side is HandSide.LEFT
    assert event.displacement_x > 0.0


def assert_two_open_palms_trigger_high_five_only_after_stability() -> None:
    target = detector()
    hands = (
        hand(HandSide.LEFT, center_x=0.28),
        hand(HandSide.RIGHT, center_x=0.72),
    )
    assert target.update(3.0, hands) is None
    event = target.update(3.1, hands)
    assert event is not None
    assert event.kind is AirInteractionKind.HIGH_FIVE
    assert event.side is None
    assert event.palm_scale > 0.17


def assert_invalid_confidence_and_disabled_detector_fail_closed() -> None:
    target = AirInteractionDetector(AirInteractionConfig(enabled=False))
    sample = (hand(HandSide.RIGHT, pinch=True),)
    assert target.update(4.0, sample) is None
    assert target.update(4.1, sample) is None
    low_confidence = AirInteractionDetector()
    assert low_confidence.update(
        5.0,
        (hand(HandSide.RIGHT, pinch=True, confidence=0.1),),
    ) is None


def assert_out_of_order_frames_are_rejected() -> None:
    target = detector()
    target.update(6.0, (hand(HandSide.RIGHT),))
    try:
        target.update(5.0, (hand(HandSide.RIGHT),))
    except ValueError as error:
        assert "time ordered" in str(error)
    else:
        raise AssertionError("out-of-order air frames must be rejected")


def run() -> None:
    assert_pinch_is_stable_and_not_repeated()
    assert_swipe_direction_is_deterministic()
    assert_two_open_palms_trigger_high_five_only_after_stability()
    assert_invalid_confidence_and_disabled_detector_fail_closed()
    assert_out_of_order_frames_are_rejected()
    print("AIR_INTERACTION_OK")


if __name__ == "__main__":
    run()
