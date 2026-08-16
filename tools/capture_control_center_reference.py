from __future__ import annotations

lazy import argparse
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtGui import QFont, QFontDatabase
lazy from PySide6.QtWidgets import QApplication
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_ui import build_language_dashboard


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


def capture(output: Path, tab_name: str) -> None:
    application = QApplication.instance() or QApplication([])
    application.setFont(QFont(_preview_font_family(), 10))
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        db, dashboard = build_language_dashboard(Path(temporary), "zh-TW")
        try:
            dashboard.resize(1320, 860)
            tab_names = tuple(
                dashboard.tabs.tabText(index)
                for index in range(dashboard.tabs.count())
            )
            dashboard.tabs.setCurrentIndex(tab_names.index(tab_name))
            dashboard.show()
            application.processEvents()
            output.parent.mkdir(parents=True, exist_ok=True)
            if not dashboard.grab().save(str(output)):
                raise RuntimeError("Could not save the control-center preview.")
        finally:
            close_dashboard(dashboard, db)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tab", default="雲裳閣")
    options = parser.parse_args()
    capture(options.output, options.tab)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
