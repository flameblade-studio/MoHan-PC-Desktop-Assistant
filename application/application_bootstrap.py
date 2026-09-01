from __future__ import annotations

lazy import ctypes
lazy import os
lazy import sys
lazy from contextlib import suppress
lazy from pathlib import Path

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from application.packaged_self_test import run_packaged_self_test
lazy from application.runtime_bootstrap import (
    ensure_default_jit,
    finalize_process_exit,
    jit_is_enabled,
)
lazy from domain.app_profile import profile_window_title
lazy from infrastructure.app_resources import (
    APP_NAME,
    APP_VERSION,
    STYLE,
    WINDOWS_APP_USER_MODEL_ID,
    application_icon,
    application_ui_font,
)
lazy from integrations.openai_fashion_trend_scout import (
    create_openai_fashion_trend_scout,
)
lazy from presentation.companion_window import CompanionWindow

ensure_default_jit(__name__, __file__)


def _argument_value(prefix: str) -> str:
    argument = next(
        (value for value in sys.argv if value.startswith(prefix)),
        "",
    )
    return argument.split("=", 1)[1] if argument else ""


def _harness_output_path(flag: str) -> Path | None:
    """只有測試工具啟動時才接受輸出路徑。

    這兩個旗標的值原本直接進 `Path(...).write_text()`，而它會截斷目標。
    `_write_jit_status()` 更在 `--self-test` 判斷**之前**無條件執行，於是
    任何一次一般啟動只要帶著這個旗標，指定的檔案就被清成一行字串。

    刻意不加「不得覆寫既有檔」那條：tools/profile_mohan_tachyon.py 會用
    同一個路徑重複執行，那條規則會讓它從第二輪起靜默不寫。

    殘留風險誠實標明：能決定啟動命令列的人仍可自己加上 `--self-test`。
    但那種人通常已經能直接執行任意程式，這個原語沒讓他多拿到什麼。
    被關掉的是「一般啟動也會寫」，那才是真正不該存在的。
    """
    value = _argument_value(flag)
    if not value:
        return None
    if not ("--self-test" in sys.argv or "--smoke-auto-exit" in sys.argv):
        return None
    target = Path(value)
    if not target.parent.is_dir():
        return None
    return target


def _write_jit_status() -> None:
    target = _harness_output_path("--jit-status-output=")
    if target is None:
        return
    expected_jit = os.environ.get("MOHAN_ENABLE_JIT") == "1"
    target.write_text(
        "PACKAGED_JIT_DEFAULT_OK"
        if jit_is_enabled() == expected_jit
        else "PACKAGED_JIT_DEFAULT_FAILED",
        encoding="utf-8",
    )


def _prepare_platform(*, offscreen: bool) -> None:
    if offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    if sys.platform != "win32":
        return
    with suppress(AttributeError, OSError):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID
        )


def _create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setFont(application_ui_font())
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(application_icon())
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    return app


def _run_smoke_event_loop(
    app: QApplication,
    window: CompanionWindow,
) -> int:
    QTimer.singleShot(2_500, window.close)
    QTimer.singleShot(2_700, app.quit)
    exit_code = app.exec()
    target = _harness_output_path("--smoke-output=")
    if target is not None:
        target.write_text(
            "PACKAGED_EVENT_LOOP_OK"
            if exit_code == 0
            else "PACKAGED_EVENT_LOOP_FAILED",
            encoding="utf-8",
        )
    return exit_code


def run_application() -> int:
    self_test = "--self-test" in sys.argv
    smoke_auto_exit = "--smoke-auto-exit" in sys.argv
    _write_jit_status()
    _prepare_platform(offscreen=self_test or smoke_auto_exit)
    app = _create_application()
    window = CompanionWindow(
        startup_speech=not self_test,
        defer_visual_startup=not self_test,
        fashion_trend_scout_factory=create_openai_fashion_trend_scout,
    )
    app.setApplicationName(profile_window_title(window.db))
    if self_test:
        exit_code = run_packaged_self_test(
            app,
            window,
            output_path=_argument_value("--self-test-output="),
        )
    else:
        window.show()
        QTimer.singleShot(75, window.complete_deferred_startup)
        exit_code = (
            _run_smoke_event_loop(app, window)
            if smoke_auto_exit
            else app.exec()
        )
    # Keep app.py a pure composition root while still cutting off the one
    # unsafe frozen-JIT interpreter-finalization tail after Qt has shut down.
    return finalize_process_exit(exit_code)


__all__ = ("run_application",)
