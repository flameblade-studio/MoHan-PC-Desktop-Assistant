from __future__ import annotations

lazy import sys
lazy from dataclasses import FrozenInstanceError, replace
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from character_framing import FramingMode, NormalizedRect
lazy from framing_context_policy import (
    EmotionValence,
    FocusState,
    FramingPolicyContext,
    FramingReasonCode,
    WellbeingReminderKind,
    WellbeingReminderSnapshot,
    evaluate_framing_context,
)

FULL_BODY_SCORE_MAX = 0.14
CLOSE_SCORE_MIN = 0.25
CLOSE_SCORE_MAX = 0.04
HALF_SCORE_MIN = 0.62


def context(**changes: object) -> FramingPolicyContext:
    base = FramingPolicyContext(
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
        close_framing_allowed=False,
    )
    return replace(base, **changes)


def proposal(result, mode: FramingMode):
    return result.proposals[int(mode)]


def assert_typed_frozen_complete_contract() -> None:
    value = context()
    try:
        value.intimacy = 1.0  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Policy context must be frozen")
    result = evaluate_framing_context(value)
    assert tuple(item.mode for item in result.proposals) == tuple(FramingMode)
    assert all(0.0 <= item.score <= 1.0 for item in result.proposals)
    assert all(0.0 <= item.confidence <= 1.0 for item in result.proposals)
    assert all(item.reasons for item in result.proposals)


def assert_daily_companion_prefers_half() -> None:
    result = evaluate_framing_context(context())
    assert result.recommended.mode is FramingMode.HALF
    assert proposal(result, FramingMode.FULL_BODY).score <= FULL_BODY_SCORE_MAX
    assert FramingReasonCode.FULL_BODY_NOT_JUSTIFIED in proposal(
        result, FramingMode.FULL_BODY
    ).reasons


def assert_full_body_requires_complete_body_reason() -> None:
    cases = (
        context(outfit_preview=True),
        context(weapon_or_large_prop=True),
        context(
            gesture_bounds=NormalizedRect(0.0, 0.0, 1.0, 1.0)
        ),
    )
    expected = (
        FramingReasonCode.OUTFIT_PREVIEW,
        FramingReasonCode.WEAPON_OR_LARGE_PROP,
        FramingReasonCode.GESTURE_REQUIRES_FULL,
    )
    for value, reason in zip(cases, expected, strict=True):
        result = evaluate_framing_context(value)
        assert result.recommended.mode is FramingMode.FULL_BODY
        assert reason in result.recommended.reasons


def assert_gesture_boundary_uses_three_quarter() -> None:
    result = evaluate_framing_context(
        context(gesture_bounds=NormalizedRect(0.10, 0.0, 0.90, 0.75))
    )
    assert result.recommended.mode is FramingMode.THREE_QUARTER
    assert FramingReasonCode.GESTURE_OUTSIDE_HALF in result.recommended.reasons


def assert_close_is_private_and_restrained() -> None:
    intimate = context(
        intimacy=0.92,
        emotion_intensity=0.9,
        emotion_valence=EmotionValence.POSITIVE,
        close_framing_allowed=True,
    )
    allowed = evaluate_framing_context(intimate)
    assert allowed.recommended.mode in {FramingMode.CLOSE, FramingMode.HALF}
    assert proposal(allowed, FramingMode.CLOSE).score > CLOSE_SCORE_MIN
    blocked = evaluate_framing_context(
        replace(intimate, close_framing_allowed=False)
    )
    close = proposal(blocked, FramingMode.CLOSE)
    assert close.score <= CLOSE_SCORE_MAX
    assert FramingReasonCode.CLOSE_PRIVACY_BLOCKED in close.reasons
    assert blocked.recommended.mode is not FramingMode.CLOSE


def assert_focus_reduces_interruption() -> None:
    available = evaluate_framing_context(
        context(
            intimacy=0.9,
            emotion_intensity=0.9,
            close_framing_allowed=True,
        )
    )
    focused = evaluate_framing_context(
        context(
            intimacy=0.9,
            emotion_intensity=0.9,
            close_framing_allowed=True,
            focus_state=FocusState.DEEP_FOCUS,
            proactive_greeting=True,
        )
    )
    assert proposal(focused, FramingMode.CLOSE).score < proposal(
        available, FramingMode.CLOSE
    ).score
    assert focused.recommended.mode is FramingMode.HALF
    assert FramingReasonCode.USER_DEEP_FOCUS in focused.recommended.reasons


