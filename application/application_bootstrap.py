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


def _write_jit_status() -> None:
    output_path = _argument_value("--jit-status-output=")
    if not output_path:
        return
    Path(output_path).write_text(
        "PACKAGED_JIT_DEFAULT_OK"
        if jit_is_enabled()
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
    output_path = _argument_value("--smoke-output=")
    if output_path:
        Path(output_path).write_text(
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
