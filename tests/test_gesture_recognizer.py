from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from gesture_configuration import GestureLandmark, GestureSample
lazy from gesture_intent import HandSide
lazy from gesture_recognizer import (
    GestureId,
    GestureRecognizer,
    GestureTiming,
    HandSkeleton,
    RecognitionState,
)


def hand(
    gesture: str,
    at: float,
    *,
    side: HandSide = HandSide.RIGHT,
    shift_x: float = 0.0,
) -> HandSkeleton:
    points = [GestureLandmark(0.50 + shift_x, 0.80, 0.0) for _ in range(21)]
    points[0] = GestureLandmark(0.50 + shift_x, 0.82, 0.0)
    bases = ((5, 6, 8, 0.38), (9, 10, 12, 0.46), (13, 14, 16, 0.54), (17, 18, 20, 0.62))
    for base, middle, tip, x in bases:
        points[base] = GestureLandmark(x + shift_x, 0.65, 0.0)
        points[middle] = GestureLandmark(x + shift_x, 0.52, 0.0)
        points[tip] = GestureLandmark(x + shift_x, 0.32, 0.0)
    points[2] = GestureLandmark(0.43 + shift_x, 0.70, 0.0)
    points[4] = GestureLandmark(0.25 + shift_x, 0.58, 0.0)
    if gesture in {"closed-fist", "thumbs-up", "thumbs-down"}:
        for base, middle, tip, x in bases:
            points[middle] = GestureLandmark(x + shift_x, 0.69, 0.0)
            points[tip] = GestureLandmark(0.50 + shift_x, 0.72, 0.0)
        points[4] = GestureLandmark(0.45 + shift_x, 0.71, 0.0)
    if gesture == "thumbs-up":
        points[2] = GestureLandmark(0.43 + shift_x, 0.70, 0.0)
        points[4] = GestureLandmark(0.43 + shift_x, 0.40, 0.0)
    elif gesture == "thumbs-down":
        points[2] = GestureLandmark(0.43 + shift_x, 0.62, 0.0)
        points[4] = GestureLandmark(0.43 + shift_x, 0.92, 0.0)
    elif gesture in {"point-left", "point-right"}:
        for base, middle, tip, x in bases[1:]:
            points[middle] = GestureLandmark(x + shift_x, 0.69, 0.0)
            points[tip] = GestureLandmark(0.50 + shift_x, 0.72, 0.0)
        direction = -1.0 if gesture == "point-left" else 1.0
        points[5] = GestureLandmark(0.50 + shift_x, 0.62, 0.0)
        points[6] = GestureLandmark(0.50 + shift_x + 0.12 * direction, 0.62, 0.0)
        points[8] = GestureLandmark(0.50 + shift_x + 0.30 * direction, 0.62, 0.0)
        points[4] = GestureLandmark(0.47 + shift_x, 0.70, 0.0)
    return HandSkeleton(at, side, tuple(points))


def assert_builtin_classification_and_both_hands() -> None:
    expected = {
        "open-palm": GestureId.OPEN_PALM,
        "closed-fist": GestureId.CLOSED_FIST,
        "thumbs-up": GestureId.THUMBS_UP,
        "thumbs-down": GestureId.THUMBS_DOWN,
        "point-left": GestureId.POINT_LEFT,
        "point-right": GestureId.POINT_RIGHT,
    }
    for index, (name, gesture_id) in enumerate(expected.items()):
        side = HandSide.LEFT if index % 2 else HandSide.RIGHT
        recognizer = GestureRecognizer()
        first = recognizer.update(hand(name, 1.0, side=side))
        second = recognizer.update(hand(name, 1.09, side=side))
        result = recognizer.update(hand(name, 1.19, side=side))
        assert first.state is RecognitionState.CANDIDATE
        assert second.state is RecognitionState.CANDIDATE
        assert result.gesture_id is gesture_id
        assert result.side is side
        assert result.triggered


def assert_wave_requires_ordered_debounced_sequence() -> None:
    recognizer = GestureRecognizer(timing=GestureTiming(cooldown_seconds=1.0))
    single = recognizer.update(hand("open-palm", 0.0))
    assert single.gesture_id is GestureId.OPEN_PALM
    results = tuple(
        recognizer.update(hand("open-palm", at, shift_x=shift))
        for at, shift in ((0.2, 0.08), (0.4, -0.06), (0.6, 0.09))
    )
    assert results[-1].gesture_id is GestureId.WAVE
    assert results[-1].triggered
    held = recognizer.update(hand("open-palm", 0.8, shift_x=-0.06))
    assert held.gesture_id is not GestureId.WAVE
    out_of_order = recognizer.update(hand("open-palm", 0.7, shift_x=0.09))
    assert out_of_order.gesture_id is GestureId.UNKNOWN


def assert_cooldown_is_single_trigger_and_resettable() -> None:
    recognizer = GestureRecognizer(timing=GestureTiming(cooldown_seconds=2.0))
    recognizer.update(hand("thumbs-up", 1.0))
    recognizer.update(hand("thumbs-up", 1.09))
    first = recognizer.update(hand("thumbs-up", 1.19))
    repeated = recognizer.update(hand("thumbs-up", 1.36))
    assert first.triggered
    assert repeated.state is RecognitionState.COOLDOWN
    assert recognizer.update(hand("thumbs-up", 3.19)).state is RecognitionState.CANDIDATE
    recognizer.reset()
    assert recognizer.update(hand("thumbs-up", 1.2)).state is RecognitionState.CANDIDATE


