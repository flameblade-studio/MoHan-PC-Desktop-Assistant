from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import performance_preferences
lazy import performance_runtime
lazy from behavior_director import SemanticEmotion
lazy from body_pose_renderer import BodyPoseFrame
lazy from character_pose import default_pose_registry
lazy from performance_preferences import PerformancePreferences
lazy from performance_runtime import (
    AtomicPerformanceFrame,
    BodyRenderRequest,
    PerformanceContextEvent,
    PerformanceRuntime,
    RuntimeSpeechEvent,
)
lazy from speech_performance import SpeechEventKind

PROVIDERS = ("windows", "openai", "realtime", "azure", "dragon-hd")
CORRECTIONS = frozenset({"idle_front.png", "idle_lean.png", "idle.png"})


class FakeRenderer:
    def __init__(self) -> None:
        self.generation = 0
        self.current_frame = BodyPoseFrame(1, 1, b"\0\0\0\0", 0, (), (), False)
        self.fail = False
        self.calls = 0

    def begin_transition(self) -> int:
        self.generation += 1
        return self.generation

    def render(self, generation: int, *_args: object) -> BodyPoseFrame:
        self.calls += 1
        if self.fail:
            raise RuntimeError("render failed")
        self.current_frame = BodyPoseFrame(
            1, 1, bytes((generation % 255, 0, 0, 255)), generation,
            ("rendered",), ("body",), True,
        )
        return self.current_frame


@dataclass(frozen=True, slots=True)
class FakeBlend:
    marker: str = "blend"


def request(frame, registry):
    pose = registry.get(frame.pose)
    if pose is None:
        return None
    return BodyRenderRequest(FakeBlend(), pose, pose)  # type: ignore[arg-type]


def event(
    kind: RuntimeSpeechEvent,
    **options: object,
) -> PerformanceContextEvent:
    provider = str(options.get("provider", "windows"))
    speech_generation_value = options.get("speech_generation")
    speech_generation = (
        None
        if speech_generation_value is None
        else int(speech_generation_value)
    )
    behavior_generation = int(options.get("behavior_generation", 1))
    emotion = options.get("emotion", SemanticEmotion.NEUTRAL)
    assert isinstance(emotion, SemanticEmotion)
    intensity = float(options.get("intensity", 0.5))
    viseme = str(options.get("viseme", "A"))
    level = float(options.get("level", 0.7))
    return PerformanceContextEvent(
        kind, provider, speech_generation, behavior_generation,
        emotion, intensity, 1, True, True, 0.0,
        "front-crossed", "idle", False, level, viseme, 1, 0.8,
    )


def runtime(
    *,
    preferences: PerformancePreferences | None = None,
    seed: int = 1,
) -> tuple[PerformanceRuntime, FakeRenderer]:
    renderer = FakeRenderer()
    return (
        PerformanceRuntime(
            default_pose_registry(), renderer, request,
            preferences=preferences or PerformancePreferences(),
            clock=lambda: 1.0,
            seed=seed,
        ),
        renderer,
    )


def start(runtime: PerformanceRuntime, provider: str = "windows") -> AtomicPerformanceFrame:
    prepared = runtime.process(event(RuntimeSpeechEvent.PREPARE, provider=provider), available_corrections=CORRECTIONS)
    assert prepared is not None
    generation = runtime.timeline.snapshot.generation
    first = runtime.process(
        event(RuntimeSpeechEvent.FIRST_AUDIO, provider=provider, speech_generation=generation, behavior_generation=2),
        available_corrections=CORRECTIONS,
    )
    assert first is not None
    return first


def assert_five_providers_share_runtime() -> None:
    signatures = set()
    for provider in PROVIDERS:
        engine, _renderer = runtime(seed=7)
        frame = start(engine, provider)
        signatures.add((frame.performance.pose, frame.performance.breath, frame.performance.transition))
    assert len(signatures) == 1


