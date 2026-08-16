from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, fields
lazy from typing import Final

PREFERENCES_FORMAT: Final = "mohan-companion-proactivity-preferences"
PREFERENCES_VERSION: Final = 1

MASTER_ENABLED_KEY: Final = "companion_proactivity_enabled"
MEAL_ENABLED_KEY: Final = "companion_meal_reminders_enabled"
HYDRATION_ENABLED_KEY: Final = "companion_hydration_reminders_enabled"
REST_ENABLED_KEY: Final = "companion_rest_reminders_enabled"
SITTING_ENABLED_KEY: Final = "companion_sitting_reminders_enabled"
OCCASIONS_ENABLED_KEY: Final = "companion_special_occasions_enabled"
BIRTHDAY_ENABLED_KEY: Final = "companion_birthday_enabled"
BRIEF_ABSENCE_SECONDS_KEY: Final = "companion_brief_absence_seconds"
LONG_WAIT_SECONDS_KEY: Final = "companion_long_wait_seconds"
FOCUS_PROTECTION_KEY: Final = "companion_focus_protection_enabled"
MEETING_PROTECTION_KEY: Final = "companion_meeting_protection_enabled"
FULLSCREEN_PROTECTION_KEY: Final = "companion_fullscreen_protection_enabled"
DAILY_LIMIT_KEY: Final = "companion_daily_proactivity_limit"

SETTING_KEYS: Final = (
    MASTER_ENABLED_KEY,
    MEAL_ENABLED_KEY,
    HYDRATION_ENABLED_KEY,
    REST_ENABLED_KEY,
    SITTING_ENABLED_KEY,
    OCCASIONS_ENABLED_KEY,
    BIRTHDAY_ENABLED_KEY,
    BRIEF_ABSENCE_SECONDS_KEY,
    LONG_WAIT_SECONDS_KEY,
    FOCUS_PROTECTION_KEY,
    MEETING_PROTECTION_KEY,
    FULLSCREEN_PROTECTION_KEY,
    DAILY_LIMIT_KEY,
)

_BOOLEAN_FIELDS: Final = (
    "enabled",
    "meal_enabled",
    "hydration_enabled",
    "rest_enabled",
    "prolonged_sitting_enabled",
    "special_occasions_enabled",
    "birthday_enabled",
    "focus_protection_enabled",
    "meeting_protection_enabled",
    "fullscreen_protection_enabled",
)
_FIELD_SETTING_KEYS: Final = {
    "enabled": MASTER_ENABLED_KEY,
    "meal_enabled": MEAL_ENABLED_KEY,
    "hydration_enabled": HYDRATION_ENABLED_KEY,
    "rest_enabled": REST_ENABLED_KEY,
    "prolonged_sitting_enabled": SITTING_ENABLED_KEY,
    "special_occasions_enabled": OCCASIONS_ENABLED_KEY,
    "birthday_enabled": BIRTHDAY_ENABLED_KEY,
    "brief_absence_seconds": BRIEF_ABSENCE_SECONDS_KEY,
    "long_wait_seconds": LONG_WAIT_SECONDS_KEY,
    "focus_protection_enabled": FOCUS_PROTECTION_KEY,
    "meeting_protection_enabled": MEETING_PROTECTION_KEY,
    "fullscreen_protection_enabled": FULLSCREEN_PROTECTION_KEY,
    "daily_limit": DAILY_LIMIT_KEY,
}


class CompanionProactivityPreferencesError(RuntimeError):
    """A fixed-detail preference boundary error."""


