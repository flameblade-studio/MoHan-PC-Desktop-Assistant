"""Dashboard window resize contract.

v4.5.1 live report (2026-08-29): the dashboard could be resized from its
left/right edges but not from the top/bottom edges or any corner.  Cause:
word-wrapped labels propagate height-for-width up to the top-level layout,
and Qt then treats the window height as a function of its width, so the
native frame refuses vertical resizing.  The window overrides
``hasHeightForWidth`` to keep its height a free variable; this contract
keeps that override alive.
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
            # The layout may legitimately be height-for-width internally
            # (word-wrapped labels), but the WINDOW must not be: that is what
            # the native frame consults when deciding whether the top/bottom
            # edges and corners may resize.
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
