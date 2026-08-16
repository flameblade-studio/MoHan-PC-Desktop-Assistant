from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.multisensory_interaction import (
    InteractionKind,
    MultisensoryInteractionArbiter,
    ProactiveInteraction,
    WelcomeStyle,
    WelcomeTimingRules,
    interaction_text,
)
lazy from application.visual_perception import (
    ActivityState,
    LightingState,
    LocalVisualAnalyzer,
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


def observation(
    presence: PresenceState,
    lighting: LightingState = LightingState.COMFORTABLE,
) -> VisualObservation:
    return VisualObservation(
        observed_at=0.0,
        presence=presence,
        lighting=lighting,
        activity=ActivityState.STILL,
        brightness=80.0,
        motion=0.0,
    )


def assert_local_visual_analysis() -> None:
    clock = Clock()
    analyzer = LocalVisualAnalyzer(clock=clock, presence_hold_seconds=45.0)
    first = analyzer.analyze([80] * 12)
    assert first.presence is PresenceState.AWAY
    assert first.lighting is LightingState.COMFORTABLE
    clock.advance(1)
    moving = analyzer.analyze([100, 60] * 6)
    assert moving.presence is PresenceState.PRESENT
    assert moving.activity is ActivityState.ACTIVE
    clock.advance(44)
    assert analyzer.analyze([100, 60] * 6).presence is PresenceState.PRESENT
    clock.advance(2)
    assert analyzer.analyze([100, 60] * 6).presence is PresenceState.AWAY
    assert analyzer.analyze([0] * 12).lighting is LightingState.DARK
    analyzer.reset()
    assert analyzer.analyze([220] * 12).lighting is LightingState.BRIGHT


def assert_proactive_arbiter() -> None:
    clock = Clock()
    arbiter = MultisensoryInteractionArbiter(
        minimum_away_seconds=60,
        clock=clock,
    )
    daytime = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert arbiter.consider(
        observation(PresenceState.AWAY),
        proactive_mode="平衡（推薦）",
        wall_time=daytime,
        busy=False,
    ) is None
    clock.advance(59)
    assert arbiter.consider(
        observation(PresenceState.PRESENT),
        proactive_mode="平衡（推薦）",
        wall_time=daytime,
        busy=False,
    ) is None
    arbiter.consider(
        observation(PresenceState.AWAY),
        proactive_mode="平衡（推薦）",
        wall_time=daytime,
        busy=False,
    )
    clock.advance(61)
    welcome = arbiter.consider(
        observation(PresenceState.PRESENT),
        proactive_mode="平衡（推薦）",
        wall_time=daytime,
        busy=False,
    )
    assert welcome is not None
    assert welcome.kind is InteractionKind.WELCOME_BACK
    assert arbiter.consider(
        observation(PresenceState.PRESENT, LightingState.DIM),
        proactive_mode="平衡（推薦）",
        wall_time=daytime,
        busy=False,
    ) is None


def assert_quiet_and_busy_guards() -> None:
    for mode, moment, busy in (
        ("安靜（只提醒必要事項）", datetime(2026, 8, 13, 12, 0, tzinfo=UTC), False),
        ("積極（主動建議）", datetime(2026, 8, 13, 23, 0, tzinfo=UTC), False),
        ("積極（主動建議）", datetime(2026, 8, 13, 12, 0, tzinfo=UTC), True),
    ):
        clock = Clock()
        arbiter = MultisensoryInteractionArbiter(
            minimum_away_seconds=1,
            clock=clock,
        )
        arbiter.consider(
            observation(PresenceState.AWAY),
            proactive_mode=mode,
            wall_time=moment,
            busy=False,
        )
        clock.advance(2)
        assert arbiter.consider(
            observation(PresenceState.PRESENT),
            proactive_mode=mode,
            wall_time=moment,
            busy=busy,
        ) is None


def assert_welcome_timing_boundaries() -> None:
    rules = WelcomeTimingRules()
    assert rules.minimum_away_seconds == 60
    assert rules.brief_max_seconds == 30 * 60
    assert rules.long_away_seconds == 4 * 60 * 60
    for invalid in (
        (60, 60, 3600),
        (60, 3600, 3600),
        (3600, 60, 7200),
    ):
        try:
            WelcomeTimingRules(*invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("contradictory welcome timing must be rejected")

    clock = Clock()
    arbiter = MultisensoryInteractionArbiter(timing=rules, clock=clock)
    daytime = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    arbiter.consider(observation(PresenceState.AWAY), proactive_mode="active", wall_time=daytime, busy=False)
    clock.advance(30 * 60)
    brief = arbiter.consider(observation(PresenceState.PRESENT), proactive_mode="active", wall_time=daytime, busy=False)
    assert brief is not None and brief.style is WelcomeStyle.WARM

    clock = Clock()
    arbiter = MultisensoryInteractionArbiter(timing=rules, clock=clock)
    arbiter.consider(observation(PresenceState.AWAY), proactive_mode="active", wall_time=daytime, busy=False)
    clock.advance(30 * 60 + 1)
    general = arbiter.consider(observation(PresenceState.PRESENT), proactive_mode="active", wall_time=daytime, busy=False)
    assert general is not None and general.style is WelcomeStyle.GENERAL

    custom = interaction_text(
        "zh-TW",
        ProactiveInteraction(InteractionKind.WELCOME_BACK, "happy", WelcomeStyle.CEREMONIAL),
        user_title="主上",
        wall_time=daytime,
        custom_welcome={WelcomeStyle.CEREMONIAL: "恭迎主上"},
    )
    assert custom == "恭迎主上"


def assert_four_language_lines() -> None:
    interaction = ProactiveInteraction(InteractionKind.WELCOME_BACK, "happy")
    lines = {
        language: interaction_text(language, interaction, user_title="Owner")
        for language in ("zh-TW", "zh-CN", "en-US", "ja-JP")
    }
    assert all("Owner" in line for line in lines.values())
    assert len(set(lines.values())) == 4
    assert "主上" in interaction_text("zh-TW", interaction, user_title="主上")
    diagnostic_words = ("辨識", "识别", "recognized", "confidence", "認識度")
    assert all(
        word.casefold() not in line.casefold()
        for line in lines.values()
        for word in diagnostic_words
    )
    assert "早安" in interaction_text(
        "zh-TW",
        interaction,
        user_title="主上",
        wall_time=datetime(2026, 8, 13, 8, 0, tzinfo=UTC),
    )
    assert "書" in interaction_text(
        "zh-TW",
        interaction,
        user_title="主上",
        wall_time=datetime(2026, 8, 13, 14, 0, tzinfo=UTC),
        activities=("possible_reading",),
    )


def assert_proactive_conversation_requires_identity_and_silence() -> None:
    clock = Clock()
    arbiter = MultisensoryInteractionArbiter(
        conversation_silence_seconds=10 * 60,
        clock=clock,
    )
    daytime = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    clock.advance(10 * 60)
    assert arbiter.consider(
        observation(PresenceState.PRESENT),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=False,
    ) is None
    check_in = arbiter.consider(
        observation(PresenceState.PRESENT),
        proactive_mode="active",
        wall_time=daytime,
        busy=False,
        recognized_user=True,
    )
    assert check_in is not None
    assert check_in.kind is InteractionKind.GENTLE_CHECK_IN


def run() -> None:
    assert_local_visual_analysis()
    assert_proactive_arbiter()
    assert_quiet_and_busy_guards()
    assert_welcome_timing_boundaries()
    assert_four_language_lines()
    assert_proactive_conversation_requires_identity_and_silence()


if __name__ == "__main__":
    run()
    print("MULTISENSORY_VISION_OK")
