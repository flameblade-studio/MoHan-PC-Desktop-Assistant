from __future__ import annotations

lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.performance_preferences import (
    CAMERA_CONTEXT_KEY,
    EMOTIONAL_BACK_KEY,
    FULL_BACK_KEY,
    INTENSITY_KEY,
    LEFT_GESTURES_KEY,
    PREFERENCES_FORMAT,
    PREFERENCES_VERSION,
    PROACTIVE_BODY_KEY,
    RIGHT_GESTURES_KEY,
    SETTING_KEYS,
    VIEW_360_KEY,
    PerformancePreferences,
    PerformancePreferencesError,
    PerformancePreferencesService,
    UnsupportedPreferencesVersion,
)


class MemorySettings:
    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        fail_write_after: int | None = None,
        fail_restore: bool = False,
        fail_read: bool = False,
    ) -> None:
        self.values = dict(values or {})
        self.fail_write_after = fail_write_after
        self.fail_restore = fail_restore
        self.fail_read = fail_read

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        if self.fail_read:
            raise RuntimeError("PRIVATE-READ-DETAIL")
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        for index, (key, value) in enumerate(values.items()):
            self.values[key] = value
            if self.fail_write_after is not None and index >= self.fail_write_after:
                raise RuntimeError("PRIVATE-WRITE-DETAIL")

    def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise RuntimeError("PRIVATE-RESTORE-DETAIL")
        for key in SETTING_KEYS:
            self.values.pop(key, None)
        self.values.update(snapshot)


def expect_error(operation, error_type=PerformancePreferencesError) -> str:
    try:
        operation()
    except error_type as exc:
        message = str(exc)
        assert "PRIVATE" not in message
        return message
    raise AssertionError("operation unexpectedly succeeded")


def assert_safe_defaults_preserve_existing_behavior() -> None:
    preferences = PerformancePreferencesService(MemorySettings()).load()
    assert preferences == PerformancePreferences()
    assert preferences.proactive_body_enabled is True
    assert preferences.left_gestures_enabled is True
    assert preferences.right_gestures_enabled is True
    assert preferences.view_360_enabled is False
    assert preferences.full_back_view_enabled is False
    assert preferences.emotional_back_view_enabled is False
    assert preferences.camera_context_enabled is False


def assert_strict_ranges_and_corruption_fail_closed() -> None:
    invalid = MemorySettings(
        {
            PROACTIVE_BODY_KEY: 1,
            INTENSITY_KEY: 101,
            VIEW_360_KEY: "yes",
            FULL_BACK_KEY: None,
            EMOTIONAL_BACK_KEY: [],
            LEFT_GESTURES_KEY: 0,
            RIGHT_GESTURES_KEY: "false",
            CAMERA_CONTEXT_KEY: 1,
        }
    )
    assert PerformancePreferencesService(invalid).load() == PerformancePreferences()
    assert PerformancePreferencesService(MemorySettings(fail_read=True)).load() == PerformancePreferences()
    for intensity in (-1, 101, True, 1.5):
        expect_error(lambda intensity=intensity: PerformancePreferences(intensity_percent=intensity), ValueError)


def assert_legacy_migration_is_atomic_and_canonical() -> None:
    settings = MemorySettings(
        {
            "proactive_performance_enabled": False,
            "performance_intensity": 35,
            "character_360_enabled": True,
            "allow_full_back_view": True,
            "allow_emotional_back_view": True,
            "left_gestures_enabled": False,
            "right_gestures_enabled": True,
            "camera_context_driven": False,
        }
    )
    service = PerformancePreferencesService(settings)
    migrated = service.migrate_legacy()
    assert migrated == PerformancePreferences(
        proactive_body_enabled=False,
        intensity_percent=35,
        view_360_enabled=True,
        full_back_view_enabled=True,
        emotional_back_view_enabled=True,
        left_gestures_enabled=False,
        right_gestures_enabled=True,
        camera_context_enabled=False,
    )
    assert all(key in settings.values for key in SETTING_KEYS)


def assert_snapshot_save_cancel_and_rollback() -> None:
    settings = MemorySettings({PROACTIVE_BODY_KEY: True, INTENSITY_KEY: 60})
    service = PerformancePreferencesService(settings)
    snapshot = service.snapshot()
    changed = PerformancePreferences(
        proactive_body_enabled=False,
        intensity_percent=25,
        left_gestures_enabled=False,
        right_gestures_enabled=False,
    )
    service.save(changed)
    assert service.load() == changed
    service.cancel(snapshot)
    assert service.load() == PerformancePreferences()

    failing = MemorySettings(
        {PROACTIVE_BODY_KEY: True, INTENSITY_KEY: 60},
        fail_write_after=2,
    )
    failing_service = PerformancePreferencesService(failing)
    expect_error(lambda: failing_service.save(changed))
    assert failing.values == {PROACTIVE_BODY_KEY: True, INTENSITY_KEY: 60}

    incomplete = MemorySettings(fail_write_after=0, fail_restore=True)
    message = expect_error(lambda: PerformancePreferencesService(incomplete).save(changed))
    assert "rollback was incomplete" in message


def assert_portable_schema_round_trip_and_unknown_ignored() -> None:
    preferences = PerformancePreferences(
        intensity_percent=85,
        view_360_enabled=True,
        camera_context_enabled=True,
    )
    payload = PerformancePreferencesService.export_payload(preferences)
    assert payload == {
        "format": PREFERENCES_FORMAT,
        "version": PREFERENCES_VERSION,
        "preferences": {
            "proactive_body_enabled": True,
            "intensity_percent": 85,
            "view_360_enabled": True,
            "full_back_view_enabled": False,
            "emotional_back_view_enabled": False,
            "left_gestures_enabled": True,
            "right_gestures_enabled": True,
            "camera_context_enabled": True,
        },
    }
    payload["future_top_level"] = "ignored"
    payload["preferences"]["future_performance_option"] = "ignored"
    assert PerformancePreferencesService.import_payload(payload) == preferences
    assert "secret" not in repr(payload).lower()


def assert_import_corruption_and_version_validation() -> None:
    defaults = PerformancePreferences()
    assert PerformancePreferencesService.import_payload({}) == defaults
    assert PerformancePreferencesService.import_payload(
        {"format": PREFERENCES_FORMAT, "version": 1, "preferences": "broken"}
    ) == defaults
    corrupted = {
        "format": PREFERENCES_FORMAT,
        "version": 1,
        "preferences": {
            "intensity_percent": -50,
            "camera_context_enabled": "true",
            "left_gestures_enabled": False,
        },
    }
    imported = PerformancePreferencesService.import_payload(corrupted)
    assert imported.intensity_percent == defaults.intensity_percent
    assert imported.camera_context_enabled is False
    assert imported.left_gestures_enabled is False
    for version in (0, 2, True, "1"):
        expect_error(
            lambda version=version: PerformancePreferencesService.import_payload(
                {"format": PREFERENCES_FORMAT, "version": version, "preferences": {}}
            ),
            UnsupportedPreferencesVersion,
        )


def run() -> None:
    assert_safe_defaults_preserve_existing_behavior()
    assert_strict_ranges_and_corruption_fail_closed()
    assert_legacy_migration_is_atomic_and_canonical()
    assert_snapshot_save_cancel_and_rollback()
    assert_portable_schema_round_trip_and_unknown_ignored()
    assert_import_corruption_and_version_validation()
    print("PERFORMANCE_PREFERENCES_OK")


if __name__ == "__main__":
    run()
