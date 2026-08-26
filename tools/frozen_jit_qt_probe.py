"""Minimal frozen-runtime probe for the Python 3.15 JIT + Qt exit contract."""

from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication, QWidget

lazy from application.runtime_bootstrap import finalize_process_exit, jit_is_enabled


def _output_path() -> Path | None:
    prefix = "--output="
    for argument in sys.argv[1:]:
        if argument.startswith(prefix):
            return Path(argument.removeprefix(prefix))
    return None


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("MoHan frozen JIT Qt probe")
    QTimer.singleShot(0, app.quit)
    exit_code = int(app.exec())
    window.close()
    app.processEvents()
    output = _output_path()
    if output is not None:
        output.write_text(
            f"jit_enabled={jit_is_enabled()};qt_exit={exit_code}",
            encoding="utf-8",
        )
    return finalize_process_exit(0 if jit_is_enabled() and exit_code == 0 else 2)


if __name__ == "__main__":
    main()
