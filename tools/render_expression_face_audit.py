from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from app import (
    CompanionWindow,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
)


FACE_RECTS = {
    "cheek": QRect(118, 82, 185, 190),
    "lean": QRect(112, 82, 185, 190),
    "front": QRect(142, 78, 185, 195),
}


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        for timer in window.findChildren(QTimer):
            timer.stop()

        expressions = tuple(
            expression
            for expression in EXPRESSION_POSES
            if expression in window.expression_pixmaps
        )
        cell_width = 390
        cell_height = 450
        sheet = QPixmap(cell_width * 4, cell_height * len(expressions))
        sheet.fill(QColor("#0d1c27"))
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setFont(QFont("Microsoft JhengHei", 13))
        painter.setPen(QColor("#d8edf5"))

        for row, expression in enumerate(expressions):
            pose = EXPRESSION_POSES[expression]
            suffix = window._pose_suffix(pose)
            frames = EXPRESSION_SPEECH_FRAMES[expression]
            window.state = "speaking"
            window.speech_closed_expression = expression
            window.speech_pose_suffix = suffix
            window.speech_gesture_expression = expression
            window.speech_mid_expression = frames["mid"]
            window.speech_open_expression = frames["open"]
            closed = window.expression_pixmaps[expression]
            middle = window._mouth_aperture_pixmap(
                window.speech_mid_expression,
                0.48,
            )
            opened = window._mouth_aperture_pixmap(
                window.speech_open_expression,
                0.90,
            )
            blink = window._blink_composite(opened, expression)
            for column, (label, frame) in enumerate(
                (
                    ("閉嘴", closed),
                    ("半開", middle),
                    ("張嘴", opened),
                    ("張嘴＋眨眼", blink),
                )
            ):
                face = frame.copy(FACE_RECTS[pose]).scaled(
                    360,
                    380,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = column * cell_width + 15
                y = row * cell_height
                painter.drawPixmap(x, y, face)
                painter.drawText(
                    QRect(
                        column * cell_width,
                        y + 382,
                        cell_width,
                        26,
                    ),
                    Qt.AlignCenter,
                    label,
                )
                painter.drawText(
                    QRect(
                        column * cell_width,
                        y + 410,
                        cell_width,
                        28,
                    ),
                    Qt.AlignCenter,
                    expression,
                )
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        assert sheet.save(str(output))
        window.close()
        window.db.close()
        app.processEvents()


if __name__ == "__main__":
    destination = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("tmp/expression-face-audit.png")
    )
    render(destination.resolve())
    print(destination.resolve())