def assert_stale_generation_never_applies() -> None:
    engine, renderer = runtime()
    current = start(engine)
    calls = renderer.calls
    stale = engine.process(
        event(RuntimeSpeechEvent.VISEME, speech_generation=0, behavior_generation=3),
        available_corrections=CORRECTIONS,
    )
    assert stale is current
    assert renderer.calls == calls
    accepted = engine.process(
        event(
            RuntimeSpeechEvent.VISEME,
            speech_generation=engine.timeline.snapshot.generation,
            behavior_generation=8,
        ),
        available_corrections=CORRECTIONS,
    )
    assert accepted is not None
    calls = renderer.calls
    stale_behavior = engine.process(
        event(
            RuntimeSpeechEvent.VISEME,
            speech_generation=engine.timeline.snapshot.generation,
            behavior_generation=7,
        ),
        available_corrections=CORRECTIONS,
    )
    assert stale_behavior is accepted
    assert renderer.calls == calls


def assert_renderer_failure_keeps_last_atomic_frame() -> None:
    engine, renderer = runtime()
    good = start(engine)
    renderer.fail = True
    failed = engine.process(
        event(
            RuntimeSpeechEvent.VISEME,
            speech_generation=engine.timeline.snapshot.generation,
            behavior_generation=3,
        ),
        available_corrections=CORRECTIONS,
    )
    assert failed is good


def assert_interruption_and_failure_keep_closed_safe_frame() -> None:
    for kind in (RuntimeSpeechEvent.INTERRUPT, RuntimeSpeechEvent.FAILURE):
        engine, _renderer = runtime()
        start(engine)
        frame = engine.process(
            event(
                kind,
                speech_generation=engine.timeline.snapshot.generation,
                behavior_generation=3,
            ),
            available_corrections=CORRECTIONS,
        )
        assert frame is not None
        assert frame.performance.mouth_closed
        assert frame.performance.viseme == "CLOSED"
        assert frame.performance.event in {SpeechEventKind.INTERRUPT, SpeechEventKind.FAILURE}


def assert_post_speech_settles_before_motion() -> None:
    engine, _renderer = runtime()
    speaking = start(engine)
    generation = engine.timeline.snapshot.generation
    final = engine.process(
        event(RuntimeSpeechEvent.FINAL_AUDIO, speech_generation=generation, behavior_generation=3),
        available_corrections=CORRECTIONS,
    )
    assert final is not None
    closed = engine.process(
        event(RuntimeSpeechEvent.MOUTH_CLOSED, speech_generation=generation, behavior_generation=4),
        available_corrections=CORRECTIONS,
    )
    assert closed is not None
    assert closed.performance.pose == final.performance.pose == speaking.performance.pose
    assert closed.performance.mouth_closed
    assert closed.performance.transition.value == "hold"
    assert closed.performance.breath.value == "settling"


def assert_preferences_gate_views_and_hands() -> None:
    assert performance_runtime.PerformancePreferences is performance_preferences.PerformancePreferences
    assert "PerformancePreferences" not in performance_runtime.__dict__ or (
        performance_runtime.__dict__["PerformancePreferences"]
        is performance_preferences.PerformancePreferences
    )
    disabled, _renderer = runtime(
        preferences=PerformancePreferences(
            view_360_enabled=False,
            full_back_view_enabled=False,
            left_gestures_enabled=False,
            right_gestures_enabled=False,
        )
    )
    frame = start(disabled)
    assert frame.performance.pose in {"front-crossed", "left-neutral"}
    assert frame.performance.left_hand == "relaxed"
    assert frame.performance.right_hand == "relaxed"


def assert_missing_corrections_fall_back() -> None:
    engine, renderer = runtime()
    good = start(engine)
    calls = renderer.calls
    fallback = engine.process(
        event(
            RuntimeSpeechEvent.VISEME,
            speech_generation=engine.timeline.snapshot.generation,
            behavior_generation=3,
        ),
        available_corrections=frozenset(),
    )
    assert fallback is good
    assert renderer.calls == calls


def assert_deterministic_seed() -> None:
    first, _ = runtime(seed=11)
    second, _ = runtime(seed=11)
    assert start(first).performance == start(second).performance


def run() -> None:
    assert_five_providers_share_runtime()
    assert_stale_generation_never_applies()
    assert_renderer_failure_keeps_last_atomic_frame()
    assert_interruption_and_failure_keep_closed_safe_frame()
    assert_post_speech_settles_before_motion()
    assert_preferences_gate_views_and_hands()
    assert_missing_corrections_fall_back()
    assert_deterministic_seed()
    print("PERFORMANCE_RUNTIME_OK")


def test_performance_runtime_contract() -> None:
    run()


if __name__ == "__main__":
    run()
