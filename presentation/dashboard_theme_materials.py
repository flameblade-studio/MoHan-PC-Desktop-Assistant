"""Resolve stable dashboard materials from the built-in or legacy theme.

The dashboard drawing layer uses semantic materials instead of depending on
the implementation names of either the Lingxiao palette or a theme archive.
Theme-pack structure and persistence stay in their existing modules; this
adapter only translates the values needed by the new dashboard presentation.
"""
from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Final

lazy from domain.theme_pack import ThemePack
lazy from presentation.lingxiao_tokens import (
    LingxiaoPalette,
    contrast_ratio,
    font_stack,
)

__all__ = ("MaterialPalette", "resolve_material_palette")

MINIMUM_CONTRAST_RATIO: Final = 4.5
_DARK_ON_PRIMARY: Final = "#111827"
_BLACK_ON_PRIMARY: Final = "#000000"
_LIGHT_ON_PRIMARY: Final = "#FFFFFF"


@dataclass(frozen=True, slots=True)
class MaterialPalette:
    """The semantic colors and typography used by dashboard paint code."""

    panel: str
    window: str
    text: str
    title: str
    muted: str
    border: str
    primary: str
    on_primary: str
    font: str
    background_tint: str | None


def resolve_material_palette(
    palette: LingxiaoPalette,
    theme: ThemePack | None = None,
) -> MaterialPalette:
    """Return dashboard materials for ``palette`` or an installed theme pack.

    A theme pack supplies only stable semantic colors, so the adapter reads
    the existing v2 tokens directly.  Its ``background`` color is exposed as
    ``background_tint`` for a color-only scene layer; an optional packaged
    background remains an independent asset decision at the UI hook.
    """

    if theme is None:
        return _materials_from_lingxiao(palette)
    return _materials_from_theme(theme)


def _materials_from_lingxiao(palette: LingxiaoPalette) -> MaterialPalette:
    primary = palette.gold
    return MaterialPalette(
        panel=palette.lacquer,
        window=palette.ink,
        text=palette.moon,
        title=palette.gold_2,
        muted=palette.mist,
        border=palette.line,
        primary=primary,
        on_primary=_readable_on_primary(primary, palette.on_gold),
        font=font_stack("body"),
        background_tint=None,
    )


def _materials_from_theme(theme: ThemePack) -> MaterialPalette:
    token = theme.tokens
    primary = token["primary"]
    return MaterialPalette(
        panel=token["card"],
        window=token["window"],
        text=token["text"],
        title=token["title"],
        muted=token["muted"],
        border=token["border"],
        primary=primary,
        on_primary=_readable_on_primary(primary, token["surface"]),
        font=theme.font_family,
        background_tint=token["background"],
    )


def _readable_on_primary(primary: str, preferred: str) -> str:
    """Keep a primary action readable while retaining a valid theme token."""

    if contrast_ratio(preferred, primary) >= MINIMUM_CONTRAST_RATIO:
        return preferred
    candidates = (_DARK_ON_PRIMARY, _BLACK_ON_PRIMARY, _LIGHT_ON_PRIMARY)
    return max(candidates, key=lambda color: contrast_ratio(color, primary))
