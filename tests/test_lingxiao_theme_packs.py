from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication, QWidget

lazy from presentation.flagship_theme import apply_flagship_theme
lazy from presentation.lingxiao_themes import (
    DEFAULT_THEME_ID,
    THEME_IDS,
    THEMES,
    canonical_theme_id,
    palette_for_theme,
    theme_contrast_failures,
)
lazy from presentation.lingxiao_tokens import (
    TEXT_ON_SURFACE_PAIRS,
    contrast_ratio,
)
lazy from presentation.flagship_ui_localization import FlagshipTranslator

MINIMUM_CONTRAST_RATIO = 4.5
MINIMUM_DANGER_DISTANCE = 80.0
EXPECTED_THEME_IDS = ("ink-gold", "celadon", "crimson")
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
EXPECTED_THEME_LABELS = {
    "凌霄主題": ("凌霄主題", "凌霄主题", "Lingxiao theme", "凌霄テーマ"),
    "墨金・凌霄": ("墨金・凌霄", "墨金・凌霄", "Ink-Gold · Lingxiao", "墨金・凌霄"),
    "霧靄青瓷": ("霧靄青瓷", "雾霭青瓷", "Misty Celadon", "霧靄青磁"),
    "赤焰劍光": ("赤焰劍光", "赤焰剑光", "Crimson Swordlight", "赤焔剣光"),
}


def _rgb_distance(first: str, second: str) -> float:
    channels = lambda value: tuple(
        int(value[index:index + 2], 16) for index in (1, 3, 5)
    )
    left, right = channels(first), channels(second)
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) ** 0.5


def test_theme_catalog_has_three_complete_theme_packs() -> None:
    assert THEME_IDS == EXPECTED_THEME_IDS
    assert tuple(THEMES) == EXPECTED_THEME_IDS
    for theme_id in THEME_IDS:
        theme = THEMES[theme_id]
        assert theme.theme_id == theme_id
        assert set(theme.palette.__dataclass_fields__) == set(
            theme.high_contrast_palette.__dataclass_fields__
        )


def test_unknown_theme_fails_safely_to_ink_gold() -> None:
    assert canonical_theme_id("unknown-theme") == DEFAULT_THEME_ID
    assert palette_for_theme(
        "unknown-theme",
        high_contrast=False,
    ) == palette_for_theme(DEFAULT_THEME_ID, high_contrast=False)


def test_every_theme_palette_meets_wcag_pairs() -> None:
    for theme_id in THEME_IDS:
        theme = THEMES[theme_id]
        assert theme_contrast_failures(theme) == ()
        for palette in (theme.palette, theme.high_contrast_palette):
            for foreground, background in TEXT_ON_SURFACE_PAIRS:
                assert contrast_ratio(
                    getattr(palette, foreground),
                    getattr(palette, background),
                ) >= MINIMUM_CONTRAST_RATIO


def test_danger_color_is_distinct_from_primary_color() -> None:
    for theme_id in THEME_IDS:
        for high_contrast in (False, True):
            palette = palette_for_theme(theme_id, high_contrast=high_contrast)
            assert _rgb_distance(palette.cinnabar, palette.gold) >= MINIMUM_DANGER_DISTANCE


def test_theme_selector_labels_are_translated_in_all_languages() -> None:
    for source, expected in EXPECTED_THEME_LABELS.items():
        labels = tuple(FlagshipTranslator(language).text(source) for language in LANGUAGES)
        assert labels == expected
        assert all(label.strip() for label in labels)


def test_switching_theme_changes_the_flagship_stylesheet() -> None:
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    sheets = []
    for theme_id in THEME_IDS:
        apply_flagship_theme(root, theme=theme_id)
        sheet = root.styleSheet()
        assert palette_for_theme(theme_id, high_contrast=False).gold in sheet
        sheets.append(sheet)
    assert len(set(sheets)) == len(THEME_IDS)
    root.close()
    app.processEvents()


if __name__ == "__main__":
    test_theme_catalog_has_three_complete_theme_packs()
    test_unknown_theme_fails_safely_to_ink_gold()
    test_every_theme_palette_meets_wcag_pairs()
    test_danger_color_is_distinct_from_primary_color()
    test_theme_selector_labels_are_translated_in_all_languages()
    test_switching_theme_changes_the_flagship_stylesheet()
    print("LINGXIAO_THEME_PACKS_OK")
