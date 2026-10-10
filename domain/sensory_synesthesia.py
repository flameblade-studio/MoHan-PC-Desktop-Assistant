from __future__ import annotations

"""Sensory synesthesia (感官共感), sharing the user's physical world.

MoHan lives in the same physical world as the user.  When the local temperature
exceeds a hot threshold, her idle motion gains a "wipe sweat" or "brush hair"
frequency and she may complain; when it rains, a faint raindrop alpha layer
overlays her sleeves and her gaze turns a little wistful.

This is pure domain logic with Qt outside the domain boundary.  It maps a temperature and a
weather string to a physiological-response profile.
"""

lazy import json
lazy from collections.abc import Mapping
lazy from enum import StrEnum
lazy from functools import cache
lazy from string import Formatter

lazy from domain.character_source import active_character_data_path, active_expression_catalog
lazy from domain.immutable_config import deep_freeze

_RUNTIME_DIALOGUE_PATH = active_character_data_path("dialogue/runtime.json")
_RUNTIME_TEXT_KEYS = frozenset(
    {
        "background_diagnostic",
        "dashboard_ai_empty",
        "dashboard_ai_failure",
        "dashboard_quick_capture_prompt",
        "dashboard_teasing",
        "dashboard_tool_plan",
        "dashboard_work_duration",
        "pinch_reply",
        "realtime_context",
        "realtime_empty_long_term_memory",
        "realtime_empty_recent_context",
        "realtime_ready",
        "weather_hot",
        "weather_rainy",
    }
)
_RUNTIME_LOCALE_KEYS = _RUNTIME_TEXT_KEYS | {"wave_greetings"}
_SUPPORTED_LOCALES = frozenset({"zh-TW", "zh-CN", "en", "ja-JP"})
_RUNTIME_FORMAT_FIELDS = {
    "background_diagnostic": frozenset({"report_name", "issues"}),
    "dashboard_work_duration": frozenset({"duration"}),
    "realtime_context": frozenset(
        {"instructions", "memory_context", "recent_context"}
    ),
}


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate runtime-dialogue key: {key}")
        result[key] = value
    return result


@cache
def _runtime_dialogue_payload() -> Mapping[str, object]:
    """Load immutable character-owned runtime lines from the bundled data file."""

    try:
        payload = json.loads(
            _RUNTIME_DIALOGUE_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Character runtime dialogue must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema",
        "schema_version",
        "locales",
        "reply_expression_rules",
    }:
        raise ValueError("Character runtime dialogue has an invalid top-level shape.")
    if (
        payload["schema"] != "flameblade.character-runtime-dialogue.v1"
        or payload["schema_version"] != 1
    ):
        raise ValueError("Character runtime dialogue schema is unsupported.")
    locales = payload["locales"]
    if not isinstance(locales, dict) or set(locales) != _SUPPORTED_LOCALES:
        raise ValueError("Character runtime dialogue requires all four locales.")
    for locale, values in locales.items():
        if not isinstance(values, dict) or set(values) != _RUNTIME_LOCALE_KEYS:
            raise ValueError(f"Character runtime dialogue fields differ for {locale}.")
        if any(
            not isinstance(values[key], str) or not values[key]
            for key in _RUNTIME_TEXT_KEYS
        ):
            raise ValueError(f"Character runtime dialogue text is invalid for {locale}.")
        for key in _RUNTIME_TEXT_KEYS:
            fields = {
                field_name
                for _literal, field_name, _format_spec, _conversion in Formatter().parse(
                    values[key]
                )
                if field_name is not None
            }
            if fields != _RUNTIME_FORMAT_FIELDS.get(key, frozenset()):
                raise ValueError(
                    f"Character runtime dialogue placeholders differ for {locale}.{key}."
                )
        greetings = values["wave_greetings"]
        if (
            not isinstance(greetings, list)
            or not greetings
            or any(not isinstance(line, str) or not line for line in greetings)
        ):
            raise ValueError(f"Character wave greetings are invalid for {locale}.")
    rules = payload["reply_expression_rules"]
    if not isinstance(rules, list) or not rules:
        raise ValueError("Character reply-expression rules are required.")
    known_emotions = active_expression_catalog().emotion_to_expression
    seen_emotions: set[str] = set()
    seen_phrases: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"emotion", "phrases"}:
            raise ValueError("Character reply-expression rule fields differ.")
        emotion = rule["emotion"]
        phrases = rule["phrases"]
        if (
            not isinstance(emotion, str)
            or emotion not in known_emotions
            or not isinstance(phrases, list)
            or not phrases
            or any(not isinstance(phrase, str) or not phrase for phrase in phrases)
        ):
            raise ValueError("Character reply-expression rule values are invalid.")
        if emotion in seen_emotions or any(phrase in seen_phrases for phrase in phrases):
            raise ValueError("Character reply-expression rules must be unique.")
        seen_emotions.add(emotion)
        seen_phrases.update(phrases)
    return deep_freeze(payload)


def runtime_dialogue_locale(language: str) -> Mapping[str, object]:
    """Return one validated locale from the bundled runtime dialogue."""

    locales = _runtime_dialogue_payload()["locales"]
    if not isinstance(locales, Mapping):
        raise TypeError("Character runtime dialogue locales are unavailable.")
    locale = language if language in _SUPPORTED_LOCALES else "zh-TW"
    values = locales[locale]
    if not isinstance(values, Mapping):
        raise TypeError("Character runtime dialogue locale is unavailable.")
    return values


def runtime_reply_expression_rules() -> tuple[Mapping[str, object], ...]:
    """Return ordered character-owned phrase-to-emotion rules."""

    rules = _runtime_dialogue_payload()["reply_expression_rules"]
    if not isinstance(rules, tuple):
        raise TypeError("Character reply-expression rules are unavailable.")
    return rules


# Temperature thresholds (Celsius) for physiological responses.
HOT_THRESHOLD_C = 32.0

# Weather strings that count as rain.
RAIN_WEATHER = frozenset({"rain", "drizzle", "shower", "thunderstorm", "雨", "下雨"})


class WeatherMood(StrEnum):
    CLEAR = "clear"
    HOT = "hot"
    RAINY = "rainy"


def weather_mood(temperature_c: float, weather: str) -> WeatherMood:
    """Classify the current weather into a physiological mood."""
    normalized = str(weather).strip().lower()
    if normalized in RAIN_WEATHER:
        return WeatherMood.RAINY
    if temperature_c >= HOT_THRESHOLD_C:
        return WeatherMood.HOT
    return WeatherMood.CLEAR


def sweat_frequency(mood: WeatherMood) -> float:
    """The wipe-sweat/brush-hair frequency (0 = baseline, 1 = frequent)."""
    if mood is WeatherMood.HOT:
        return 1.0
    return 0.0


def rain_alpha(mood: WeatherMood) -> float:
    """The raindrop overlay alpha (0 = baseline, 1 = full)."""
    if mood is WeatherMood.RAINY:
        return 0.35
    return 0.0


def complaint_line(language: str, mood: WeatherMood) -> str:
    """Return a four-language complaint for an uncomfortable weather."""
    dialogue = runtime_dialogue_locale(language)
    if mood is WeatherMood.HOT:
        return str(dialogue["weather_hot"])
    if mood is WeatherMood.RAINY:
        return str(dialogue["weather_rainy"])
    return ""
