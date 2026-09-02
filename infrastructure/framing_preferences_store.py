from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

lazy from domain.framing_preferences import (
    ADAPTIVE_FRAMING_KEY,
    ALLOW_CLOSE_KEY,
    ALLOW_FULL_BODY_KEY,
    FOCUS_PROTECTION_KEY,
    PREFERRED_FRAMING_KEY,
    SETTING_KEYS,
    FramingPreferences,
    FramingPreferencesError,
    PreferredFraming,
    UnsupportedFramingPreferencesVersion,
    export_framing_preferences,
    import_framing_preferences,
)
lazy from domain.performance_preferences import SettingsPort

STORE_SCHEMA_KEY: Final = "framing_preferences_schema_version"
STORE_SCHEMA_VERSION: Final = 1
_STORE_KEYS: Final = (*SETTING_KEYS, STORE_SCHEMA_KEY)
_BOUNDARY_ERRORS: Final = (Exception,)
_LEGACY_KEYS: Final = {
    ADAPTIVE_FRAMING_KEY: ("adaptive_framing_enabled",),
    ALLOW_CLOSE_KEY: ("allow_close_framing",),
    ALLOW_FULL_BODY_KEY: ("allow_full_body_framing",),
    FOCUS_PROTECTION_KEY: ("framing_focus_protection",),
    PREFERRED_FRAMING_KEY: ("preferred_framing",),
}
_ALL_READ_KEYS: Final = _STORE_KEYS + tuple(
    legacy for aliases in _LEGACY_KEYS.values() for legacy in aliases
)

SnapshotT = TypeVar("SnapshotT")


class FramingPreferencesStoreError(RuntimeError):
    """A fixed-detail persistence error without backend information."""


@dataclass(slots=True)
class FramingPreferencesDraft[SnapshotT]:
    _store: FramingPreferencesStore[SnapshotT]
    original: FramingPreferences
    value: FramingPreferences
    _closed: bool = False

    def update(self, **changes: bool | PreferredFraming) -> Self:
        self._assert_open()
        try:
            self.value = replace(self.value, **changes)
        except (TypeError, ValueError):
            raise FramingPreferencesStoreError(
                "Framing preference draft is invalid."
            ) from None
        return self

    def commit(self) -> FramingPreferences:
        self._assert_open()
        self._store.save(self.value)
        self._closed = True
        return self.value

    def cancel(self) -> FramingPreferences:
        self._assert_open()
        self._closed = True
        self.value = self.original
        return self.original

    def _assert_open(self) -> None:
        if self._closed:
            raise FramingPreferencesStoreError(
                "Framing preference draft is already closed."
            )


class FramingPreferencesStore[SnapshotT]:
    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self) -> FramingPreferences:
        try:
            raw = self._settings.read(_ALL_READ_KEYS)
        except _BOUNDARY_ERRORS:
            # 後端讀不到不是「從未保存」，比照其他偏好 store 拋型別化錯誤。
            raise FramingPreferencesStoreError(
                "Framing preferences could not be read."
            ) from None
        if not isinstance(raw, Mapping):
            return FramingPreferences()
        version = raw.get(STORE_SCHEMA_KEY)
        if version is not None and (
            type(version) is not int or version != STORE_SCHEMA_VERSION
        ):
            return FramingPreferences()
        return FramingPreferences(
            adaptive_enabled=_bool_value(raw, ADAPTIVE_FRAMING_KEY, True),
            allow_close=_bool_value(raw, ALLOW_CLOSE_KEY, True),
            allow_full_body=_bool_value(raw, ALLOW_FULL_BODY_KEY, True),
            focus_protection_enabled=_bool_value(
                raw, FOCUS_PROTECTION_KEY, True
            ),
            preferred_framing=_framing_value(raw),
        )

    def begin_edit(self) -> FramingPreferencesDraft[SnapshotT]:
        current = self.load()
        return FramingPreferencesDraft(self, current, current)

    def save(self, preferences: FramingPreferences) -> None:
        if not isinstance(preferences, FramingPreferences):
            raise FramingPreferencesStoreError("Framing preferences are invalid.")
        self._atomic_write(_persisted_values(preferences))

    def migrate(self) -> FramingPreferences:
        preferences = self.load()
        self.save(preferences)
        return preferences

    def export_portable(self) -> dict[str, object]:
        return export_framing_preferences(self.load())

    def import_portable(
        self, payload: Mapping[str, object]
    ) -> FramingPreferences:
        try:
            preferences = import_framing_preferences(payload)
        except UnsupportedFramingPreferencesVersion:
            raise
        except FramingPreferencesError:
            preferences = FramingPreferences()
        self.save(preferences)
        return preferences

    def _atomic_write(self, values: Mapping[str, object]) -> None:
        try:
            before = self._settings.snapshot(_STORE_KEYS)
        except _BOUNDARY_ERRORS:
            raise FramingPreferencesStoreError(
                "Framing preferences could not be snapshotted."
            ) from None
        try:
            self._settings.write(values)
        except _BOUNDARY_ERRORS:
            try:
                self._settings.restore(before)
            except _BOUNDARY_ERRORS:
                raise FramingPreferencesStoreError(
                    "Framing preference persistence failed and rollback was incomplete."
                ) from None
            raise FramingPreferencesStoreError(
                "Framing preference persistence failed; previous values were restored."
            ) from None


def _first(raw: Mapping[str, object], key: str) -> object:
    if key in raw:
        return raw[key]
    for legacy in _LEGACY_KEYS[key]:
        if legacy in raw:
            return raw[legacy]
    return None


def _bool_value(raw: Mapping[str, object], key: str, default: bool) -> bool:
    value = _first(raw, key)
    return value if type(value) is bool else default


def _framing_value(raw: Mapping[str, object]) -> PreferredFraming:
    value = _first(raw, PREFERRED_FRAMING_KEY)
    try:
        return PreferredFraming(value) if isinstance(value, str) else PreferredFraming.AUTO
    except ValueError:
        return PreferredFraming.AUTO


def _persisted_values(preferences: FramingPreferences) -> dict[str, object]:
    return {
        ADAPTIVE_FRAMING_KEY: preferences.adaptive_enabled,
        ALLOW_CLOSE_KEY: preferences.allow_close,
        ALLOW_FULL_BODY_KEY: preferences.allow_full_body,
        FOCUS_PROTECTION_KEY: preferences.focus_protection_enabled,
        PREFERRED_FRAMING_KEY: preferences.preferred_framing.value,
        STORE_SCHEMA_KEY: STORE_SCHEMA_VERSION,
    }
