from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import asdict, dataclass
lazy from typing import Protocol, TypeVar

PREFERENCES_FORMAT = "mohan-performance-preferences"
PREFERENCES_VERSION = 1
MAX_INTENSITY_PERCENT = 100

PROACTIVE_BODY_KEY = "performance_proactive_body_enabled"
INTENSITY_KEY = "performance_intensity_percent"
VIEW_360_KEY = "performance_360_view_enabled"
FULL_BACK_KEY = "performance_full_back_view_enabled"
EMOTIONAL_BACK_KEY = "performance_emotional_back_view_enabled"
LEFT_GESTURES_KEY = "performance_left_gestures_enabled"
RIGHT_GESTURES_KEY = "performance_right_gestures_enabled"
CAMERA_CONTEXT_KEY = "performance_camera_context_enabled"

SETTING_KEYS = (
    PROACTIVE_BODY_KEY,
    INTENSITY_KEY,
    VIEW_360_KEY,
    FULL_BACK_KEY,
    EMOTIONAL_BACK_KEY,
    LEFT_GESTURES_KEY,
    RIGHT_GESTURES_KEY,
    CAMERA_CONTEXT_KEY,
)

_FIELD_KEYS = {
    "proactive_body_enabled": PROACTIVE_BODY_KEY,
    "intensity_percent": INTENSITY_KEY,
    "view_360_enabled": VIEW_360_KEY,
    "full_back_view_enabled": FULL_BACK_KEY,
    "emotional_back_view_enabled": EMOTIONAL_BACK_KEY,
    "left_gestures_enabled": LEFT_GESTURES_KEY,
    "right_gestures_enabled": RIGHT_GESTURES_KEY,
    "camera_context_enabled": CAMERA_CONTEXT_KEY,
}
_LEGACY_KEYS = {
    PROACTIVE_BODY_KEY: ("proactive_performance_enabled",),
    INTENSITY_KEY: ("performance_intensity",),
    VIEW_360_KEY: ("character_360_enabled",),
    FULL_BACK_KEY: ("allow_full_back_view",),
    EMOTIONAL_BACK_KEY: ("allow_emotional_back_view",),
    LEFT_GESTURES_KEY: ("left_gestures_enabled",),
    RIGHT_GESTURES_KEY: ("right_gestures_enabled",),
    CAMERA_CONTEXT_KEY: ("camera_context_driven",),
}
_ALL_READ_KEYS = SETTING_KEYS + tuple(
    legacy
    for aliases in _LEGACY_KEYS.values()
    for legacy in aliases
)
_SETTINGS_BOUNDARY_ERRORS = (Exception,)

SnapshotT = TypeVar("SnapshotT")


class SettingsPort(Protocol[SnapshotT]):
    """Atomic-capable setting boundary supplied by a composition root."""

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]: ...

    def snapshot(self, keys: tuple[str, ...]) -> SnapshotT: ...

    def write(self, values: Mapping[str, object]) -> None: ...

    def restore(self, snapshot: SnapshotT) -> None: ...


class PerformancePreferencesError(RuntimeError):
    """Fixed-detail preference boundary failure."""


