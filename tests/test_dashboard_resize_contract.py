"""Dashboard resizing supports all edges and corners.

v4.5.1 live report (2026-08-29): resizing worked only at the left and right
edges. Word-wrapped labels propagated height-for-width to the top-level
layout, coupling height to width. The hasHeightForWidth override keeps
height independent so vertical and corner resizing remain available.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.db import StudioDB


def test_dashboard_height_stays_a_free_variable() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()
        from presentation.companion_window import CompanionWindow

        app = QApplication.instance() or QApplication([])
        window = CompanionWindow(startup_speech=False)
        dashboard = window.dashboard
        try:
            dashboard.show()
            app.processEvents()
            # Internal layouts may use height-for-width for wrapped labels. The window
            # keeps height independent because the native frame uses its answer to
            # enable resizing at vertical edges and corners.
            assert dashboard.hasHeightForWidth() is False
            assert dashboard.sizePolicy().hasHeightForWidth() is False
            assert dashboard.maximumHeight() > dashboard.minimumHeight()
        finally:
            dashboard.close()
            window.close()
            app.processEvents()


if __name__ == "__main__":
    test_dashboard_height_stays_a_free_variable()
    print("DASHBOARD_RESIZE_CONTRACT_OK")
