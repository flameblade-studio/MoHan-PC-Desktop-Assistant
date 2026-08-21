from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.performance_preferences_store import (
    STORE_SCHEMA_KEY,
    STORE_SCHEMA_VERSION,
    PerformancePreferencesStore,
    PerformancePreferencesStoreError,
)
lazy from performance_preferences import (
    CAMERA_CONTEXT_KEY,
    INTENSITY_KEY,
    PREFERENCES_FORMAT,
    PREFERENCES_VERSION,
    PROACTIVE_BODY_KEY,
    SETTING_KEYS,
    PerformancePreferences,
    UnsupportedPreferencesVersion,
)

MIGRATED_INTENSITY_PERCENT = 35
ROUND_TRIP_INTENSITY_PERCENT = 88


class MemorySettings:
    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        fail_write_after: int | None = None,
        fail_restore: bool = False,
    ) -> None:
        self.values = dict(values or {})
        self.write_calls = 0
        self.restore_calls = 0
        self.fail_write_after = fail_write_after
        self.fail_restore = fail_restore

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.write_calls += 1
        for index, (key, value) in enumerate(values.items()):
            self.values[key] = copy.deepcopy(value)
            if self.fail_write_after is not None and index >= self.fail_write_after:
                raise RuntimeError("PRIVATE-WRITE-DETAIL")

    def restore(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        if self.fail_restore:
            raise RuntimeError("PRIVATE-RESTORE-DETAIL")
        for key in (*SETTING_KEYS, STORE_SCHEMA_KEY):
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def expect_store_error(operation, error_type=PerformancePreferencesStoreError) -> str:
    try:
        operation()
    except error_type as exc:
        message = str(exc)
        assert "PRIVATE" not in message
        return message
    raise AssertionError("operation unexpectedly succeeded")


def assert_cancel_never_persists() -> None:
    settings = MemorySettings({PROACTIVE_BODY_KEY: True, INTENSITY_KEY: 60})
    store = PerformancePreferencesStore(settings)
    original = copy.deepcopy(settings.values)
    draft = store.begin_edit().update(
        proactive_body_enabled=False,
        intensity_percent=90,
        camera_context_enabled=True,
    )
    assert draft.cancel() == PerformancePreferences()
    assert settings.values == original
    assert settings.write_calls == 0
    assert settings.restore_calls == 0
    expect_store_error(draft.commit)


def assert_commit_is_one_atomic_persistence_operation() -> None:
    settings = MemorySettings()
    store = PerformancePreferencesStore(settings)
    committed = store.begin_edit().update(
        intensity_percent=75,
        view_360_enabled=True,
        full_back_view_enabled=True,
    ).commit()
    assert settings.write_calls == 1
    assert settings.values[STORE_SCHEMA_KEY] == STORE_SCHEMA_VERSION
    assert store.load() == committed


def assert_partial_write_rolls_back_without_harming_old_settings() -> None:
    original = {
        PROACTIVE_BODY_KEY: True,
        INTENSITY_KEY: 40,
        "unrelated_existing_setting": "preserve-me",
    }
    settings = MemorySettings(original, fail_write_after=3)
    store = PerformancePreferencesStore(settings)
    expect_store_error(lambda: store.save(PerformancePreferences(intensity_percent=80)))
    assert settings.values == original
    assert settings.restore_calls == 1

    incomplete = MemorySettings(original, fail_write_after=0, fail_restore=True)
    message = expect_store_error(
        lambda: PerformancePreferencesStore(incomplete).save(PerformancePreferences())
    )
    assert "rollback was incomplete" in message


def assert_corruption_and_versions_fail_closed() -> None:
    damaged = MemorySettings(
        {
            STORE_SCHEMA_KEY: STORE_SCHEMA_VERSION,
            PROACTIVE_BODY_KEY: "yes",
            INTENSITY_KEY: 999,
            CAMERA_CONTEXT_KEY: "enabled",
        }
    )
    assert PerformancePreferencesStore(damaged).load() == PerformancePreferences()
    for corrupt_version in ("1", True, -1, 2):
        settings = MemorySettings({STORE_SCHEMA_KEY: corrupt_version, INTENSITY_KEY: 90})
        assert PerformancePreferencesStore(settings).load() == PerformancePreferences()


def assert_versioned_legacy_migration_preserves_old_and_unrelated_values() -> None:
    settings = MemorySettings(
        {
            "proactive_performance_enabled": False,
            "performance_intensity": 35,
            "camera_context_driven": False,
            "unrelated_existing_setting": {"keep": True},
        }
    )
    store = PerformancePreferencesStore(settings)
    migrated = store.migrate()
    assert migrated.proactive_body_enabled is False
    assert migrated.intensity_percent == MIGRATED_INTENSITY_PERCENT
    assert migrated.camera_context_enabled is False
    assert settings.values[STORE_SCHEMA_KEY] == STORE_SCHEMA_VERSION
    assert settings.values["proactive_performance_enabled"] is False
    assert settings.values["unrelated_existing_setting"] == {"keep": True}


def assert_portable_round_trip_is_complete_and_private_data_is_dropped() -> None:
    source = PerformancePreferencesStore(
        MemorySettings(
            {
                PROACTIVE_BODY_KEY: False,
                INTENSITY_KEY: 88,
                CAMERA_CONTEXT_KEY: True,
                "api_key": "must-not-export",
                "face_identity_templates": "must-not-export",
                "multisensory_phrasebook_v1": "must-not-export",
            }
        )
    )
    payload = source.export_portable()
    assert payload["format"] == PREFERENCES_FORMAT
    assert payload["version"] == PREFERENCES_VERSION
    assert set(payload) == {"format", "version", "preferences"}
    serialized = repr(payload)
    assert "must-not-export" not in serialized
    assert "api_key" not in serialized
    assert "face_identity" not in serialized
    assert "phrasebook" not in serialized

    payload["future_top_level"] = "ignored-private-value"
    payload["secret"] = "ignored-secret"
    payload["preferences"]["future_field"] = "ignored"
    payload["preferences"]["camera_biometric_data"] = "ignored"
    payload["preferences"]["private_phrasebook"] = "ignored"
    target_settings = MemorySettings({"api_key": "local-secret-remains"})
    imported = PerformancePreferencesStore(target_settings).import_portable(payload)
    assert imported.proactive_body_enabled is False
    assert imported.intensity_percent == ROUND_TRIP_INTENSITY_PERCENT
    assert imported.camera_context_enabled is True
    assert target_settings.values["api_key"] == "local-secret-remains"
    assert "future_field" not in target_settings.values
    assert "camera_biometric_data" not in target_settings.values
    assert "private_phrasebook" not in target_settings.values


def assert_unknown_portable_version_is_rejected_without_writes() -> None:
    settings = MemorySettings({INTENSITY_KEY: 42})
    store = PerformancePreferencesStore(settings)
    original = copy.deepcopy(settings.values)
    expect_store_error(
        lambda: store.import_portable(
            {
                "format": PREFERENCES_FORMAT,
                "version": PREFERENCES_VERSION + 1,
                "preferences": {},
            }
        ),
        UnsupportedPreferencesVersion,
    )
    assert settings.values == original
    assert settings.write_calls == 0


def run() -> None:
    assert_cancel_never_persists()
    assert_commit_is_one_atomic_persistence_operation()
    assert_partial_write_rolls_back_without_harming_old_settings()
    assert_corruption_and_versions_fail_closed()
    assert_versioned_legacy_migration_preserves_old_and_unrelated_values()
    assert_portable_round_trip_is_complete_and_private_data_is_dropped()
    assert_unknown_portable_version_is_rejected_without_writes()
    print("PERFORMANCE_PREFERENCES_STORE_OK")


if __name__ == "__main__":
    run()
