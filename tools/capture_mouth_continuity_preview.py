from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QSize, Qt
lazy from PySide6.QtGui import QColor, QFont, QImage, QPainter
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from infrastructure.app_resources import STYLE

FRAME_WIDTH = 300
FRAME_HEIGHT = 250
FRAME_CROP = (155, 165, 120, 100)
FRAME_COUNT = 16
FRAME_INTERVAL_MS = 16
GRID_COLUMNS = 4
TITLE_HEIGHT = 28
GRID_MARGIN = 12


def configure_speaking_window(window: CompanionWindow) -> None:
    window.show()
    window.bubble.hide()
    window.idle_pose = "cheek"
    window.state = "speaking"
    window.speech_pose_suffix = ""
    window.speech_closed_expression = window._closed_speech_expression()
    window.speech_mid_expression = window._mouth_mid_expression()
    window.speech_open_expression = window._speaking_expression()
    window.speech_blinking = False
    window._start_mouth_animation(audio_driven=True)


def capture_mouth_frames(
    app: QApplication,
    window: CompanionWindow,
) -> list[QImage]:
    cue_schedule = {
        0: ("A", "A"),
        5: ("O", "O"),
        11: ("CLOSED",),
    }
    frames: list[QImage] = []
    for index in range(FRAME_COUNT):
        for vowel in cue_schedule.get(index, ()):
            window._audio_viseme_cue(
                0.62 if vowel != "CLOSED" else 0.0,
                vowel,
            )
        QTest.qWait(FRAME_INTERVAL_MS)
        app.processEvents()
        frame = (
            window.character
            .pixmap()
            .toImage()
            .copy(QRect(*FRAME_CROP))
            .scaled(
                QSize(FRAME_WIDTH, FRAME_HEIGHT),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        frames.append(frame)
    return frames


def draw_frame_grid(painter: QPainter, frames: list[QImage]) -> None:
    for index, frame in enumerate(frames):
        row, column = divmod(index, GRID_COLUMNS)
        x = GRID_MARGIN + column * (FRAME_WIDTH + GRID_MARGIN)
        y = GRID_MARGIN + row * (FRAME_HEIGHT + TITLE_HEIGHT + GRID_MARGIN)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRect(x, y, FRAME_WIDTH, TITLE_HEIGHT),
            Qt.AlignCenter,
            f"{index * FRAME_INTERVAL_MS:03d} ms",
        )
        painter.fillRect(
            QRect(x, y + TITLE_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT),
            QColor("#101a25"),
        )
        painter.drawImage(x, y + TITLE_HEIGHT, frame)


def compose_preview(frames: list[QImage]) -> QImage:
    canvas = QImage(
        FRAME_WIDTH * GRID_COLUMNS + GRID_MARGIN * (GRID_COLUMNS + 1),
        (FRAME_HEIGHT + TITLE_HEIGHT) * GRID_COLUMNS + GRID_MARGIN * (GRID_COLUMNS + 1),
        QImage.Format_ARGB32,
    )
    canvas.fill(QColor("#263746"))
    painter = QPainter(canvas)
    painter.setFont(QFont("Arial", 11))
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    draw_frame_grid(painter, frames)
    painter.end()
    return canvas


def save_preview(canvas: QImage, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save preview: {output}")


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        app.setStyleSheet(STYLE)
        window = CompanionWindow(startup_speech=False)
        configure_speaking_window(window)
        save_preview(compose_preview(capture_mouth_frames(app, window)), output)
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
