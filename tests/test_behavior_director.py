from __future__ import annotations

lazy import sys
lazy from dataclasses import FrozenInstanceError, replace
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from behavior_director import (
    BehaviorDirector,
    BehaviorInput,
    BodyPerformancePlan,
    BreathStyle,
    GazeTarget,
    SemanticEmotion,
    SpeechLifecycle,
    TransitionStyle,
)

PAIR_LENGTH = 2
MIN_HOLD_MS = 2_200


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def context(**changes: object) -> BehaviorInput:
    values = {
        "speech": SpeechLifecycle.IDLE,
        "emotion": SemanticEmotion.NEUTRAL,
        "intensity": 0.5,
        "current_pose": "front-crossed",
        "previous_action": "idle",
        "disabled": False,
    }
    values.update(changes)
    return BehaviorInput(
        speech=values["speech"],
        emotion=values["emotion"],
        emotion_intensity=values["intensity"],
        conversation_turn=3,
        user_in_gaze=True,
        user_present=True,
        away_seconds=0.0,
        current_pose=values["current_pose"],
        previous_action=values["previous_action"],
        proactive_performance_disabled=values["disabled"],
    )


def assert_frozen_typed_contract() -> None:
    value = context()
    try:
        value.current_pose = "changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("BehaviorInput must be frozen")
    plan = BodyPerformancePlan(
        "front-crossed", "front-000", "neutral", "relaxed", "relaxed",
        GazeTarget.USER, BreathStyle.CALM, TransitionStyle.HOLD, 1000,
    )
    try:
        plan.pose = "changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("BodyPerformancePlan must be frozen")


def assert_deterministic_and_seeded_variation() -> None:
    first = BehaviorDirector(clock=lambda: 0.0, seed=7).direct(context())
    repeat = BehaviorDirector(clock=lambda: 0.0, seed=7).direct(context())
    assert first == repeat
    variants = {
        BehaviorDirector(clock=lambda: 0.0, seed=seed).direct(context()).pose
        for seed in range(12)
    }
    assert len(variants) >= PAIR_LENGTH
    assert variants <= {
        "front-crossed",
        "left-neutral",
        "right-neutral",
        "left-cheek-rest",
    }
    turn_zero = BehaviorDirector(clock=lambda: 0.0, seed=7).direct(
        replace(context(), conversation_turn=0)
    )
    turn_one = BehaviorDirector(clock=lambda: 0.0, seed=7).direct(
        replace(context(), conversation_turn=1)
    )
    assert turn_zero.pose != turn_one.pose


def assert_anger_progression_and_recovery() -> None:
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=4, cooldown_ms=0)
    heartfelt = context(emotion=SemanticEmotion.ANGRY, intensity=0.95)
    side = director.direct(heartfelt)
    assert side.pose in {"left-neutral", "right-neutral"}
    assert side.transition is TransitionStyle.TURN_AWAY
    clock.advance(5)
    two_thirds = director.direct(heartfelt)
    assert two_thirds.pose.startswith("back-two-thirds-")
    clock.advance(5)
    full = director.direct(heartfelt)
    assert full.pose == "back-full"
    assert full.gaze is GazeTarget.AWAY

    clock.advance(5)
    recovery_two_thirds = director.direct(context())
    assert recovery_two_thirds.pose.startswith("back-two-thirds-")
    assert recovery_two_thirds.transition is TransitionStyle.TURN_BACK
    clock.advance(5)
    recovery_side = director.direct(context())
    assert recovery_side.pose in {"left-neutral", "right-neutral"}
    clock.advance(5)
    recovered = director.direct(context())
    assert recovered.pose == "front-crossed"
    assert recovered.transition is TransitionStyle.TURN_BACK


def assert_anger_levels_and_no_keyword_trigger() -> None:
    mild = BehaviorDirector(clock=lambda: 0.0, seed=2).direct(
        context(emotion=SemanticEmotion.ANGRY, intensity=0.3)
    )
    assert mild.pose in {"left-neutral", "right-neutral"}
    negative_but_not_angry = BehaviorDirector(clock=lambda: 0.0, seed=2).direct(
        context(emotion=SemanticEmotion.SAD, intensity=1.0, previous_action="angry words")
    )
    assert not negative_but_not_angry.pose.startswith("back-")
    assert "angry" not in negative_but_not_angry.face


def assert_speech_is_always_safe_and_synchronized() -> None:
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=8, cooldown_ms=0)
    for emotion in SemanticEmotion:
        plan = director.direct(
            context(
                speech=SpeechLifecycle.SPEAKING,
                emotion=emotion,
                intensity=1.0,
            )
        )
        assert plan.pose in {"front-crossed", "left-neutral", "right-neutral"}
        assert plan.breath is BreathStyle.SPEAKING
        assert plan.pose != "back-full"
        clock.advance(5)


def assert_safety_and_reminder_preempt_hold() -> None:
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=3)
    ambient = director.direct(context())
    safety = director.direct(
        context(emotion=SemanticEmotion.SAFETY, intensity=1.0)
    )
    assert safety != ambient
    assert safety.transition is TransitionStyle.SAFETY
    assert safety.face == "protective"
    clock.advance(4)
    reminder = director.direct(
        context(emotion=SemanticEmotion.REMINDER, intensity=0.8)
    )
    assert reminder.face == "reminder"


