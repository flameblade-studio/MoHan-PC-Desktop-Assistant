from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from companion_proactivity_preferences import (
    PREFERENCES_FORMAT,
    PREFERENCES_VERSION,
    CompanionProactivityPreferences,
    UnsupportedCompanionProactivityVersion,
    export_companion_proactivity_preferences,
    import_companion_proactivity_preferences,
)


def assert_defaults_are_public_neutral_and_safe() -> None:
    preferences = CompanionProactivityPreferences()
    assert preferences.enabled is True
    assert preferences.meal_enabled is True
    assert preferences.hydration_enabled is True
    assert preferences.rest_enabled is True
    assert preferences.prolonged_sitting_enabled is True
    assert preferences.special_occasions_enabled is True
    assert preferences.birthday_enabled is True
    assert preferences.brief_absence_seconds == 30 * 60
    assert preferences.long_wait_seconds == 4 * 60 * 60
    assert preferences.focus_protection_enabled is True
    assert preferences.meeting_protection_enabled is True
    assert preferences.fullscreen_protection_enabled is True
    assert preferences.daily_limit == 8
    assert "title" not in repr(preferences).lower()
    assert "phrase" not in repr(preferences).lower()


def assert_threshold_and_type_invariants() -> None:
    invalid = (
        {"enabled": 1},
        {"brief_absence_seconds": 60, "long_wait_seconds": 60},
        {"brief_absence_seconds": 0},
        {"long_wait_seconds": 31 * 24 * 60 * 60},
        {"daily_limit": 0},
        {"daily_limit": True},
    )
    for changes in invalid:
        try:
            CompanionProactivityPreferences(**changes)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid preferences accepted: {changes!r}")


def assert_portable_round_trip_and_unknown_field_compatibility() -> None:
    expected = CompanionProactivityPreferences(
        enabled=False,
        meal_enabled=False,
        hydration_enabled=True,
        rest_enabled=False,
        prolonged_sitting_enabled=True,
        special_occasions_enabled=False,
        birthday_enabled=True,
        brief_absence_seconds=900,
        long_wait_seconds=7200,
        focus_protection_enabled=False,
        meeting_protection_enabled=True,
        fullscreen_protection_enabled=False,
        daily_limit=12,
    )
    payload = export_companion_proactivity_preferences(expected)
    assert payload["format"] == PREFERENCES_FORMAT
    assert payload["version"] == PREFERENCES_VERSION
    payload["future"] = "ignored"
    payload["preferences"]["future_option"] = "ignored"
    assert import_companion_proactivity_preferences(payload) == expected


def assert_corruption_falls_back_without_guessing_overlap() -> None:
    payload = {
        "format": PREFERENCES_FORMAT,
        "version": PREFERENCES_VERSION,
        "preferences": {
            "enabled": "yes",
            "brief_absence_seconds": 10000,
            "long_wait_seconds": 9000,
            "daily_limit": 999,
        },
    }
    assert import_companion_proactivity_preferences(payload) == (
        CompanionProactivityPreferences()
    )
    for version in (True, "1", 2):
        payload["version"] = version
        try:
            import_companion_proactivity_preferences(payload)
        except UnsupportedCompanionProactivityVersion:
            pass
        else:
            raise AssertionError("unsupported version unexpectedly accepted")


def run() -> None:
    assert_defaults_are_public_neutral_and_safe()
    assert_threshold_and_type_invariants()
    assert_portable_round_trip_and_unknown_field_compatibility()
    assert_corruption_falls_back_without_guessing_overlap()
    print("COMPANION_PROACTIVITY_PREFERENCES_OK")


if __name__ == "__main__":
    run()
