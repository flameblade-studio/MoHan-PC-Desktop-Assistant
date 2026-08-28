from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.character_framing import CharacterFramingDirector, FramingMode, NormalizedRect
lazy from domain.framing_context_policy import (
    EmotionValence,
    FocusState,
    FramingPolicyContext,
    WellbeingReminderKind,
    WellbeingReminderSnapshot,
)
lazy from application.framing_orchestrator import (
    FramingOrchestrationInput,
    FramingOrchestrator,
    OrchestrationReason,
    SpecialOccasionCandidate,
)
lazy from domain.framing_preferences import FramingPreferences, PreferredFraming
lazy from application.wellbeing_reminder import (
    ReminderExpression,
    ReminderFraming,
    ReminderGaze,
    ReminderGesture,
    ReminderStage,
    WellbeingCue,
    WellbeingKind,
)


class Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float = 2.0) -> None:
        self.value += seconds


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


def wellbeing(kind: WellbeingReminderKind) -> WellbeingReminderSnapshot:
    return WellbeingReminderSnapshot(
        event_id=f"{kind.value}-2026-08-13",
        kind=kind,
        occurrence=2,
        waiting_window_expired=True,
        acknowledged=False,
        snoozed=False,
        dismissed=False,
        in_meeting=False,
        fullscreen_active=False,
        proactive_care_allowed=True,
        variation_eligible=True,
        daily_limit=4,
        daily_used=0,
        category_limit=1,
        category_used=0,
        cooldown_seconds=1800.0,
        seconds_since_last_nudge=3600.0,
    )


def request(
    *,
    policy_context: FramingPolicyContext | None = None,
    preferences: FramingPreferences | None = None,
    wellbeing_cue: WellbeingCue | None = None,
    special: SpecialOccasionCandidate | None = None,
    viewport: tuple[int, int] = (1280, 900),
) -> FramingOrchestrationInput:
    return FramingOrchestrationInput(
        policy_context or policy(),
        preferences or FramingPreferences(),
        *viewport,
        wellbeing_cue,
        special,
    )


def codes(result) -> tuple[str, ...]:
    return tuple(entry.code for entry in result.reason_chain)


def approved_wellbeing_cue(
    kind: WellbeingKind,
    *,
    stage: ReminderStage = ReminderStage.RESTRAINED_REINFORCEMENT,
    framing: ReminderFraming = ReminderFraming.CLOSE_CANDIDATE,
) -> WellbeingCue:
    return WellbeingCue(
        event_id=f"approved-{kind.value}-2026-08-13",
        kind=kind,
        stage=stage,
        expression=ReminderExpression.RESTRAINED_TSUNDERE,
        gaze=ReminderGaze.USER,
        gesture=ReminderGesture.OPEN_HAND,
        framing=framing,
        line_key=f"wellbeing.{kind.value}.{stage.value}",
        reason_code="wellbeing-approved-by-lifecycle",
    )


def assert_raw_wellbeing_snapshot_never_authorizes_enhanced_framing() -> None:
    baseline = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request()
    )
    raw_only = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(
            policy_context=policy(
                wellbeing_reminder=wellbeing(WellbeingReminderKind.MEAL)
            )
        )
    )
    assert raw_only.requested_mode is baseline.requested_mode
    assert not any("repeated-wellbeing" in code for code in codes(raw_only))
    assert OrchestrationReason.APPROVED_WELLBEING_CUE.value not in codes(raw_only)


def assert_only_approved_cue_can_create_enhanced_wellbeing_candidate() -> None:
    for kind in WellbeingKind:
        framing = (
            ReminderFraming.THREE_QUARTER
            if kind is WellbeingKind.PROLONGED_SITTING
            else ReminderFraming.CLOSE_CANDIDATE
        )
        result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
            request(wellbeing_cue=approved_wellbeing_cue(kind, framing=framing))
        )
        expected = (
            FramingMode.THREE_QUARTER
            if framing is ReminderFraming.THREE_QUARTER
            else FramingMode.CLOSE
        )
        assert result.requested_mode is expected
        assert OrchestrationReason.APPROVED_WELLBEING_CUE.value in codes(result)
        assert "wellbeing-approved-by-lifecycle" in codes(result)


def assert_initial_approved_cue_is_half_and_never_close() -> None:
    cue = approved_wellbeing_cue(
        WellbeingKind.MEAL,
        stage=ReminderStage.INITIAL,
        framing=ReminderFraming.HALF,
    )
    result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(wellbeing_cue=cue)
    )
    assert result.requested_mode is FramingMode.HALF


def assert_user_consent_blocks_wellbeing_and_occasion_close() -> None:
    blocked = FramingPreferences(allow_close=False)
    for kind in WellbeingKind:
        result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
            request(
                preferences=blocked,
                wellbeing_cue=approved_wellbeing_cue(kind),
            )
        )
        assert result.requested_mode is not FramingMode.CLOSE
        assert OrchestrationReason.CLOSE_DISABLED.value in codes(result)
    occasion = SpecialOccasionCandidate(
        "birthday-2026",
        FramingMode.CLOSE,
        1.0,
        1.0,
        "birthday-close-candidate",
    )
    result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(preferences=blocked, special=occasion)
    )
    assert result.requested_mode is not FramingMode.CLOSE
    assert "birthday-close-candidate" not in codes(result)


