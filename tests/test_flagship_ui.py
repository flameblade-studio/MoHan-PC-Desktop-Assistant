lazy import os
lazy import sys
lazy from datetime import datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication, QMessageBox

lazy from flagship_core import ActionRequest
lazy from flagship_ui import FlagshipControlCenter
lazy from infrastructure.db import StudioDB


def assert_tabs_and_defaults(center: FlagshipControlCenter) -> None:
    assert center.tabs.count() == 8
    assert [
        center.tabs.tabText(index) for index in range(center.tabs.count())
    ] == [
        "任務中心",
        "工作流程",
        "雲端連接器",
        "智慧家庭",
        "遠端與隱私",
        "陪伴與關心",
        "安全權限",
        "稽核紀錄",
    ]
    assert center.remote_server is None
    initial_port = center.remote_port.value()
    QTest.mouseClick(center.remote_port_up, Qt.LeftButton)
    assert center.remote_port.value() == initial_port + 1
    QTest.mouseClick(center.remote_port_down, Qt.LeftButton)
    assert center.remote_port.value() == initial_port
    assert center.remote_enabled.isChecked() is False
    assert center.camera_enabled.isChecked() is False
    assert center.face_identity.isEnabled() is False
    assert center.ha_enabled.isChecked() is False
    assert center._permission_controls["delete_file"].currentText() == "禁止"
    assert center._permission_controls["home_lock"].currentText() == "禁止"
    assert center._permission_controls["email_send"].currentText() == "每次詢問"


def assert_known_safe_plans(center: FlagshipControlCenter) -> None:
    local_gmail = center._known_safe_plan(
        "請幫我讀取最近七天最多三封 Gmail 郵件"
    )
    assert local_gmail is not None
    assert local_gmail["steps"][0]["capability"] == "email_read"
    assert local_gmail["steps"][0]["arguments"] == {
        "provider": "google",
        "query": "newer_than:7d",
        "limit": 3,
    }
    assert center._known_safe_plan("請幫我寄出 Gmail 郵件") is None
    local_calendar = center._known_safe_plan(
        "請幫我讀取今天的 Google Calendar"
    )
    assert local_calendar is not None
    assert local_calendar["steps"][0]["capability"] == "calendar_read"
    assert local_calendar["steps"][0]["arguments"]["provider"] == "google"
    local_drive = center._known_safe_plan("請幫我讀取 Google Drive")
    assert local_drive is not None
    assert local_drive["steps"][0]["capability"] == "cloud_file_read"
    assert local_drive["steps"][0]["arguments"]["name"] == ""
    assert (
        center._known_safe_plan("請測試 Google Calendar")["steps"][0][
            "capability"
        ]
        == "calendar_read"
    )
    assert (
        center._known_safe_plan("幫我檢查 Google Drive")["steps"][0][
            "capability"
        ]
        == "cloud_file_read"
    )
    assert (
        center._known_safe_plan("請查詢 Gmail")["steps"][0]["capability"]
        == "email_read"
    )


def assert_explicit_provider_resolution(center: FlagshipControlCenter) -> None:
    assert center._provider_from_request(
        ActionRequest(
            "cloud_file_read",
            "讀取雲端檔案",
            {"provider": "Google Drive"},
        )
    ) == "google"
    assert center._provider_from_request(
        ActionRequest(
            "calendar_read",
            "讀取 Google Calendar",
            {"provider": "google_calendar"},
        )
    ) == "google"
    assert center._provider_from_request(
        ActionRequest("calendar_read", "讀取 Google Calendar", {})
    ) == "google"
    assert center._provider_from_request(
        ActionRequest(
            "calendar_read",
            "讀取行程",
            {"source": "google_calendar"},
        )
    ) == "google"


def assert_stored_provider_resolution(center: FlagshipControlCenter) -> None:
    fake_google_store = type(
        "FakeSecretStore",
        (),
        {"load": lambda _self: "token"},
    )()
    empty_store = type(
        "EmptySecretStore",
        (),
        {"load": lambda _self: ""},
    )()
    with patch.object(
        center,
        "_oauth_store",
        side_effect=lambda provider: (
            fake_google_store if provider == "google" else empty_store
        ),
    ):
        assert center._provider_from_request(
            ActionRequest(
                "calendar_read",
                "讀取今天到明天的行程",
                {"range": "today_to_tomorrow"},
            )
        ) == "google"


