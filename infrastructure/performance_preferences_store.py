from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

lazy from domain.performance_preferences import (
    CAMERA_CONTEXT_KEY,
    EMOTIONAL_BACK_KEY,
    FULL_BACK_KEY,
    INTENSITY_KEY,
    LEFT_GESTURES_KEY,
    PROACTIVE_BODY_KEY,
    RIGHT_GESTURES_KEY,
    SETTING_KEYS,
    VIEW_360_KEY,
    PerformancePreferences,
    PerformancePreferencesError,
    PerformancePreferencesService,
    SettingsPort,
    UnsupportedPreferencesVersion,
)

STORE_SCHEMA_KEY: Final = "performance_preferences_schema_version"
STORE_SCHEMA_VERSION: Final = 1
_STORE_KEYS: Final = (*SETTING_KEYS, STORE_SCHEMA_KEY)
_BOUNDARY_ERRORS: Final = (Exception,)
_PREFERENCE_SETTING_VALUES: Final = {
    "proactive_body_enabled": PROACTIVE_BODY_KEY,
    "intensity_percent": INTENSITY_KEY,
    "view_360_enabled": VIEW_360_KEY,
    "full_back_view_enabled": FULL_BACK_KEY,
    "emotional_back_view_enabled": EMOTIONAL_BACK_KEY,
    "left_gestures_enabled": LEFT_GESTURES_KEY,
    "right_gestures_enabled": RIGHT_GESTURES_KEY,
    "camera_context_enabled": CAMERA_CONTEXT_KEY,
}

SnapshotT = TypeVar("SnapshotT")


class PerformancePreferencesStoreError(RuntimeError):
    """A fixed-detail persistence error without backend information."""


@dataclass(slots=True)
class PerformancePreferencesDraft[SnapshotT]:
    """In-memory edit session; cancellation never touches persistence."""

    _store: PerformancePreferencesStore[SnapshotT]
    original: PerformancePreferences
    value: PerformancePreferences
    _closed: bool = False

    def update(self, **changes: bool | int) -> Self:
        self._assert_open()
        try:
            self.value = replace(self.value, **changes)
        except (TypeError, ValueError):
            raise PerformancePreferencesStoreError(
                "Performance preference draft is invalid."
            ) from None
        return self

    def commit(self) -> PerformancePreferences:
        self._assert_open()
        self._store.save(self.value)
        self._closed = True
        return self.value

    def cancel(self) -> PerformancePreferences:
        self._assert_open()
        self._closed = True
        self.value = self.original
        return self.original

    def _assert_open(self) -> None:
        if self._closed:
            raise PerformancePreferencesStoreError(
                "Performance preference draft is already closed."
            )


class PerformancePreferencesStore[SnapshotT]:
    """Pluggable atomic persistence and portable-transfer adapter."""

    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings
        self._service = PerformancePreferencesService(settings)

    def load(self) -> PerformancePreferences:
        version = self._stored_version()
        if version not in (None, STORE_SCHEMA_VERSION):
            return PerformancePreferences()
        return self._service.load()

    def begin_edit(self) -> PerformancePreferencesDraft[SnapshotT]:
        current = self.load()
        return PerformancePreferencesDraft(self, current, current)

    def save(self, preferences: PerformancePreferences) -> None:
        if not isinstance(preferences, PerformancePreferences):
            raise PerformancePreferencesStoreError(
                "Performance preferences are invalid."
            )
        self._atomic_write(_persisted_values(preferences))

    def migrate(self) -> PerformancePreferences:
        """Write canonical keys and current schema without deleting old keys."""

        preferences = self.load()
        self.save(preferences)
        return preferences

    def export_portable(self) -> dict[str, object]:
        """Rebuild the allowlisted portable payload from typed preferences."""

        return self._service.export_payload(self.load())

    def import_portable(
        self,
        payload: Mapping[str, object],
    ) -> PerformancePreferences:
        """Import known fields only and persist them atomically."""

        try:
            preferences = self._service.import_payload(payload)
        except UnsupportedPreferencesVersion:
            raise
        except PerformancePreferencesError:
            preferences = PerformancePreferences()
        self.save(preferences)
        return preferences

    def _stored_version(self) -> int | None:
        try:
            raw = self._settings.read((STORE_SCHEMA_KEY,))
        except _BOUNDARY_ERRORS:
            return -1
        if not isinstance(raw, Mapping) or STORE_SCHEMA_KEY not in raw:
            return None
        version = raw[STORE_SCHEMA_KEY]
        return version if type(version) is int else -1

    def _atomic_write(self, values: Mapping[str, object]) -> None:
        try:
            before = self._settings.snapshot(_STORE_KEYS)
        except _BOUNDARY_ERRORS:
            raise PerformancePreferencesStoreError(
                "Performance preferences could not be snapshotted."
            ) from None
        try:
            self._settings.write(values)
        except _BOUNDARY_ERRORS:
            try:
                self._settings.restore(before)
            except _BOUNDARY_ERRORS:
                raise PerformancePreferencesStoreError(
                    "Performance preference persistence failed and rollback was incomplete."
                ) from None
            raise PerformancePreferencesStoreError(
                "Performance preference persistence failed; previous values were restored."
            ) from None


def _persisted_values(
    preferences: PerformancePreferences,
) -> dict[str, object]:
    values = {
        setting_key: getattr(preferences, field)
        for field, setting_key in _PREFERENCE_SETTING_VALUES.items()
    }
    values[STORE_SCHEMA_KEY] = STORE_SCHEMA_VERSION
    return values