def assert_return_and_proactive_greeting_are_proportional() -> None:
    short = evaluate_framing_context(
        context(away_seconds=20, returned_to_seat=True, proactive_greeting=True)
    )
    assert short.recommended.mode is FramingMode.HALF
    long = evaluate_framing_context(
        context(away_seconds=600, returned_to_seat=True, proactive_greeting=True)
    )
    assert long.recommended.mode is FramingMode.THREE_QUARTER
    assert FramingReasonCode.RETURNED_AFTER_ABSENCE in long.recommended.reasons


def assert_angry_back_turn_avoids_close() -> None:
    result = evaluate_framing_context(
        context(
            intimacy=1.0,
            emotion_intensity=1.0,
            emotion_valence=EmotionValence.NEGATIVE,
            angry_back_turn=True,
            close_framing_allowed=True,
        )
    )
    assert result.recommended.mode in {
        FramingMode.THREE_QUARTER,
        FramingMode.FULL_BODY,
    }
    assert proposal(result, FramingMode.CLOSE).score == 0.0
    assert FramingReasonCode.ANGRY_BACK_TURN in result.recommended.reasons


def assert_speech_only_suggests_hold() -> None:
    result = evaluate_framing_context(
        context(speech_active=True, mouth_closed=False, outfit_preview=True)
    )
    assert result.recommended.mode is FramingMode.FULL_BODY
    assert all(item.hold_during_speech for item in result.proposals)
    assert all(
        FramingReasonCode.SPEECH_ACTIVE in item.reasons
        for item in result.proposals
    )
    idle = evaluate_framing_context(context())
    assert not any(item.hold_during_speech for item in idle.proposals)


def assert_conflict_priority_is_auditable() -> None:
    result = evaluate_framing_context(
        context(
            outfit_preview=True,
            focus_state=FocusState.DEEP_FOCUS,
            intimacy=1.0,
            emotion_intensity=1.0,
            close_framing_allowed=True,
        )
    )
    assert result.recommended.mode is FramingMode.FULL_BODY
    assert FramingReasonCode.OUTFIT_PREVIEW in result.recommended.reasons
    assert proposal(result, FramingMode.HALF).score > HALF_SCORE_MIN
    assert FramingReasonCode.USER_DEEP_FOCUS in proposal(
        result, FramingMode.HALF
    ).reasons


def assert_boundaries_reject_invalid_context() -> None:
    invalid = (
        {"away_seconds": -0.1},
        {"intimacy": 1.1},
        {"emotion_intensity": -0.1},
        {"speech_active": True, "mouth_closed": True},
    )
    for changes in invalid:
        try:
            context(**changes)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid context accepted: {changes}")


def reminder(**changes: object) -> WellbeingReminderSnapshot:
    base = WellbeingReminderSnapshot(
        event_id="lunch-2026-08-13",
        kind=WellbeingReminderKind.MEAL,
        occurrence=1,
        waiting_window_expired=False,
        acknowledged=False,
        snoozed=False,
        dismissed=False,
        in_meeting=False,
        fullscreen_active=False,
        proactive_care_allowed=True,
        variation_eligible=False,
        daily_limit=2,
        daily_used=0,
        category_limit=1,
        category_used=0,
        cooldown_seconds=3600.0,
        seconds_since_last_nudge=7200.0,
    )
    return replace(base, **changes)


def assert_first_wellbeing_reminder_never_closes_in() -> None:
    for kind in WellbeingReminderKind:
        result = evaluate_framing_context(
            context(
                intimacy=1.0,
                emotion_intensity=1.0,
                close_framing_allowed=True,
                wellbeing_reminder=reminder(kind=kind),
            )
        )
        assert result.recommended.mode is FramingMode.HALF
        assert proposal(result, FramingMode.CLOSE).score == 0.0
        assert FramingReasonCode.FIRST_WELLBEING_REMINDER in proposal(
            result, FramingMode.HALF
        ).reasons


