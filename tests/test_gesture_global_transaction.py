from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication

lazy from application.presentation_ports import PresentationPorts
lazy from dashboard_composition import DashboardDependencies
lazy from dashboard_window import Dashboard
lazy from gesture_configuration import (
    GestureConfiguration,
    GestureLandmark,
    GestureSample,
)
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStore,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths


class ProtectedSecret:
    """In-memory stand-in for the operating-system protected secret store."""

    def __init__(self) -> None:
        self.value = ""
        self.fail_when_saving = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        if self.fail_when_saving and value == self.fail_when_saving:
            raise OSError("synthetic protected rollback failure")
        self.value = value

    def clear(self) -> None:
        self.value = ""


class OfflineListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        raise AssertionError("Transaction test attempted microphone access.")


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=("portable-zip",),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(root / "data", root / "config", root / "cache")

    def set_autostart(self, *_args, **_kwargs) -> None:
        raise AssertionError("Transaction test attempted device configuration.")

    def open_path(self, _path: Path) -> None:
        raise AssertionError("Transaction test attempted an external path.")


class OfflineVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return []


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


class FailingProactivityStore:
    def __init__(
        self,
        delegate: CompanionProactivityPreferencesStore,
    ) -> None:
        self.delegate = delegate

    def load(self):
        return self.delegate.load()

    def begin_edit(self):
        return self.delegate.begin_edit()

    def save(self, _value) -> None:
        raise RuntimeError("synthetic proactivity save failure")


def sample(offset: float) -> GestureSample:
    return GestureSample(
        tuple(
            GestureLandmark(index / 20 + offset, index / 40, -index / 80)
            for index in range(21)
        )
    )


def initial_configuration() -> GestureConfiguration:
    return GestureConfiguration(enabled=True).add_custom(
        "Transaction gesture",
        (sample(0.0),),
        gesture_id="custom:transaction",
    )


@pytest.fixture(scope="module", autouse=True)
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dashboard(tmp_path: Path):
    db = StudioDB(tmp_path / "mohan.db")
    db.set_setting("onboarding_complete", True)
    protected = ProtectedSecret()
    ordinary_secret = ProtectedSecret()

    def secret_factory(_path: Path, description: str = "") -> ProtectedSecret:
        if "gesture" in description.casefold():
            return protected
        return ordinary_secret

    dependencies = DashboardDependencies(
        listener=OfflineListener(),
        secret_store=ordinary_secret,
        azure_secret_store=ordinary_secret,
        azure_hd_secret_store=ordinary_secret,
        secret_store_factory=secret_factory,
        platform_services=OfflinePlatformServices(tmp_path),
        presentation_ports=offline_presentation_ports(),
    )
    with patch.object(QTimer, "start", return_value=None):
        value = Dashboard(db, dependencies)
    center = value.flagship_center
    center.gesture_store.save(initial_configuration())
    center.reload_draft_settings()
    yield value, db, protected
    center.close_services()
    value.close()
    value.deleteLater()
    QApplication.processEvents()
    db.close()


def stage_changed_protected_sample(dashboard: Dashboard) -> None:
    center = dashboard.flagship_center
    current = center._gesture_draft.value
    definition = current.definition("custom:transaction")
    center._gesture_draft.update_definition(
        replace(definition, samples=(sample(0.07),))
    )


def install_dashboard_transaction_probes(
    dashboard: Dashboard,
    db: StudioDB,
) -> list[bool]:
    external_calls: list[bool] = []

    def save_general(**options: object) -> bool:
        assert options == {
            "silent": True,
            "persist_external": False,
            "finish": False,
        }
        db.set_setting("transaction_general_probe", "temporary")
        return True

    dashboard.save_settings = save_general
    dashboard.save_permissions = lambda: db.set_setting(
        "transaction_permission_probe", "temporary"
    )
    dashboard._persist_external_settings = lambda: external_calls.append(True)
    return external_calls


def assert_rebuilt_from_initial(
    dashboard: Dashboard,
    protected: ProtectedSecret,
    before_secret: str,
) -> None:
    center = dashboard.flagship_center
    assert protected.value == before_secret
    assert center.gesture_store.load() == initial_configuration()
    assert center._gesture_draft.value == initial_configuration()
    assert center.gesture_enabled.isChecked() is True


def test_proactivity_failure_restores_both_layers_and_rebuilds_ui(
    dashboard,
) -> None:
    value, db, protected = dashboard
    stage_changed_protected_sample(value)
    center = value.flagship_center
    center.proactivity_store = FailingProactivityStore(center.proactivity_store)
    before_db = db.settings_snapshot()
    before_secret = protected.value
    external_calls = install_dashboard_transaction_probes(value, db)

    assert value.save_all_settings() is False
    QApplication.processEvents()

    assert db.settings_snapshot() == before_db
    assert_rebuilt_from_initial(value, protected, before_secret)
    assert external_calls == []


def test_late_db_failure_restores_both_layers_and_rebuilds_ui(
    dashboard,
) -> None:
    value, db, protected = dashboard
    stage_changed_protected_sample(value)
    center = value.flagship_center
    # ``proactive_interaction_mode`` is only written after the user touches
    # its control (untouched controls no longer overwrite other pages).
    center.proactive_mode.setCurrentIndex(
        center.proactive_mode.findData("active")
    )
    before_db = db.settings_snapshot()
    before_secret = protected.value
    external_calls = install_dashboard_transaction_probes(value, db)
    original_set_setting = db.set_setting

    def fail_late(key: str, setting: object) -> None:
        if key == "proactive_interaction_mode":
            raise RuntimeError("synthetic late DB failure")
        original_set_setting(key, setting)

    db.set_setting = fail_late

    assert value.save_all_settings() is False
    QApplication.processEvents()

    assert db.settings_snapshot() == before_db
    assert_rebuilt_from_initial(value, protected, before_secret)
    assert external_calls == []


def test_incomplete_protected_rollback_fails_closed_with_safe_diagnostic(
    dashboard,
) -> None:
    value, db, protected = dashboard
    stage_changed_protected_sample(value)
    center = value.flagship_center
    center.proactivity_store = FailingProactivityStore(center.proactivity_store)
    before_db = db.settings_snapshot()
    before_secret = protected.value
    protected.fail_when_saving = before_secret
    external_calls = install_dashboard_transaction_probes(value, db)

    assert value.save_all_settings() is False
    QApplication.processEvents()
    assert db.settings_snapshot() == before_db
    assert external_calls == []
    assert protected.value != before_secret

    diagnostic = center.last_settings_transaction_error
    assert diagnostic == "rollback-incomplete"
    assert before_secret not in diagnostic
    assert "synthetic" not in diagnostic.casefold()
