from __future__ import annotations

lazy from pathlib import Path

lazy from PySide6.QtGui import QFontDatabase

__all__ = (
    "DASHBOARD_TAB_ALIASES",
    "preview_font_family",
    "resolve_dashboard_tab",
    "select_dashboard_tab",
)


DASHBOARD_TAB_ALIASES = {
    "conversation": 0,
    "chat": 0,
    "today": 1,
    "tasks": 1,
    "tasks-and-ideas": 1,
    "platforms": 2,
    "work-platforms": 2,
    "memory": 3,
    "long-term-memory": 3,
    "voice": 4,
    "voice-modes": 4,
    "permissions": 5,
    "security": 5,
    "security-permissions": 5,
    "wardrobe": 6,
    "settings": 7,
}
SECURITY_TAB_INDEX = 5
SECURITY_SUBPAGE_INDEX = 6


def preview_font_family() -> str:
    """Load a real CJK font when the isolated Qt runtime has no font database."""

    candidates = (
        Path(r"C:\Windows\Fonts\msjh.ttc"),
        Path(r"C:\Windows\Fonts\msjhbd.ttc"),
        Path(r"C:\Windows\Fonts\seguisym.ttf"),
        Path(r"C:\Windows\Fonts\seguiemj.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    )
    preferred_family = ""
    for candidate in candidates:
        if not candidate.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(candidate))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and not preferred_family:
            preferred_family = families[0]
    return preferred_family or "sans-serif"


def resolve_dashboard_tab(dashboard, requested: str) -> int:
    normalized = requested.strip().casefold()
    if normalized in DASHBOARD_TAB_ALIASES:
        return DASHBOARD_TAB_ALIASES[normalized]
    if normalized.isdecimal():
        index = int(normalized)
        if index in range(dashboard.tabs.count()):
            return index
    for index in range(dashboard.tabs.count()):
        if dashboard.tabs.tabText(index).strip().casefold() == normalized:
            return index
    visible = tuple(
        dashboard.tabs.tabText(index) for index in range(dashboard.tabs.count())
    )
    raise ValueError(
        f"Unknown dashboard tab {requested!r}; use a stable name, index, "
        f"or one of {visible!r}."
    )


def select_dashboard_tab(dashboard, requested: str) -> int:
    """Select an outer dashboard page and its nested security page when needed."""

    index = resolve_dashboard_tab(dashboard, requested)
    dashboard.tabs.setCurrentIndex(index)
    if index == SECURITY_TAB_INDEX:
        dashboard.flagship_center.tabs.setCurrentIndex(SECURITY_SUBPAGE_INDEX)
    return index
