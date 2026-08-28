from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from application.behavior_director import BehaviorInput, SemanticEmotion, SpeechLifecycle
lazy from application.body_pose_renderer import BodyPoseFrame
lazy from domain.character_pose import default_pose_registry
lazy from application.performance_app_bridge import (
    BridgeDisposition,
    PerformanceAppBridge,
    PerformanceBridgeInput,
)
lazy from domain.performance_preferences import PerformancePreferences
lazy from application.performance_runtime import BodyRenderRequest
lazy from application.speech_performance import (
    SpeechEvent,
    SpeechEventKind,
    SpeechPerformanceDirective,
    SpeechPerformancePhase,
)

EXPECTED_PUBLISHED_COUNT = 2

CORRECTIONS = frozenset({"idle_front.png", "idle_lean.png", "idle.png"})


class Clock:
    def __init__(self) -> None:
        self.value = 1.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeRenderer:
    def __init__(self) -> None:
        self.generation = 0
        self.calls = 0
        self.fail = False
        self.current_frame = BodyPoseFrame(1, 1, b"\0\0\0\0", 0, (), (), False)

    def begin_transition(self) -> int:
        self.generation += 1
        return self.generation

    def render(self, generation: int, *_args: object) -> BodyPoseFrame:
        self.calls += 1
        if self.fail:
            raise RuntimeError("render failed")
        self.current_frame = BodyPoseFrame(
            1, 1, bytes((generation, 0, 0, 255)), generation,
            ("view",), ("body",), True,
        )
        return self.current_frame


@dataclass(frozen=True, slots=True)
class FakeBlend:
    value: str = "blend"


def render_request(frame, registry):
    pose = registry.get(frame.pose)
    return None if pose is None else BodyRenderRequest(FakeBlend(), pose, pose)  # type: ignore[arg-type]


def behavior() -> BehaviorInput:
    return BehaviorInput(
        SpeechLifecycle.SPEAKING,
        SemanticEmotion.NEUTRAL,
        0.5,
        1,
        True,
        True,
        0.0,
        "front-crossed",
        "idle",
        False,
    )


def pair(
    kind: SpeechEventKind,
    phase: SpeechPerformancePhase,
    **options: object,
) -> tuple[SpeechEvent, SpeechPerformanceDirective]:
    generation = int(options.get("generation", 1))
    timestamp = float(options.get("timestamp", 1.0))
    viseme = str(options.get("viseme", "A"))
    level = float(options.get("level", 0.7))
    gesture = bool(options.get("gesture", False))
    return (
        SpeechEvent(generation, "shared", kind, timestamp, level, viseme, 1),
        SpeechPerformanceDirective(
            generation, phase, 0.4, 0.3, 0.5, gesture,
            kind in {SpeechEventKind.PREPARE, SpeechEventKind.MOUTH_CLOSED},
            kind in {SpeechEventKind.FIRST_AUDIO, SpeechEventKind.PAUSE, SpeechEventKind.FINAL_AUDIO},
            "test",
        ),
    )


def bridge(clock: Clock):
    renderer = FakeRenderer()
    published = []
    value = PerformanceAppBridge(
        default_pose_registry(),
        renderer,
        render_request,
        published.append,
        clock=clock,
        seed=3,
        minimum_render_interval_seconds=0.02,
    )
    return value, renderer, published


def input_value(
    event: SpeechEvent,
    directive: SpeechPerformanceDirective,
    *,
    behavior_generation: int = 1,
    enabled: bool = True,
) -> PerformanceBridgeInput:
    return PerformanceBridgeInput(
        event,
        directive,
        behavior_generation,
        behavior(),
        PerformancePreferences(),
        CORRECTIONS,
        enabled,
    )


def assert_disabled_is_complete_bypass() -> None:
    clock = Clock()
    app_bridge, renderer, published = bridge(clock)
    event, directive = pair(SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING)
    result = app_bridge.dispatch(input_value(event, directive, enabled=False))
    assert result is BridgeDisposition.BYPASSED
    assert renderer.calls == 0
    assert not published
    assert app_bridge.last_known_good is None


def assert_atomic_emit_and_exact_duplicate() -> None:
    clock = Clock()
    app_bridge, renderer, published = bridge(clock)
    event, directive = pair(SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING)
    value = input_value(event, directive)
    assert app_bridge.dispatch(value) is BridgeDisposition.EMITTED
    assert len(published) == 1 and renderer.calls == 1
    assert app_bridge.dispatch(value) is BridgeDisposition.DUPLICATE
    assert len(published) == 1 and renderer.calls == 1


