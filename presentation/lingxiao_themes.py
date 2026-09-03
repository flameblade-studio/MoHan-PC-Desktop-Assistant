"""凌霄內建主題包的資料定義與對比保護。

這裡只放主題資料，不複製旗艦 QSS。三個主題共用同一組語意角色；
QSS 仍由 ``presentation.flagship_theme`` 依角色套用。
"""
from __future__ import annotations

lazy import colorsys
lazy from dataclasses import dataclass
lazy from typing import Final

lazy from presentation.lingxiao_tokens import (
    PALETTE,
    PALETTE_HIGH_CONTRAST,
    TEXT_ON_SURFACE_PAIRS,
    LingxiaoPalette,
    contrast_ratio,
)

DEFAULT_THEME_ID: Final = "ink-gold"
MINIMUM_CONTRAST_RATIO: Final = 4.5
THEME_SETTING_KEY: Final = "flagship_theme"
THEME_IDS: Final = ("ink-gold", "celadon", "crimson")
_PALETTE_FIELDS: Final = tuple(LingxiaoPalette.__dataclass_fields__)


@dataclass(frozen=True, slots=True)
class LingxiaoTheme:
    """一個可選的凌霄主題包，包含一般與高對比完整色板。"""

    theme_id: str
    palette: LingxiaoPalette
    high_contrast_palette: LingxiaoPalette


def _palette(values: dict[str, str]) -> LingxiaoPalette:
    return LingxiaoPalette(**values)


def _rotate_hex(color: str, hue_shift: float) -> str:
    """Rotate a source token first; curated overrides then resolve semantics."""

    red, green, blue = (
        int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)
    )
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    rotated = colorsys.hsv_to_rgb((hue + hue_shift) % 1.0, saturation, value)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rotated)


def _retinted_palette(
    source: LingxiaoPalette,
    hue_shift: float,
    overrides: dict[str, str],
) -> LingxiaoPalette:
    """Use hue rotation as the baseline, then tune role conflicts explicitly."""

    values = {
        field: _rotate_hex(getattr(source, field), hue_shift)
        for field in _PALETTE_FIELDS
    }
    values.update(overrides)
    return _palette(values)


# B：以深青瓷與月白為骨，金色角色改為水色，保留 jade/amber 的語意分層。
_CELADON = LingxiaoTheme(
    "celadon",
    _retinted_palette(
        PALETTE,
        0.96,
        {
            "ink": "#071b22",
            "ink_deep": "#041319",
            "lacquer": "#0d2c33",
            "lacquer_2": "#16434a",
            "moon": "#e9f4ef",
            "mist": "#b4cfca",
            "gold": "#67d2d0",
            "gold_2": "#a4eeee",
            "gold_dim": "#418c91",
            "jade": "#75d7c6",
            "amber": "#efc35c",
            "cinnabar": "#f07863",
            "cinnabar_text": "#ffdcd3",
            "sky": "#91d8f5",
            "on_gold": "#062127",
            "selection": "#24606b",
        }
    ),
    _retinted_palette(
        PALETTE_HIGH_CONTRAST,
        0.96,
        {
            "ink": "#000d11",
            "ink_deep": "#00080b",
            "lacquer": "#082128",
            "lacquer_2": "#0f3740",
            "moon": "#ffffff",
            "mist": "#d9f2ee",
            "gold": "#7debea",
            "gold_2": "#d0ffff",
            "gold_dim": "#62b4b9",
            "jade": "#9affee",
            "amber": "#ffd66b",
            "cinnabar": "#ff806b",
            "cinnabar_text": "#ffffff",
            "sky": "#bde8ff",
            "on_gold": "#001b20",
            "selection": "#2d6975",
        }
    ),
)

