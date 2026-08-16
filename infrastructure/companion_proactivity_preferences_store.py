from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

lazy from domain.companion_proactivity_preferences import (
    BIRTHDAY_ENABLED_KEY,
    BRIEF_ABSENCE_SECONDS_KEY,
    DAILY_LIMIT_KEY,
    FOCUS_PROTECTION_KEY,
    FULLSCREEN_PROTECTION_KEY,
    HYDRATION_ENABLED_KEY,
    LONG_WAIT_SECONDS_KEY,
    MASTER_ENABLED_KEY,
    MEAL_ENABLED_KEY,
    MEETING_PROTECTION_KEY,
    OCCASIONS_ENABLED_KEY,
    REST_ENABLED_KEY,
    SETTING_KEYS,
    SITTING_ENABLED_KEY,
    CompanionProactivityPreferences,
    CompanionProactivityPreferencesError,
    UnsupportedCompanionProactivityVersion,
    export_companion_proactivity_preferences,
    import_companion_proactivity_preferences,
    preferences_from_mapping,
    settings_payload,
)
lazy from domain.performance_preferences import SettingsPort

STORE_SCHEMA_KEY: Final = "companion_proactivity_schema_version"
STORE_SCHEMA_VERSION: Final = 1
PORTABLE_SETTING_KEYS: Final = (*SETTING_KEYS, STORE_SCHEMA_KEY)
_BOUNDARY_ERRORS: Final = (Exception,)
_LEGACY_KEYS: Final = {
    MASTER_ENABLED_KEY: ("proactive_interaction_enabled",),
    BRIEF_ABSENCE_SECONDS_KEY: ("multisensory_welcome_brief_max_seconds",),
    LONG_WAIT_SECONDS_KEY: ("multisensory_welcome_long_seconds",),
}
_ALL_READ_KEYS: Final = PORTABLE_SETTING_KEYS + tuple(
    legacy for aliases in _LEGACY_KEYS.values() for legacy in aliases
)
_SETTING_FIELDS: Final = {
    MASTER_ENABLED_KEY: "enabled",
    MEAL_ENABLED_KEY: "meal_enabled",
    HYDRATION_ENABLED_KEY: "hydration_enabled",
    REST_ENABLED_KEY: "rest_enabled",
    SITTING_ENABLED_KEY: "prolonged_sitting_enabled",
    OCCASIONS_ENABLED_KEY: "special_occasions_enabled",
    BIRTHDAY_ENABLED_KEY: "birthday_enabled",
    BRIEF_ABSENCE_SECONDS_KEY: "brief_absence_seconds",
    LONG_WAIT_SECONDS_KEY: "long_wait_seconds",
    FOCUS_PROTECTION_KEY: "focus_protection_enabled",
    MEETING_PROTECTION_KEY: "meeting_protection_enabled",
    FULLSCREEN_PROTECTION_KEY: "fullscreen_protection_enabled",
    DAILY_LIMIT_KEY: "daily_limit",
}

SnapshotT = TypeVar("SnapshotT")


class CompanionProactivityPreferencesStoreError(RuntimeError):
    """A fixed-detail persistence error without backend content."""


@dataclass(slots=True)
class CompanionProactivityPreferencesDraft[SnapshotT]:
    _store: CompanionProactivityPreferencesStore[SnapshotT]
    original: CompanionProactivityPreferences
    value: CompanionProactivityPreferences
    _closed: bool = False

    def update(self, **changes: bool | int) -> Self:
        self._assert_open()
        try:
            self.value = replace(self.value, **changes)
        except (TypeError, ValueError):
            raise CompanionProactivityPreferencesStoreError(
                "Companion proactivity draft is invalid."
            ) from None
        return self

    def commit(self) -> CompanionProactivityPreferences:
        self._assert_open()
        self._store.save(self.value)
        self._closed = True
        return self.value

    def cancel(self) -> CompanionProactivityPreferences:
        self._assert_open()
        self._closed = True
        self.value = self.original
        return self.original

    def _assert_open(self) -> None:
        if self._closed:
            raise CompanionProactivityPreferencesStoreError(
                "Companion proactivity draft is already closed."
            )


class CompanionProactivityPreferencesStore[SnapshotT]:
    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self) -> CompanionProactivityPreferences:
        try:
            raw = self._settings.read(_ALL_READ_KEYS)
        except _BOUNDARY_ERRORS:
            return CompanionProactivityPreferences()
        if not isinstance(raw, Mapping):
            return CompanionProactivityPreferences()
        version = raw.get(STORE_SCHEMA_KEY)
        if version is not None and (
            type(version) is not int or version != STORE_SCHEMA_VERSION
        ):
            return CompanionProactivityPreferences()
        values = {
            field: _first(raw, key)
            for key, field in _SETTING_FIELDS.items()
        }
        return preferences_from_mapping(values)

    def begin_edit(self) -> CompanionProactivityPreferencesDraft[SnapshotT]:
        current = self.load()
        return CompanionProactivityPreferencesDraft(self, current, current)

    def save(self, preferences: CompanionProactivityPreferences) -> None:
        if not isinstance(preferences, CompanionProactivityPreferences):
            raise CompanionProactivityPreferencesStoreError(
                "Companion proactivity preferences are invalid."
            )
        values = settings_payload(preferences)
        values[STORE_SCHEMA_KEY] = STORE_SCHEMA_VERSION
        self._atomic_write(values)

    def migrate(self) -> CompanionProactivityPreferences:
        preferences = self.load()
        self.save(preferences)
        return preferences

    def export_portable(self) -> dict[str, object]:
        return export_companion_proactivity_preferences(self.load())

    def import_portable(
        self,
        payload: Mapping[str, object],
    ) -> CompanionProactivityPreferences:
        try:
            preferences = import_companion_proactivity_preferences(payload)
        except UnsupportedCompanionProactivityVersion:
            raise
        except CompanionProactivityPreferencesError:
            preferences = CompanionProactivityPreferences()
        self.save(preferences)
        return preferences

    def _atomic_write(self, values: Mapping[str, object]) -> None:
        try:
            before = self._settings.snapshot(PORTABLE_SETTING_KEYS)
        except _BOUNDARY_ERRORS:
            raise CompanionProactivityPreferencesStoreError(
                "Companion proactivity preferences could not be snapshotted."
            ) from None
        try:
            self._settings.write(values)
        except _BOUNDARY_ERRORS:
            try:
                self._settings.restore(before)
            except _BOUNDARY_ERRORS:
                raise CompanionProactivityPreferencesStoreError(
                    "Companion proactivity save failed and rollback was incomplete."
                ) from None
            raise CompanionProactivityPreferencesStoreError(
                "Companion proactivity save failed; previous values were restored."
            ) from None


def _first(raw: Mapping[str, object], key: str) -> object:
    if key in raw:
        return raw[key]
    for legacy in _LEGACY_KEYS.get(key, ()):
        if legacy in raw:
            return raw[legacy]
    return getattr(CompanionProactivityPreferences(), _SETTING_FIELDS[key])
