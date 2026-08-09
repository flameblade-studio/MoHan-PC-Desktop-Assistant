from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import Qt, QTimer
lazy from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from app import (
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_VISEME_FRAMES,
    CompanionWindow,
)

LABELS = ("CLOSED", "CONS", "A", "I", "U", "E", "O", "BLINK+E")
CELL_WIDTH = 170
CELL_HEIGHT = 180
HEADER_HEIGHT = 42


def _prepare_window() -> CompanionWindow:
    window = CompanionWindow(startup_speech=False)
    for timer in window.findChildren(QTimer):
        timer.stop()
    return window


def _create_sheet(expression_count: int) -> QImage:
    sheet = QImage(
        CELL_WIDTH * len(LABELS),
        HEADER_HEIGHT + CELL_HEIGHT * expression_count,
        QImage.Format_ARGB32,
    )
    sheet.fill(QColor("#0d2130"))
    return sheet


def _draw_headers(painter: QPainter) -> None:
    for column, label in enumerate(LABELS):
        painter.drawText(
            column * CELL_WIDTH,
            0,
            CELL_WIDTH,
            HEADER_HEIGHT,
            Qt.AlignCenter,
            label,
        )


def _configure_speech(window: CompanionWindow, expression: str) -> None:
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_pose_suffix = window._pose_suffix(
        EXPRESSION_POSES[expression]
    )
    window.speech_closed_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window.speech_gesture_expression = expression


def _rendered_visemes(
    window: CompanionWindow,
    expression: str,
) -> list[QPixmap]:
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    visemes = EXPRESSION_VISEME_FRAMES[expression]
    rendered = [
        QPixmap(window.expression_pixmaps[expression]),
        window._mouth_aperture_pixmap(frames["mid"], 0.12),
        *(
            window._mouth_aperture_pixmap(visemes[vowel], 0.90)
            for vowel in ("A", "I", "U", "E", "O")
        ),
    ]
    rendered.append(window._blink_composite(rendered[-2], expression))
    return rendered


def _draw_preview(
    painter: QPainter,
    pixmap: QPixmap,
    row: int,
    column: int,
) -> None:
    preview = pixmap.scaled(
        150,
        150,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    x = column * CELL_WIDTH + (CELL_WIDTH - preview.width()) // 2
    y = (
        HEADER_HEIGHT
        + row * CELL_HEIGHT
        + (CELL_HEIGHT - preview.height()) // 2
    )
    painter.drawPixmap(x, y, preview)


def _draw_viseme_row(
    painter: QPainter,
    window: CompanionWindow,
    row: int,
    expression: str,
) -> None:
    _configure_speech(window, expression)
    for column, pixmap in enumerate(_rendered_visemes(window, expression)):
        _draw_preview(painter, pixmap, row, column)
    painter.setPen(QColor("#8fc9e0"))
    painter.drawText(6, HEADER_HEIGHT + row * CELL_HEIGHT + 18, expression)
    painter.setPen(QColor("#e5f2f7"))


def _render_sheet(
    window: CompanionWindow,
    expressions: tuple[str, ...],
) -> QImage:
    sheet = _create_sheet(len(expressions))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setFont(QFont("Segoe UI", 10))
    painter.setPen(QColor("#e5f2f7"))
    _draw_headers(painter)
    for row, expression in enumerate(expressions):
        _draw_viseme_row(painter, window, row, expression)
    painter.end()
    return sheet


def run(output: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = _prepare_window()
        sheet = _render_sheet(window, tuple(EXPRESSION_POSES))
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