def assert_calendar_read(center: FlagshipControlCenter) -> None:
    legacy_start, legacy_end = center._calendar_read_bounds(
        {"range": "today_to_tomorrow"}
    )
    assert (
        datetime.fromisoformat(legacy_end)
        - datetime.fromisoformat(legacy_start)
    ).days == 2
    with (
        patch.object(center, "_cloud_token", return_value="token"),
        patch(
            "integrations.cloud_connectors.GoogleCalendarConnector.events",
            return_value=[],
        ) as events,
    ):
        result = center._action_calendar_read(
            ActionRequest(
                "calendar_read",
                "讀取今天到明天的 Google Calendar 行程",
                {
                    "range": "today_to_tomorrow",
                    "source": "google_calendar",
                },
            )
        )
    assert result.success
    assert events.call_args.kwargs["time_min"]
    assert events.call_args.kwargs["time_max"]


def assert_drive_read(center: FlagshipControlCenter) -> None:
    with (
        patch.object(center, "_cloud_token", return_value="token"),
        patch(
            "integrations.cloud_connectors.GoogleDriveConnector.search",
            return_value=[],
        ) as drive_search,
    ):
        result = center._action_cloud_file_read(
            ActionRequest(
                "cloud_file_read",
                "在 Google Drive 搜尋檔案",
                {"query": "墨寒", "search_scope": "name_only"},
            )
        )
    assert result.success
    drive_search.assert_called_once_with("墨寒", 20)


def assert_local_planner_fast_path(
    app: QApplication,
    db: StudioDB,
    center: FlagshipControlCenter,
) -> None:
    center.task_instruction.setText("請幫我讀取最近七天三封 Gmail 郵件")
    with patch(
        "PySide6.QtWidgets.QMessageBox.question",
        return_value=QMessageBox.No,
    ):
        center.plan_instruction(center.task_instruction.text())
        app.processEvents()
    assert center.planner_busy is False
    assert center.plan_button.isEnabled()
    assert any(
        row["event_type"] == "planner_local_fast_path"
        for row in db.audit_rows(20)
    )


def assert_connector_test_plans(
    app: QApplication,
    center: FlagshipControlCenter,
) -> None:
    for instruction in (
        "請測試 Gmail",
        "請測試 Google Calendar",
        "請測試 Google Drive",
    ):
        with (
            patch(
                "PySide6.QtWidgets.QMessageBox.question",
                return_value=QMessageBox.No,
            ),
            patch("PySide6.QtWidgets.QMessageBox.information") as information,
        ):
            center.plan_instruction(instruction)
            app.processEvents()
        assert center.planner_busy is False
        assert information.call_count == 0


def assert_planner_timeout(center: FlagshipControlCenter) -> None:
    center.planner_busy = True
    center._planner_generation = 3
    center.plan_button.setEnabled(False)
    center.plan_button.setText("規劃中…")
    center.planner_timeout.start()
    with patch("PySide6.QtWidgets.QMessageBox.warning") as warning:
        center._planner_timed_out()
    assert warning.call_count == 1
    assert center.planner_busy is False
    assert center._planner_generation == 4
    assert center.plan_button.isEnabled()
    assert center.plan_button.text() == "先產生安全計畫"
    assert not center.planner_timeout.isActive()


def assert_service_shutdown(
    app: QApplication,
    db: StudioDB,
    center: FlagshipControlCenter,
) -> None:
    center._update_remote_status_cache()
    assert center._remote_status_payload()["assistant"] == "墨寒"
    center.close_services()
    assert not center.remote_poll.isActive()
    assert not center.screen_timer.isActive()
    assert not center.workflow_timer.isActive()
    assert not center.planner_timeout.isActive()
    db.close()
    center._refresh_screen_cache()  # must not touch the closed database
    center.deleteLater()
    app.processEvents()


def run() -> None:
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = StudioDB(root / "mohan.db")
        center = FlagshipControlCenter(db, root)
        assert_tabs_and_defaults(center)
        assert_known_safe_plans(center)
        assert_explicit_provider_resolution(center)
        assert_stored_provider_resolution(center)
        assert_calendar_read(center)
        assert_drive_read(center)
        assert_local_planner_fast_path(app, db, center)
        assert_connector_test_plans(app, center)
        assert_planner_timeout(center)
        assert_service_shutdown(app, db, center)
    print("FLAGSHIP_UI_OK")


if __name__ == "__main__":
    run()
