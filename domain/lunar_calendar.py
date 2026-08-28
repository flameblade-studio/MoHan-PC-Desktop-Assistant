"""Built-in lunisolar (Chinese lunar) calendar for 1900–2100.

Ruling 2026-08-27: festival dates such as Qixi (lunar 7/7) previously came
from a hand-written ten-year Gregorian lookup that silently ran out in 2036.
An external calendar service would break the offline/privacy contract, so
the perpetual calendar lives here instead: the standard Purple Mountain
Observatory lunar data (one packed integer per year, 1900–2100) plus the
classic day-count conversion — the same data every desktop calendar embeds.
"""

from __future__ import annotations

lazy from datetime import date, timedelta

LUNAR_EPOCH = date(1900, 1, 31)  # lunar 1900-01-01
LUNAR_YEAR_MIN = 1900
LUNAR_YEAR_MAX = 2100
LUNAR_MONTHS_PER_YEAR = 12

# Bits 4..16: big (30-day) month flags for months 1..13 (bit 16 = month 1);
# bits 0..3: leap-month number (0 = none); bit 16+ of 0xF0000 area unused
# in this packed form. This is the widely published PMO dataset.
_LUNAR_INFO = (
    0x04BD8, 0x04AE0, 0x0A570, 0x054D5, 0x0D260, 0x0D950, 0x16554, 0x056A0,
    0x09AD0, 0x055D2, 0x04AE0, 0x0A5B6, 0x0A4D0, 0x0D250, 0x1D255, 0x0B540,
    0x0D6A0, 0x0ADA2, 0x095B0, 0x14977, 0x04970, 0x0A4B0, 0x0B4B5, 0x06A50,
    0x06D40, 0x1AB54, 0x02B60, 0x09570, 0x052F2, 0x04970, 0x06566, 0x0D4A0,
    0x0EA50, 0x06E95, 0x05AD0, 0x02B60, 0x186E3, 0x092E0, 0x1C8D7, 0x0C950,
    0x0D4A0, 0x1D8A6, 0x0B550, 0x056A0, 0x1A5B4, 0x025D0, 0x092D0, 0x0D2B2,
    0x0A950, 0x0B557, 0x06CA0, 0x0B550, 0x15355, 0x04DA0, 0x0A5B0, 0x14573,
    0x052B0, 0x0A9A8, 0x0E950, 0x06AA0, 0x0AEA6, 0x0AB50, 0x04B60, 0x0AAE4,
    0x0A570, 0x05260, 0x0F263, 0x0D950, 0x05B57, 0x056A0, 0x096D0, 0x04DD5,
    0x04AD0, 0x0A4D0, 0x0D4D4, 0x0D250, 0x0D558, 0x0B540, 0x0B6A0, 0x195A6,
    0x095B0, 0x049B0, 0x0A974, 0x0A4B0, 0x0B27A, 0x06A50, 0x06D40, 0x0AF46,
    0x0AB60, 0x09570, 0x04AF5, 0x04970, 0x064B0, 0x074A3, 0x0EA50, 0x06B58,
    0x055C0, 0x0AB60, 0x096D5, 0x092E0, 0x0C960, 0x0D954, 0x0D4A0, 0x0DA50,
    0x07552, 0x056A0, 0x0ABB7, 0x025D0, 0x092D0, 0x0CAB5, 0x0A950, 0x0B4A0,
    0x0BAA4, 0x0AD50, 0x055D9, 0x04BA0, 0x0A5B0, 0x15176, 0x052B0, 0x0A930,
    0x07954, 0x06AA0, 0x0AD50, 0x05B52, 0x04B60, 0x0A6E6, 0x0A4E0, 0x0D260,
    0x0EA65, 0x0D530, 0x05AA0, 0x076A3, 0x096D0, 0x04AFB, 0x04AD0, 0x0A4D0,
    0x1D0B6, 0x0D250, 0x0D520, 0x0DD45, 0x0B5A0, 0x056D0, 0x055B2, 0x049B0,
    0x0A577, 0x0A4B0, 0x0AA50, 0x1B255, 0x06D20, 0x0ADA0, 0x14B63, 0x09370,
    0x049F8, 0x04970, 0x064B0, 0x168A6, 0x0EA50, 0x06B20, 0x1A6C4, 0x0AAE0,
    0x092E0, 0x0D2E3, 0x0C960, 0x0D557, 0x0D4A0, 0x0DA50, 0x05D55, 0x056A0,
    0x0A6D0, 0x055D4, 0x052D0, 0x0A9B8, 0x0A950, 0x0B4A0, 0x0B6A6, 0x0AD50,
    0x055A0, 0x0ABA4, 0x0A5B0, 0x052B0, 0x0B273, 0x06930, 0x07337, 0x06AA0,
    0x0AD50, 0x14B55, 0x04B60, 0x0A570, 0x054E4, 0x0D160, 0x0E968, 0x0D520,
    0x0DAA0, 0x16AA6, 0x056D0, 0x04AE0, 0x0A9D4, 0x0A2D0, 0x0D150, 0x0F252,
    0x0D520,
)


