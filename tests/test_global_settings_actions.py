from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QObject, Qt, QTimer, Signal
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication, QPushButton, QWidget

lazy from application.presentation_ports import PresentationPorts
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from infrastructure.db import StudioDB
lazy from infrastructure.gesture_configuration_store import (
    GestureConfigurationStoreError,
)
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths

FORBIDDEN_SUBPAGE_ACTIONS = frozenset({
    "保存設定",
    "保存工具權限",
    "保存安全權限",
    "保存連線設定",
})
MAX_BUTTON_GAP = 16


class FakeSecretStore:
    def load(self) -> str:
        return ""

    def save(self, _value: str) -> None:
        return None

    def clear(self) -> None:
        return None


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        return None


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=True,
        native_window_management=True,
        published_installers=("portable-zip", "exe", "msi"),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(
            data=root / "data",
            config=root / "config",
            cache=root / "cache",
        )

    def set_autostart(
        self,
        _enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        raise AssertionError(
            f"Settings action test attempted autostart: {application_id} {command}"
        )

    def open_path(self, path: Path) -> None:
        raise AssertionError(f"Settings action test attempted external open: {path}")


def fake_secret_store_factory(
    _path: Path,
    _description: str = "MoHan protected secret",
) -> FakeSecretStore:
    return FakeSecretStore()


class OfflineVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return []


class OfflinePanel(QWidget):
    def __init__(self, *args: object, **_kwargs: object) -> None:
        parent = next(
            (value for value in reversed(args) if isinstance(value, QWidget)),
            None,
        )
        super().__init__(parent)


def offline_presentation_ports() -> PresentationPorts:
    unavailable = lambda *_args, **_kwargs: None
    return PresentationPorts(
        ai_worker_factory=unavailable,
        voice_catalog=OfflineVoiceCatalog(),
        profile_manager_factory=unavailable,
        update_manager_factory=unavailable,
        portable_secret_binder=unavailable,
        autostart_configurator=unavailable,
        validate_face_assets=lambda _path: (),
        face_renderer_factory=unavailable,
        visible_windows=list,
    )


def dependencies(root: Path) -> DashboardDependencies:
    secret_store = FakeSecretStore()
    return DashboardDependencies(
        listener=FakeListener(),
        secret_store=secret_store,
        azure_secret_store=secret_store,
        azure_hd_secret_store=secret_store,
        secret_store_factory=fake_secret_store_factory,
        platform_services=OfflinePlatformServices(root),
        presentation_ports=offline_presentation_ports(),
    )


def build_dashboard(root: Path) -> tuple[StudioDB, Dashboard]:
    db = StudioDB(root / "mohan.db")
    db.set_setting("onboarding_complete", True)
    with (
        patch.object(QTimer, "start", return_value=None),
        patch("presentation.dashboard_settings.PortableProfilePanel", OfflinePanel),
        patch("presentation.dashboard_settings.UpdatePanel", OfflinePanel),
    ):
        dashboard = Dashboard(db, dependencies(root))
    dashboard.show()
    QApplication.processEvents()
    return db, dashboard


def close_dashboard(dashboard: Dashboard, db: StudioDB) -> None:
    dashboard.flagship_center.close_services()
    for timer in dashboard.findChildren(QTimer):
        timer.stop()
    dashboard.close()
    dashboard.deleteLater()
    QApplication.processEvents()
    db.close()


def test_global_actions_are_grouped_bottom_right_and_keyboard_usable() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            cancel = dashboard.cancel_settings_button
            save = dashboard.save_settings_button
            tabs = dashboard.tabs

            assert cancel.isVisible() and cancel.isEnabled()
            assert save.isVisible() and save.isEnabled()
            assert cancel.geometry().center().x() < save.geometry().center().x()
            assert save.geometry().left() - cancel.geometry().right() <= MAX_BUTTON_GAP
            assert save.geometry().right() >= tabs.geometry().right() - 24
            assert cancel.geometry().top() >= tabs.geometry().bottom()
            assert save.geometry().top() >= tabs.geometry().bottom()
            assert cancel.focusPolicy() is not Qt.NoFocus
            assert save.focusPolicy() is not Qt.NoFocus
            assert save.property("mohanPrimaryAction") is True
            stylesheet = save.styleSheet()
            assert "background" in stylesheet
            assert "font-weight:700" in stylesheet
            assert "padding:10px 24px" in stylesheet

            db.set_setting("keyboard_save_probe", "draft")
            dashboard.save_settings = lambda **_options: (
                db.set_setting("keyboard_save_probe", "saved") or True
            )
            dashboard.save_permissions = lambda: None
            dashboard._persist_external_settings = lambda: None
            dashboard.flagship_center.validate_draft_settings = lambda: object()
            dashboard.flagship_center.save_draft_settings = lambda _values: True
            save.setFocus(Qt.OtherFocusReason)
            QTest.keyClick(save, Qt.Key_Space)
            application.processEvents()
            assert db.setting("keyboard_save_probe") == "saved"
        finally:
            close_dashboard(dashboard, db)


def test_subpages_do_not_expose_general_save_buttons() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            visible_forbidden = [
                button.text()
                for button in dashboard.findChildren(QPushButton)
                if button is not dashboard.save_settings_button
                and button.isVisibleTo(dashboard)
                and button.text() in FORBIDDEN_SUBPAGE_ACTIONS
            ]
            assert visible_forbidden == []
        finally:
            close_dashboard(dashboard, db)


def test_cancel_restores_database_settings_snapshot_from_keyboard() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            original = dashboard._settings_draft_snapshot
            old_gesture_draft = dashboard.flagship_center._gesture_draft
            dashboard.flagship_center.gesture_enabled.setChecked(True)
            db.set_setting("draft_only", "discard me")
            db.set_setting("onboarding_complete", False)

            cancel = dashboard.cancel_settings_button
            cancel.setFocus(Qt.OtherFocusReason)
            QTest.keyClick(cancel, Qt.Key_Space)
            application.processEvents()

            assert db.settings_snapshot() == original
            assert db.setting("draft_only", None) is None
            assert dashboard.flagship_center.gesture_enabled.isChecked() is False
            try:
                old_gesture_draft.cancel()
            except GestureConfigurationStoreError as error:
                assert "already closed" in str(error)
            else:
                raise AssertionError("global cancel left the old gesture draft open")
            assert dashboard.result() == Dashboard.Rejected
        finally:
            close_dashboard(dashboard, db)


def test_save_updates_database_settings_snapshot() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            original = dashboard._settings_draft_snapshot

            def save_general(**options: object) -> bool:
                assert options == {
                    "silent": True,
                    "persist_external": False,
                    "finish": False,
                }
                db.set_setting("saved_probe", "committed")
                return True

            dashboard.save_settings = save_general
            dashboard.save_permissions = lambda: None
            dashboard._persist_external_settings = lambda: None
            dashboard.flagship_center.validate_draft_settings = lambda: object()
            dashboard.flagship_center.save_draft_settings = lambda _values: True
            assert dashboard.save_all_settings() is True

            updated = db.settings_snapshot()
            assert updated != original
            assert dashboard._settings_draft_snapshot == updated
            assert db.setting("saved_probe") == "committed"
        finally:
            close_dashboard(dashboard, db)


def test_global_save_emits_one_confirmation_not_a_permission_duplicate() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            confirmations: list[str] = []
            dashboard.speak_requested.connect(
                lambda text, _mood: confirmations.append(text)
            )
            dashboard._persist_external_settings = lambda: None
            assert dashboard.save_all_settings() is True
            expected = dashboard._t("settings_saved", "設定已保存。")
            assert confirmations == [expected]
        finally:
            close_dashboard(dashboard, db)


def test_center_failure_rolls_back_dashboard_settings() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db, dashboard = build_dashboard(Path(temp))
        try:
            before = db.settings_snapshot()
            original_draft_snapshot = dashboard._settings_draft_snapshot

            def save_general(**options: object) -> bool:
                assert options == {
                    "silent": True,
                    "persist_external": False,
                    "finish": False,
                }
                db.set_setting("general_partial_probe", "must rollback")
                return True

            dashboard.save_settings = save_general
            dashboard.save_permissions = lambda: db.set_setting(
                "permission_partial_probe", "must rollback"
            )
            external_calls: list[bool] = []
            dashboard._persist_external_settings = lambda: external_calls.append(True)
            dashboard.flagship_center.validate_draft_settings = lambda: object()
            dashboard.flagship_center.save_draft_settings = lambda _values: False
            assert dashboard.save_all_settings() is False
            assert db.settings_snapshot() == before
            assert dashboard._settings_draft_snapshot == original_draft_snapshot
            assert external_calls == []
        finally:
            close_dashboard(dashboard, db)


if __name__ == "__main__":
    test_global_actions_are_grouped_bottom_right_and_keyboard_usable()
    test_subpages_do_not_expose_general_save_buttons()
    test_cancel_restores_database_settings_snapshot_from_keyboard()
    test_save_updates_database_settings_snapshot()
    test_center_failure_rolls_back_dashboard_settings()
    print("GLOBAL_SETTINGS_ACTIONS_OK")
