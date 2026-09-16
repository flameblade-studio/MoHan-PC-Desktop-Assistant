"""Contract tests for the dashboard material resolver."""
from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.theme_pack import ThemePack
lazy from presentation.dashboard_theme_materials import (
    MaterialPalette,
    resolve_material_palette,
)
lazy from presentation.lingxiao_tokens import (
    PALETTE,
    contrast_ratio,
    font_stack,
)

MINIMUM_CONTRAST_RATIO = 4.5


def _theme(*, primary: str = "#F0603A", background: str | None = None) -> ThemePack:
    return ThemePack(
        theme_id="flameblade.sponsor.flame-sword",
        display_names=frozendict(
            {
                "zh-TW": "赤焰劍光",
                "zh-CN": "赤焰劍光",
                "en": "Flame Sword Radiance",
                "ja-JP": "赤焔剣光",
            }
        ),
        tokens=frozendict(
            {
                "window": "#1A1214",
                "background": "#1A1214",
                "card": "#241A1C",
                "surface": "#241A1C",
                "text": "#F2E6E0",
                "title": "#FFD9C9",
                "muted": "#C4A99D",
                "border": "#5C4038",
                "primary": primary,
            }
        ),
        font_family="Microsoft JhengHei UI",
        radius=12,
        background=background,
        source_channel="flameblade-official",
        source_kind="original",
        author="CHOU MING HUA",
        license_name="MoHan Sponsor DLC - All Rights Reserved (ASSETS-LICENSE.md)",
    )


def test_material_palette_is_immutable_and_typed() -> None:
    materials = resolve_material_palette(PALETTE)

    assert isinstance(materials, MaterialPalette)
    assert tuple(MaterialPalette.__dataclass_fields__) == (
        "panel",
        "window",
        "text",
        "title",
        "muted",
        "border",
        "primary",
        "on_primary",
        "font",
        "background_tint",
    )
    assert MaterialPalette.__dataclass_params__.frozen
    assert hasattr(MaterialPalette, "__slots__")


def test_builtin_lingxiao_palette_maps_to_dashboard_materials() -> None:
    materials = resolve_material_palette(PALETTE)

    assert materials.panel == PALETTE.lacquer
    assert materials.window == PALETTE.ink
    assert materials.text == PALETTE.moon
    assert materials.title == PALETTE.gold_2
    assert materials.muted == PALETTE.mist
    assert materials.border == PALETTE.line
    assert materials.primary == PALETTE.gold
    assert materials.on_primary == PALETTE.on_gold
    assert materials.font == font_stack("body")
    assert materials.background_tint is None
    assert (
        contrast_ratio(materials.on_primary, materials.primary)
        >= MINIMUM_CONTRAST_RATIO
    )


def test_legacy_theme_pack_tokens_and_font_are_preserved() -> None:
    theme = _theme()
    materials = resolve_material_palette(PALETTE, theme)

    assert materials.panel == theme.tokens["card"]
    assert materials.window == theme.tokens["window"]
    assert materials.text == theme.tokens["text"]
    assert materials.title == theme.tokens["title"]
    assert materials.muted == theme.tokens["muted"]
    assert materials.border == theme.tokens["border"]
    assert materials.primary == theme.tokens["primary"]
    assert materials.on_primary == theme.tokens["surface"]
    assert materials.font == theme.font_family
    assert materials.background_tint == theme.tokens["background"]
    assert (
        contrast_ratio(materials.on_primary, materials.primary)
        >= MINIMUM_CONTRAST_RATIO
    )


def test_theme_primary_gets_a_contrast_safe_foreground() -> None:
    theme = _theme(primary="#777777")
    materials = resolve_material_palette(PALETTE, theme)

    assert materials.on_primary != theme.tokens["surface"]
    assert (
        contrast_ratio(materials.on_primary, materials.primary)
        >= MINIMUM_CONTRAST_RATIO
    )


def test_pack_background_asset_does_not_change_color_material_contract() -> None:
    materials = resolve_material_palette(PALETTE, _theme(background="assets/background.png"))

    assert materials.background_tint == "#1A1214"
