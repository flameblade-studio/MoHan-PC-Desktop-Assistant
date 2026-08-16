from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication

lazy from application.service_container import (
    create_cloud_vision_service_factory,
    create_presentation_ports,
)
lazy from domain.openai_vision_preferences import OpenAIVisionPreferences
lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_services import create_platform_services
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard


class FakeListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        return None


class FakeSecretStore:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.load_calls = 0

    def load(self) -> str:
        self.load_calls += 1
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


def assert_dashboard_receives_official_factory_without_request(root: Path) -> None:
    db = StudioDB(root / "mohan.db")
    secret = FakeSecretStore("PRIVATE-FIXTURE-KEY")
    provider_calls: list[object] = []

    def forbidden_provider_factory(*arguments: object) -> object:
        provider_calls.append(arguments)
        raise AssertionError("provider must not build while disabled")

    dependencies = DashboardDependencies(
        listener=FakeListener(),
        secret_store=secret,
        platform_services=create_platform_services(
            "linux",
            environ={},
            home=root,
        ),
        cloud_vision_service_factory=create_cloud_vision_service_factory(
            forbidden_provider_factory
        ),
        presentation_ports=create_presentation_ports(),
    )
    with patch.object(QTimer, "start", return_value=None):
        dashboard = Dashboard(db, dependencies)
        try:
            assert dashboard.flagship_center.cloud_vision_service is not None
            assert secret.load_calls <= 1
            assert provider_calls == []
            assert "PRIVATE-FIXTURE-KEY" not in repr(dashboard.flagship_center)
            assert dashboard.flagship_center.openai_vision_store.load() == (
                OpenAIVisionPreferences()
            )
        finally:
            dashboard.flagship_center.close_services()
            dashboard.deleteLater()
            QApplication.processEvents()
            db.close()


def run() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        assert_dashboard_receives_official_factory_without_request(Path(temp))
    print("CLOUD_VISION_COMPOSITION_OK")


if __name__ == "__main__":
    run()
