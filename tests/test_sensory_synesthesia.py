from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.sensory_synesthesia import (
    WeatherMood,
    complaint_line,
    rain_alpha,
    sweat_frequency,
    weather_mood,
)


def test_weather_mood_classification() -> None:
    assert weather_mood(35.0, "clear") is WeatherMood.HOT
    assert weather_mood(20.0, "rain") is WeatherMood.RAINY
    assert weather_mood(20.0, "clear") is WeatherMood.CLEAR


def test_sweat_frequency_only_when_hot() -> None:
    assert sweat_frequency(WeatherMood.HOT) == 1.0
    assert sweat_frequency(WeatherMood.CLEAR) == 0.0
    assert sweat_frequency(WeatherMood.RAINY) == 0.0


def test_rain_alpha_only_when_rainy() -> None:
    assert rain_alpha(WeatherMood.RAINY) > 0.0
    assert rain_alpha(WeatherMood.CLEAR) == 0.0
    assert rain_alpha(WeatherMood.HOT) == 0.0


def test_complaint_lines_are_four_language() -> None:
    hot = complaint_line("zh-TW", WeatherMood.HOT)
    assert "暑氣" in hot
    assert complaint_line("en", WeatherMood.HOT)
    assert complaint_line("ja-JP", WeatherMood.HOT)
    rainy = complaint_line("zh-TW", WeatherMood.RAINY)
    assert "煙雨" in rainy
    assert complaint_line("zh-TW", WeatherMood.CLEAR) == ""


def run() -> None:
    test_weather_mood_classification()
    test_sweat_frequency_only_when_hot()
    test_rain_alpha_only_when_rainy()
    test_complaint_lines_are_four_language()
    print("SENSORY_SYNESTHESIA_OK")


if __name__ == "__main__":
    run()
