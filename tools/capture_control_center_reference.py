from __future__ import annotations

lazy import argparse
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtGui import QFont, QFontDatabase
lazy from PySide6.QtWidgets import QApplication
lazy from presentation.lingxiao_widgets import set_motion_override
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_ui import build_language_dashboard

DEFAULT_OUTPUT_NAME = "control-center-reference.png"
DASHBOARD_TAB_ALIASES = {
    "conversation": 0,
    "chat": 0,
    "today": 1,
    "tasks": 1,
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


def _preview_font_family() -> str:
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


def output_path(output: Path) -> Path:
    if output.suffix.casefold() == ".png":
        return output
    return output / DEFAULT_OUTPUT_NAME


def capture(output: Path, tab_name: str) -> Path:
    application = QApplication.instance() or QApplication([])
    application.setFont(QFont(_preview_font_family(), 10))
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        set_motion_override(False)
        db, dashboard = build_language_dashboard(Path(temporary), "zh-TW")
        try:
            dashboard.resize(1320, 860)
            dashboard.tabs.setCurrentIndex(
                resolve_dashboard_tab(dashboard, tab_name)
            )
            dashboard.show()
            application.processEvents()
            destination = output_path(output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not dashboard.grab().save(str(destination)):
                raise RuntimeError("Could not save the control-center preview.")
        finally:
            close_dashboard(dashboard, db)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory; a .png path remains accepted for compatibility.",
    )
    parser.add_argument(
        "--tab",
        default="wardrobe",
        help="Dashboard tab stable name, visible label, or zero-based index.",
    )
    options = parser.parse_args()
    destination = capture(options.output, options.tab)
    print(f"CONTROL_CENTER_REFERENCE_OK output={destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
