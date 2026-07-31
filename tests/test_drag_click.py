from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from app import ClickableLabel, CompanionWindow
from db import StudioDB


def run() -> None:
    app = QApplication([])
    label = ClickableLabel()
    label.resize(200, 200)
    label.show()
    app.processEvents()
    spy = QSignalSpy(label.clicked)

    QTest.mousePress(label, Qt.LeftButton, pos=QPoint(30, 30))
    QTest.mouseMove(label, QPoint(90, 90), delay=20)
    QTest.mouseRelease(label, Qt.LeftButton, pos=QPoint(90, 90))
    app.processEvents()
    assert spy.count() == 0

    QTest.mouseClick(label, Qt.LeftButton, pos=QPoint(40, 40))
    app.processEvents()
    assert spy.count() == 1

    # Normal hand jitter below the OS threshold remains a click.
    small_delta = max(1, QApplication.startDragDistance() - 2)
    QTest.mousePress(label, Qt.LeftButton, pos=QPoint(50, 50))
    QTest.mouseMove(
        label,
        QPoint(50 + small_delta, 50),
        delay=20,
    )
    QTest.mouseRelease(
        label,
        Qt.LeftButton,
        pos=QPoint(50 + small_delta, 50),
    )
    app.processEvents()
    assert spy.count() == 2

    label.close()
    app.processEvents()

    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = (
            Path(temp_dir)
            / "YanJianStudio"
            / "MoHan"
            / "mohan.db"
        )
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.dashboard.hide()
        app.processEvents()
        QTest.mousePress(
            window.character,
            Qt.LeftButton,
            pos=QPoint(220, 220),
        )
        QTest.mouseMove(
            window.character,
            QPoint(290, 270),
            delay=20,
        )
        QTest.mouseRelease(
            window.character,
            Qt.LeftButton,
            pos=QPoint(290, 270),
        )
        app.processEvents()
        assert not window.dashboard.isVisible()
        QTest.mouseClick(
            window.character,
            Qt.LeftButton,
            pos=QPoint(220, 220),
        )
        app.processEvents()
        assert window.dashboard.isVisible()
        window.close()
        app.processEvents()
    print("DRAG_CLICK_DISAMBIGUATION_OK")


if __name__ == "__main__":
    run()
