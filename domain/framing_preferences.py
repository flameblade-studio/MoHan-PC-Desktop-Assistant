from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import asdict, dataclass
lazy from enum import StrEnum
lazy from typing import Final

FRAMING_PREFERENCES_FORMAT: Final = "mohan-framing-preferences"
FRAMING_PREFERENCES_VERSION: Final = 1

ADAPTIVE_FRAMING_KEY: Final = "framing_adaptive_enabled"
ALLOW_CLOSE_KEY: Final = "framing_allow_close"
ALLOW_FULL_BODY_KEY: Final = "framing_allow_full_body"
FOCUS_PROTECTION_KEY: Final = "framing_focus_protection_enabled"
PREFERRED_FRAMING_KEY: Final = "framing_preferred_mode"

SETTING_KEYS: Final = (
    ADAPTIVE_FRAMING_KEY,
    ALLOW_CLOSE_KEY,
    ALLOW_FULL_BODY_KEY,
    FOCUS_PROTECTION_KEY,
    PREFERRED_FRAMING_KEY,
)


class PreferredFraming(StrEnum):
    AUTO = "auto"
    CLOSE = "close"
    HALF = "half"
    THREE_QUARTER = "three_quarter"
    FULL_BODY = "full_body"


@dataclass(frozen=True, slots=True)
class FramingPreferences:
    adaptive_enabled: bool = True
    allow_close: bool = True
    allow_full_body: bool = True
    focus_protection_enabled: bool = True
    preferred_framing: PreferredFraming = PreferredFraming.AUTO

    def __post_init__(self) -> None:
        flags = (
            self.adaptive_enabled,
            self.allow_close,
            self.allow_full_body,
            self.focus_protection_enabled,
        )
        if any(type(value) is not bool for value in flags):
            raise TypeError("Framing preference flags must be boolean.")
        if not isinstance(self.preferred_framing, PreferredFraming):
            raise TypeError("Preferred framing is invalid.")


class FramingPreferencesError(RuntimeError):
    """A fixed-detail framing preference error."""


class UnsupportedFramingPreferencesVersion(FramingPreferencesError):
    """The portable framing schema cannot be interpreted safely."""


def export_framing_preferences(
    preferences: FramingPreferences,
) -> dict[str, object]:
    if not isinstance(preferences, FramingPreferences):
        raise FramingPreferencesError("Framing preferences are invalid.")
    values = asdict(preferences)
    values["preferred_framing"] = preferences.preferred_framing.value
    return {
        "format": FRAMING_PREFERENCES_FORMAT,
        "version": FRAMING_PREFERENCES_VERSION,
        "preferences": values,
    }


def import_framing_preferences(
    payload: Mapping[str, object],
) -> FramingPreferences:
    if not isinstance(payload, Mapping):
        return FramingPreferences()
    if payload.get("format") != FRAMING_PREFERENCES_FORMAT:
        return FramingPreferences()
    version = payload.get("version")
    if type(version) is not int or version != FRAMING_PREFERENCES_VERSION:
        raise UnsupportedFramingPreferencesVersion(
            "Framing preference schema version is unsupported."
        )
    raw = payload.get("preferences")
    if not isinstance(raw, Mapping):
        return FramingPreferences()
    defaults = FramingPreferences()
    return FramingPreferences(
        adaptive_enabled=_safe_bool(
            raw.get("adaptive_enabled"), defaults.adaptive_enabled
        ),
        allow_close=_safe_bool(raw.get("allow_close"), defaults.allow_close),
        allow_full_body=_safe_bool(
            raw.get("allow_full_body"), defaults.allow_full_body
        ),
        focus_protection_enabled=_safe_bool(
            raw.get("focus_protection_enabled"),
            defaults.focus_protection_enabled,
        ),
        preferred_framing=_safe_framing(raw.get("preferred_framing")),
    )


def _safe_bool(value: object, default: bool) -> bool:
    return value if type(value) is bool else default


def _safe_framing(value: object) -> PreferredFraming:
    try:
        return PreferredFraming(value) if isinstance(value, str) else PreferredFraming.AUTO
    except ValueError:
        return PreferredFraming.AUTO
