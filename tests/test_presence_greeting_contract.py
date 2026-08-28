from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.camera_presence import PresenceDebouncer
lazy from application.multisensory_interaction import (
    InteractionKind,
    MultisensoryInteractionArbiter,
    WelcomeStyle,
    WelcomeTimingRules,
)
lazy from application.visual_perception import (
    ActivityState,
    LightingState,
    PresenceState,
    VisualObservation,
)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def observation(presence: PresenceState, observed_at: float) -> VisualObservation:
    return VisualObservation(
        observed_at,
        presence,
        LightingState.COMFORTABLE,
        ActivityState.STILL,
        80.0,
        0.0,
    )


def assert_brief_occlusion_does_not_create_return_transition() -> None:
    debouncer = PresenceDebouncer(dropout_grace_seconds=5.0)
    assert debouncer.stabilize(observation(PresenceState.PRESENT, 0.0)).presence is PresenceState.PRESENT
    for moment in (1.0, 2.0, 4.9):
        stable = debouncer.stabilize(observation(PresenceState.AWAY, moment))
        assert stable.presence is PresenceState.PRESENT
    recovered = debouncer.stabilize(observation(PresenceState.PRESENT, 5.0))
    assert recovered.presence is PresenceState.PRESENT


def assert_sustained_absence_and_return_are_single_shot() -> None:
    clock = Clock()
    arbiter = MultisensoryInteractionArbiter(
        timing=WelcomeTimingRules(60.0, 30.0 * 60.0, 4.0 * 60.0 * 60.0),
        clock=clock,
    )
    daytime = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    arbiter.consider(
        observation(PresenceState.PRESENT, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
    )
    arbiter.consider(
        observation(PresenceState.AWAY, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
    )
    clock.advance(61.0)
    welcome = arbiter.consider(
        observation(PresenceState.PRESENT, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=True,
    )
    assert welcome is not None
    assert welcome.kind is InteractionKind.WELCOME_BACK
    assert welcome.style is WelcomeStyle.WARM
    assert arbiter.consider(
        observation(PresenceState.PRESENT, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=True,
    ) is None


def assert_long_wait_and_unknown_identity_are_explicit() -> None:
    daytime = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    clock = Clock()
    rules = WelcomeTimingRules()
    arbiter = MultisensoryInteractionArbiter(timing=rules, clock=clock)
    arbiter.consider(
        observation(PresenceState.AWAY, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
    )
    clock.advance(rules.long_away_seconds)
    welcome = arbiter.consider(
        observation(PresenceState.PRESENT, clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=True,
    )
    assert welcome is not None and welcome.style is WelcomeStyle.CEREMONIAL

    unknown_clock = Clock()
    unknown = MultisensoryInteractionArbiter(
        conversation_silence_seconds=10.0 * 60.0,
        clock=unknown_clock,
    )
    unknown_clock.advance(10.0 * 60.0)
    assert unknown.consider(
        observation(PresenceState.PRESENT, unknown_clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=False,
    ) is None
    known = unknown.consider(
        observation(PresenceState.PRESENT, unknown_clock.now),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=True,
    )
    assert known is not None and known.kind is InteractionKind.GENTLE_CHECK_IN


def assert_camera_read_gap_preserves_state_and_reset_is_explicit() -> None:
    debouncer = PresenceDebouncer(dropout_grace_seconds=5.0)
    present = debouncer.stabilize(observation(PresenceState.PRESENT, 1.0))
    assert present.presence is PresenceState.PRESENT
    # A failed read does not call stabilize, so no state transition can occur.
    recovered = debouncer.stabilize(observation(PresenceState.PRESENT, 30.0))
    assert recovered.presence is PresenceState.PRESENT
    debouncer.reset()
    away = debouncer.stabilize(observation(PresenceState.AWAY, 31.0))
    assert away.presence is PresenceState.AWAY


def run() -> None:
    assert_brief_occlusion_does_not_create_return_transition()
    assert_sustained_absence_and_return_are_single_shot()
    assert_long_wait_and_unknown_identity_are_explicit()
    assert_camera_read_gap_preserves_state_and_reset_is_explicit()
    print("PRESENCE_GREETING_CONTRACT_OK")


if __name__ == "__main__":
    run()