def assert_ignored_wellbeing_nudge_is_reproducibly_occasional() -> None:
    eligible = reminder(
        occurrence=2,
        waiting_window_expired=True,
        variation_eligible=True,
    )
    close = evaluate_framing_context(
        context(
            intimacy=0.9,
            emotion_intensity=0.8,
            close_framing_allowed=True,
            wellbeing_reminder=eligible,
        )
    )
    assert close.recommended.mode is FramingMode.CLOSE
    assert FramingReasonCode.REPEATED_WELLBEING_NUDGE in close.recommended.reasons
    same_input = evaluate_framing_context(
        context(
            intimacy=0.9,
            emotion_intensity=0.8,
            close_framing_allowed=True,
            wellbeing_reminder=eligible,
        )
    )
    assert close == same_input
    ineligible = evaluate_framing_context(
        context(
            intimacy=0.9,
            emotion_intensity=0.8,
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, variation_eligible=False),
        )
    )
    assert ineligible.recommended.mode is not FramingMode.CLOSE


def assert_all_wellbeing_kinds_share_guards_but_choose_suitable_shots() -> None:
    cases = (
        (
            WellbeingReminderKind.MEAL,
            FramingMode.CLOSE,
            FramingReasonCode.REPEATED_MEAL_NUDGE,
        ),
        (
            WellbeingReminderKind.HYDRATION,
            FramingMode.HALF,
            FramingReasonCode.REPEATED_HYDRATION_NUDGE,
        ),
        (
            WellbeingReminderKind.REST,
            FramingMode.CLOSE,
            FramingReasonCode.REPEATED_REST_NUDGE,
        ),
        (
            WellbeingReminderKind.PROLONGED_SITTING,
            FramingMode.THREE_QUARTER,
            FramingReasonCode.REPEATED_PROLONGED_SITTING_NUDGE,
        ),
    )
    for kind, expected_mode, reason in cases:
        snapshot = reminder(
            event_id=f"{kind.value}-2026-08-13",
            kind=kind,
            occurrence=2,
            waiting_window_expired=True,
            variation_eligible=True,
        )
        result = evaluate_framing_context(
            context(
                intimacy=0.9,
                emotion_intensity=0.8,
                close_framing_allowed=True,
                wellbeing_reminder=snapshot,
            )
        )
        assert result.recommended.mode is expected_mode
        assert FramingReasonCode.REPEATED_WELLBEING_NUDGE in (
            result.recommended.reasons
        )
        assert reason in result.recommended.reasons
        assert result == evaluate_framing_context(
            context(
                intimacy=0.9,
                emotion_intensity=0.8,
                close_framing_allowed=True,
                wellbeing_reminder=snapshot,
            )
        )


def assert_wellbeing_nudge_respects_attention_rejection_budget_and_cooldown() -> None:
    eligible = reminder(
        occurrence=2,
        waiting_window_expired=True,
        variation_eligible=True,
    )
    blocked_cases = (
        context(
            focus_state=FocusState.DEEP_FOCUS,
            close_framing_allowed=True,
            wellbeing_reminder=eligible,
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, acknowledged=True),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, snoozed=True),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, dismissed=True),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, in_meeting=True),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, fullscreen_active=True),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, proactive_care_allowed=False),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, daily_used=2),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, category_used=1),
        ),
        context(
            close_framing_allowed=True,
            wellbeing_reminder=replace(eligible, seconds_since_last_nudge=30),
        ),
    )
    for value in blocked_cases:
        result = evaluate_framing_context(value)
        assert result.recommended.mode is not FramingMode.CLOSE
        assert FramingReasonCode.WELLBEING_NUDGE_NOT_ELIGIBLE in proposal(
            result, FramingMode.CLOSE
        ).reasons


def run() -> None:
    assert_typed_frozen_complete_contract()
    assert_daily_companion_prefers_half()
    assert_full_body_requires_complete_body_reason()
    assert_gesture_boundary_uses_three_quarter()
    assert_close_is_private_and_restrained()
    assert_focus_reduces_interruption()
    assert_return_and_proactive_greeting_are_proportional()
    assert_angry_back_turn_avoids_close()
    assert_speech_only_suggests_hold()
    assert_conflict_priority_is_auditable()
    assert_boundaries_reject_invalid_context()
    assert_first_wellbeing_reminder_never_closes_in()
    assert_ignored_wellbeing_nudge_is_reproducibly_occasional()
    assert_all_wellbeing_kinds_share_guards_but_choose_suitable_shots()
    assert_wellbeing_nudge_respects_attention_rejection_budget_and_cooldown()
    print("FRAMING_CONTEXT_POLICY_OK")


if __name__ == "__main__":
    run()
