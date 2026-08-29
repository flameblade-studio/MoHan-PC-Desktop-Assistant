"""Contract tests for the theme retint transform.

Guards the v4.5.1 fix where installed theme packs only tinted a few stray
frames: the flagship stylesheet must adopt the pack's color family while
neutrals, gold accents, and danger reds keep their semantic roles.
"""

from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.theme_retint import retint_stylesheet
lazy from presentation.flagship_theme import _theme_stylesheet

CRIMSON_TOKENS = {"primary": "#D9481C"}


def test_neutrals_and_semantic_accents_stay_put() -> None:
    sheet = (
        "QLabel { color: #ffffff; background: #24364a00; }"
        "QFrame { border: 1px solid #b42318; }"  # danger red
        "QLineEdit:focus { border-color: #f0d58b; }"  # gold focus
        "QWidget { background: rgba(255, 255, 255, 26); }"
    )
    # #24364a00 is not matched as an 8-digit color by design; the 6-digit
    # prefix would be desaturated navy — verify true neutrals separately.
    result = retint_stylesheet("QLabel { color: #ffffff; }", CRIMSON_TOKENS)
    assert result == "QLabel { color: #ffffff; }"
    result = retint_stylesheet(sheet, CRIMSON_TOKENS)
    assert "#b42318" in result
    assert "#f0d58b" in result
    assert "rgba(255, 255, 255, 26)" in result


def test_blue_violet_band_moves_to_theme_family() -> None:
    result = retint_stylesheet(
        "QFrame { background: #7189c7; }", CRIMSON_TOKENS
    )
    assert "#7189c7" not in result
    # The replacement must be a warm color: red channel dominates blue.
    replacement = result.split("#")[1][:6]
    red = int(replacement[0:2], 16)
    blue = int(replacement[4:6], 16)
    assert red > blue


def test_rgba_alpha_survives() -> None:
    result = retint_stylesheet(
        "QFrame { background: rgba(53, 67, 133, 248); }", CRIMSON_TOKENS
    )
    assert result.endswith("248); }")
    assert "rgba(53, 67, 133, 248)" not in result


def test_neutral_primary_disables_retint() -> None:
    sheet = "QFrame { background: #7189c7; }"
    assert retint_stylesheet(sheet, {"primary": "#888888"}) == sheet
    assert retint_stylesheet(sheet, {}) == sheet


def test_full_flagship_stylesheet_recolors_without_structural_drift() -> None:
    base = _theme_stylesheet(1.0, high_contrast=False)
    themed = retint_stylesheet(base, CRIMSON_TOKENS)
    assert themed != base
    # Only color literals may change: selector/brace structure is identical.
    strip = lambda text: [
        line
        for line in text.splitlines()
        if "#" not in line and "rgba(" not in line
    ]
    assert strip(themed) == strip(base)
    assert themed.count("{") == base.count("{")
    assert themed.count("}") == base.count("}")


if __name__ == "__main__":
    test_neutrals_and_semantic_accents_stay_put()
    test_blue_violet_band_moves_to_theme_family()
    test_rgba_alpha_survives()
    test_neutral_primary_disables_retint()
    test_full_flagship_stylesheet_recolors_without_structural_drift()
    print("THEME_RETINT_OK")