def assert_50hz_throttle_but_lifecycle_bypasses() -> None:
    clock = Clock()
    app_bridge, renderer, published = bridge(clock)
    prepare_event, prepare_directive = pair(
        SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING
    )
    assert app_bridge.dispatch(input_value(prepare_event, prepare_directive)) is BridgeDisposition.EMITTED
    first_event, first_directive = pair(
        SpeechEventKind.FIRST_AUDIO, SpeechPerformancePhase.SPEAKING
    )
    assert app_bridge.dispatch(
        input_value(first_event, first_directive, behavior_generation=2)
    ) is BridgeDisposition.EMITTED
    viseme_event, viseme_directive = pair(
        SpeechEventKind.VISEME, SpeechPerformancePhase.SPEAKING,
        timestamp=1.02, viseme="I", level=0.4,
    )
    assert app_bridge.dispatch(
        input_value(viseme_event, viseme_directive, behavior_generation=3)
    ) is BridgeDisposition.THROTTLED
    assert len(published) == EXPECTED_PUBLISHED_COUNT and renderer.calls == EXPECTED_PUBLISHED_COUNT
    clock.advance(0.02)
    assert app_bridge.dispatch(
        input_value(viseme_event, viseme_directive, behavior_generation=3)
    ) is BridgeDisposition.EMITTED


def assert_stale_generations_never_render() -> None:
    clock = Clock()
    app_bridge, renderer, _published = bridge(clock)
    event, directive = pair(
        SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING,
        generation=3,
    )
    assert app_bridge.dispatch(input_value(event, directive, behavior_generation=5)) is BridgeDisposition.EMITTED
    calls = renderer.calls
    old_event, old_directive = pair(
        SpeechEventKind.VISEME, SpeechPerformancePhase.SPEAKING,
        generation=2,
    )
    assert app_bridge.dispatch(input_value(old_event, old_directive, behavior_generation=6)) is BridgeDisposition.STALE
    current_event, current_directive = pair(
        SpeechEventKind.VISEME, SpeechPerformancePhase.SPEAKING,
        generation=3,
    )
    assert app_bridge.dispatch(input_value(current_event, current_directive, behavior_generation=4)) is BridgeDisposition.STALE
    mismatch = input_value(current_event, pair(
        SpeechEventKind.VISEME, SpeechPerformancePhase.SPEAKING,
        generation=4,
    )[1], behavior_generation=6)
    assert app_bridge.dispatch(mismatch) is BridgeDisposition.STALE
    assert renderer.calls == calls


def assert_failures_keep_last_known_good_and_do_not_publish() -> None:
    clock = Clock()
    app_bridge, renderer, published = bridge(clock)
    event, directive = pair(SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING)
    assert app_bridge.dispatch(input_value(event, directive)) is BridgeDisposition.EMITTED
    good = app_bridge.last_known_good
    renderer.fail = True
    clock.advance(0.1)
    viseme_event, viseme_directive = pair(
        SpeechEventKind.VISEME, SpeechPerformancePhase.SPEAKING,
        timestamp=1.1, viseme="O",
    )
    result = app_bridge.dispatch(
        input_value(viseme_event, viseme_directive, behavior_generation=2)
    )
    assert result is BridgeDisposition.FALLBACK
    assert app_bridge.last_known_good is good
    assert len(published) == 1


def assert_publish_failure_is_fail_closed() -> None:
    clock = Clock()
    renderer = FakeRenderer()
    calls = []

    def fail(frame):
        calls.append(frame)
        raise RuntimeError("publish failed")

    app_bridge = PerformanceAppBridge(
        default_pose_registry(), renderer, render_request, fail,
        clock=clock, seed=1,
    )
    event, directive = pair(SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING)
    assert app_bridge.dispatch(input_value(event, directive)) is BridgeDisposition.FALLBACK
    assert app_bridge.last_known_good is None
    assert len(calls) == 1


def run() -> None:
    assert_disabled_is_complete_bypass()
    assert_atomic_emit_and_exact_duplicate()
    assert_50hz_throttle_but_lifecycle_bypasses()
    assert_stale_generations_never_render()
    assert_failures_keep_last_known_good_and_do_not_publish()
    assert_publish_failure_is_fail_closed()
    print("PERFORMANCE_APP_BRIDGE_OK")


def test_performance_app_bridge_contract() -> None:
    run()


if __name__ == "__main__":
    run()
