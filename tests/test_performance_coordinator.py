from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from behavior_director import (
    BehaviorInput,
    BodyPerformancePlan,
    BreathStyle,
    GazeTarget,
    SemanticEmotion,
    SpeechLifecycle,
    TransitionStyle,
)
lazy from character_pose import canonical_view_id
lazy from performance_coordinator import PerformanceCoordinator
lazy from performance_preferences import PerformancePreferences
lazy from speech_performance import (
    SpeechEvent,
    SpeechEventKind,
    SpeechPerformanceDirective,
    SpeechPerformancePhase,
)

PROVIDERS = ("windows", "openai", "realtime", "azure", "dragon-hd")


@dataclass(frozen=True, slots=True)
class FakePose:
    pose_id: str
    speech_safe: bool
    required_corrections: frozenset[str]


class FakeRegistry:
    def __init__(self) -> None:
        self.poses = {
            "front-crossed": FakePose("front-crossed", True, frozenset({"front"})),
            "left-neutral": FakePose("left-neutral", True, frozenset({"left"})),
            "right-neutral": FakePose("right-neutral", True, frozenset({"right"})),
            "back-two-thirds-left": FakePose(
                "back-two-thirds-left", False, frozenset({"back-120"})
            ),
            "back-full": FakePose("back-full", False, frozenset({"back-180"})),
        }

    def get(self, pose_id: str) -> FakePose | None:
        return self.poses.get(pose_id)

    def available(self, pose_id: str, corrections: object) -> bool:
        pose = self.get(pose_id)
        return bool(pose and pose.required_corrections <= frozenset(corrections))


ALL_CORRECTIONS = frozenset({"front", "left", "right", "back-120", "back-180"})


def context(
    *,
    speech: SpeechLifecycle = SpeechLifecycle.IDLE,
    emotion: SemanticEmotion = SemanticEmotion.NEUTRAL,
) -> BehaviorInput:
    return BehaviorInput(
        speech, emotion, 0.5, 1, True, True, 0.0,
        "front-crossed", "idle", False,
    )


def plan(
    pose: str = "front-crossed",
    *,
    face: str = "neutral",
    left: str = "relaxed",
    right: str = "relaxed",
    transition: TransitionStyle = TransitionStyle.SOFT,
) -> BodyPerformancePlan:
    views = {
        "front-crossed": "front-000",
        "left-neutral": "left-030",
        "right-neutral": "right-030",
        "back-two-thirds-left": "back-left-120",
        "back-full": "back-180",
    }
    return BodyPerformancePlan(
        pose, views[pose], face, left, right,
        GazeTarget.AWAY if pose.startswith("back-") else GazeTarget.USER,
        BreathStyle.CALM, transition, 1800,
    )


def event(
    kind: SpeechEventKind,
    *,
    generation: int = 1,
    provider: str = "provider",
    viseme: str = "A",
    level: float = 0.7,
) -> SpeechEvent:
    return SpeechEvent(generation, provider, kind, 1.0, level, viseme)


def directive(
    phase: SpeechPerformancePhase,
    *,
    generation: int = 1,
    gesture: bool = False,
    hold: bool = False,
) -> SpeechPerformanceDirective:
    return SpeechPerformanceDirective(
        generation, phase, 0.4, 0.3, 0.6, gesture,
        phase in {SpeechPerformancePhase.IDLE, SpeechPerformancePhase.PREPARING},
        hold, "test",
    )


def coordinate(
    coordinator: PerformanceCoordinator,
    kind: SpeechEventKind,
    phase: SpeechPerformancePhase,
    body: BodyPerformancePlan,
    **options: object,
):
    generation = int(options.get("generation", 1))
    behavior_generation = int(options.get("behavior_generation", 1))
    provider = str(options.get("provider", "provider"))
    gesture = bool(options.get("gesture", False))
    corrections = frozenset(options.get("corrections", ALL_CORRECTIONS))
    return coordinator.coordinate(
        event=event(kind, generation=generation, provider=provider),
        directive=directive(phase, generation=generation, gesture=gesture),
        behavior_generation=behavior_generation,
        context=context(
            speech=(SpeechLifecycle.SPEAKING if phase is SpeechPerformancePhase.SPEAKING else SpeechLifecycle.IDLE)
        ),
        plan=body,
        available_corrections=corrections,
    )