class UnsupportedCompanionProactivityVersion(
    CompanionProactivityPreferencesError
):
    """The portable schema version cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class CompanionProactivityPreferences:
    enabled: bool = True
    meal_enabled: bool = True
    hydration_enabled: bool = True
    rest_enabled: bool = True
    prolonged_sitting_enabled: bool = True
    special_occasions_enabled: bool = True
    birthday_enabled: bool = True
    brief_absence_seconds: int = 30 * 60
    long_wait_seconds: int = 4 * 60 * 60
    focus_protection_enabled: bool = True
    meeting_protection_enabled: bool = True
    fullscreen_protection_enabled: bool = True
    daily_limit: int = 8

    def __post_init__(self) -> None:
        if any(type(getattr(self, name)) is not bool for name in _BOOLEAN_FIELDS):
            raise TypeError("Companion proactivity flags must be boolean.")
        if (
            type(self.brief_absence_seconds) is not int
            or not 60 <= self.brief_absence_seconds <= 12 * 60 * 60
        ):
            raise ValueError("Brief absence threshold is invalid.")
        if (
            type(self.long_wait_seconds) is not int
            or not 5 * 60 <= self.long_wait_seconds <= 30 * 24 * 60 * 60
        ):
            raise ValueError("Long wait threshold is invalid.")
        if self.brief_absence_seconds >= self.long_wait_seconds:
            raise ValueError("Brief absence and long wait thresholds overlap.")
        if type(self.daily_limit) is not int or not 1 <= self.daily_limit <= 32:
            raise ValueError("Daily proactivity limit is invalid.")


def export_companion_proactivity_preferences(
    preferences: CompanionProactivityPreferences,
) -> dict[str, object]:
    if not isinstance(preferences, CompanionProactivityPreferences):
        raise CompanionProactivityPreferencesError(
            "Companion proactivity preferences are invalid."
        )
    return {
        "format": PREFERENCES_FORMAT,
        "version": PREFERENCES_VERSION,
        "preferences": _field_values(preferences),
    }


def import_companion_proactivity_preferences(
    payload: Mapping[str, object],
) -> CompanionProactivityPreferences:
    if not isinstance(payload, Mapping):
        return CompanionProactivityPreferences()
    if payload.get("format") != PREFERENCES_FORMAT:
        return CompanionProactivityPreferences()
    version = payload.get("version")
    if type(version) is not int or version != PREFERENCES_VERSION:
        raise UnsupportedCompanionProactivityVersion(
            "Companion proactivity preference version is unsupported."
        )
    raw = payload.get("preferences")
    return preferences_from_mapping(raw)


def preferences_from_mapping(
    raw: object,
) -> CompanionProactivityPreferences:
    defaults = CompanionProactivityPreferences()
    if not isinstance(raw, Mapping):
        return defaults
    values = {
        field.name: _safe_field_value(
            field.name,
            raw.get(field.name, getattr(defaults, field.name)),
            defaults,
        )
        for field in fields(defaults)
    }
    try:
        return CompanionProactivityPreferences(**values)
    except (TypeError, ValueError):
        return defaults


def settings_payload(
    preferences: CompanionProactivityPreferences,
) -> dict[str, object]:
    if not isinstance(preferences, CompanionProactivityPreferences):
        raise CompanionProactivityPreferencesError(
            "Companion proactivity preferences are invalid."
        )
    return {
        setting_key: getattr(preferences, field_name)
        for field_name, setting_key in _FIELD_SETTING_KEYS.items()
    }


def _field_values(
    preferences: CompanionProactivityPreferences,
) -> dict[str, object]:
    return {
        field.name: getattr(preferences, field.name)
        for field in fields(preferences)
    }


def _safe_field_value(
    name: str,
    value: object,
    defaults: CompanionProactivityPreferences,
) -> bool | int:
    default = getattr(defaults, name)
    if name in _BOOLEAN_FIELDS:
        return value if type(value) is bool else default
    if name == "brief_absence_seconds":
        return value if type(value) is int and 60 <= value <= 43200 else default
    if name == "long_wait_seconds":
        return (
            value
            if type(value) is int and 300 <= value <= 2592000
            else default
        )
    if name == "daily_limit":
        return value if type(value) is int and 1 <= value <= 32 else default
    raise AssertionError("Unknown companion proactivity preference field.")
