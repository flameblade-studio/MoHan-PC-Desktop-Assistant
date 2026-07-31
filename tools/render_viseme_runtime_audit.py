from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from app import (
    CompanionWindow,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_VISEME_FRAMES,
)


def run(output: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        for timer in window.findChildren(QTimer):
            timer.stop()

        labels = ("CLOSED", "CONS", "A", "I", "U", "E", "O", "BLINK+E")
        cell_width = 170
        cell_height = 180
        header_height = 42
        expressions = tuple(EXPRESSION_POSES)
        sheet = QImage(
            cell_width * len(labels),
            header_height + cell_height * len(expressions),
            QImage.Format_ARGB32,
        )
        sheet.fill(QColor("#0d2130"))
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#e5f2f7"))
        for column, label in enumerate(labels):
            painter.drawText(
                column * cell_width,
                0,
                cell_width,
                header_height,
                Qt.AlignCenter,
                label,
            )

        for row, expression in enumerate(expressions):
            frames = EXPRESSION_SPEECH_FRAMES[expression]
            window.state = "speaking"
            window.speech_pose_suffix = window._pose_suffix(
                EXPRESSION_POSES[expression]
            )
            window.speech_closed_expression = expression
            window.speech_mid_expression = frames["mid"]
            window.speech_open_expression = frames["open"]
            window.speech_gesture_expression = expression
            visemes = EXPRESSION_VISEME_FRAMES[expression]
            closed = QPixmap(window.expression_pixmaps[expression])
            consonant = window._mouth_aperture_pixmap(
                frames["mid"],
                0.12,
            )
            rendered = [
                closed,
                consonant,
                *(
                    window._mouth_aperture_pixmap(
                        visemes[vowel],
                        0.90,
                    )
                    for vowel in ("A", "I", "U", "E", "O")
                ),
            ]
            rendered.append(
                window._blink_composite(rendered[-2], expression)
            )
            for column, pixmap in enumerate(rendered):
                preview = pixmap.scaled(
                    150,
                    150,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = column * cell_width + (cell_width - preview.width()) // 2
                y = (
                    header_height
                    + row * cell_height
                    + (cell_height - preview.height()) // 2
                )
                painter.drawPixmap(x, y, preview)
            painter.setPen(QColor("#8fc9e0"))
            painter.drawText(
                6,
                header_height + row * cell_height + 18,
                expression,
            )
            painter.setPen(QColor("#e5f2f7"))
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not sheet.save(str(output)):
            raise RuntimeError(f"Could not save {output}")
        window.close()
        window.db.close()
        app.processEvents()


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "tmp" / "viseme-runtime-audit.png"
    )
    run(target)
    print(target)
