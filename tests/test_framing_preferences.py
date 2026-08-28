from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.framing_preferences import (
    FRAMING_PREFERENCES_FORMAT,
    FRAMING_PREFERENCES_VERSION,
    FramingPreferences,
    PreferredFraming,
    UnsupportedFramingPreferencesVersion,
    export_framing_preferences,
    import_framing_preferences,
)


def assert_defaults_preserve_current_director_behavior() -> None:
    defaults = FramingPreferences()
    assert defaults.adaptive_enabled is True
    assert defaults.allow_close is True
    assert defaults.allow_full_body is True
    assert defaults.focus_protection_enabled is True
    assert defaults.preferred_framing is PreferredFraming.AUTO


def assert_strict_typed_values() -> None:
    invalid = (
        {"adaptive_enabled": 1},
        {"allow_close": "true"},
        {"allow_full_body": None},
        {"focus_protection_enabled": 0},
        {"preferred_framing": "half"},
    )
    for values in invalid:
        try:
            FramingPreferences(**values)
        except (TypeError, ValueError):
            continue
        raise AssertionError("invalid typed framing preference was accepted")


def assert_portable_round_trip_and_unknown_fields() -> None:
    preferences = FramingPreferences(
        adaptive_enabled=False,
        allow_close=False,
        allow_full_body=True,
        focus_protection_enabled=False,
        preferred_framing=PreferredFraming.THREE_QUARTER,
    )
    payload = export_framing_preferences(preferences)
    assert payload["format"] == FRAMING_PREFERENCES_FORMAT
    assert payload["version"] == FRAMING_PREFERENCES_VERSION
    payload["unknown"] = "ignored"
    payload["preferences"]["future_field"] = "ignored"
    payload["preferences"]["api_key"] = "must-not-forward"
    assert import_framing_preferences(payload) == preferences


def assert_corruption_fails_closed_and_versions_reject() -> None:
    defaults = FramingPreferences()
    assert import_framing_preferences({}) == defaults
    damaged = {
        "format": FRAMING_PREFERENCES_FORMAT,
        "version": FRAMING_PREFERENCES_VERSION,
        "preferences": {
            "adaptive_enabled": "yes",
            "allow_close": 1,
            "allow_full_body": False,
            "focus_protection_enabled": None,
            "preferred_framing": "unknown",
        },
    }
    restored = import_framing_preferences(damaged)
    assert restored.adaptive_enabled is True
    assert restored.allow_close is True
    assert restored.allow_full_body is False
    assert restored.focus_protection_enabled is True
    assert restored.preferred_framing is PreferredFraming.AUTO
    for version in (0, 2, True, "1"):
        try:
            import_framing_preferences(
                {
                    "format": FRAMING_PREFERENCES_FORMAT,
                    "version": version,
                    "preferences": {},
                }
            )
        except UnsupportedFramingPreferencesVersion:
            continue
        raise AssertionError("unsupported framing version was accepted")


def run() -> None:
    assert_defaults_preserve_current_director_behavior()
    assert_strict_typed_values()
    assert_portable_round_trip_and_unknown_fields()
    assert_corruption_fails_closed_and_versions_reject()
    print("FRAMING_PREFERENCES_OK")


if __name__ == "__main__":
    run()
