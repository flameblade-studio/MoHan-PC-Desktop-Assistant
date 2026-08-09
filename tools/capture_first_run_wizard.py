from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "windows" if sys.platform == "win32" else "offscreen",
)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication

lazy from app import FirstRunWizard, application_ui_font
lazy from db import StudioDB


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app = QApplication([])
        app.setFont(application_ui_font())
        database = StudioDB(Path(temp_dir) / "first-run-preview.db")
        wizard = FirstRunWizard(database)
        wizard.show()
        app.processEvents()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not wizard.grab().save(str(output)):
            raise RuntimeError(f"Could not save {output}")
        wizard.close()
        database.close()
        app.processEvents()


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "tmp" / "first-run-wizard.png"
    )
    render(target)
    print(target)
