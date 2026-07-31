import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from db import StudioDB
from flagship_core import ActionRequest
from flagship_ui import FlagshipControlCenter


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
                "flagship_ui.GmailConnector.search",
                return_value=[],
            ),
            patch(
                "flagship_ui.GoogleCalendarConnector.events",
                return_value=[],
            ),
            patch(
                "flagship_ui.GoogleDriveConnector.search",
                return_value=[],
            ),
            ThreadPoolExecutor(max_workers=12) as pool,
        ):
            results = list(pool.map(execute, requests))

        assert len(results) == 90
        assert all(result.success for result in results)
        center.close_services()
        db.close()
        center.deleteLater()
        app.processEvents()
    print("CLOUD_RAPID_SEQUENCE_OK")


if __name__ == "__main__":
    run()
