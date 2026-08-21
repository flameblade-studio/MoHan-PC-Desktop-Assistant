from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from flagship_core import ActionRequest
lazy from flagship_ui import FlagshipControlCenter
lazy from infrastructure.concurrency_tools import thread_pool_executor
lazy from infrastructure.db import StudioDB

EXPECTED_RESULT_COUNT = 90


class FakeStore:
    def __init__(self, value: str):
        self.value = value

    def load(self) -> str:
        return self.value


def run() -> None:
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = StudioDB(root / "mohan.db")
        center = FlagshipControlCenter(db, root)
        try:

            def oauth_store(provider: str) -> FakeStore:
                return FakeStore("google-token" if provider == "google" else "")

            center._oauth_store = oauth_store
            center._cloud_token = lambda provider: f"{provider}-token"

            requests = []
            for _ in range(30):
                requests.extend(
                [
                    ActionRequest(
                        "email_read",
                        "讀取 Gmail",
                        {"provider": "google", "limit": 3},
                    ),
                    ActionRequest(
                        "calendar_read",
                        "讀取今天到明天的行程",
                        {"range": "today_to_tomorrow"},
                    ),
                    ActionRequest(
                        "cloud_file_read",
                        "搜尋雲端檔案",
                        {"query": "墨寒", "search_scope": "filename"},
                    ),
                ]
                )

            def execute(request: ActionRequest):
                if request.capability == "email_read":
                    return center._action_email_read(request)
                if request.capability == "calendar_read":
                    return center._action_calendar_read(request)
                return center._action_cloud_file_read(request)

            with (
                patch(
                    "integrations.cloud_connectors.GmailConnector.search",
                    return_value=[],
                ),
                patch(
                    "integrations.cloud_connectors.GoogleCalendarConnector.events",
                    return_value=[],
                ),
                patch(
                    "integrations.cloud_connectors.GoogleDriveConnector.search",
                    return_value=[],
                ),
                thread_pool_executor(max_workers=12) as pool,
            ):
                results = list(pool.map(execute, requests))

            assert len(results) == EXPECTED_RESULT_COUNT
            assert all(result.success for result in results)
        finally:
            center.close_services()
            db.close()
            center.deleteLater()
            app.processEvents()
    print("CLOUD_RAPID_SEQUENCE_OK")


if __name__ == "__main__":
    run()
