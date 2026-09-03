"""四語凌霄內建主題名稱。"""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

THEME_TRANSLATIONS: TranslationCatalog = frozendict(
    {
        "凌霄主題": translations(
            "凌霄主题",
            "Lingxiao theme",
            "凌霄テーマ",
        ),
        "墨金・凌霄": translations(
            "墨金・凌霄",
            "Ink-Gold · Lingxiao",
            "墨金・凌霄",
        ),
        "霧靄青瓷": translations(
            "雾霭青瓷",
            "Misty Celadon",
            "霧靄青磁",
        ),
        "赤焰劍光": translations(
            "赤焰剑光",
            "Crimson Swordlight",
            "赤焔剣光",
        ),
    }
)

__all__ = ("THEME_TRANSLATIONS",)
