from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from companion_proactivity_preferences import (
    BRIEF_ABSENCE_SECONDS_KEY,
    LONG_WAIT_SECONDS_KEY,
    MASTER_ENABLED_KEY,
    SETTING_KEYS,
    CompanionProactivityPreferences,
)
lazy from infrastructure.companion_proactivity_preferences_store import (
    PORTABLE_SETTING_KEYS,
    STORE_SCHEMA_KEY,
    STORE_SCHEMA_VERSION,
    CompanionProactivityPreferencesStore,
    CompanionProactivityPreferencesStoreError,
)

BRIEF_ABSENCE_SECONDS = 1200
LONG_WAIT_SECONDS = 10800


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
        self.write_calls = 0

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.write_calls += 1
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("PRIVATE-WRITE-CONTENT")

    def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise RuntimeError("PRIVATE-RESTORE-CONTENT")
        for key in PORTABLE_SETTING_KEYS:
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def assert_staged_save_cancel_and_round_trip() -> None:
    settings = MemorySettings()
    store = CompanionProactivityPreferencesStore(settings)
    original = copy.deepcopy(settings.values)
    cancelled = store.begin_edit().update(
        enabled=False,
        brief_absence_seconds=600,
        long_wait_seconds=3600,
    ).cancel()
    assert cancelled == CompanionProactivityPreferences()
    assert settings.values == original
    assert settings.write_calls == 0

    expected = store.begin_edit().update(
        enabled=False,
        meal_enabled=False,
        hydration_enabled=True,
        rest_enabled=False,
        prolonged_sitting_enabled=False,
        special_occasions_enabled=False,
        birthday_enabled=False,
        brief_absence_seconds=600,
        long_wait_seconds=3600,
        focus_protection_enabled=False,
        meeting_protection_enabled=False,
        fullscreen_protection_enabled=False,
        daily_limit=5,
    ).commit()
    assert store.load() == expected
    assert settings.values[STORE_SCHEMA_KEY] == STORE_SCHEMA_VERSION
    assert set(SETTING_KEYS) <= settings.values.keys()

    target = CompanionProactivityPreferencesStore(MemorySettings())
    assert target.import_portable(store.export_portable()) == expected
    assert target.load() == expected


def assert_legacy_migration_preserves_source_and_unrelated_values() -> None:
    settings = MemorySettings(
        {
            "proactive_interaction_enabled": False,
            "multisensory_welcome_brief_max_seconds": BRIEF_ABSENCE_SECONDS,
            "multisensory_welcome_long_seconds": LONG_WAIT_SECONDS,
            "unrelated": {"keep": True},
        }
    )
    store = CompanionProactivityPreferencesStore(settings)
    loaded = store.load()
    assert loaded.enabled is False
    assert loaded.brief_absence_seconds == BRIEF_ABSENCE_SECONDS
    assert loaded.long_wait_seconds == LONG_WAIT_SECONDS
    assert store.migrate() == loaded
    assert settings.values[MASTER_ENABLED_KEY] is False
    assert settings.values[BRIEF_ABSENCE_SECONDS_KEY] == BRIEF_ABSENCE_SECONDS
    assert settings.values[LONG_WAIT_SECONDS_KEY] == LONG_WAIT_SECONDS
    assert settings.values["proactive_interaction_enabled"] is False
    assert settings.values["unrelated"] == {"keep": True}


def assert_corrupt_database_values_fail_closed() -> None:
    corruptions = (
        {STORE_SCHEMA_KEY: True, MASTER_ENABLED_KEY: False},
        {STORE_SCHEMA_KEY: 2, MASTER_ENABLED_KEY: False},
        {
            STORE_SCHEMA_KEY: STORE_SCHEMA_VERSION,
            BRIEF_ABSENCE_SECONDS_KEY: 10000,
            LONG_WAIT_SECONDS_KEY: 9000,
        },
    )
    for values in corruptions:
        assert CompanionProactivityPreferencesStore(
            MemorySettings(values)
        ).load() == CompanionProactivityPreferences()


def assert_atomic_failure_rolls_back_and_hides_backend_content() -> None:
    original = {MASTER_ENABLED_KEY: True, "unrelated": "keep"}
    settings = MemorySettings(original, fail_write=True)
    try:
        CompanionProactivityPreferencesStore(settings).save(
            CompanionProactivityPreferences(enabled=False)
        )
    except CompanionProactivityPreferencesStoreError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing save unexpectedly succeeded")
    assert settings.values == original

    broken = MemorySettings(original, fail_write=True, fail_restore=True)
    try:
        CompanionProactivityPreferencesStore(broken).save(
            CompanionProactivityPreferences(enabled=False)
        )
    except CompanionProactivityPreferencesStoreError as exc:
        assert "rollback was incomplete" in str(exc)
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failing rollback unexpectedly succeeded")


def run() -> None:
    assert_staged_save_cancel_and_round_trip()
    assert_legacy_migration_preserves_source_and_unrelated_values()
    assert_corrupt_database_values_fail_closed()
    assert_atomic_failure_rolls_back_and_hides_backend_content()
    print("COMPANION_PROACTIVITY_PREFERENCES_STORE_OK")


if __name__ == "__main__":
    run()