def assert_minimum_hold_prevents_twitch_and_then_varies() -> None:
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=1, cooldown_ms=0)
    first = director.direct(context())
    clock.advance(0.05)
    second = director.direct(
        context(emotion=SemanticEmotion.HAPPY, intensity=0.9)
    )
    assert second is first
    clock.advance(5)
    third = director.direct(
        context(emotion=SemanticEmotion.HAPPY, intensity=0.9)
    )
    assert third.hold_ms >= MIN_HOLD_MS
    assert third.face == "gentle-smile"


def assert_speech_preempts_unsafe_back_without_twitch() -> None:
    """Ruling 2026-08-27: speech recovers from back-full one depth at a time.

    The earlier expectation (back-full straight to a side/front pose) was
    itself the forbidden two-level pose jump: the renderer's crossfade
    safety check rejects it and keeps the old frame, which is how the
    permanent back-turned lock manifested.  She now turns back through the
    gradient while speaking, one safe step per hold window.
    """
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=5, cooldown_ms=0)
    angry = context(emotion=SemanticEmotion.ANGRY, intensity=0.95)
    director.direct(angry)
    clock.advance(5)
    director.direct(angry)
    clock.advance(5)
    full = director.direct(angry)
    assert full.pose == "back-full"
    speech = context(
        speech=SpeechLifecycle.SPEAKING,
        emotion=SemanticEmotion.NEUTRAL,
    )
    poses = []
    for _ in range(8):
        plan = director.direct(speech)
        if not poses or plan.pose != poses[-1]:
            poses.append(plan.pose)
        assert plan.breath is BreathStyle.SPEAKING
        if plan.pose in {"left-neutral", "right-neutral", "front-crossed"}:
            break
        clock.advance(5)
    else:
        raise AssertionError(f"speech never reached a visible pose: {poses}")
    depths = {"back-full": 3}
    depths.update({f"back-two-thirds-{s}": 2 for s in ("left", "right")})
    depths.update({f"{s}-neutral": 1 for s in ("left", "right")})
    trail = [3, *(depths.get(pose, 0) for pose in poses)]
    assert all(
        abs(a - b) <= 1 for a, b in zip(trail, trail[1:], strict=False)
    ), f"unsafe pose jump in recovery trail: {trail}"


def assert_disabled_and_absent_fallbacks() -> None:
    disabled = BehaviorDirector(clock=lambda: 0.0, seed=9).direct(
        context(current_pose="left-cheek-rest", disabled=True)
    )
    assert disabled.pose == "left-cheek-rest"
    assert disabled.face == "neutral"
    assert disabled.transition is TransitionStyle.HOLD


def assert_disabled_while_turned_away_never_freezes() -> None:
    """Ruling 2026-08-28: disabling performances mid-back-turn must not throw.

    The old plan gazed at the user from a rear pose, violating the
    BodyPerformancePlan contract on every frame; the runtime swallowed the
    error and froze the screen on her back permanently.  Side poses also
    rendered from the opposite camera (right-neutral shown as left-030).
    """
    for pose, view in (
        ("back-full", "back-180"),
        ("back-two-thirds-right", "back-right-120"),
        ("right-neutral", "right-045"),
        ("left-neutral", "left-045"),
    ):
        plan = BehaviorDirector(clock=lambda: 0.0, seed=9).direct(
            context(current_pose=pose, disabled=True)
        )
        assert plan.pose == pose
        assert plan.view == view


def assert_right_side_anger_stays_on_her_right() -> None:
    """right-neutral must set the side memory to "right" (2026-08-28)."""
    clock = Clock()
    director = BehaviorDirector(clock=clock, seed=1, cooldown_ms=0)
    angry = context(emotion=SemanticEmotion.ANGRY, intensity=0.95)
    first = director.direct(angry)
    assert first.pose.endswith("-neutral")
    side = "right" if first.pose.startswith("right") else "left"
    clock.advance(5)
    second = director.direct(angry)
    assert second.pose == f"back-two-thirds-{side}", (
        f"escalation flipped sides: {first.pose} -> {second.pose}"
    )
    absent = BehaviorInput(
        speech=SpeechLifecycle.IDLE,
        emotion=SemanticEmotion.NEUTRAL,
        emotion_intensity=0.5,
        conversation_turn=0,
        user_in_gaze=False,
        user_present=False,
        away_seconds=300,
        current_pose="front-crossed",
        previous_action="idle",
    )
    waiting = BehaviorDirector(clock=lambda: 0.0, seed=1).direct(absent)
    assert waiting.pose == "front-crossed"
    assert waiting.gaze is GazeTarget.DOWN


def assert_atomic_conflict_guards() -> None:
    try:
        BodyPerformancePlan(
            "back-full", "back-180", "hidden", "open", "relaxed",
            GazeTarget.USER, BreathStyle.HELD, TransitionStyle.TURN_AWAY, 2000,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Conflicting back-view layers must be rejected")


def run() -> None:
    assert_frozen_typed_contract()
    assert_deterministic_and_seeded_variation()
    assert_anger_progression_and_recovery()
    assert_anger_levels_and_no_keyword_trigger()
    assert_speech_is_always_safe_and_synchronized()
    assert_safety_and_reminder_preempt_hold()
    assert_minimum_hold_prevents_twitch_and_then_varies()
    assert_speech_preempts_unsafe_back_without_twitch()
    assert_disabled_and_absent_fallbacks()
    assert_disabled_while_turned_away_never_freezes()
    assert_right_side_anger_stays_on_her_right()
    assert_atomic_conflict_guards()
    print("BEHAVIOR_DIRECTOR_OK")


if __name__ == "__main__":
    run()
