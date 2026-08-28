from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.wellbeing_reminder import (
    WELLBEING_RULES,
    ReminderExpression,
    ReminderFraming,
    ReminderOccurrence,
    ReminderResponse,
    ReminderStage,
    WellbeingContext,
    WellbeingKind,
    WellbeingReminderPolicy,
    stable_reinforcement_eligibility,
)

NOW = datetime(2027, 1, 8, 12, 0, tzinfo=UTC)


def occurrence(kind: WellbeingKind, **changes: object) -> ReminderOccurrence:
    values: dict[str, object] = {
        "event_id": f"2027-01-08:{kind.value}:1",
        "kind": kind,
    }
    values.update(changes)
    return ReminderOccurrence(**values)


def context(item: ReminderOccurrence, **changes: object) -> WellbeingContext:
    values: dict[str, object] = {
        "local_now": NOW,
        "occurrence": item,
        "kind_enabled": True,
        "proactive_enabled": True,
        "user_present": True,
    }
    values.update(changes)
    return WellbeingContext(**values)


def assert_one_lifecycle_covers_all_four_kinds() -> None:
    policy = WellbeingReminderPolicy(eligibility=lambda *_: True)
    assert set(WELLBEING_RULES) == set(WellbeingKind)
    for kind in WellbeingKind:
        cue = policy.decide(context(occurrence(kind)))
        assert cue is not None
        assert cue.kind is kind
        assert cue.stage is ReminderStage.INITIAL
        assert cue.expression is ReminderExpression.GENTLE
        assert cue.framing is ReminderFraming.HALF
        assert cue.line_key == f"wellbeing.{kind.value}.initial"


def assert_ignored_reminders_use_distinct_restrained_performances() -> None:
    policy = WellbeingReminderPolicy(eligibility=lambda *_: True)
    expected_framing = {
        WellbeingKind.MEAL: ReminderFraming.CLOSE_CANDIDATE,
        WellbeingKind.HYDRATION: ReminderFraming.CLOSE_CANDIDATE,
        WellbeingKind.REST: ReminderFraming.CLOSE_CANDIDATE,
        WellbeingKind.PROLONGED_SITTING: ReminderFraming.THREE_QUARTER,
    }
    for kind, rule in WELLBEING_RULES.items():
        initial_at = NOW - timedelta(seconds=rule.reinforcement_delay_seconds + 1)
        cue = policy.decide(
            context(occurrence(kind, initial_delivered_at=initial_at))
        )
        assert cue is not None
        assert cue.stage is ReminderStage.RESTRAINED_REINFORCEMENT
        assert cue.framing is expected_framing[kind]
        assert cue.expression is rule.reinforcement_expression


def assert_response_and_attention_always_stop_escalation() -> None:
    policy = WellbeingReminderPolicy(eligibility=lambda *_: True)
    item = occurrence(
        WellbeingKind.MEAL,
        initial_delivered_at=NOW - timedelta(hours=1),
    )
    for changes in (
        {"kind_enabled": False},
        {"proactive_enabled": False},
        {"user_present": False},
        {"focus_protected": True},
        {"meeting_active": True},
        {"fullscreen_active": True},
        {"speech_active": True},
    ):
        assert policy.decide(context(item, **changes)) is None
    for response in ReminderResponse:
        if response is ReminderResponse.NONE:
            continue
        responded = occurrence(
            WellbeingKind.MEAL,
            initial_delivered_at=NOW - timedelta(hours=1),
            response=response,
        )
        assert policy.decide(context(responded)) is None


def assert_wait_budget_cooldown_and_single_reinforcement() -> None:
    policy = WellbeingReminderPolicy(eligibility=lambda *_: True)
    rule = WELLBEING_RULES[WellbeingKind.PROLONGED_SITTING]
    too_soon = occurrence(
        WellbeingKind.PROLONGED_SITTING,
        initial_delivered_at=NOW - timedelta(
            seconds=rule.reinforcement_delay_seconds - 1
        ),
    )
    assert policy.decide(context(too_soon)) is None

    due = occurrence(
        WellbeingKind.PROLONGED_SITTING,
        initial_delivered_at=NOW - timedelta(hours=1),
    )
    assert policy.decide(
        context(
            due,
            daily_reinforcement_count=rule.maximum_daily_reinforcements,
        )
    ) is None
    assert policy.decide(
        context(
            due,
            last_same_kind_reinforcement_at=NOW - timedelta(minutes=10),
        )
    ) is None
    already_reinforced = occurrence(
        WellbeingKind.PROLONGED_SITTING,
        initial_delivered_at=NOW - timedelta(hours=2),
        reinforcement_delivered_at=NOW - timedelta(hours=1),
    )
    assert policy.decide(context(already_reinforced)) is None


def assert_occasional_choice_is_stable_not_flaky() -> None:
    values = [
        stable_reinforcement_eligibility(
            f"event-{index}",
            WellbeingKind.HYDRATION,
            30,
        )
        for index in range(100)
    ]
    repeated = [
        stable_reinforcement_eligibility(
            f"event-{index}",
            WellbeingKind.HYDRATION,
            30,
        )
        for index in range(100)
    ]
    assert values == repeated
    assert any(values)
    assert not all(values)
    never = WellbeingReminderPolicy(eligibility=lambda *_: False)
    due = occurrence(
        WellbeingKind.HYDRATION,
        initial_delivered_at=NOW - timedelta(hours=1),
    )
    assert never.decide(context(due)) is None


def assert_invalid_history_is_rejected() -> None:
    try:
        occurrence(
            WellbeingKind.REST,
            reinforcement_delivered_at=NOW,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A reinforcement cannot precede its first reminder.")


def run() -> None:
    assert_one_lifecycle_covers_all_four_kinds()
    assert_ignored_reminders_use_distinct_restrained_performances()
    assert_response_and_attention_always_stop_escalation()
    assert_wait_budget_cooldown_and_single_reinforcement()
    assert_occasional_choice_is_stable_not_flaky()
    assert_invalid_history_is_rejected()
    print("WELLBEING_REMINDER_OK")


if __name__ == "__main__":
    run()
