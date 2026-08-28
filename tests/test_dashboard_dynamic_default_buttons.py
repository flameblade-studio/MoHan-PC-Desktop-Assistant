from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtWidgets import QApplication, QPushButton
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_ui import build_language_dashboard


def _default_offenders(dashboard) -> list[str]:
    return [
        f"{button.objectName() or button.text()}"
        for button in dashboard.findChildren(QPushButton)
        if button.autoDefault() or button.isDefault()
    ]


def test_dynamically_rebuilt_buttons_never_become_enter_targets() -> None:
    """Todo rows and platform cards rebuilt at runtime must keep
    autoDefault=False, otherwise Enter in the chat box clicks them."""

    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_language_dashboard(Path(temp), "zh-TW")
        try:
            assert _default_offenders(dashboard) == []

            db.add_todo("整理審查回饋", "其他")
            dashboard.refresh_todos()
            application.processEvents()
            assert _default_offenders(dashboard) == []

            dashboard.new_platform_name.setText("公司 ERP")
            dashboard.add_custom_platform()
            application.processEvents()
            assert _default_offenders(dashboard) == []

            dashboard._reload_platform_cards()
            application.processEvents()
            assert _default_offenders(dashboard) == []
        finally:
            close_dashboard(dashboard, db)


if __name__ == "__main__":
    test_dynamically_rebuilt_buttons_never_become_enter_targets()
    print("DASHBOARD_DYNAMIC_DEFAULT_BUTTONS_OK")
