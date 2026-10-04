from __future__ import annotations

lazy import json
lazy import os
lazy import sqlite3
lazy from concurrent.futures import ThreadPoolExecutor
lazy from threading import Event
lazy from unittest.mock import patch

lazy import pytest
lazy from PySide6.QtWidgets import QApplication, QMessageBox

lazy from infrastructure.db import StudioDB
lazy from presentation.flagship_ui import FlagshipControlCenter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class MemoryStore:
    def __init__(self, token: dict) -> None:
        self.value = json.dumps(token)
        self.saved: list[str] = []

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value
        self.saved.append(value)

    def clear(self) -> None:
        self.value = ""


@pytest.fixture
def cloud(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = StudioDB(tmp_path / "mohan.db")
    db.save_connector("google", "Google", True, {})
    center = FlagshipControlCenter(db, tmp_path)
    store = MemoryStore({"access_token": "old", "expires_in": 1, "obtained_at": 1})
    center.cloud_provider.setCurrentIndex(center.cloud_provider.findData("google"))
    try:
        with (
            patch.object(center, "_oauth_store", return_value=store),
            patch.object(QMessageBox, "question", return_value=QMessageBox.Yes),
        ):
            yield center, store
    finally:
        center.close_services()
        db.close()
        center.deleteLater()
        app.processEvents()


def test_refresh_cannot_restore_revoked_credentials(cloud) -> None:
    center, store = cloud

    def refresh(_provider, _payload):
        center.revoke_cloud()
        return {"access_token": "late"}

    with (
        patch("presentation.flagship.cloud.refresh_oauth_token", side_effect=refresh),
        pytest.raises(PermissionError),
    ):
        center._cloud_token("google")
    assert store.load() == ""
    assert not store.saved
    assert not center.db.connector("google")["enabled"]


def test_background_refresh_is_invalidated_before_it_completes(cloud) -> None:
    center, store = cloud
    entered, complete = Event(), Event()

    def refresh(_provider, _payload):
        entered.set()
        assert complete.wait(5), "The test must release the blocked refresh"
        return {"access_token": "late"}

    with (
        patch("presentation.flagship.cloud.refresh_oauth_token", side_effect=refresh),
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        future = pool.submit(center._cloud_token, "google")
        try:
            assert entered.wait(5), "The refresh must start before revocation"
            center.revoke_cloud()
        finally:
            complete.set()
        with pytest.raises(PermissionError):
            future.result(timeout=5)
    assert store.load() == ""
    assert not store.saved


def test_disabled_connector_cannot_use_remaining_token(cloud) -> None:
    center, store = cloud
    center.revoke_cloud()
    store.value = json.dumps({"access_token": "unexpired"})
    with pytest.raises(PermissionError):
        center._cloud_token("google")


def test_refresh_cannot_overwrite_reconnected_credentials(cloud) -> None:
    center, store = cloud

    def refresh(_provider, _payload):
        center.revoke_cloud()
        center._cloud_connected(
            "google", {"access_token": "reconnected"}, (),
            center._cloud_authorizations["google"],
        )
        return {"access_token": "late"}

    with (
        patch("presentation.flagship.cloud.refresh_oauth_token", side_effect=refresh),
        pytest.raises(PermissionError),
    ):
        center._cloud_token("google")
    assert json.loads(store.load())["access_token"] == "reconnected"
    assert len(store.saved) == 1


def test_late_health_result_cannot_enable_revoked_connector(cloud) -> None:
    center, _store = cloud
    generation = center._cloud_test_generation
    center.revoke_cloud()
    with patch.object(QMessageBox, "warning"), patch.object(QMessageBox, "information"):
        center._cloud_test_done("google", {}, generation)
    assert not center.db.connector("google")["enabled"]


def test_late_connection_result_cannot_restore_revoked_credentials(cloud) -> None:
    center, store = cloud
    authorization = center._cloud_authorizations["google"]
    center.revoke_cloud()
    center._cloud_connected("google", {"access_token": "late"}, (), authorization)
    assert store.load() == ""
    assert not store.saved
    assert not center.db.connector("google")["enabled"]


def test_revocation_clears_credentials_even_when_database_write_fails(cloud) -> None:
    center, store = cloud
    with (
        patch.object(center.db, "save_connector", side_effect=sqlite3.OperationalError("busy")),
        pytest.raises(sqlite3.OperationalError),
    ):
        center.revoke_cloud()
    assert store.load() == ""
    with pytest.raises(PermissionError):
        center._cloud_token("google")


def test_revocation_disables_connector_even_when_credential_deletion_fails(cloud) -> None:
    center, store = cloud
    with patch.object(store, "clear", side_effect=OSError("unavailable")), pytest.raises(OSError):
        center.revoke_cloud()
    assert not center.db.connector("google")["enabled"]
    with pytest.raises(PermissionError):
        center._cloud_token("google")


def test_authorized_refresh_still_saves_and_returns_token(cloud) -> None:
    center, store = cloud
    with patch(
        "presentation.flagship.cloud.refresh_oauth_token",
        return_value={"access_token": "refreshed"},
    ):
        assert center._cloud_token("google") == "refreshed"
    assert json.loads(store.load())["access_token"] == "refreshed"


def test_authorized_unexpired_token_needs_no_refresh(cloud) -> None:
    center, store = cloud
    store.value = json.dumps({"access_token": "unexpired"})
    with patch("presentation.flagship.cloud.refresh_oauth_token") as refresh:
        assert center._cloud_token("google") == "unexpired"
    refresh.assert_not_called()