def assert_all_providers_share_one_path() -> None:
    signatures = set()
    for provider in PROVIDERS:
        coordinator = PerformanceCoordinator(FakeRegistry())
        frame = coordinate(
            coordinator, SpeechEventKind.FIRST_AUDIO,
            SpeechPerformancePhase.SPEAKING, plan(), provider=provider,
        )
        assert frame is not None
        assert frame.view == canonical_view_id(0)
        signatures.add((frame.pose, frame.face, frame.breath, frame.transition))
    assert len(signatures) == 1


def assert_canonical_preferences_are_enforced() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    selected = coordinator.apply_preferences(
        plan("front-crossed"),
        PerformancePreferences(
            left_gestures_enabled=False,
            right_gestures_enabled=False,
        ),
    )
    assert selected.left_hand == "relaxed"
    assert selected.right_hand == "relaxed"

    class DuplicatePreferences:
        view_360_enabled = False
        full_back_view_enabled = False
        left_gestures_enabled = False
        right_gestures_enabled = False

    try:
        coordinator.apply_preferences(
            plan("front-crossed"),
            DuplicatePreferences(),  # type: ignore[arg-type]
        )
    except TypeError as error:
        assert "canonical model" in str(error)
    else:
        raise AssertionError("Duplicate preference models must fail closed.")


def assert_legacy_views_normalize_at_boundary() -> None:
    legacy_views = (
        ("front-crossed", canonical_view_id(0)),
        ("left-neutral", canonical_view_id(-30)),
        ("right-neutral", canonical_view_id(30)),
        ("back-two-thirds-left", canonical_view_id(-120)),
        ("back-full", canonical_view_id(-180)),
    )
    coordinator = PerformanceCoordinator(FakeRegistry())
    for behavior_generation, (pose_id, expected_view) in enumerate(
        legacy_views,
        start=1,
    ):
        frame = coordinate(
            coordinator,
            SpeechEventKind.PREPARE,
            SpeechPerformancePhase.PREPARING,
            plan(pose_id, face=("hidden" if pose_id.startswith("back-") else "neutral")),
            behavior_generation=behavior_generation,
        )
        assert frame is not None
        assert frame.view == expected_view


def assert_speech_safe_and_gesture_beats() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    first = coordinate(
        coordinator, SpeechEventKind.FIRST_AUDIO,
        SpeechPerformancePhase.SPEAKING,
        plan("front-crossed", left="open", right="open"),
    )
    assert first is not None and first.pose == "front-crossed"
    assert first.left_hand == "open"
    ordinary = coordinate(
        coordinator, SpeechEventKind.VISEME,
        SpeechPerformancePhase.SPEAKING,
        plan("front-crossed", left="point", right="open"),
        behavior_generation=2,
    )
    assert ordinary is not None and not ordinary.gesture_beat
    assert ordinary.left_hand == "open"
    beat = coordinate(
        coordinator, SpeechEventKind.SEGMENT_BOUNDARY,
        SpeechPerformancePhase.SPEAKING,
        plan("front-crossed", left="point", right="open"),
        behavior_generation=3, gesture=True,
    )
    assert beat is not None and beat.gesture_beat
    assert beat.left_hand == "point"


def assert_large_turn_is_forbidden_during_audio() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    front = coordinate(
        coordinator,
        SpeechEventKind.FIRST_AUDIO,
        SpeechPerformancePhase.SPEAKING,
        plan("front-crossed"),
    )
    assert front is not None
    attempted_back = coordinate(
        coordinator,
        SpeechEventKind.SEGMENT_BOUNDARY,
        SpeechPerformancePhase.SPEAKING,
        plan("back-two-thirds-left", face="hidden"),
        behavior_generation=2,
        gesture=True,
    )
    assert attempted_back is not None
    assert attempted_back.pose == "front-crossed"
    assert attempted_back.transition is TransitionStyle.HOLD


def assert_existing_back_can_speak_without_turning() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    seeded = coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan("back-full", face="hidden"),
    )
    assert seeded is not None and seeded.pose == "back-full"
    speaking = coordinate(
        coordinator, SpeechEventKind.FIRST_AUDIO,
        SpeechPerformancePhase.SPEAKING, plan("front-crossed"),
        behavior_generation=2,
    )
    assert speaking is not None
    assert speaking.pose == "back-full"
    assert speaking.face is None
    assert speaking.gaze is GazeTarget.AWAY
    assert speaking.breath is BreathStyle.SPEAKING
    assert speaking.transition is TransitionStyle.HOLD


