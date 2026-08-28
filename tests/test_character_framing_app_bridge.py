from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.character_framing import CharacterFramingDirector, FramingMode
lazy from application.character_framing_app_bridge import (
    AppFramingState,
    CharacterFramingAppBridge,
    FramingBridgeDisposition,
    FramingBridgeInput,
)
lazy from domain.framing_context_policy import (
    EmotionValence,
    FocusState,
    FramingPolicyContext,
)
lazy from application.framing_orchestrator import FramingOrchestrator
lazy from domain.framing_preferences import FramingPreferences
lazy from application.wellbeing_reminder import (
    ReminderExpression,
    ReminderFraming,
    ReminderGaze,
    ReminderGesture,
    ReminderStage,
    WellbeingCue,
    WellbeingKind,
)

EXPECTED_GENERATION = 7


class Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float = 2.0) -> None:
        self.value += seconds


class SwitchableOrchestrator:
    def __init__(self, delegate) -> None:
        self.delegate = delegate

    def decide(self, request):
        if self.delegate is None:
            raise RuntimeError("orchestration failed")
        return self.delegate.decide(request)


def policy(**changes: object) -> FramingPolicyContext:
    value = FramingPolicyContext(
        away_seconds=0.0,
        returned_to_seat=False,
        intimacy=0.5,
        emotion_intensity=0.2,
        emotion_valence=EmotionValence.NEUTRAL,
        angry_back_turn=False,
        speech_active=False,
        mouth_closed=True,
        gesture_bounds=None,
        weapon_or_large_prop=False,
        outfit_preview=False,
        focus_state=FocusState.AVAILABLE,
        proactive_greeting=False,
        close_framing_allowed=True,
    )
    return replace(value, **changes)


def state(
    generation: int = 1,
    *,
    context: FramingPolicyContext | None = None,
    enabled: bool = True,
) -> AppFramingState:
    return AppFramingState(
        generation,
        context or policy(),
        1280,
        900,
        enabled,
    )


def value(
    app_state: AppFramingState,
    *,
    cue: WellbeingCue | None = None,
    preferences: FramingPreferences | None = None,
) -> FramingBridgeInput:
    return FramingBridgeInput(
        app_state,
        preferences or FramingPreferences(),
        cue,
    )


def cue() -> WellbeingCue:
    return WellbeingCue(
        "meal-approved-1",
        WellbeingKind.MEAL,
        ReminderStage.RESTRAINED_REINFORCEMENT,
        ReminderExpression.RESTRAINED_TSUNDERE,
        ReminderGaze.USER,
        ReminderGesture.OPEN_HAND,
        ReminderFraming.CLOSE_CANDIDATE,
        "wellbeing.meal.restrained_reinforcement",
        "wellbeing-approved",
    )


def bridge(clock: Clock | None = None) -> CharacterFramingAppBridge:
    timer = clock or Clock()
    director = CharacterFramingDirector(timer)
    return CharacterFramingAppBridge(FramingOrchestrator(director))


def assert_atomic_command_has_generation_crop_transition_and_audit() -> None:
    result = bridge().dispatch(value(state(7), cue=cue()))
    assert result.disposition is FramingBridgeDisposition.EMITTED
    command = result.command
    assert command is not None
    assert command.generation == EXPECTED_GENERATION
    assert command.mode is FramingMode.CLOSE
    assert command.crop.width > 0.0 and command.crop.height > 0.0
    assert command.transition_ms > 0
    assert command.reason_chain
    assert any(entry.code == "approved-wellbeing-cue" for entry in command.reason_chain)


def assert_disabled_is_complete_legacy_bypass() -> None:
    app_bridge = bridge()
    result = app_bridge.dispatch(value(state(enabled=False), cue=cue()))
    assert result.disposition is FramingBridgeDisposition.BYPASSED
    assert result.command is None
    assert app_bridge.last_known_good is None


def assert_stale_and_duplicate_never_emit() -> None:
    app_bridge = bridge()
    current = value(state(4))
    assert app_bridge.dispatch(current).disposition is FramingBridgeDisposition.EMITTED
    assert app_bridge.dispatch(current).disposition is FramingBridgeDisposition.DUPLICATE
    stale = app_bridge.dispatch(value(state(3, context=policy(outfit_preview=True))))
    assert stale.disposition is FramingBridgeDisposition.STALE
    assert stale.command is None


def assert_equivalent_output_is_deduplicated_across_generations() -> None:
    app_bridge = bridge()
    assert app_bridge.dispatch(value(state(1))).disposition is FramingBridgeDisposition.EMITTED
    result = app_bridge.dispatch(value(state(2)))
    assert result.disposition is FramingBridgeDisposition.DUPLICATE
    assert result.command is None


def assert_failure_returns_last_known_good_without_mutation() -> None:
    clock = Clock()
    switchable = SwitchableOrchestrator(
        FramingOrchestrator(CharacterFramingDirector(clock))
    )
    app_bridge = CharacterFramingAppBridge(switchable)
    emitted = app_bridge.dispatch(value(state(1)))
    good = emitted.command
    assert good is not None
    switchable.delegate = None
    failed = app_bridge.dispatch(value(state(2, context=policy(outfit_preview=True))))
    assert failed.disposition is FramingBridgeDisposition.FALLBACK
    assert failed.command is good
    assert app_bridge.last_known_good is good


def assert_speech_hold_and_mouth_close_settle_pass_through() -> None:
    clock = Clock()
    app_bridge = bridge(clock)
    speaking = policy(
        speech_active=True,
        mouth_closed=False,
        outfit_preview=True,
    )
    held = app_bridge.dispatch(value(state(1, context=speaking)))
    assert held.command is not None
    assert held.command.mode is FramingMode.HALF
    assert any("speech-hold" in entry.code for entry in held.command.reason_chain)
    settled = app_bridge.dispatch(
        value(
            state(
                2,
                context=replace(speaking, speech_active=False, mouth_closed=True),
            )
        )
    )
    assert settled.command is not None
    assert settled.command.mode is FramingMode.THREE_QUARTER
    clock.advance()
    completed = app_bridge.dispatch(
        value(
            state(
                3,
                context=replace(speaking, speech_active=False, mouth_closed=True),
            )
        )
    )
    assert completed.command is not None
    assert completed.command.mode is FramingMode.FULL_BODY


def assert_preferences_still_constrain_approved_cue() -> None:
    result = bridge().dispatch(
        value(
            state(),
            cue=cue(),
            preferences=FramingPreferences(allow_close=False),
        )
    )
    assert result.command is not None
    assert result.command.mode is not FramingMode.CLOSE
    assert any(entry.code == "close-disabled" for entry in result.command.reason_chain)


def run() -> None:
    assert_atomic_command_has_generation_crop_transition_and_audit()
    assert_disabled_is_complete_legacy_bypass()
    assert_stale_and_duplicate_never_emit()
    assert_equivalent_output_is_deduplicated_across_generations()
    assert_failure_returns_last_known_good_without_mutation()
    assert_speech_hold_and_mouth_close_settle_pass_through()
    assert_preferences_still_constrain_approved_cue()
    print("CHARACTER_FRAMING_APP_BRIDGE_OK")


if __name__ == "__main__":
    run()
