from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy from PySide6.QtCore import Qt, QTimer
lazy from PySide6.QtGui import QPalette
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QSpinBox,
)
lazy from test_global_settings_actions import close_dashboard, dependencies
lazy from test_wardrobe_ui import build_language_dashboard

lazy from application.presentation_ports import (
    REALTIME_OUTPUT_AZURE,
    REALTIME_OUTPUT_AZURE_HD,
    REALTIME_OUTPUT_OPENAI,
)
lazy from infrastructure.db import StudioDB
lazy from presentation.dashboard_window import Dashboard

MINIMUM_STEP_BUTTON_COUNT = 2
POINT_SIZE_TOLERANCE = 0.01
SUPPORTED_UI_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _step_buttons(spin: QAbstractSpinBox) -> tuple[QPushButton, QPushButton]:
    parent = spin.parentWidget()
    assert parent is not None
    buttons = {
        button.text(): button
        for button in parent.findChildren(
            QPushButton,
            options=Qt.FindDirectChildrenOnly,
        )
    }
    increase = next(
        (buttons[label] for label in ("▲", "＋", "+") if label in buttons),
        None,
    )
    decrease = next(
        (buttons[label] for label in ("▼", "－", "-") if label in buttons),
        None,
    )
    assert increase is not None and decrease is not None, spin.accessibleName()
    return increase, decrease


def _assert_spin_buttons_change_value(
    application: QApplication,
    spin: QAbstractSpinBox,
) -> None:
    assert isinstance(spin, (QSpinBox, QDoubleSpinBox))
    up, down = _step_buttons(spin)
    assert up.isEnabled() and down.isEnabled()
    minimum = spin.minimum()
    maximum = spin.maximum()
    step = spin.singleStep()
    assert minimum < maximum
    assert step > 0

    spin.setValue(minimum)
    up.click()
    application.processEvents()
    assert spin.value() > minimum

    spin.setValue(maximum)
    down.click()
    application.processEvents()
    assert spin.value() < maximum


def test_dashboard_popups_and_step_controls_are_consistent() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_language_dashboard(Path(temp), "zh-TW")
        try:
            combos = dashboard.findChildren(QComboBox)
            assert combos
            for combo in combos:
                view = combo.view()
                palette = view.palette()
                assert palette.color(QPalette.Base).name().lower() == "#ffffff"
                assert palette.color(QPalette.Text).name().lower() == "#20364a"
                assert "background-color: #ffffff" in view.styleSheet()
                assert "color: #20364a" in view.styleSheet()

            for output_mode in (
                REALTIME_OUTPUT_AZURE,
                REALTIME_OUTPUT_AZURE_HD,
                REALTIME_OUTPUT_OPENAI,
            ):
                dashboard._apply_realtime_output_mode_state(output_mode)
                assert dashboard.realtime_voice.isEnabled()

            spins = dashboard.findChildren(QAbstractSpinBox)
            assert spins
            for spin in spins:
                assert spin.buttonSymbols() == QAbstractSpinBox.NoButtons
                parent = spin.parentWidget()
                assert parent is not None
                step_buttons = [
                    button
                    for button in parent.findChildren(QPushButton)
                    if button.text() in {"▲", "▼", "＋", "－", "+", "-"}
                ]
                assert (
                    len(step_buttons) >= MINIMUM_STEP_BUTTON_COUNT
                ), spin.accessibleName()
                assert all(button.isEnabled() for button in step_buttons)

            lock = dashboard.manual_wardrobe_lock_hours
            lock.setValue(lock.maximum())
            dashboard.manual_wardrobe_lock_hours_up.click()
            application.processEvents()
            assert lock.value() == lock.minimum()
            dashboard.manual_wardrobe_lock_hours_down.click()
            application.processEvents()
            assert lock.value() == lock.maximum()

            dashboard.showMaximized()
            application.processEvents()
            assert dashboard.restore_window_button.isVisible()
            dashboard.restore_window_button.click()
            application.processEvents()
            assert not dashboard.isMaximized()

            dashboard.showFullScreen()
            application.processEvents()
            application.processEvents()
            assert not dashboard.isFullScreen()
        finally:
            close_dashboard(dashboard, db)