def assert_custom_templates_are_translation_scale_and_mirror_invariant() -> None:
    template = hand("open-palm", 0.0).landmarks
    recognizer = GestureRecognizer(
        {"custom:fan": (GestureSample(template), GestureSample(template))},
        timing=GestureTiming(cooldown_seconds=0.0),
    )
    moved = hand("open-palm", 1.0, shift_x=0.10)
    assert recognizer.update(moved).state is RecognitionState.CANDIDATE
    recognizer.update(hand("open-palm", 1.09, shift_x=0.10))
    result = recognizer.update(hand("open-palm", 1.19, shift_x=0.10))
    assert result.gesture_id == "custom:fan"
    mirrored_points = tuple(
        GestureLandmark(1.0 - point.x, point.y, point.z) for point in template
    )
    for at in (2.0, 2.09, 2.19):
        mirrored = HandSkeleton(at, HandSide.LEFT, mirrored_points)
        mirrored_result = recognizer.update(mirrored)
    assert mirrored_result.gesture_id == "custom:fan"
    assert mirrored_result.triggered


def assert_candidate_interruption_cancel_and_hand_isolation() -> None:
    recognizer = GestureRecognizer(timing=GestureTiming(cooldown_seconds=0.0))
    assert recognizer.update(hand("thumbs-up", 1.0)).state is RecognitionState.CANDIDATE
    assert recognizer.update(hand("thumbs-down", 1.09)).state is RecognitionState.CANDIDATE
    assert recognizer.update(hand("thumbs-up", 1.18)).state is RecognitionState.CANDIDATE
    assert recognizer.update(hand("thumbs-up", 1.27)).state is RecognitionState.CANDIDATE
    assert recognizer.update(hand("thumbs-up", 1.37)).triggered

    left = HandSide.LEFT
    assert recognizer.update(hand("open-palm", 2.0, side=left)).state is RecognitionState.CANDIDATE
    recognizer.cancel(left)
    assert recognizer.update(hand("open-palm", 2.09, side=left)).state is RecognitionState.CANDIDATE
    recognizer.cancel()
    assert recognizer.update(hand("open-palm", 2.18, side=left)).state is RecognitionState.CANDIDATE

    recognizer.update(hand("closed-fist", 3.0, side=HandSide.RIGHT))
    recognizer.update(hand("closed-fist", 3.09, side=HandSide.RIGHT))
    assert recognizer.update(hand("closed-fist", 3.19, side=HandSide.RIGHT)).triggered
    assert recognizer.update(hand("closed-fist", 3.0, side=left)).state is RecognitionState.CANDIDATE


def assert_malformed_and_ambiguous_inputs_fail_closed() -> None:
    try:
        HandSkeleton(0.0, HandSide.RIGHT, hand("open-palm", 0.0).landmarks[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError("A malformed skeleton must be rejected.")
    points = list(hand("open-palm", 0.0).landmarks)
    points[0] = GestureLandmark(0.5, 0.5, 0.0)
    points[4] = GestureLandmark(0.5, 0.5, 0.0)
    points[8] = GestureLandmark(0.52, 0.51, 0.0)
    ambiguous = GestureRecognizer().update(
        HandSkeleton(1.0, HandSide.RIGHT, tuple(points))
    )
    assert ambiguous.gesture_id is GestureId.UNKNOWN
    assert ambiguous.confidence == 0.0
    assert GestureRecognizer().silence_requires_external_fusion


def assert_relative_negative_z_is_supported_but_invalid_depth_is_rejected() -> None:
    def with_depth(skeleton: HandSkeleton, depth: float) -> HandSkeleton:
        return HandSkeleton(
            skeleton.observed_at,
            skeleton.side,
            tuple(
                GestureLandmark(point.x, point.y, depth)
                for point in skeleton.landmarks
            ),
        )

    recognizer = GestureRecognizer()
    for at in (1.0, 1.09, 1.19):
        result = recognizer.update(with_depth(hand("thumbs-up", at), -0.35))
    assert result.gesture_id is GestureId.THUMBS_UP
    assert result.triggered

    for invalid in (float("nan"), float("inf"), -8.01, 8.01):
        try:
            with_depth(hand("open-palm", 2.0), invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Non-finite or out-of-range z must be rejected.")


def run() -> None:
    assert_builtin_classification_and_both_hands()
    assert_wave_requires_ordered_debounced_sequence()
    assert_cooldown_is_single_trigger_and_resettable()
    assert_custom_templates_are_translation_scale_and_mirror_invariant()
    assert_candidate_interruption_cancel_and_hand_isolation()
    assert_malformed_and_ambiguous_inputs_fail_closed()
    assert_relative_negative_z_is_supported_but_invalid_depth_is_rejected()
    print("GESTURE_RECOGNIZER_OK")


if __name__ == "__main__":
    run()
