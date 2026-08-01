from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from db import StudioDB
from expression_system import AI_WAIT_TIMEOUT_MS


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()

        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        dashboard = window.dashboard
        dashboard.ai_busy = True

        def schedule(prompt: str) -> list[tuple[int, object]]:
            callbacks: list[tuple[int, object]] = []
            with patch(
                "app.QTimer.singleShot",
                side_effect=lambda delay, callback: callbacks.append(
                    (delay, callback)
                ),
            ):
                dashboard._schedule_ai_wait_expressions(prompt)
            return callbacks

        # The status text is informational: greetings and ordinary questions
        # have no expression callback inside the normal response window.
        window.set_state("idle", force=True)
        greeting = schedule("早安，墨寒")
        assert [delay for delay, _ in greeting] == [AI_WAIT_TIMEOUT_MS]
        assert window.state == "idle"
        dashboard.set_voice_phase("墨寒思考中…")
        assert window.state == "idle"

        ordinary = schedule("天空為什麼是藍色？")
        assert [delay for delay, _ in ordinary] == [AI_WAIT_TIMEOUT_MS]
        ordinary_generation = dashboard.active_ai_wait_generation
        dashboard._finish_ai_wait_expression()
        ordinary[0][1]()
        assert dashboard.active_ai_wait_generation == 0
        assert window.state == "idle"

        # A complex prompt may react only after its noticeable delay.
        complex_callbacks = schedule(
            "請分析兩個方案的利弊、風險與優先順序。"
        )
        assert len(complex_callbacks) == 2
        assert complex_callbacks[0][0] >= 1_000
        assert window.state == "idle"
        complex_callbacks[0][1]()
        assert window.state == "thinking_front"
        assert window.active_ai_wait_generation == (
            dashboard.active_ai_wait_generation
        )

        # Completion owns and clears only this request's wait expression.
        dashboard._finish_ai_wait_expression()
        assert window.state == "idle"
        assert window.active_ai_wait_generation == 0

        # A genuinely slow ordinary request may think at the timeout, but the
        # arbiter prevents the same pose from repeating during cooldown.
        window.expression_arbiter.last_started_ms.clear()
        delayed = schedule("明天臺北天氣如何？")
        delayed[0][1]()
        assert window.state == "thinking_front"
        dashboard._finish_ai_wait_expression()
        repeated = schedule("後天天氣呢？")
        repeated[0][1]()
        assert window.state == "idle"
        assert window.active_ai_wait_generation == 0

        # API failure invalidates every old timer and removes a wait pose
        # before the worried fallback response is prepared.
        window.expression_arbiter.last_started_ms.clear()
        failing = schedule("請分析這份規劃的風險。")
        failing[0][1]()
        assert window.state == "thinking_front"
        with patch.object(dashboard, "_reply") as reply:
            dashboard._ai_failed("timeout")
        assert window.state == "idle"
        assert dashboard.active_ai_wait_generation == 0
        assert reply.call_args.args[1] == "worried"
        failing[-1][1]()
        assert window.state == "idle"

        # Non-Realtime transcription enters the same text queue but merely
        # setting its “thinking” status never selects a pose.
        with patch.object(dashboard, "_start_next_ai_request") as start:
            dashboard._voice_text("天空為什麼是藍色？")
        start.assert_called_once()
        assert dashboard.ai_queue[-1][0] == "天空為什麼是藍色？"
        assert window.state == "idle"
        dashboard.ai_queue.clear()

        # Realtime transcripts never use the standard wait scheduler. Starting
        # Realtime speech cancels a pending standard wait and enters visemes.
        prior_generation = dashboard.ai_wait_generation
        window._realtime_user_text("早安，墨寒")
        assert dashboard.ai_wait_generation == prior_generation
        window.expression_arbiter.last_started_ms.clear()
        dashboard.ai_busy = True
        realtime_pending = schedule("請分析這份長期策略。")
        realtime_pending[0][1]()
        assert window.state == "thinking_front"
        window._realtime_speaking(True)
        assert dashboard.active_ai_wait_generation == 0
        assert window.state == "speaking"
        assert window.realtime_mouth_active
        window._realtime_speaking(False)
        window._complete_realtime_speaking_stop()
        assert window.state == "idle"
        assert not window.realtime_mouth_active

        # An explicit internal thinking tag remains authoritative for the
        # answer itself and is handled by the existing speech emotion path.
        window._realtime_speaking(True)
        window._realtime_assistant_text(
            "主上，此事容妾斟酌。[[MOHAN_EMOTION:thinking:0.72]]"
        )
        assert window.realtime_after_speech_state == "thinking_front"
        window._realtime_speaking(False)
        window._complete_realtime_speaking_stop()
        assert window.state == "thinking_front"
        window.set_state("idle", force=True)

        window.close()
        app.processEvents()
    print("AI_WAIT_EXPRESSION_OK")


if __name__ == "__main__":
    run()