def test_saved_chat_zoom_is_applied_to_initial_document() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db = StudioDB(root / "mohan.db")
        db.set_setting("onboarding_complete", True)
        db.set_setting("chat_zoom_percent", 130)
        db.log_chat("assistant", "persisted zoom verification")
        with patch.object(QTimer, "start", return_value=None):
            dashboard = Dashboard(db, dependencies(root))
        try:
            dashboard.show()
            application.processEvents()
            expected = dashboard.chat_base_point_size * 1.3
            assert dashboard.chat_zoom_label.text() == "130%"
            assert abs(
                dashboard.chat.document().defaultFont().pointSizeF() - expected
            ) < POINT_SIZE_TOLERANCE
            dashboard.refresh_chat()
            application.processEvents()
            assert abs(
                dashboard.chat.document().defaultFont().pointSizeF() - expected
            ) < POINT_SIZE_TOLERANCE
        finally:
            close_dashboard(dashboard, db)


def test_four_language_dashboard_controls_are_interactive_and_readable() -> None:
    application = QApplication.instance() or QApplication([])
    for language in SUPPORTED_UI_LANGUAGES:
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            db, dashboard = build_language_dashboard(Path(temp), language)
            try:
                for tab_index in range(dashboard.tabs.count()):
                    dashboard.tabs.setCurrentIndex(tab_index)
                    application.processEvents()
                    combos = dashboard.tabs.currentWidget().findChildren(QComboBox)
                    for combo in combos:
                        view = combo.view()
                        palette = view.palette()
                        assert palette.color(QPalette.Base).name().lower() == "#ffffff"
                        assert palette.color(QPalette.Text).name().lower() == "#20364a"
                        assert "background-color: #ffffff" in view.styleSheet()
                        assert "color: #20364a" in view.styleSheet()
                        enabled_indexes = tuple(
                            index
                            for index in range(combo.count())
                            if combo.model().flags(combo.model().index(index, 0))
                            & Qt.ItemIsEnabled
                        )
                        if combo.isEnabled() and enabled_indexes:
                            original = combo.currentIndex()
                            combo.setCurrentIndex(enabled_indexes[-1])
                            application.processEvents()
                            assert combo.currentIndex() == enabled_indexes[-1]
                            combo.setCurrentIndex(original)

                assert dashboard.realtime_voice.isEnabled()
                assert dashboard.realtime_voice.count() > 1
                original_voice = dashboard.realtime_voice.currentIndex()
                target_voice = (original_voice + 1) % dashboard.realtime_voice.count()
                dashboard.realtime_voice.setCurrentIndex(target_voice)
                application.processEvents()
                assert dashboard.realtime_voice.currentIndex() == target_voice
                assert dashboard.realtime_voice.currentText().strip()

                spins = dashboard.findChildren(QAbstractSpinBox)
                assert spins
                for spin in spins:
                    assert spin.buttonSymbols() == QAbstractSpinBox.NoButtons
                    up, down = _step_buttons(spin)
                    assert up.isEnabled() and down.isEnabled()
                    if isinstance(spin, (QSpinBox, QDoubleSpinBox)):
                        _assert_spin_buttons_change_value(application, spin)

                dashboard.showNormal()
                dashboard.self_outfit_generation_enabled.setChecked(True)
                emitted: list[bool] = []
                dashboard.outfit_generation_requested.connect(
                    lambda: emitted.append(True)
                )
                original_flags = dashboard.windowFlags()
                dashboard.wardrobe_generate_button.click()
                application.processEvents()
                assert emitted == [True]
                assert dashboard.windowState() == Qt.WindowNoState
                assert dashboard.windowFlags() == original_flags
                assert dashboard.windowFlags() & Qt.WindowTitleHint
                assert dashboard.windowFlags() & Qt.WindowCloseButtonHint
                dashboard.set_outfit_generation_status("provider-unavailable")
            finally:
                close_dashboard(dashboard, db)


if __name__ == "__main__":
    test_dashboard_popups_and_step_controls_are_consistent()
    test_saved_chat_zoom_is_applied_to_initial_document()
    test_four_language_dashboard_controls_are_interactive_and_readable()
    print("DASHBOARD_CONTROL_CONSISTENCY_OK")
