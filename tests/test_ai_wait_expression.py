from __future__ import annotations

lazy import os
lazy import sys
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from app import CompanionWindow, Dashboard
lazy from db import StudioDB
lazy from expression_system import AI_WAIT_TIMEOUT_MS

type ScheduledCallback = tuple[int, Callable[[], None]]


def _create_test_window(
    temp_dir: str,
) -> tuple[QApplication, CompanionWindow]:
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
    window.dashboard.ai_busy = True
    return app, window


def _schedule_wait_expression(
    dashboard: Dashboard,
    prompt: str,
) -> list[ScheduledCallback]:
    callbacks: list[ScheduledCallback] = []
    with patch(
        "app.QTimer.singleShot",
        side_effect=lambda delay, callback: callbacks.append((delay, callback)),
    ):
        dashboard._schedule_ai_wait_expressions(prompt)
    return callbacks


def _assert_status_is_informational(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    window.set_state("idle", force=True)
    greeting = _schedule_wait_expression(dashboard, "早安，墨寒")
    assert [delay for delay, _ in greeting] == [AI_WAIT_TIMEOUT_MS]
    assert window.state == "idle"
    dashboard.set_voice_phase("墨寒思考中…")
    assert window.state == "idle"

    ordinary = _schedule_wait_expression(dashboard, "天空為什麼是藍色？")
    assert [delay for delay, _ in ordinary] == [AI_WAIT_TIMEOUT_MS]
    ordinary_generation = dashboard.active_ai_wait_generation
    assert ordinary_generation > 0
    dashboard._finish_ai_wait_expression()
    ordinary[0][1]()
    assert dashboard.active_ai_wait_generation == 0
    assert window.state == "idle"


def _assert_complex_wait_and_completion(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    complex_callbacks = _schedule_wait_expression(
        dashboard,
        "請分析兩個方案的利弊、風險與優先順序。",
    )
    assert len(complex_callbacks) == 2
    assert complex_callbacks[0][0] >= 1_000
    assert window.state == "idle"
    complex_callbacks[0][1]()
    assert window.state == "thinking_front"
    assert window.active_ai_wait_generation == (
        dashboard.active_ai_wait_generation
    )

    dashboard._finish_ai_wait_expression()
    assert window.state == "idle"
    assert window.active_ai_wait_generation == 0


def _assert_cooldown_prevents_repeat(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    window.expression_arbiter.last_started_ms.clear()
    delayed = _schedule_wait_expression(dashboard, "明天臺北天氣如何？")
    delayed[0][1]()
    assert window.state == "thinking_front"
    dashboard._finish_ai_wait_expression()
    repeated = _schedule_wait_expression(dashboard, "後天天氣呢？")
    repeated[0][1]()
    assert window.state == "idle"
    assert window.active_ai_wait_generation == 0


def _assert_failure_invalidates_timers(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    window.expression_arbiter.last_started_ms.clear()
    failing = _schedule_wait_expression(
        dashboard,
        "請分析這份規劃的風險。",
    )
    failing[0][1]()
    assert window.state == "thinking_front"
    with patch.object(dashboard, "_reply") as reply:
        dashboard._ai_failed("timeout")
    assert window.state == "idle"
    assert dashboard.active_ai_wait_generation == 0
    assert reply.call_args.args[1] == "worried"
    failing[-1][1]()
    assert window.state == "idle"


def _assert_transcription_queues_without_pose(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    with patch.object(dashboard, "_start_next_ai_request") as start:
        dashboard._voice_text("天空為什麼是藍色？")
    start.assert_called_once()
    assert dashboard.ai_queue[-1][0] == "天空為什麼是藍色？"
    assert window.state == "idle"
    dashboard.ai_queue.clear()


def _assert_realtime_owns_speech_pose(
    window: CompanionWindow,
    dashboard: Dashboard,
) -> None:
    prior_generation = dashboard.ai_wait_generation
    window._realtime_user_text("早安，墨寒")
    assert dashboard.ai_wait_generation == prior_generation
    window.expression_arbiter.last_started_ms.clear()
    dashboard.ai_busy = True
    realtime_pending = _schedule_wait_expression(
        dashboard,
        "請分析這份長期策略。",
    )
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


def _assert_explicit_thinking_tag(window: CompanionWindow) -> None:
    window._realtime_speaking(True)
    window._realtime_assistant_text(
        "主上，此事容妾斟酌。[[MOHAN_EMOTION:thinking:0.72]]"
    )
    assert window.realtime_after_speech_state == "thinking_front"
    window._realtime_speaking(False)
    window._complete_realtime_speaking_stop()
    assert window.state == "thinking_front"
    window.set_state("idle", force=True)


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app, window = _create_test_window(temp_dir)
        dashboard = window.dashboard

        # The status text is informational for greetings and normal questions.
        _assert_status_is_informational(window, dashboard)
        # Complex prompts may react only after a noticeable delay.
        _assert_complex_wait_and_completion(window, dashboard)
        # A repeated slow request must respect the expression cooldown.
        _assert_cooldown_prevents_repeat(window, dashboard)
        # API failure must invalidate pending expression timers.
        _assert_failure_invalidates_timers(window, dashboard)
        # Non-Realtime transcription uses the queue without selecting a pose.
        _assert_transcription_queues_without_pose(window, dashboard)
        # Realtime speech owns its visemes and cancels standard wait poses.
        _assert_realtime_owns_speech_pose(window, dashboard)
        # Explicit internal emotion tags remain authoritative for the answer.
        _assert_explicit_thinking_tag(window)

        window.close()
        app.processEvents()
    print("AI_WAIT_EXPRESSION_OK")


if __name__ == "__main__":
    run()
