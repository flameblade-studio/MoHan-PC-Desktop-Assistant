from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow, STYLE


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        app.setStyleSheet(STYLE)
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.bubble.hide()
        window.idle_pose = "cheek"
        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_blinking = False
        window._set_expression("idle", fade=False)

        frames: list[QImage] = []
        crop = QRect(155, 165, 120, 100)
        cue_schedule = {
            0: ("A", "A"),
            5: ("O", "O"),
            11: ("CLOSED",),
        }
        for index in range(16):
            for vowel in cue_schedule.get(index, ()):
                window._audio_viseme_cue(
                    0.62 if vowel != "CLOSED" else 0.0,
                    vowel,
                )
            QTest.qWait(16)
            app.processEvents()
            frame = (
                window.character.pixmap()
                .toImage()
                .copy(crop)
                .scaled(
                    QSize(300, 250),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            frames.append(frame)

        cell_width, cell_height = 300, 250
        title_height, margin = 28, 12
        canvas = QImage(
            cell_width * 4 + margin * 5,
            (cell_height + title_height) * 4 + margin * 5,
            QImage.Format_ARGB32,
        )
        canvas.fill(QColor("#263746"))
        painter = QPainter(canvas)
        painter.setFont(QFont("Arial", 11))
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for index, frame in enumerate(frames):
            row, column = divmod(index, 4)
            x = margin + column * (cell_width + margin)
            y = margin + row * (cell_height + title_height + margin)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(
                QRect(x, y, cell_width, title_height),
                Qt.AlignCenter,
                f"{index * 16:03d} ms",
            )
            painter.fillRect(
                QRect(x, y + title_height, cell_width, cell_height),
                QColor("#101a25"),
            )
            painter.drawImage(x, y + title_height, frame)
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not canvas.save(str(output), "PNG"):
            raise RuntimeError(f"Failed to save preview: {output}")
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