def _leap_month(lunar_year: int) -> int:
    return _LUNAR_INFO[lunar_year - LUNAR_YEAR_MIN] & 0xF


def _leap_days(lunar_year: int) -> int:
    if _leap_month(lunar_year) == 0:
        return 0
    return 30 if _LUNAR_INFO[lunar_year - LUNAR_YEAR_MIN] & 0x10000 else 29


def _month_days(lunar_year: int, lunar_month: int) -> int:
    if not 1 <= lunar_month <= LUNAR_MONTHS_PER_YEAR:
        raise ValueError(f"invalid lunar month: {lunar_month}")
    flag = _LUNAR_INFO[lunar_year - LUNAR_YEAR_MIN] & (0x10000 >> lunar_month)
    return 30 if flag else 29


def _year_days(lunar_year: int) -> int:
    total = sum(
        _month_days(lunar_year, month) for month in range(1, 13)
    )
    return total + _leap_days(lunar_year)


def lunar_to_gregorian(
    lunar_year: int,
    lunar_month: int,
    lunar_day: int,
    *,
    leap: bool = False,
) -> date:
    """Convert one lunar calendar date to its Gregorian date.

    ``leap=True`` addresses the intercalary repetition of ``lunar_month``
    and is rejected when that year has no such leap month.
    """
    if not LUNAR_YEAR_MIN <= lunar_year <= LUNAR_YEAR_MAX:
        raise ValueError(
            f"lunar year {lunar_year} outside the built-in "
            f"{LUNAR_YEAR_MIN}-{LUNAR_YEAR_MAX} dataset"
        )
    if leap and _leap_month(lunar_year) != lunar_month:
        raise ValueError(
            f"lunar year {lunar_year} has no leap month {lunar_month}"
        )
    month_length = (
        _leap_days(lunar_year) if leap else _month_days(lunar_year, lunar_month)
    )
    if not 1 <= lunar_day <= month_length:
        raise ValueError(
            f"invalid lunar day {lunar_day} for {lunar_year}-{lunar_month}"
            f"{' (leap)' if leap else ''}"
        )
    offset = sum(
        _year_days(year) for year in range(LUNAR_YEAR_MIN, lunar_year)
    )
    leap_number = _leap_month(lunar_year)
    for month in range(1, lunar_month):
        offset += _month_days(lunar_year, month)
        if month == leap_number:
            offset += _leap_days(lunar_year)
    if leap:
        offset += _month_days(lunar_year, lunar_month)
    return LUNAR_EPOCH + timedelta(days=offset + lunar_day - 1)


def qixi_gregorian(gregorian_year: int) -> date | None:
    """Return the Gregorian date of Qixi (lunar 7/7) in one Gregorian year.

    Lunar 7/7 always lands in the same Gregorian year, so a single-year
    conversion is sufficient. Returns None outside the dataset instead of
    guessing.
    """
    if not LUNAR_YEAR_MIN <= gregorian_year <= LUNAR_YEAR_MAX:
        return None
    return lunar_to_gregorian(gregorian_year, 7, 7)
