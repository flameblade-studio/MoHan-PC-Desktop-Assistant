import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app import CompanionWindow
from db import StudioDB


def run() -> None:
    with TemporaryDirectory() as tmp:
        os.environ["LOCALAPPDATA"] = tmp
        db_path = Path(tmp) / "YanJianStudio" / "MoHan" / "mohan.db"
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()

        app = QApplication.instance() or QApplication([])
        window = CompanionWindow(startup_speech=False)
        dashboard = window.dashboard
        dashboard.show()
        app.processEvents()

        assert all(
            not button.autoDefault() and not button.isDefault()
            for button in dashboard.findChildren(QPushButton)
        )

        dashboard._start_next_ai_request = lambda: None
        spoken = []
        dashboard.speak_requested.connect(
            lambda text, expression: spoken.append((text, expression))
        )

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

        planned_commands = []
        dashboard.flagship_center.plan_instruction = (
            lambda text, *, source="local": planned_commands.append(
                (text, source)
            )
        )
        queued_before_tool_command = len(dashboard.ai_queue)
        dashboard.chat_input.setText("請幫我讀取 Gmail 郵件")
        QTest.keyClick(dashboard.chat_input, Qt.Key_Return)
        app.processEvents()
        assert planned_commands == [
            ("請幫我讀取 Gmail 郵件", "local")
        ]
        assert len(dashboard.ai_queue) == queued_before_tool_command

        window._handle_realtime_local_command("好呀，你說。")
        assert dashboard.db.active_session() is None

        buttons = {
            button.text(): button
            for button in dashboard.findChildren(QPushButton)
        }
        QTest.mouseClick(buttons["開始工作"], Qt.LeftButton)
        assert dashboard.db.active_session() is not None
        QTest.mouseClick(buttons["結束工作"], Qt.LeftButton)
        assert dashboard.db.active_session() is None

        assert dashboard._handle_command("我開始工作了")
        active = dashboard.db.active_session()
        assert active is not None
        session_id = active["id"]
        started_at = active["started_at"]
        spoken.clear()

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

        window.close()
        app.processEvents()
    print("CHAT_TIMER_ISOLATION_OK")


if __name__ == "__main__":
    run()
