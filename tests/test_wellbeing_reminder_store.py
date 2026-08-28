from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.wellbeing_reminder_store import (
    PORTABLE_SETTING_KEYS,
    WELLBEING_STATE_FORMAT,
    WELLBEING_STATE_KEY,
    WELLBEING_STATE_VERSION,
    WellbeingReminderStore,
    WellbeingReminderStoreError,
    default_wellbeing_state,
)
lazy from application.wellbeing_reminder import ReminderResponse, WellbeingKind

NOW = datetime(2027, 1, 8, 12, tzinfo=UTC)

MAX_DAILY_REINFORCEMENTS = 7
SAME_KIND_COOLDOWN_SECONDS = 7200
SAME_KIND_COOLDOWN_SECONDS_ALT = 3600


class MemorySettings:
    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        fail_write: bool = False,
        fail_restore: bool = False,
    ) -> None:
        self.values = copy.deepcopy(dict(values or {}))
        self.fail_write = fail_write
        self.fail_restore = fail_restore

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("PRIVATE-WRITE-CONTENT")

    def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise RuntimeError("PRIVATE-ROLLBACK-CONTENT")
        for key in PORTABLE_SETTING_KEYS:
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def assert_all_four_kinds_round_trip() -> None:
    settings = MemorySettings()
    store = WellbeingReminderStore(settings)
    state = default_wellbeing_state(NOW.date())
    responses = {
        WellbeingKind.MEAL: ReminderResponse.ACKNOWLEDGED,
        WellbeingKind.HYDRATION: ReminderResponse.COMPLETED,
        WellbeingKind.REST: ReminderResponse.DISMISSED,
        WellbeingKind.PROLONGED_SITTING: ReminderResponse.SNOOZED,
    }
    for index, kind in enumerate(WellbeingKind, start=1):
        state = store.update_kind(
            state,
            kind,
            enabled=kind is not WellbeingKind.REST,
            snooze_until=NOW + timedelta(minutes=index * 10),
            response=responses[kind],
            initial_delivered_at=NOW - timedelta(minutes=20),
            reinforcement_delivered_at=NOW - timedelta(minutes=10),
            daily_reinforcement_count=index,
            maximum_daily_reinforcements=min(index + 1, 8),
            same_kind_cooldown_seconds=1800 + index,
            last_same_kind_reinforcement_at=NOW - timedelta(minutes=10),
        )
    store.save(state)
    assert store.load(NOW) == state
    assert set(store.export_portable(NOW)) == {
        "format", "version", "local_date", "kinds"
    }
    assert settings.values[WELLBEING_STATE_KEY]["format"] == WELLBEING_STATE_FORMAT


def assert_date_rollover_resets_daily_state_only() -> None:
    store = WellbeingReminderStore(MemorySettings())
    state = default_wellbeing_state(NOW.date())
    state = store.update_kind(
        state,
        WellbeingKind.MEAL,
        enabled=False,
        snooze_until=NOW + timedelta(days=2),
        response=ReminderResponse.COMPLETED,
        initial_delivered_at=NOW,
        reinforcement_delivered_at=NOW + timedelta(minutes=20),
        daily_reinforcement_count=2,
        maximum_daily_reinforcements=7,
        same_kind_cooldown_seconds=7200,
        last_same_kind_reinforcement_at=NOW + timedelta(minutes=20),
    )
    store.save(state)
    rolled = store.load(NOW + timedelta(days=1))
    meal = rolled.for_kind(WellbeingKind.MEAL)
    assert rolled.local_date == (NOW + timedelta(days=1)).date()
    assert meal.enabled is False
    assert meal.snooze_until == NOW + timedelta(days=2)
    assert meal.response is ReminderResponse.NONE
    assert meal.initial_delivered_at is None
    assert meal.reinforcement_delivered_at is None
    assert meal.daily_reinforcement_count == 0
    assert meal.maximum_daily_reinforcements == MAX_DAILY_REINFORCEMENTS
    assert meal.same_kind_cooldown_seconds == SAME_KIND_COOLDOWN_SECONDS


def assert_corruption_fails_closed_and_future_fields_are_ignored() -> None:
    payload = {
        "format": WELLBEING_STATE_FORMAT,
        "version": WELLBEING_STATE_VERSION,
        "local_date": NOW.date().isoformat(),
        "future": "ignored",
        "kinds": {
            kind.value: {
                "enabled": True,
                "snooze_until": None,
                "response": "none",
                "initial_delivered_at": None,
                "reinforcement_delivered_at": None,
                "daily_reinforcement_count": 0,
                "maximum_daily_reinforcements": 2,
                "same_kind_cooldown_seconds": 3600,
                "last_same_kind_reinforcement_at": None,
                "future_private": "ignored",
            }
            for kind in WellbeingKind
        },
    }
    payload["kinds"][WellbeingKind.REST.value]["enabled"] = "yes"
    state = WellbeingReminderStore(
        MemorySettings({WELLBEING_STATE_KEY: payload})
    ).load(NOW)
    assert state.for_kind(WellbeingKind.REST).enabled is True
    assert state.for_kind(WellbeingKind.MEAL).same_kind_cooldown_seconds == SAME_KIND_COOLDOWN_SECONDS_ALT
    for invalid_version in (True, "1", 2):
        damaged = copy.deepcopy(payload)
        damaged["version"] = invalid_version
        assert WellbeingReminderStore(
            MemorySettings({WELLBEING_STATE_KEY: damaged})
        ).load(NOW) == default_wellbeing_state(NOW.date())


def assert_atomic_rollback_and_safe_errors() -> None:
    original = {WELLBEING_STATE_KEY: {"legacy": True}, "unrelated": "keep"}
    settings = MemorySettings(original, fail_write=True)
    try:
        WellbeingReminderStore(settings).save(default_wellbeing_state(NOW.date()))
    except WellbeingReminderStoreError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing write unexpectedly succeeded")
    assert settings.values == original

    broken = MemorySettings(original, fail_write=True, fail_restore=True)
    try:
        WellbeingReminderStore(broken).save(default_wellbeing_state(NOW.date()))
    except WellbeingReminderStoreError as exc:
        assert "rollback was incomplete" in str(exc)
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing rollback unexpectedly succeeded")


def run() -> None:
    assert_all_four_kinds_round_trip()
    assert_date_rollover_resets_daily_state_only()
    assert_corruption_fails_closed_and_future_fields_are_ignored()
    assert_atomic_rollback_and_safe_errors()
    print("WELLBEING_REMINDER_STORE_OK")


if __name__ == "__main__":
    run()