def assert_closed_settle_then_stepwise_return() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    coordinate(coordinator, SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING, plan("left-neutral"))
    coordinate(
        coordinator, SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING,
        plan("back-two-thirds-left", face="hidden"), behavior_generation=2,
    )
    coordinate(
        coordinator, SpeechEventKind.PREPARE, SpeechPerformancePhase.PREPARING,
        plan("back-full", face="hidden"), behavior_generation=3,
    )
    coordinate(
        coordinator, SpeechEventKind.FIRST_AUDIO, SpeechPerformancePhase.SPEAKING,
        plan("front-crossed"), behavior_generation=4,
    )
    final = coordinate(
        coordinator, SpeechEventKind.FINAL_AUDIO, SpeechPerformancePhase.SETTLING,
        plan("front-crossed"), behavior_generation=5,
    )
    assert final is not None and final.pose == "back-full"
    closed = coordinate(
        coordinator, SpeechEventKind.MOUTH_CLOSED, SpeechPerformancePhase.IDLE,
        plan("back-two-thirds-left", face="hidden"), behavior_generation=6,
    )
    assert closed is not None
    assert closed.pose == "back-full"
    assert closed.mouth_closed and closed.viseme == "CLOSED"
    assert closed.breath is BreathStyle.SETTLING
    assert closed.transition is TransitionStyle.HOLD
    step = coordinate(
        coordinator, SpeechEventKind.MOUTH_CLOSED, SpeechPerformancePhase.IDLE,
        plan("back-two-thirds-left", face="hidden"), behavior_generation=7,
    )
    assert step is not None and step.pose == "back-two-thirds-left"
    side = coordinate(
        coordinator, SpeechEventKind.MOUTH_CLOSED, SpeechPerformancePhase.IDLE,
        plan("left-neutral"), behavior_generation=8,
    )
    assert side is not None and side.pose == "left-neutral"


def assert_missing_assets_hold_last_good() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    good = coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan(),
    )
    assert good is not None
    missing = coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan("left-neutral"),
        behavior_generation=2, corrections=frozenset({"front"}),
    )
    assert missing is not None and missing.fallback
    assert missing.pose == good.pose
    unknown = BodyPerformancePlan(
        "unknown", "unknown", "neutral", "relaxed", "relaxed",
        GazeTarget.USER, BreathStyle.CALM, TransitionStyle.SOFT, 1800,
    )
    held = coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, unknown, behavior_generation=3,
    )
    assert held is not None and held.pose == good.pose and held.fallback


def assert_generations_reject_stale_frames() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    assert coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan(), generation=3,
        behavior_generation=5,
    ) is not None
    assert coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan(), generation=2,
        behavior_generation=6,
    ) is None
    assert coordinate(
        coordinator, SpeechEventKind.PREPARE,
        SpeechPerformancePhase.PREPARING, plan(), generation=3,
        behavior_generation=4,
    ) is None
    mismatched = coordinator.coordinate(
        event=event(SpeechEventKind.PREPARE, generation=4),
        directive=directive(SpeechPerformancePhase.PREPARING, generation=5),
        behavior_generation=7,
        context=context(),
        plan=plan(),
        available_corrections=ALL_CORRECTIONS,
    )
    assert mismatched is None


def assert_safety_event_is_atomic_and_speech_safe() -> None:
    coordinator = PerformanceCoordinator(FakeRegistry())
    frame = coordinator.coordinate(
        event=event(SpeechEventKind.FIRST_AUDIO),
        directive=directive(SpeechPerformancePhase.SPEAKING),
        behavior_generation=1,
        context=context(
            speech=SpeechLifecycle.SPEAKING,
            emotion=SemanticEmotion.SAFETY,
        ),
        plan=plan("front-crossed", face="protective", left="open", right="open"),
        available_corrections=ALL_CORRECTIONS,
    )
    assert frame is not None
    assert frame.pose == "front-crossed"
    assert frame.face == "protective"
    assert frame.breath is BreathStyle.SPEAKING


def run() -> None:
    assert_canonical_preferences_are_enforced()
    assert_all_providers_share_one_path()
    assert_legacy_views_normalize_at_boundary()
    assert_speech_safe_and_gesture_beats()
    assert_large_turn_is_forbidden_during_audio()
    assert_existing_back_can_speak_without_turning()
    assert_closed_settle_then_stepwise_return()
    assert_missing_assets_hold_last_good()
    assert_generations_reject_stale_frames()
    assert_safety_event_is_atomic_and_speech_safe()
    print("PERFORMANCE_COORDINATOR_OK")


def test_performance_coordinator_contract() -> None:
    run()


if __name__ == "__main__":
    run()
