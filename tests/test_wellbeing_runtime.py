from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from dataclasses import replace
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.special_occasion_store import (
    PORTABLE_SETTING_KEYS as OCCASION_KEYS,
)
lazy from infrastructure.special_occasion_store import SpecialOccasionStore
lazy from infrastructure.wellbeing_reminder_store import (
    PORTABLE_SETTING_KEYS as WELLBEING_KEYS,
)
lazy from infrastructure.wellbeing_reminder_store import (
    WellbeingReminderStore,
    WellbeingReminderStoreError,
)
lazy from special_occasion import OccasionKind, OccasionResponse, OccasionStage
lazy from wellbeing_reminder import ReminderResponse, ReminderStage, WellbeingKind
lazy from wellbeing_runtime import (
    RuntimeAttention,
    RuntimePolicies,
    RuntimeSource,
    WellbeingRuntime,
    WellbeingRuntimeError,
)


class MemorySettings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.writes = 0
        self.fail_write = False

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {
            key: copy.deepcopy(self.values[key]) for key in keys if key in self.values
        }

    def write(self, values: Mapping[str, object]) -> None:
        self.writes += 1
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("PRIVATE-WRITE")

    def restore(self, snapshot: dict[str, object]) -> None:
        for key in (*WELLBEING_KEYS, *OCCASION_KEYS):
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def runtime_at(moment: datetime):
    wellbeing_settings = MemorySettings()
    occasion_settings = MemorySettings()
    clock = MutableClock(moment)
    runtime = WellbeingRuntime(
        WellbeingReminderStore(wellbeing_settings),
        SpecialOccasionStore(occasion_settings),
        clock=clock,
        policies=RuntimePolicies(
            variation=lambda _key, _stable_id: 7,
            wellbeing_eligibility=lambda *_args: True,
        ),
    )
    return runtime, clock, wellbeing_settings, occasion_settings


ATTENTION = RuntimeAttention(proactive_enabled=True, user_present=True)


def assert_four_kinds_decide_without_side_effects() -> None:
    runtime, _clock, settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 12, tzinfo=UTC)
    )
    for kind in WellbeingKind:
        cue = runtime.decide_wellbeing(kind, ATTENTION)
        assert cue is not None
        assert cue.source is RuntimeSource.WELLBEING
        assert cue.cue.kind is kind
        assert cue.cue.stage is ReminderStage.INITIAL
        assert cue.line_key == f"wellbeing.{kind.value}.initial"
        assert cue.variation_index == 7
    assert settings.writes == 0


def assert_success_only_delivery_and_quota() -> None:
    runtime, clock, settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 12, tzinfo=UTC)
    )
    initial = runtime.decide_wellbeing(WellbeingKind.HYDRATION, ATTENTION)
    assert initial is not None
    assert runtime.record_delivery(initial, succeeded=False) is False
    assert settings.writes == 0
    assert runtime.record_delivery(initial, succeeded=True) is True
    assert runtime.record_delivery(initial, succeeded=True) is False
    state = runtime._wellbeing_store.load(clock.now)
    item = state.for_kind(WellbeingKind.HYDRATION)
    assert item.initial_delivered_at == clock.now
    assert item.daily_reinforcement_count == 0

    clock.now += timedelta(minutes=13)
    reinforcement = runtime.decide_wellbeing(WellbeingKind.HYDRATION, ATTENTION)
    assert reinforcement is not None
    assert reinforcement.cue.stage is ReminderStage.RESTRAINED_REINFORCEMENT
    assert runtime.record_delivery(reinforcement, succeeded=False) is False
    assert (
        runtime._wellbeing_store
        .load(clock.now)
        .for_kind(WellbeingKind.HYDRATION)
        .daily_reinforcement_count
        == 0
    )
    assert runtime.record_delivery(reinforcement, succeeded=True) is True
    item = runtime._wellbeing_store.load(clock.now).for_kind(WellbeingKind.HYDRATION)
    assert item.daily_reinforcement_count == 1
    assert item.last_same_kind_reinforcement_at == clock.now


def assert_persistence_failure_does_not_consume_delivery_or_quota() -> None:
    runtime, clock, settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 12, tzinfo=UTC)
    )
    initial = runtime.decide_wellbeing(WellbeingKind.HYDRATION, ATTENTION)
    assert initial is not None
    settings.fail_write = True
    try:
        runtime.record_delivery(initial, succeeded=True)
    except WellbeingReminderStoreError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failed persistence unexpectedly succeeded")
    settings.fail_write = False
    item = runtime._wellbeing_store.load(clock.now).for_kind(WellbeingKind.HYDRATION)
    assert item.initial_delivered_at is None
    assert item.daily_reinforcement_count == 0
    assert runtime.decide_wellbeing(WellbeingKind.HYDRATION, ATTENTION) == initial


def assert_response_and_snooze_apis() -> None:
    runtime, clock, _settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 12, tzinfo=UTC)
    )
    runtime.acknowledge_wellbeing(WellbeingKind.MEAL)
    runtime.complete_wellbeing(WellbeingKind.HYDRATION)
    runtime.dismiss_wellbeing(WellbeingKind.REST)
    runtime.snooze_wellbeing(
        WellbeingKind.PROLONGED_SITTING,
        clock.now + timedelta(minutes=30),
    )
    state = runtime._wellbeing_store.load(clock.now)
    assert state.for_kind(WellbeingKind.MEAL).response is ReminderResponse.ACKNOWLEDGED
    assert (
        state.for_kind(WellbeingKind.HYDRATION).response is ReminderResponse.COMPLETED
    )
    assert state.for_kind(WellbeingKind.REST).response is ReminderResponse.DISMISSED
    sitting = state.for_kind(WellbeingKind.PROLONGED_SITTING)
    assert sitting.response is ReminderResponse.SNOOZED
    assert runtime.decide_wellbeing(WellbeingKind.PROLONGED_SITTING, ATTENTION) is None
    clock.now += timedelta(minutes=31)
    resumed = runtime.decide_wellbeing(WellbeingKind.PROLONGED_SITTING, ATTENTION)
    assert resumed is not None
    assert resumed.cue.stage is ReminderStage.INITIAL


