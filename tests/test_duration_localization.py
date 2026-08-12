from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from db import format_duration

EXPECTED_DURATIONS = frozendict({
    "zh-TW": (
        "0 分鐘",
        "0 分鐘",
        "0 分鐘",
        "1 分鐘",
        "1 分鐘",
        "59 分鐘",
        "1 小時 0 分",
        "1 小時 0 分",
        "1 小時 0 分",
        "1 小時 1 分",
        "1 小時 59 分",
        "2 小時 0 分",
    ),
    "zh-CN": (
        "0 分钟",
        "0 分钟",
        "0 分钟",
        "1 分钟",
        "1 分钟",
        "59 分钟",
        "1 小时 0 分",
        "1 小时 0 分",
        "1 小时 0 分",
        "1 小时 1 分",
        "1 小时 59 分",
        "2 小时 0 分",
    ),
    "en": (
        "0 min",
        "0 min",
        "0 min",
        "1 min",
        "1 min",
        "59 min",
        "1 h 0 min",
        "1 h 0 min",
        "1 h 0 min",
        "1 h 1 min",
        "1 h 59 min",
        "2 h 0 min",
    ),
    "ja-JP": (
        "0分",
        "0分",
        "0分",
        "1分",
        "1分",
        "59分",
        "1時間0分",
        "1時間0分",
        "1時間0分",
        "1時間1分",
        "1時間59分",
        "2時間0分",
    ),
})

BOUNDARY_SECONDS = (
    -1,
    0,
    59,
    60,
    61,
    3599,
    3600,
    3601,
    3659,
    3660,
    7199,
    7200,
)


def assert_all_languages_and_boundaries() -> None:
    assert tuple(EXPECTED_DURATIONS) == ("zh-TW", "zh-CN", "en", "ja-JP")
    for language, expected_values in EXPECTED_DURATIONS.items():
        assert tuple(
            format_duration(seconds, language)
            for seconds in BOUNDARY_SECONDS
        ) == expected_values


def assert_language_aliases_and_fallback() -> None:
    assert format_duration(3660, "zh-Hans") == "1 小时 1 分"
    assert format_duration(3660, "en-US") == "1 h 1 min"
    assert format_duration(3660, "ja") == "1時間1分"
    assert format_duration(3660, "unsupported") == "1 小時 1 分"
    assert format_duration(3660, "") == "1 小時 1 分"


def assert_default_remains_traditional_chinese() -> None:
    assert format_duration(-1) == "0 分鐘"
    assert format_duration(3599) == "59 分鐘"
    assert format_duration(3600) == "1 小時 0 分"
    assert format_duration(3720) == "1 小時 2 分"


def run() -> None:
    assert_all_languages_and_boundaries()
    assert_language_aliases_and_fallback()
    assert_default_remains_traditional_chinese()
    print("DURATION_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
