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


def render(output: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.bubble.hide()
        for timer in window.findChildren(QTimer):
            timer.stop()
        app.processEvents()

        expressions = [
            expression
            for expression in EXPRESSION_POSES
            if expression in window.expression_pixmaps
        ]
        columns = 4
        card_width = 300
        card_height = 410
        rows = (len(expressions) + columns - 1) // columns
        sheet = QPixmap(columns * card_width, rows * card_height)
        sheet.fill(QColor("#0d1c27"))
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setFont(QFont("Microsoft JhengHei", 14))
        painter.setPen(QColor("#d8edf5"))

        for index, expression in enumerate(expressions):
            window.state = expression
            window._set_expression(expression, fade=False)
            window._attention_tick()
            window._physics_tick()
            app.processEvents()
            frame = window.grab().scaled(
                280,
                370,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = (index % columns) * card_width
            y = (index // columns) * card_height
            painter.drawPixmap(x + 10, y, frame)
            painter.drawText(
                QRect(x + 8, y + 374, card_width - 16, 30),
                Qt.AlignCenter,
                expression,
            )

        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        assert sheet.save(str(output))

        speech_expressions = tuple(
            expression
            for expression in EXPRESSION_POSES
            if expression in window.expression_pixmaps
        )
        speech_sheet = QPixmap(4 * 300, len(speech_expressions) * 340)
        speech_sheet.fill(QColor("#0d1c27"))
        painter = QPainter(speech_sheet)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setFont(QFont("Arial", 12))
        painter.setPen(QColor("#d8edf5"))
        for row, expression in enumerate(speech_expressions):
            pose = EXPRESSION_POSES[expression]
            suffix = window._pose_suffix(pose)
            frames = EXPRESSION_SPEECH_FRAMES[expression]
            window.state = "speaking"
            window.speech_closed_expression = expression
            window.speech_pose_suffix = suffix
            window.speech_gesture_expression = expression
            window.speech_mid_expression = frames["mid"]
            window.speech_open_expression = frames["open"]
            base = window.expression_pixmaps[expression]
            mid = window._mouth_aperture_pixmap(
                window.speech_mid_expression,
                0.48,
            )
            opened = window._mouth_aperture_pixmap(
                window.speech_open_expression,
                0.9,
            )
            blink = window._blink_composite(opened, expression)
            for column, (label, frame) in enumerate(
                (
                    ("closed", base),
                    ("mid", mid),
                    ("open", opened),
                    ("open+blink", blink),
                )
            ):
                preview = frame.scaled(
                    280,
                    280,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = column * 300
                y = row * 340
                painter.drawPixmap(x + 10, y, preview)
                painter.drawText(
                    QRect(x + 8, y + 282, 284, 22),
                    Qt.AlignCenter,
                    label,
                )
                painter.drawText(
                    QRect(x + 8, y + 306, 284, 22),
                    Qt.AlignCenter,
                    expression,
                )
        painter.end()
        speech_output = output.with_name("expression-speech-sheet.png")
        assert speech_sheet.save(str(speech_output))
        window.close()
        app.processEvents()


if __name__ == "__main__":
    destination = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("tmp/expression-contact-sheet.png")
    )
    render(destination.resolve())
    print(destination.resolve())
