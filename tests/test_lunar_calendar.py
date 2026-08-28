from __future__ import annotations

lazy import sys
lazy from datetime import date, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.special_occasion import OccasionKind, active_occasion
lazy from domain.lunar_calendar import (
    LUNAR_YEAR_MAX,
    LUNAR_YEAR_MIN,
    lunar_to_gregorian,
    qixi_gregorian,
)

# Cross-checked anchors: Chinese New Year (lunar 1/1) Gregorian dates.
KNOWN_NEW_YEARS = {
    1900: (1, 31),
    1984: (2, 2),
    2000: (2, 5),
    2024: (2, 10),
    2025: (1, 29),
    2026: (2, 17),
    2031: (1, 23),
    2033: (1, 31),
    2034: (2, 19),
    2036: (1, 28),
    2100: (2, 9),
}

# Qixi (lunar 7/7). 2033/2034 differ from the retired ten-year lookup:
# ruling 2026-08-27 — the old table was off by one day in those two years
# (the famous 2033 leap-eleventh-month year), confirmed against New Year,
# leap-month and Mid-Autumn anchors.
KNOWN_QIXI = {
    2024: (8, 10),
    2025: (8, 29),
    2026: (8, 19),
    2027: (8, 8),
    2028: (8, 26),
    2029: (8, 16),
    2030: (8, 5),
    2031: (8, 24),
    2032: (8, 12),
    2033: (8, 1),
    2034: (8, 20),
    2035: (8, 10),
}

MIN_LUNAR_YEAR_DAYS = 353
MAX_LUNAR_YEAR_DAYS = 385


def test_new_year_anchors() -> None:
    for year, (month, day) in KNOWN_NEW_YEARS.items():
        assert lunar_to_gregorian(year, 1, 1) == date(year, month, day)


def test_qixi_anchors_and_no_expiry() -> None:
    for year, (month, day) in KNOWN_QIXI.items():
        assert qixi_gregorian(year) == date(year, month, day)
    # The retired lookup expired after 2035; the perpetual calendar must not.
    for year in (2036, 2050, 2075, 2100):
        resolved = qixi_gregorian(year)
        assert resolved is not None
        assert resolved.year == year
        assert resolved.month in (7, 8)
    assert qixi_gregorian(LUNAR_YEAR_MIN - 1) is None
    assert qixi_gregorian(LUNAR_YEAR_MAX + 1) is None


def test_known_leap_months_and_festivals() -> None:
    # 2033 is the famous leap-eleventh-month year.
    assert lunar_to_gregorian(2033, 8, 15) == date(2033, 9, 8)  # Mid-Autumn
    assert lunar_to_gregorian(2025, 5, 5) == date(2025, 5, 31)  # Duanwu
    try:
        lunar_to_gregorian(2026, 2, 1, leap=True)
    except ValueError:
        pass
    else:
        raise AssertionError("2026 has no leap second month")


def test_year_lengths_stay_astronomical() -> None:
    for year in range(LUNAR_YEAR_MIN, LUNAR_YEAR_MAX + 1):
        start = lunar_to_gregorian(year, 1, 1)
        if year == LUNAR_YEAR_MAX:
            break
        length = (lunar_to_gregorian(year + 1, 1, 1) - start).days
        assert MIN_LUNAR_YEAR_DAYS <= length <= MAX_LUNAR_YEAR_DAYS, (
            f"lunar year {year} has impossible length {length}"
        )


def test_special_occasion_resolves_qixi_beyond_the_old_table() -> None:
    for year, (month, day) in KNOWN_QIXI.items():
        occasion = active_occasion(datetime(year, month, day, 12, 0))
        assert occasion is not None
        assert occasion.kind is OccasionKind.QIXI
    beyond = qixi_gregorian(2040)
    assert beyond is not None
    occasion = active_occasion(datetime(2040, beyond.month, beyond.day, 12, 0))
    assert occasion is not None and occasion.kind is OccasionKind.QIXI


def run() -> None:
    test_new_year_anchors()
    test_qixi_anchors_and_no_expiry()
    test_known_leap_months_and_festivals()
    test_year_lengths_stay_astronomical()
    test_special_occasion_resolves_qixi_beyond_the_old_table()
    print("LUNAR_CALENDAR_OK")


if __name__ == "__main__":
    run()
