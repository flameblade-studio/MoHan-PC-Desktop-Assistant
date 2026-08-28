"""Recolor the flagship stylesheet toward a theme pack's palette.

The flagship stylesheet owns MoHan's page structure with a blue-violet
palette expressed through ~100 literal colors (hex and rgba, many inside
gradients).  Theme packs previously appended low-specificity selectors that
the flagship's attribute selectors always beat, so an installed theme only
tinted a handful of stray widgets (v4.5.1 live report, 2026-08-29: the
crimson theme showed up as "a few orange frames").

Instead of tokenizing every literal (a rewrite the line-count ratchet also
forbids), this module retints the rendered stylesheet as a string transform:

* Neutral colors (near-greyscale) keep their role and are never touched.
* Accent colors outside the blue-violet band — the gold focus ring and the
  danger reds — are semantic and stay put.
* Colors inside the blue-violet band (hue 180°-360°) are compressed onto a
  narrow band around the theme's primary hue, preserving their relative
  hue offsets, saturation, and lightness — so gradients keep their depth
  while the whole shell adopts the theme's color family.

The transform is deliberately pure and Qt-free so it can be unit-tested.
"""

from __future__ import annotations

lazy import colorsys
lazy import re

__all__ = ("retint_stylesheet",)

# Colors with less saturation than this are treated as neutral greys/whites.
NEUTRAL_SATURATION_THRESHOLD = 0.08
# The flagship's own color family lives in this hue band (degrees).
SOURCE_BAND_START = 180.0
SOURCE_BAND_END = 360.0
# Center of the flagship blue-violet band; offsets are measured from here.
SOURCE_BAND_CENTER = 260.0
# Relative hue offsets are compressed by this factor around the target hue,
# keeping layered gradients distinguishable without scattering the palette.
HUE_COMPRESSION = 0.30

MAX_CHANNEL_VALUE = 255

HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6})\b")
RGBA_COLOR = re.compile(
    r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)"
)


def _hue_degrees(red: int, green: int, blue: int) -> tuple[float, float, float]:
    hue, lightness, saturation = colorsys.rgb_to_hls(
        red / 255.0, green / 255.0, blue / 255.0
    )
    return hue * 360.0, lightness, saturation


def _retint_channels(
    red: int,
    green: int,
    blue: int,
    target_hue: float,
) -> tuple[int, int, int] | None:
    """Return retinted RGB, or None when the color must stay untouched."""

    hue, lightness, saturation = _hue_degrees(red, green, blue)
    if saturation < NEUTRAL_SATURATION_THRESHOLD:
        return None
    if not (SOURCE_BAND_START <= hue < SOURCE_BAND_END):
        return None
    offset = (hue - SOURCE_BAND_CENTER) * HUE_COMPRESSION
    new_hue = (target_hue + offset) % 360.0
    new_red, new_green, new_blue = colorsys.hls_to_rgb(
        new_hue / 360.0, lightness, saturation
    )
    return (
        round(new_red * 255.0),
        round(new_green * 255.0),
        round(new_blue * 255.0),
    )


def _primary_hue(tokens: object) -> float | None:
    try:
        primary = str(tokens["primary"])  # type: ignore[index]
        red = int(primary[1:3], 16)
        green = int(primary[3:5], 16)
        blue = int(primary[5:7], 16)
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    hue, _, saturation = _hue_degrees(red, green, blue)
    if saturation < NEUTRAL_SATURATION_THRESHOLD:
        # A neutral primary (grey/white theme) has no meaningful hue to
        # steer toward; leave the flagship palette alone.
        return None
    return hue


def retint_stylesheet(stylesheet: str, tokens: object) -> str:
    """Steer the flagship stylesheet's color family toward the theme primary.

    ``tokens`` is a theme pack's token mapping; only ``primary`` is read.
    The transform never changes stylesheet structure — only color literals.
    """

    target_hue = _primary_hue(tokens)
    if target_hue is None:
        return stylesheet

    def _replace_hex(match: re.Match[str]) -> str:
        value = match.group(1)
        channels = _retint_channels(
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
            target_hue,
        )
        if channels is None:
            return match.group(0)
        return "#{:02x}{:02x}{:02x}".format(*channels)

    def _replace_rgba(match: re.Match[str]) -> str:
        red, green, blue, alpha = (int(part) for part in match.groups())
        if max(red, green, blue) > MAX_CHANNEL_VALUE:
            return match.group(0)
        channels = _retint_channels(red, green, blue, target_hue)
        if channels is None:
            return match.group(0)
        return "rgba({}, {}, {}, {})".format(*channels, alpha)

    recolored = HEX_COLOR.sub(_replace_hex, stylesheet)
    return RGBA_COLOR.sub(_replace_rgba, recolored)
