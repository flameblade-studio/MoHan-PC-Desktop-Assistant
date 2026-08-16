from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from special_occasion import (
    MOHAN_BIRTHDAY_DAY,
    MOHAN_BIRTHDAY_MONTH,
    MOHAN_ZODIAC,
    OccasionContext,
    OccasionDelivery,
    OccasionExpression,
    OccasionGaze,
    OccasionKind,
    OccasionResponse,
    OccasionStage,
    SpecialOccasionPolicy,
    active_occasion,
)


def context(moment: datetime, **changes: object) -> OccasionContext:
    values: dict[str, object] = {
        "local_now": moment,
        "user_present": True,
        "proactive_enabled": True,
        "special_occasions_enabled": True,
    }
    values.update(changes)
    return OccasionContext(**values)


def moment(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2027, month, day, hour, minute, tzinfo=UTC)


def assert_character_canon_and_dates() -> None:
    assert (MOHAN_BIRTHDAY_MONTH, MOHAN_BIRTHDAY_DAY) == (1, 8)
    assert MOHAN_ZODIAC == "capricorn"
    assert active_occasion(moment(1, 8, 9)).kind is OccasionKind.MOHAN_BIRTHDAY
    assert active_occasion(moment(2, 14, 12)).kind is OccasionKind.VALENTINES_DAY
    assert active_occasion(moment(12, 25, 12)).kind is OccasionKind.CHRISTMAS_DAY
    assert active_occasion(moment(8, 13, 12)) is None


def assert_subtle_then_restrained_progression() -> None:
    policy = SpecialOccasionPolicy()
    birthday_morning = moment(1, 8, 9)
    hint = policy.decide(context(birthday_morning))
    assert hint is not None
    assert hint.stage is OccasionStage.SUBTLE_HINT
    assert hint.expression is OccasionExpression.QUIETLY_HOPEFUL
    assert hint.gaze is OccasionGaze.NEAR_USER

    before_evening = policy.decide(
        context(
            moment(1, 8, 16),
            delivered_stages=frozenset({OccasionStage.SUBTLE_HINT}),
            first_hint_at=birthday_morning,
        )
    )
    assert before_evening is None

    grumble = policy.decide(
        context(
            moment(1, 8, 18, 30),
            delivered_stages=frozenset({OccasionStage.SUBTLE_HINT}),
            first_hint_at=birthday_morning,
        )
    )
    assert grumble is not None
    assert grumble.stage is OccasionStage.RESTRAINED_GRUMBLE
    assert grumble.expression is OccasionExpression.RESTRAINED_SULK
    assert grumble.gaze is OccasionGaze.BRIEFLY_AWAY
    assert grumble.delivery is OccasionDelivery.SOFT_MURMUR
    assert grumble.line_key.endswith("restrained_grumble")


def assert_attention_and_autonomy_guards() -> None:
    policy = SpecialOccasionPolicy()
    occasion_time = moment(2, 14, 20)
    for changes in (
        {"user_present": False},
        {"proactive_enabled": False},
        {"special_occasions_enabled": False},
        {"focus_protected": True},
        {"meeting_active": True},
        {"fullscreen_active": True},
        {"speech_active": True},
        {"response": OccasionResponse.ACKNOWLEDGED},
        {"response": OccasionResponse.CELEBRATED},
        {"response": OccasionResponse.SNOOZED},
        {"response": OccasionResponse.DISMISSED},
    ):
        assert policy.decide(context(occasion_time, **changes)) is None


def assert_no_repetition_or_premature_grumble() -> None:
    policy = SpecialOccasionPolicy()
    hint_time = moment(12, 25, 17)
    delivered_hint = frozenset({OccasionStage.SUBTLE_HINT})
    assert policy.decide(
        context(
            moment(12, 25, 20),
            delivered_stages=delivered_hint,
            first_hint_at=hint_time,
        )
    ) is None
    assert policy.decide(
        context(
            moment(12, 25, 22),
            delivered_stages=frozenset(
                {
                    OccasionStage.SUBTLE_HINT,
                    OccasionStage.RESTRAINED_GRUMBLE,
                }
            ),
            first_hint_at=hint_time,
        )
    ) is None


def assert_invalid_history_is_rejected() -> None:
    try:
        context(
            moment(1, 8, 20),
            delivered_stages=frozenset({OccasionStage.RESTRAINED_GRUMBLE}),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("An occasion must never grumble before its hint.")


def run() -> None:
    assert_character_canon_and_dates()
    assert_subtle_then_restrained_progression()
    assert_attention_and_autonomy_guards()
    assert_no_repetition_or_premature_grumble()
    assert_invalid_history_is_rejected()
    print("SPECIAL_OCCASION_OK")


if __name__ == "__main__":
    run()
