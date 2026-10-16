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

lazy from presentation.flagship_core import ActionRequest
lazy from presentation.flagship_ui import FlagshipControlCenter
lazy from infrastructure.db import StudioDB

FLAGSHIP_TAB_COUNT = 8
CALENDAR_RANGE_DAYS = 2
PLANNER_GENERATION_AFTER_TIMEOUT = 4


def assert_tabs_and_defaults(center: FlagshipControlCenter) -> None:
    assert center.tabs.count() == FLAGSHIP_TAB_COUNT
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
    assert center._permission_controls["delete_file"].currentText() == "封鎖"
    assert center._permission_controls["delete_file"].currentData() == "禁止"
    assert center._permission_controls["home_lock"].currentText() == "封鎖"
    assert center._permission_controls["home_lock"].currentData() == "禁止"
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
    ).days == CALENDAR_RANGE_DAYS
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


class _PlannerTestSignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *values) -> None:
        for callback in tuple(self._callbacks):
            callback(*values)


class _CapturedPlannerSignals:
    def __init__(self) -> None:
        self.done = _PlannerTestSignal()
        self.failed = _PlannerTestSignal()


class _CapturedPlannerWorker:
    def __init__(self, instruction: str, **kwargs) -> None:
        self.instruction = instruction
        self.kwargs = kwargs
        self.signals = _CapturedPlannerSignals()

    def setAutoDelete(self, _enabled: bool) -> None:
        pass


class _PlannerCapturePool:
    def __init__(self) -> None:
        self.started = []

    def start(self, worker) -> None:
        self.started.append(worker)


def _open_web_plan(language: str) -> dict[str, object]:
    return {
        "title": f"Open the requested work folder ({language})",
        "steps": [
            {
                "capability": "open_web",
                "description": "Open the requested work folder",
                "arguments": {"url": "https://example.com"},
                "reversible": True,
            }
        ],
    }


def assert_multilingual_planner_intent(
    app: QApplication,
    center: FlagshipControlCenter,
) -> None:
    explicit_requests = (
        ("English", "Please open my work folder"),
        ("繁體中文", "請幫我開啟工作資料夾"),
        ("简体中文", "请帮我打开工作文件夹"),
        ("日本語", "作業フォルダーを開いてください"),
        ("繁體中文未知動詞", "請幫我整理工作資料夾"),
        ("繁體中文未知動詞", "幫我播放音樂"),
        ("繁體中文未知動詞", "替我安排明天的工作"),
    )
    ordinary_chat = (
        ("繁體中文", "昨天我整理了工作資料夾，今天想聊聊這件事。"),
        ("简体中文", "我昨天打开了工作文件夹，心情有点复杂。"),
        ("English", "I opened my work folder yesterday and felt distracted."),
        ("日本語", "昨日は作業フォルダーを開きました。"),
        ("繁體中文否定句", "請不要刪除工作檔案。"),
        ("简体中文否定句", "请不要删除工作文件。"),
        ("English negative request", "Could you please not delete that file?"),
        ("日本語否定文", "ファイルを削除しないでください。"),
    )
    pool = _PlannerCapturePool()
    with (
        patch.object(center, "thread_pool", pool),
        patch(
            "presentation.flagship.planner.ActionPlannerWorker",
            _CapturedPlannerWorker,
        ),
        patch("PySide6.QtWidgets.QMessageBox.information") as information,
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.No,
        ) as question,
        patch.object(center.executor, "execute") as execute,
    ):
        for index, (language, instruction) in enumerate(explicit_requests, 1):
            center.plan_instruction(instruction)
            assert information.call_count == 0, (
                f"{language} explicit task was rejected before planning"
            )
            assert center.planner_busy is True
            assert len(pool.started) == index
            worker = pool.started[-1]
            assert worker.instruction == instruction
            worker.signals.done.emit(_open_web_plan(language))
            app.processEvents()
            assert question.call_count == index
            assert center.planner_busy is False
            execute.assert_not_called()

        for language, message in ordinary_chat:
            started_before = len(pool.started)
            notices_before = information.call_count
            center.plan_instruction(message)
            assert len(pool.started) == started_before, (
                f"{language} ordinary chat unexpectedly started a planner"
            )
            assert information.call_count == notices_before + 1, (
                f"{language} ordinary chat did not stay out of the planner"
            )
            assert center.planner_busy is False


def assert_planner_authorization_stays_fail_closed(
    center: FlagshipControlCenter,
) -> None:
    executor = center.executor
    assert executor.policy.permission_mode("delete_file") == "禁止"
    pool = _PlannerCapturePool()
    denied_results = []
    delete_handler_calls = []
    original_execute = executor.execute

    def capture_execute(plan):
        results = original_execute(plan)
        denied_results.extend(results)
        return results

    def forbidden_delete_handler(request):
        delete_handler_calls.append(request)
        raise RuntimeError("a denied action reached its handler")

    handlers = dict(executor.handlers)
    handlers["delete_file"] = (forbidden_delete_handler, None)
    with (
        patch.object(center, "thread_pool", pool),
        patch(
            "presentation.flagship.planner.ActionPlannerWorker",
            _CapturedPlannerWorker,
        ),
        patch.object(executor, "handlers", handlers),
        patch.object(executor, "execute", side_effect=capture_execute),
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ) as question,
        patch("PySide6.QtWidgets.QMessageBox.information") as information,
    ):
        center.plan_instruction("Please delete a work file")
        assert center.planner_busy is True
        assert len(pool.started) == 1
        pool.started[0].signals.done.emit(
            {
                "title": "Delete a work file",
                "steps": [
                    {
                        "capability": "delete_file",
                        "description": "Delete the requested work file",
                        "arguments": {"path": "work-file.txt"},
                        "reversible": False,
                    }
                ],
            }
        )

    assert question.call_count == 1
    assert information.call_count == 1
    assert len(denied_results) == 1
    assert denied_results[0].success is False
    assert "安全政策已阻擋" in denied_results[0].message
    assert delete_handler_calls == []
    assert center.planner_busy is False


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
    assert center._planner_generation == PLANNER_GENERATION_AFTER_TIMEOUT
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
    center._refresh_screen_cache()  # preserve the closed database lifecycle boundary
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
        try:
            assert_multilingual_planner_intent(app, center)
            assert_planner_authorization_stays_fail_closed(center)
        except Exception:
            center.close_services()
            db.close()
            center.deleteLater()
            app.processEvents()
            raise
        assert_calendar_read(center)
        assert_drive_read(center)
        assert_local_planner_fast_path(app, db, center)
        assert_connector_test_plans(app, center)
        assert_planner_timeout(center)
        assert_service_shutdown(app, db, center)
    print("FLAGSHIP_UI_OK")


if __name__ == "__main__":
    run()