def assert_full_body_consent_blocks_optional_occasion() -> None:
    occasion = SpecialOccasionCandidate(
        "festival-2026",
        FramingMode.FULL_BODY,
        1.0,
        1.0,
        "festival-full-candidate",
    )
    result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(
            preferences=FramingPreferences(allow_full_body=False),
            special=occasion,
        )
    )
    assert result.requested_mode is not FramingMode.FULL_BODY
    assert OrchestrationReason.FULL_BODY_DISABLED.value in codes(result)


def assert_focus_protection_wins_over_close_and_can_be_disabled() -> None:
    focused = policy(
        intimacy=1.0,
        emotion_intensity=1.0,
        focus_state=FocusState.DEEP_FOCUS,
    )
    protected = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(policy_context=focused)
    )
    assert protected.requested_mode is not FramingMode.CLOSE
    assert OrchestrationReason.FOCUS_PROTECTION.value in codes(protected)
    unprotected = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(
            policy_context=focused,
            preferences=FramingPreferences(focus_protection_enabled=False),
        )
    )
    assert unprotected.requested_mode in {FramingMode.CLOSE, FramingMode.HALF}
    assert OrchestrationReason.FOCUS_PROTECTION.value not in codes(unprotected)


def assert_fixed_preference_wins_without_bypassing_permissions() -> None:
    fixed = FramingPreferences(
        preferred_framing=PreferredFraming.THREE_QUARTER,
    )
    result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(
            policy_context=policy(outfit_preview=True),
            preferences=fixed,
        )
    )
    assert result.requested_mode is FramingMode.THREE_QUARTER
    assert OrchestrationReason.FIXED_PREFERENCE.value in codes(result)
    forbidden = FramingPreferences(
        allow_close=False,
        preferred_framing=PreferredFraming.CLOSE,
    )
    result = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(preferences=forbidden)
    )
    assert result.requested_mode is not FramingMode.CLOSE


def assert_director_preserves_speech_settle_cooldown_and_steps() -> None:
    clock = Clock()
    orchestrator = FramingOrchestrator(CharacterFramingDirector(clock))
    speaking = policy(
        speech_active=True,
        mouth_closed=False,
        outfit_preview=True,
    )
    held = orchestrator.decide(request(policy_context=speaking))
    assert held.decision.mode is FramingMode.HALF
    assert held.decision.held
    assert held.decision.reason.value == "speech-hold"
    settling = orchestrator.decide(
        request(policy_context=replace(speaking, speech_active=False, mouth_closed=True))
    )
    assert settling.decision.mode is FramingMode.THREE_QUARTER
    assert not settling.decision.held
    rate_limited = orchestrator.decide(
        request(policy_context=replace(speaking, speech_active=False, mouth_closed=True))
    )
    assert rate_limited.decision.mode is FramingMode.THREE_QUARTER
    assert rate_limited.decision.held
    clock.advance()
    completed = orchestrator.decide(
        request(policy_context=replace(speaking, speech_active=False, mouth_closed=True))
    )
    assert completed.decision.mode is FramingMode.FULL_BODY


def assert_containment_and_small_viewport_survive_translation() -> None:
    gesture = NormalizedRect(0.01, 0.10, 0.99, 0.80)
    contained = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(policy_context=policy(gesture_bounds=gesture))
    )
    assert contained.decision.crop.contains(gesture)
    assert OrchestrationReason.REQUIRED_CONTENT_CONTAINMENT.value in codes(
        contained
    )
    weapon = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(
            policy_context=policy(weapon_or_large_prop=True),
            viewport=(360, 520),
        )
    )
    assert weapon.decision.mode is FramingMode.HALF
    assert weapon.decision.reason.value == "small-viewport"


def assert_reason_chain_and_decision_are_deterministic() -> None:
    occasion = SpecialOccasionCandidate(
        "new-year-2027",
        FramingMode.THREE_QUARTER,
        0.96,
        0.88,
        "new-year-stage-candidate",
    )
    first = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(special=occasion)
    )
    second = FramingOrchestrator(CharacterFramingDirector(Clock())).decide(
        request(special=occasion)
    )
    assert first == second
    assert first.requested_mode is FramingMode.THREE_QUARTER
    assert "new-year-stage-candidate" in codes(first)
    assert first.reason_chain[-1].stage == "director"


def run() -> None:
    assert_raw_wellbeing_snapshot_never_authorizes_enhanced_framing()
    assert_only_approved_cue_can_create_enhanced_wellbeing_candidate()
    assert_initial_approved_cue_is_half_and_never_close()
    assert_user_consent_blocks_wellbeing_and_occasion_close()
    assert_full_body_consent_blocks_optional_occasion()
    assert_focus_protection_wins_over_close_and_can_be_disabled()
    assert_fixed_preference_wins_without_bypassing_permissions()
    assert_director_preserves_speech_settle_cooldown_and_steps()
    assert_containment_and_small_viewport_survive_translation()
    assert_reason_chain_and_decision_are_deterministic()
    print("FRAMING_ORCHESTRATOR_OK")


if __name__ == "__main__":
    run()
