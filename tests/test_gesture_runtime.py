from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.gesture_configuration import (
    GestureAction,
    GestureBinding,
    GestureConfiguration,
    GestureLandmark,
    GestureSample,
)
lazy from domain.gesture_intent import HandSide
lazy from application.gesture_recognizer import RecognitionState
lazy from application.gesture_runtime import GestureRuntime
lazy from infrastructure.hand_landmark_provider import (
    Handedness,
    HandLandmark,
    HandObservation,
)

TRIGGERED_RECOGNITION_COUNT = 2


def hand(
    gesture: str,
    *,
    side: Handedness = Handedness.RIGHT,
    confidence: float = 0.95,
    shift_x: float = 0.0,
) -> HandObservation:
    points = [HandLandmark(0.50 + shift_x, 0.80, 0.0) for _ in range(21)]
    points[0] = HandLandmark(0.50 + shift_x, 0.82, 0.0)
    bases = (
        (5, 6, 8, 0.38),
        (9, 10, 12, 0.46),
        (13, 14, 16, 0.54),
        (17, 18, 20, 0.62),
    )
    for base, middle, tip, x in bases:
        points[base] = HandLandmark(x + shift_x, 0.65, 0.0)
        points[middle] = HandLandmark(x + shift_x, 0.52, 0.0)
        points[tip] = HandLandmark(x + shift_x, 0.32, 0.0)
    points[2] = HandLandmark(0.43 + shift_x, 0.70, 0.0)
    points[4] = HandLandmark(0.25 + shift_x, 0.58, 0.0)
    if gesture in {"closed-fist", "thumbs-up", "thumbs-down"}:
        for _base, middle, tip, x in bases:
            points[middle] = HandLandmark(x + shift_x, 0.69, 0.0)
            points[tip] = HandLandmark(0.50 + shift_x, 0.72, 0.0)
        points[4] = HandLandmark(0.45 + shift_x, 0.71, 0.0)
    if gesture == "thumbs-up":
        points[2] = HandLandmark(0.43 + shift_x, 0.70, 0.0)
        points[4] = HandLandmark(0.43 + shift_x, 0.40, 0.0)
    elif gesture == "thumbs-down":
        points[2] = HandLandmark(0.43 + shift_x, 0.62, 0.0)
        points[4] = HandLandmark(0.43 + shift_x, 0.92, 0.0)
    return HandObservation(side, confidence, tuple(points))


def enabled_configuration() -> GestureConfiguration:
    return GestureConfiguration(enabled=True)


def frames(
    runtime: GestureRuntime,
    hands: tuple[HandObservation, ...],
    configuration: GestureConfiguration,
    *,
    start: float = 1.0,
):
    return tuple(
        runtime.update(start + offset, hands, configuration)
        for offset in (0.0, 0.09, 0.19)
    )


def assert_builtin_debounce_routes_only_triggered_action() -> None:
    runtime = GestureRuntime()
    results = frames(runtime, (hand("open-palm"),), enabled_configuration())
    assert results[0].decision is None
    assert results[1].decision is None
    assert results[0].recognitions[0].state is RecognitionState.CANDIDATE
    assert results[2].decision is not None
    assert results[2].decision.action is GestureAction.STOP_SPEECH


def assert_custom_configuration_builds_templates_and_preserves_timing() -> None:
    sample = GestureSample(
        tuple(
            GestureLandmark(point.x, point.y, point.z)
            for point in hand("open-palm").landmarks
        )
    )
    configuration = enabled_configuration().add_custom(
        "Fan",
        (sample, sample),
        gesture_id="custom:fan",
        binding=GestureBinding(GestureAction.SHOW_DASHBOARD),
    )
    results = frames(GestureRuntime(), (hand("open-palm", shift_x=0.08),), configuration)
    assert results[-1].decision is not None
    assert results[-1].decision.gesture_id == "custom:fan"


def assert_two_hand_conflict_has_one_deterministic_winner() -> None:
    configuration = enabled_configuration()
    thumbs_down = configuration.definition("thumbs-down").with_binding(
        GestureBinding(GestureAction.HIDE_DASHBOARD)
    )
    configuration = configuration.replace_definition(thumbs_down)
    runtime = GestureRuntime()
    both = (
        hand("thumbs-up", side=Handedness.RIGHT),
        hand("thumbs-down", side=Handedness.LEFT),
    )
    result = frames(runtime, both, configuration)[-1]
    assert len(tuple(item for item in result.recognitions if item.triggered)) == TRIGGERED_RECOGNITION_COUNT
    assert result.decision is not None
    assert result.decision.gesture_id == "thumbs-down"


def assert_disabled_unknown_empty_and_candidate_never_execute() -> None:
    runtime = GestureRuntime()
    disabled = runtime.update(1.0, (hand("open-palm"),), GestureConfiguration())
    assert disabled.recognitions == () and disabled.decision is None
    empty = runtime.update(2.0, (), enabled_configuration())
    assert empty.recognitions == () and empty.decision is None
    unknown = runtime.update(
        3.0,
        (hand("open-palm", side=Handedness.UNKNOWN),),
        enabled_configuration(),
    )
    assert unknown.recognitions == () and unknown.decision is None
    candidate = runtime.update(4.0, (hand("open-palm"),), enabled_configuration())
    assert candidate.decision is None


def assert_configuration_change_empty_frame_cancel_and_reset_clear_state() -> None:
    runtime = GestureRuntime()
    first = enabled_configuration()
    runtime.update(1.0, (hand("open-palm"),), first)
    runtime.update(1.09, (hand("open-palm"),), first)
    changed = first.replace_definition(
        first.definition("open-palm").with_binding(
            GestureBinding(GestureAction.MUTE_AUDIO)
        )
    )
    after_change = runtime.update(1.19, (hand("open-palm"),), changed)
    assert after_change.decision is None
    runtime.update(1.28, (hand("open-palm"),), changed)
    assert runtime.update(1.38, (), changed).decision is None
    assert runtime.update(1.47, (hand("open-palm"),), changed).decision is None
    runtime.cancel(HandSide.RIGHT)
    assert runtime.update(1.66, (hand("open-palm"),), changed).decision is None
    runtime.reset()
    assert runtime.update(1.85, (hand("open-palm"),), changed).decision is None


def assert_air_interaction_is_observable_without_executing_actions() -> None:
    runtime = GestureRuntime()
    configuration = enabled_configuration()
    both = (
        hand("open-palm", side=Handedness.LEFT),
        hand("open-palm", side=Handedness.RIGHT),
    )
    first = runtime.update(2.0, both, configuration)
    second = runtime.update(2.1, both, configuration)
    assert first.air_interaction is None
    assert second.air_interaction is not None
    assert second.air_interaction.kind.value == "high-five"
    assert second.decision is None


def run() -> None:
    assert_builtin_debounce_routes_only_triggered_action()
    assert_custom_configuration_builds_templates_and_preserves_timing()
    assert_two_hand_conflict_has_one_deterministic_winner()
    assert_disabled_unknown_empty_and_candidate_never_execute()
    assert_configuration_change_empty_frame_cancel_and_reset_clear_state()
    assert_air_interaction_is_observable_without_executing_actions()
    print("GESTURE_RUNTIME_OK")


if __name__ == "__main__":
    run()
