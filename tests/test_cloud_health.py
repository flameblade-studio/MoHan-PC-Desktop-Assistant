lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from cloud_connectors import (
    PROVIDERS,
    GoogleDriveConnector,
    normalize_cloud_provider,
    register_cloud_provider_alias,
)
lazy from db import StudioDB
lazy from flagship_ui import CloudHealthWorker, FlagshipControlCenter


def run() -> None:
    app = QApplication.instance() or QApplication([])
    assert (
        "https://www.googleapis.com/auth/drive.metadata.readonly"
        in PROVIDERS["google"].default_scopes
    )
    assert normalize_cloud_provider("YouTube") == "google"
    assert normalize_cloud_provider("google_new_service") == "google"
    register_cloud_provider_alias("google", "Example Future Google Tool")
    assert normalize_cloud_provider("Example Future Google Tool") == "google"

    with (
        patch(
            "flagship_ui.GmailConnector.request",
            return_value={"emailAddress": "user@example.com"},
        ),
        patch(
            "flagship_ui.GoogleCalendarConnector.request",
            return_value={"items": []},
        ),
        patch(
            "flagship_ui.GoogleDriveConnector.request",
            return_value={"files": []},
        ),
    ):
        results = CloudHealthWorker("google", "test-token")._google_probes()
    assert set(results) == {"Gmail", "Calendar", "Drive"}
    assert all(item["ok"] for item in results.values())
    with patch.object(
        GoogleDriveConnector,
        "request",
        return_value={"files": [{"id": "1", "name": "test"}]},
    ) as request:
        rows = GoogleDriveConnector("token").recent(5)
    assert rows[0]["name"] == "test"
    assert request.call_args.kwargs["query"]["orderBy"] == "modifiedTime desc"

    with (
        patch(
            "flagship_ui.GmailConnector.request",
            side_effect=PermissionError("scope"),
        ),
        patch(
            "flagship_ui.GoogleCalendarConnector.request",
            return_value={"items": []},
        ),
        patch(
            "flagship_ui.GoogleDriveConnector.request",
            return_value={"files": []},
        ),
    ):
        results = CloudHealthWorker("google", "test-token")._google_probes()
    assert results["Gmail"]["ok"] is False
    assert results["Calendar"]["ok"] is True
    assert results["Drive"]["ok"] is True

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = StudioDB(root / "mohan.db")
        center = FlagshipControlCenter(db, root)
        center.cloud_test_button.setEnabled(False)
        center.cloud_test_timeout.start()
        center._cloud_test_timed_out()
        assert center.cloud_test_button.isEnabled()
        assert not center.cloud_test_timeout.isActive()
        assert any(
            row["event_type"] == "cloud_health_timeout"
            for row in db.audit_rows(10)
        )
        center.close_services()
        db.close()
        center.deleteLater()
        app.processEvents()

    print("CLOUD_HEALTH_OK")


if __name__ == "__main__":
    run()