class UnsupportedPreferencesVersion(PerformancePreferencesError):
    """The portable schema version cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class PerformancePreferences:
    proactive_body_enabled: bool = True
    intensity_percent: int = 60
    view_360_enabled: bool = False
    full_back_view_enabled: bool = False
    emotional_back_view_enabled: bool = False
    left_gestures_enabled: bool = True
    right_gestures_enabled: bool = True
    camera_context_enabled: bool = False

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for name, value in asdict(self).items()
            if name != "intensity_percent"
        ):
            raise ValueError("Performance preference flags must be boolean.")
        if (
            type(self.intensity_percent) is not int
            or not 0 <= self.intensity_percent <= MAX_INTENSITY_PERCENT
        ):
            raise ValueError("Performance intensity must be from 0 to 100.")


class PerformancePreferencesService[SnapshotT]:
    """Load, migrate and transact portable performance preferences."""

    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self) -> PerformancePreferences:
        try:
            raw = self._settings.read(_ALL_READ_KEYS)
        except _SETTINGS_BOUNDARY_ERRORS:
            return PerformancePreferences()
        if not isinstance(raw, Mapping):
            return PerformancePreferences()
        resolved = {
            field: _safe_value(field, _first_value(raw, key))
            for field, key in _FIELD_KEYS.items()
        }
        return PerformancePreferences(**resolved)

    def snapshot(self) -> SnapshotT:
        try:
            return self._settings.snapshot(SETTING_KEYS)
        except _SETTINGS_BOUNDARY_ERRORS:
            raise PerformancePreferencesError(
                "Performance preferences could not be snapshotted."
            ) from None

    def save(self, preferences: PerformancePreferences) -> None:
        if not isinstance(preferences, PerformancePreferences):
            raise PerformancePreferencesError(
                "Performance preferences are invalid."
            )
        before = self.snapshot()
        try:
            self._settings.write(_settings_payload(preferences))
        except _SETTINGS_BOUNDARY_ERRORS:
            try:
                self._settings.restore(before)
            except _SETTINGS_BOUNDARY_ERRORS:
                raise PerformancePreferencesError(
                    "Performance preference save failed and rollback was incomplete."
                ) from None
            raise PerformancePreferencesError(
                "Performance preference save failed; previous values were restored."
            ) from None

    def cancel(self, snapshot: SnapshotT) -> None:
        try:
            self._settings.restore(snapshot)
        except _SETTINGS_BOUNDARY_ERRORS:
            raise PerformancePreferencesError(
                "Performance preference cancellation could not be restored."
            ) from None

    def migrate_legacy(self) -> PerformancePreferences:
        preferences = self.load()
        self.save(preferences)
        return preferences

    @staticmethod
    def export_payload(
        preferences: PerformancePreferences,
    ) -> dict[str, object]:
        if not isinstance(preferences, PerformancePreferences):
            raise PerformancePreferencesError(
                "Performance preferences are invalid."
            )
        return {
            "format": PREFERENCES_FORMAT,
            "version": PREFERENCES_VERSION,
            "preferences": asdict(preferences),
        }

    @staticmethod
    def import_payload(payload: Mapping[str, object]) -> PerformancePreferences:
        if not isinstance(payload, Mapping):
            return PerformancePreferences()
        if payload.get("format") != PREFERENCES_FORMAT:
            return PerformancePreferences()
        version = payload.get("version")
        if type(version) is not int or version != PREFERENCES_VERSION:
            raise UnsupportedPreferencesVersion(
                "Performance preference schema version is unsupported."
            )
        raw = payload.get("preferences")
        if not isinstance(raw, Mapping):
            return PerformancePreferences()
        defaults = PerformancePreferences()
        values = {
            field: _safe_value(field, raw.get(field, getattr(defaults, field)))
            for field in _FIELD_KEYS
        }
        return PerformancePreferences(**values)


def _first_value(raw: Mapping[str, object], canonical: str) -> object:
    if canonical in raw:
        return raw[canonical]
    for legacy in _LEGACY_KEYS[canonical]:
        if legacy in raw:
            return raw[legacy]
    return getattr(PerformancePreferences(), _field_for_key(canonical))


def _field_for_key(key: str) -> str:
    return next(field for field, setting_key in _FIELD_KEYS.items() if setting_key == key)


def _safe_value(field: str, value: object) -> bool | int:
    default = getattr(PerformancePreferences(), field)
    if field == "intensity_percent":
        return value if type(value) is int and 0 <= value <= MAX_INTENSITY_PERCENT else default
    return value if type(value) is bool else default


def _settings_payload(
    preferences: PerformancePreferences,
) -> dict[str, object]:
    values = asdict(preferences)
    return {setting_key: values[field] for field, setting_key in _FIELD_KEYS.items()}
