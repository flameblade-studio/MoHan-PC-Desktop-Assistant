lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication, QPushButton

lazy from companion_window import CompanionWindow
lazy from dashboard_window import Dashboard
lazy from infrastructure.db import StudioDB


def _create_test_window(
    temp_dir: str,
) -> tuple[QApplication, CompanionWindow]:
    os.environ["LOCALAPPDATA"] = temp_dir
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    preflight = StudioDB(db_path)
    preflight.set_setting("tts_enabled", False)
    preflight.close()

    app = QApplication.instance() or QApplication([])
    window = CompanionWindow(startup_speech=False)
    window.dashboard.show()
    app.processEvents()
    return app, window


def _assert_buttons_are_not_default(dashboard: Dashboard) -> None:
    assert all(
        not button.autoDefault() and not button.isDefault()
        for button in dashboard.findChildren(QPushButton)
    )


def _capture_spoken_responses(
    dashboard: Dashboard,
) -> list[tuple[str, str]]:
    dashboard._start_next_ai_request = lambda: None
    spoken: list[tuple[str, str]] = []
    dashboard.speak_requested.connect(
        lambda text, expression: spoken.append((text, expression))
    )
    return spoken


def _assert_text_and_voice_chat_do_not_start_timer(
    app: QApplication,
    dashboard: Dashboard,
    spoken: list[tuple[str, str]],
) -> None:
    dashboard.chat_input.setFocus()
    dashboard.chat_input.setText("寒，今天陪妾聊聊天。")
    QTest.keyClick(dashboard.chat_input, Qt.Key_Return)
    app.processEvents()
    assert dashboard.db.active_session() is None
    assert not any("計時" in text for text, _ in spoken)

    dashboard._voice_text("墨寒，你今天心情如何？")
    app.processEvents()
    assert dashboard.db.active_session() is None
    assert not any("計時" in text for text, _ in spoken)


def _assert_tool_command_is_planned(
    app: QApplication,
    dashboard: Dashboard,
) -> None:
    planned_commands: list[tuple[str, str]] = []
    dashboard.flagship_center.plan_instruction = (
        lambda text, *, source="local": planned_commands.append((text, source))
    )
    queued_before_tool_command = len(dashboard.ai_queue)
    dashboard.chat_input.setText("請幫我讀取 Gmail 郵件")
    QTest.keyClick(dashboard.chat_input, Qt.Key_Return)
    app.processEvents()
    assert planned_commands == [("請幫我讀取 Gmail 郵件", "local")]
    assert len(dashboard.ai_queue) == queued_before_tool_command


def _assert_realtime_chat_does_not_start_timer(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    window._handle_realtime_local_command("好呀，你說。")
    assert dashboard.db.active_session() is None


def _assert_work_buttons_toggle_session(dashboard: Dashboard) -> None:
    buttons = {
        button.text(): button
        for button in dashboard.findChildren(QPushButton)
    }
    QTest.mouseClick(buttons["開始工作"], Qt.LeftButton)
    assert dashboard.db.active_session() is not None
    QTest.mouseClick(buttons["結束工作"], Qt.LeftButton)
    assert dashboard.db.active_session() is None


def _start_command_session(dashboard: Dashboard) -> tuple[int, str]:
    assert dashboard._handle_command("我開始工作了")
    active = dashboard.db.active_session()
    assert active is not None
    return active["id"], active["started_at"]


def _assert_chat_preserves_active_session(
    app: QApplication,
    window: CompanionWindow,
    spoken: list[tuple[str, str]],
    session_id: int,
    started_at: str,
) -> None:
    spoken.clear()
    dashboard = window.dashboard
    dashboard.chat_input.setText("寒，陪妾聊聊今日的事。")
    QTest.keyClick(dashboard.chat_input, Qt.Key_Return)
    dashboard._voice_text("墨寒，替妾分析一個問題。")
    window._handle_realtime_local_command("妾想聽你的看法。")
    app.processEvents()

    active = dashboard.db.active_session()
    assert active["id"] == session_id
    assert active["started_at"] == started_at
    assert not any(
        "計時已啟" in text or "重複開局" in text
        for text, _ in spoken
    )


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        app, window = _create_test_window(temp_dir)
        dashboard = window.dashboard
        _assert_buttons_are_not_default(dashboard)
        spoken = _capture_spoken_responses(dashboard)
        _assert_text_and_voice_chat_do_not_start_timer(app, dashboard, spoken)
        _assert_tool_command_is_planned(app, dashboard)
        _assert_realtime_chat_does_not_start_timer(window, dashboard)
        _assert_work_buttons_toggle_session(dashboard)
        session_id, started_at = _start_command_session(dashboard)
        _assert_chat_preserves_active_session(
            app,
            window,
            spoken,
            session_id,
            started_at,
        )

        window.close()
        app.processEvents()
    print("CHAT_TIMER_ISOLATION_OK")


if __name__ == "__main__":
    run()