def assert_date_rollover_starts_a_new_bounded_lifecycle() -> None:
    runtime, clock, _settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 23, 50, tzinfo=UTC)
    )
    cue = runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION)
    assert cue is not None
    assert runtime.record_delivery(cue, succeeded=True)
    runtime.complete_wellbeing(WellbeingKind.MEAL)
    assert runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION) is None
    clock.now += timedelta(minutes=20)
    next_day = runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION)
    assert next_day is not None
    assert next_day.stable_id.startswith("2027-01-10:")
    assert next_day.cue.stage is ReminderStage.INITIAL


def assert_special_occasions_are_independent_and_low_frequency() -> None:
    runtime, clock, wellbeing, occasion = runtime_at(
        datetime(2027, 1, 8, 9, tzinfo=UTC)
    )
    hint = runtime.decide_special_occasion(ATTENTION)
    assert hint is not None
    assert hint.source is RuntimeSource.SPECIAL_OCCASION
    assert hint.cue.kind is OccasionKind.MOHAN_BIRTHDAY
    assert hint.cue.stage is OccasionStage.SUBTLE_HINT
    assert wellbeing.writes == 0
    assert occasion.writes == 0
    assert runtime.record_delivery(hint, succeeded=True)
    assert runtime.decide_special_occasion(ATTENTION) is None

    clock.now = datetime(2027, 1, 8, 18, 30, tzinfo=UTC)
    grumble = runtime.decide_special_occasion(ATTENTION)
    assert grumble is not None
    assert grumble.cue.stage is OccasionStage.RESTRAINED_GRUMBLE
    assert runtime.record_delivery(grumble, succeeded=False) is False
    assert runtime.decide_special_occasion(ATTENTION) == grumble
    assert runtime.record_delivery(grumble, succeeded=True)
    assert runtime.decide_special_occasion(ATTENTION) is None
    assert wellbeing.writes == 0

    runtime.complete_special_occasion(OccasionKind.MOHAN_BIRTHDAY)
    state = runtime._occasion_store.load(clock.now)
    assert (
        state.occasions[OccasionKind.MOHAN_BIRTHDAY].response
        is OccasionResponse.CELEBRATED
    )


def assert_invalid_clock_variation_and_token_fail_closed() -> None:
    wellbeing = WellbeingReminderStore(MemorySettings())
    occasion = SpecialOccasionStore(MemorySettings())
    invalid_clock = WellbeingRuntime(
        wellbeing,
        occasion,
        clock=lambda: datetime.fromisoformat("2027-01-08T00:00:00"),
    )
    try:
        invalid_clock.decide_wellbeing(WellbeingKind.MEAL, ATTENTION)
    except WellbeingRuntimeError:
        pass
    else:
        raise AssertionError("naive clock unexpectedly accepted")

    invalid_variation = WellbeingRuntime(
        wellbeing,
        occasion,
        clock=lambda: datetime(2027, 1, 8, 12, tzinfo=UTC),
        policies=RuntimePolicies(variation=lambda *_args: -1),
    )
    try:
        invalid_variation.decide_wellbeing(WellbeingKind.MEAL, ATTENTION)
    except WellbeingRuntimeError:
        pass
    else:
        raise AssertionError("negative variation unexpectedly accepted")

    valid_runtime, _clock, _settings, _occasion = runtime_at(
        datetime(2027, 1, 9, 12, tzinfo=UTC)
    )
    cue = valid_runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION)
    assert cue is not None
    tampered = replace(cue, line_key="wellbeing.hydration.initial")
    try:
        valid_runtime.record_delivery(tampered, succeeded=True)
    except WellbeingRuntimeError:
        pass
    else:
        raise AssertionError("tampered cue unexpectedly accepted")


def assert_attention_suppression_has_no_side_effects() -> None:
    runtime, _clock, wellbeing, occasion = runtime_at(
        datetime(2027, 1, 8, 12, tzinfo=UTC)
    )
    protected = RuntimeAttention(
        proactive_enabled=True,
        user_present=True,
        focus_protected=True,
    )
    assert runtime.decide_wellbeing(WellbeingKind.MEAL, protected) is None
    assert runtime.decide_special_occasion(protected) is None
    assert wellbeing.writes == 0
    assert occasion.writes == 0


def run() -> None:
    assert_four_kinds_decide_without_side_effects()
    assert_success_only_delivery_and_quota()
    assert_persistence_failure_does_not_consume_delivery_or_quota()
    assert_response_and_snooze_apis()
    assert_date_rollover_starts_a_new_bounded_lifecycle()
    assert_special_occasions_are_independent_and_low_frequency()
    assert_invalid_clock_variation_and_token_fail_closed()
    assert_attention_suppression_has_no_side_effects()
    print("WELLBEING_RUNTIME_OK")


if __name__ == "__main__":
    run()
