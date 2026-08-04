from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app import FirstRunWizard, application_ui_font
from db import StudioDB


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