# C：赤金同源於 DLC「赤焰劍光」。危險色刻意改成暗赤紫，避免紅色主題
# 讓危險狀態與主色混淆；danger QSS 仍保留獨立邊框與狀態角色。
_CRIMSON = LingxiaoTheme(
    "crimson",
    _retinted_palette(
        PALETTE,
        0.02,
        {
            "ink": "#1d0b13",
            "ink_deep": "#12060c",
            "lacquer": "#32121d",
            "lacquer_2": "#4c1b28",
            "moon": "#fff0e8",
            "mist": "#e7bdaf",
            "gold": "#e0ad5a",
            "gold_2": "#ffd27d",
            "gold_dim": "#a96e2f",
            "jade": "#91d6b4",
            "amber": "#f3c15d",
            "cinnabar": "#7e1f5b",
            "cinnabar_text": "#ffd9e4",
            "sky": "#a7d6ed",
            "on_gold": "#210b12",
            "selection": "#70283c",
        }
    ),
    _retinted_palette(
        PALETTE_HIGH_CONTRAST,
        0.02,
        {
            "ink": "#120008",
            "ink_deep": "#080004",
            "lacquer": "#270d18",
            "lacquer_2": "#3e1424",
            "moon": "#ffffff",
            "mist": "#ffd7d8",
            "gold": "#f0b958",
            "gold_2": "#ffe19a",
            "gold_dim": "#d08b31",
            "jade": "#a9f4cf",
            "amber": "#ffd875",
            "cinnabar": "#78245f",
            "cinnabar_text": "#ffe7f4",
            "sky": "#c9e8ff",
            "on_gold": "#26050d",
            "selection": "#6d2441",
        }
    ),
)


THEMES: Final = frozendict(
    {
        DEFAULT_THEME_ID: LingxiaoTheme(
            DEFAULT_THEME_ID,
            PALETTE,
            PALETTE_HIGH_CONTRAST,
        ),
        "celadon": _CELADON,
        "crimson": _CRIMSON,
    }
)


def canonical_theme_id(theme_id: object) -> str:
    """Return a known theme id, failing safely to the non-dangerous default."""

    candidate = str(theme_id or DEFAULT_THEME_ID).strip().casefold()
    return candidate if candidate in THEMES else DEFAULT_THEME_ID


def theme_definition(theme_id: object) -> LingxiaoTheme:
    return THEMES[canonical_theme_id(theme_id)]


def palette_for_theme(
    theme_id: object,
    *,
    high_contrast: bool,
) -> LingxiaoPalette:
    theme = theme_definition(theme_id)
    return theme.high_contrast_palette if high_contrast else theme.palette


def theme_contrast_failures(theme: LingxiaoTheme) -> tuple[tuple[str, str, float], ...]:
    """Return any failed token pairs so tests and diagnostics share one rule."""

    failures: list[tuple[str, str, float]] = []
    for palette in (theme.palette, theme.high_contrast_palette):
        for foreground, background in TEXT_ON_SURFACE_PAIRS:
            ratio = contrast_ratio(
                getattr(palette, foreground),
                getattr(palette, background),
            )
            if ratio < MINIMUM_CONTRAST_RATIO:
                failures.append((foreground, background, ratio))
    return tuple(failures)


def validate_theme_definitions() -> None:
    """Fail closed if a palette ever loses a role or its WCAG margin."""

    for theme_id in THEME_IDS:
        theme = THEMES[theme_id]
        for palette in (theme.palette, theme.high_contrast_palette):
            if tuple(palette.__dataclass_fields__) != _PALETTE_FIELDS:
                raise ValueError(f"Incomplete Lingxiao palette: {theme_id}")
        failures = theme_contrast_failures(theme)
        if failures:
            raise ValueError(f"WCAG contrast failure in {theme_id}: {failures}")


validate_theme_definitions()

__all__ = (
    "DEFAULT_THEME_ID",
    "MINIMUM_CONTRAST_RATIO",
    "THEME_IDS",
    "THEME_SETTING_KEY",
    "THEMES",
    "LingxiaoTheme",
    "canonical_theme_id",
    "palette_for_theme",
    "theme_contrast_failures",
    "theme_definition",
    "validate_theme_definitions",
)
