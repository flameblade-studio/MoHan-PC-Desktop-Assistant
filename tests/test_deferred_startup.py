from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import EXPRESSION_IMAGE_ASSETS
lazy from presentation.companion_window import CompanionWindow


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        os.environ["LOCALAPPDATA"] = temp
        app = QApplication.instance() or QApplication([])

        # Closing during the short first-paint window must not access timers,
        # animations, or tray objects that intentionally do not exist yet.
        early_window = CompanionWindow(
            startup_speech=False,
            defer_visual_startup=True,
        )
        early_window.show()
        app.processEvents()
        early_window.close()
        app.processEvents()
        early_window.complete_deferred_startup()
        assert early_window._closing is True
        assert early_window._visual_startup_complete is False
        assert not hasattr(early_window, "tray")

        window = CompanionWindow(
            startup_speech=False,
            defer_visual_startup=True,
        )

        # The first paint needs only the neutral base image. Expensive visual
        # composition and tray/timer setup must wait for the event loop.
        assert window._visual_startup_complete is False
        assert set(window.expression_pixmaps) == {"idle"}
        assert not hasattr(window, "tray")
        assert not hasattr(window, "blink_timer")
        assert window.character.pixmap() is not None
        assert not window.character.pixmap().isNull()

        window.show()
        app.processEvents()
        assert window.isVisible()

        with patch.object(
            window.dashboard.update_panel,
            "start_automatic_check",
        ) as start_check:
            window.complete_deferred_startup()
            window.complete_deferred_startup()
            assert start_check.call_count == 1

        assert window._visual_startup_complete is True
        assert set(EXPRESSION_IMAGE_ASSETS).issubset(window.expression_pixmaps)
        assert all(
            not window.expression_pixmaps[name].isNull()
            for name in EXPRESSION_IMAGE_ASSETS
        )
        assert window.blink_timer.isActive()
        assert window.tray is not None

        window.close()
        app.processEvents()
    print("DEFERRED_STARTUP_OK")


if __name__ == "__main__":
    run()
