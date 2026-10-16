"""WCAG 1.4.3 contrast governance over every application stylesheet.

Owner ruling 2026-08-29 («WCAG 對比度治理應該要徹查漏網之魚»): any rule that
pairs a text color with a background in the same block must reach 4.5:1.
Disabled-state selectors are exempt per WCAG 1.4.3 (inactive UI components),
and that exemption is explicit and reviewed here rather than silent.
"""

from __future__ import annotations

lazy import re
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.theme_pack import _contrast_ratio
lazy from presentation.dashboard_control_style import POPUP_STYLE
lazy from presentation.flagship_theme import _theme_stylesheet
lazy from presentation.presentation_resources import LIGHT_MENU_STYLE, STYLE

MINIMUM_RATIO = 4.5
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
FOREGROUND = re.compile(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6})")
BACKGROUND = re.compile(r"(?<![-\w])background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6})")
SELECTION_BG = re.compile(r"selection-background-color\s*:\s*(#[0-9a-fA-F]{6})")
SELECTION_FG = re.compile(r"selection-color\s*:\s*(#[0-9a-fA-F]{6})")
# WCAG 1.4.3 exempts inactive (disabled) components from the 4.5:1 minimum.
EXEMPT_SELECTOR = re.compile(r":disabled")


def _violations(name: str, stylesheet: str) -> list[str]:
    found: list[str] = []
    for match in RULE.finditer(stylesheet):
        selectors = tuple(
            " ".join(selector.split())
            for selector in match.group(1).split(",")
            if selector.strip()
        )
        body = match.group(2)
        checks: list[tuple[str, str, str]] = []
        foreground = _last_declaration(FOREGROUND, body)
        background = _last_declaration(BACKGROUND, body)
        if foreground and background:
            checks.append((foreground, background, "text"))
        sel_fg = _last_declaration(SELECTION_FG, body)
        sel_bg = _last_declaration(SELECTION_BG, body)
        if sel_fg and sel_bg:
            checks.append((sel_fg, sel_bg, "selection"))
        for fg, bg, kind in checks:
            ratio = _contrast_ratio(bg, fg)
            if ratio < MINIMUM_RATIO:
                found.extend(
                    f"{name}: {selector[:70]} [{kind}] "
                    f"{fg} on {bg} = {ratio:.2f}"
                    for selector in selectors
                    if not EXEMPT_SELECTOR.search(selector)
                )
    return found


def _last_declaration(pattern: re.Pattern[str], body: str) -> str | None:
    matches = pattern.findall(body)
    return matches[-1] if matches else None


def test_all_stylesheets_meet_wcag_contrast() -> None:
    violations: list[str] = []
    violations += _violations("STYLE", STYLE)
    violations += _violations("LIGHT_MENU_STYLE", LIGHT_MENU_STYLE)
    violations += _violations("POPUP_STYLE", POPUP_STYLE)
    violations += _violations(
        "FLAGSHIP", _theme_stylesheet(1.0, high_contrast=False)
    )
    violations += _violations(
        "FLAGSHIP_HIGH_CONTRAST", _theme_stylesheet(1.0, high_contrast=True)
    )
    assert not violations, (
        "Same-rule text/background pairs below WCAG 4.5:1 "
        "(disabled states are the only reviewed exemption): "
        + "; ".join(violations)
    )


def test_flagship_selection_colors_are_readable() -> None:
    # The regression this file was born from: white selected text sat on the
    # decorative glow color at 3.44:1 in the flagship theme.
    for high_contrast in (False, True):
        sheet = _theme_stylesheet(1.0, high_contrast=high_contrast)
        for bg in SELECTION_BG.findall(sheet):
            assert _contrast_ratio(bg, "#ffffff") >= MINIMUM_RATIO, (
                high_contrast,
                bg,
            )


def test_mixed_disabled_and_enabled_selectors_are_checked_independently() -> None:
    violations = _violations(
        "mixed-selectors",
        "QPushButton:disabled, QLabel { color:#ffffff; background:#ffffff; }",
    )

    assert len(violations) == 1
    assert "QLabel" in violations[0]


def test_last_color_declaration_controls_contrast() -> None:
    violations = _violations(
        "duplicate-colors",
        "QLabel { color:#000000; color:#ffffff; background:#ffffff; }",
    )

    assert len(violations) == 1
    assert "#ffffff on #ffffff" in violations[0]


if __name__ == "__main__":
    test_all_stylesheets_meet_wcag_contrast()
    test_flagship_selection_colors_are_readable()
    test_mixed_disabled_and_enabled_selectors_are_checked_independently()
    test_last_color_declaration_controls_contrast()
    print("WCAG_CONTRAST_GOVERNANCE_OK")
