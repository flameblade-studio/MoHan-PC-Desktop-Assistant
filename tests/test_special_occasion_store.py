from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.special_occasion_store import (
    PORTABLE_SETTING_KEYS,
    SPECIAL_OCCASION_STATE_FORMAT,
    SPECIAL_OCCASION_STATE_KEY,
    SPECIAL_OCCASION_STATE_VERSION,
    OccasionState,
    SpecialOccasionState,
    SpecialOccasionStore,
    SpecialOccasionStoreError,
    default_special_occasion_state,
)
lazy from special_occasion import OccasionKind, OccasionResponse

NOW = datetime(2027, 1, 8, 12, tzinfo=UTC)


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


def populated_state() -> SpecialOccasionState:
    responses = {
        OccasionKind.MOHAN_BIRTHDAY: OccasionResponse.ACKNOWLEDGED,
        OccasionKind.VALENTINES_DAY: OccasionResponse.CELEBRATED,
        OccasionKind.CHRISTMAS_DAY: OccasionResponse.DISMISSED,
    }
    return SpecialOccasionState(
        NOW.date(),
        {
            kind: OccasionState(
                enabled=kind is not OccasionKind.VALENTINES_DAY,
                hint_delivered_at=NOW - timedelta(hours=4),
                grumble_delivered_at=NOW - timedelta(hours=1),
                response=responses[kind],
            )
            for kind in OccasionKind
        },
    )


def assert_all_occasions_round_trip() -> None:
    settings = MemorySettings()
    store = SpecialOccasionStore(settings)
    expected = populated_state()
    store.save(expected)
    assert store.load(NOW) == expected
    payload = store.export_portable(NOW)
    assert set(payload) == {"format", "version", "local_date", "occasions"}
    assert payload["format"] == SPECIAL_OCCASION_STATE_FORMAT
    assert payload["version"] == SPECIAL_OCCASION_STATE_VERSION


def assert_date_rollover_preserves_enable_only() -> None:
    store = SpecialOccasionStore(MemorySettings())
    store.save(populated_state())
    rolled = store.load(NOW + timedelta(days=1))
    assert rolled.local_date == (NOW + timedelta(days=1)).date()
    for kind in OccasionKind:
        item = rolled.occasions[kind]
        assert item.enabled is (kind is not OccasionKind.VALENTINES_DAY)
        assert item.hint_delivered_at is None
        assert item.grumble_delivered_at is None
        assert item.response is OccasionResponse.NONE

    target = SpecialOccasionStore(MemorySettings())
    imported = target.import_portable(
        SpecialOccasionStore(
            MemorySettings()
        ).export_portable(NOW)
        | {
            "occasions": {
                kind.value: {
                    "enabled": kind is OccasionKind.MOHAN_BIRTHDAY,
                    "hint_delivered_at": NOW.isoformat(),
                    "grumble_delivered_at": None,
                    "response": "acknowledged",
                }
                for kind in OccasionKind
            }
        },
        NOW + timedelta(days=1),
    )
    assert imported.local_date == (NOW + timedelta(days=1)).date()
    for kind in OccasionKind:
        item = imported.occasions[kind]
        assert item.enabled is (kind is OccasionKind.MOHAN_BIRTHDAY)
        assert item.hint_delivered_at is None
        assert item.grumble_delivered_at is None
        assert item.response is OccasionResponse.NONE


def assert_corruption_fails_closed_and_future_fields_are_ignored() -> None:
    payload = {
        "format": SPECIAL_OCCASION_STATE_FORMAT,
        "version": SPECIAL_OCCASION_STATE_VERSION,
        "local_date": NOW.date().isoformat(),
        "future": "ignored",
        "occasions": {
            kind.value: {
                "enabled": True,
                "hint_delivered_at": None,
                "grumble_delivered_at": None,
                "response": "none",
                "future_private": "ignored",
            }
            for kind in OccasionKind
        },
    }
    payload["occasions"][OccasionKind.CHRISTMAS_DAY.value]["response"] = "bad"
    state = SpecialOccasionStore(
        MemorySettings({SPECIAL_OCCASION_STATE_KEY: payload})
    ).load(NOW)
    assert state.occasions[OccasionKind.CHRISTMAS_DAY] == OccasionState()
    for invalid_version in (True, "1", 2):
        damaged = copy.deepcopy(payload)
        damaged["version"] = invalid_version
        assert SpecialOccasionStore(
            MemorySettings({SPECIAL_OCCASION_STATE_KEY: damaged})
        ).load(NOW) == default_special_occasion_state(NOW.date())


def assert_atomic_rollback_and_safe_errors() -> None:
    original = {SPECIAL_OCCASION_STATE_KEY: {"legacy": True}, "unrelated": "keep"}
    settings = MemorySettings(original, fail_write=True)
    try:
        SpecialOccasionStore(settings).save(populated_state())
    except SpecialOccasionStoreError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing write unexpectedly succeeded")
    assert settings.values == original

    broken = MemorySettings(original, fail_write=True, fail_restore=True)
    try:
        SpecialOccasionStore(broken).save(populated_state())
    except SpecialOccasionStoreError as exc:
        assert "rollback was incomplete" in str(exc)
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing rollback unexpectedly succeeded")


def run() -> None:
    assert_all_occasions_round_trip()
    assert_date_rollover_preserves_enable_only()
    assert_corruption_fails_closed_and_future_fields_are_ignored()
    assert_atomic_rollback_and_safe_errors()
    print("SPECIAL_OCCASION_STORE_OK")


if __name__ == "__main__":
    run()
