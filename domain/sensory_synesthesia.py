from __future__ import annotations

"""Sensory synesthesia (感官共感), sharing the user's physical world.

MoHan lives in the same physical world as the user.  When the local temperature
exceeds a hot threshold, her idle motion gains a "wipe sweat" or "brush hair"
frequency and she may complain; when it rains, a faint raindrop alpha layer
overlays her sleeves and her gaze turns a little wistful.

This is pure domain logic with no Qt dependency.  It maps a temperature and a
weather string to a physiological-response profile.
"""

lazy from enum import StrEnum

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
    """The wipe-sweat/brush-hair frequency (0 = none, 1 = frequent)."""
    if mood is WeatherMood.HOT:
        return 1.0
    return 0.0


def rain_alpha(mood: WeatherMood) -> float:
    """The raindrop overlay alpha (0 = none, 1 = full)."""
    if mood is WeatherMood.RAINY:
        return 0.35
    return 0.0


def complaint_line(language: str, mood: WeatherMood) -> str:
    """Return a four-language complaint for an uncomfortable weather."""
    if mood is WeatherMood.HOT:
        return {
            "zh-TW": "高雄的暑氣，連妾的赤焰劍都快融了……",
            "zh-CN": "高雄的暑气，连妾的赤焰剑都快融了……",
            "en": "This heat… even my Crimson Flame Sword is about to melt…",
            "ja-JP": "この暑さ……妾の赤焔剣まで溶けてしまいそうです……",
        }.get(language, "高雄的暑氣，連妾的赤焰劍都快融了……")
    if mood is WeatherMood.RAINY:
        return {
            "zh-TW": "下雨了……妾的衣袖，都沾上了汴京的煙雨。",
            "zh-CN": "下雨了……妾的衣袖，都沾上了汴京的烟雨。",
            "en": "It is raining… my sleeves are touched by the mist of Bianjing.",
            "ja-JP": "雨ですね……妾の袖に、汴京の煙雨がかかります。",
        }.get(language, "下雨了……妾的衣袖，都沾上了汴京的煙雨。")
    return ""
