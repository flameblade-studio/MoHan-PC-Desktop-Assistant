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

lazy from PySide6.QtGui import QFont
lazy from PySide6.QtWidgets import QApplication
lazy from presentation.lingxiao_widgets import set_motion_override
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_ui import build_language_dashboard
lazy from tools.capture_media_contract import preview_font_family, select_dashboard_tab

DEFAULT_OUTPUT_NAME = "control-center-reference.png"
def output_path(output: Path) -> Path:
    if output.suffix.casefold() == ".png":
        return output
    return output / DEFAULT_OUTPUT_NAME


def capture(output: Path, tab_name: str) -> Path:
    application = QApplication.instance() or QApplication([])
    application.setFont(QFont(preview_font_family(), 10))
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        set_motion_override(False)
        db, dashboard = build_language_dashboard(Path(temporary), "zh-TW")
        try:
            dashboard.resize(1320, 860)
            select_dashboard_tab(dashboard, tab_name)
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
