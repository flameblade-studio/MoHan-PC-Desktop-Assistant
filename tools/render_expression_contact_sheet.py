from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, Qt, QTimer
lazy from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
)
lazy from presentation.companion_window import CompanionWindow

EXPRESSION_COLUMNS = 4
EXPRESSION_CARD_WIDTH = 300
EXPRESSION_CARD_HEIGHT = 410
SPEECH_CELL_WIDTH = 300
SPEECH_ROW_HEIGHT = 340


def _prepare_window(app: QApplication) -> CompanionWindow:
    window = CompanionWindow(startup_speech=False)
    window.show()
    window.bubble.hide()
    for timer in window.findChildren(QTimer):
        timer.stop()
    app.processEvents()
    return window


def _available_expressions(window: CompanionWindow) -> tuple[str, ...]:
    return tuple(
        expression
        for expression in EXPRESSION_POSES
        if expression in window.expression_pixmaps
    )


def _configure_painter(
    painter: QPainter,
    font_name: str,
    font_size: int,
) -> None:
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setFont(QFont(font_name, font_size))
    painter.setPen(QColor("#d8edf5"))


def _draw_expression_card(
    painter: QPainter,
    window: CompanionWindow,
    app: QApplication,
    index: int,
    expression: str,
) -> None:
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
    x = (index % EXPRESSION_COLUMNS) * EXPRESSION_CARD_WIDTH
    y = (index // EXPRESSION_COLUMNS) * EXPRESSION_CARD_HEIGHT
    painter.drawPixmap(x + 10, y, frame)
    painter.drawText(
        QRect(x + 8, y + 374, EXPRESSION_CARD_WIDTH - 16, 30),
        Qt.AlignCenter,
        expression,
    )


def _render_expression_sheet(
    window: CompanionWindow,
    app: QApplication,
    expressions: tuple[str, ...],
) -> QPixmap:
    rows = (len(expressions) + EXPRESSION_COLUMNS - 1) // EXPRESSION_COLUMNS
    sheet = QPixmap(
        EXPRESSION_COLUMNS * EXPRESSION_CARD_WIDTH,
        rows * EXPRESSION_CARD_HEIGHT,
    )
    sheet.fill(QColor("#0d1c27"))
    painter = QPainter(sheet)
    _configure_painter(painter, "Microsoft JhengHei", 14)
    for index, expression in enumerate(expressions):
        _draw_expression_card(painter, window, app, index, expression)
    painter.end()
    return sheet


def _speech_frames(
    window: CompanionWindow,
    expression: str,
) -> tuple[tuple[str, QPixmap], ...]:
    pose = EXPRESSION_POSES[expression]
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_closed_expression = expression
    window.speech_pose_suffix = window._pose_suffix(pose)
    window.speech_gesture_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    base = window.expression_pixmaps[expression]
    middle = window._mouth_aperture_pixmap(window.speech_mid_expression, 0.48)
    opened = window._mouth_aperture_pixmap(window.speech_open_expression, 0.9)
    blink = window._blink_composite(opened, expression)
    return (
        ("closed", base),
        ("mid", middle),
        ("open", opened),
        ("open+blink", blink),
    )


def _draw_speech_row(
    painter: QPainter,
    window: CompanionWindow,
    row: int,
    expression: str,
) -> None:
    for column, (label, frame) in enumerate(
        _speech_frames(window, expression)
    ):
        preview = frame.scaled(
            280,
            280,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        x = column * SPEECH_CELL_WIDTH
        y = row * SPEECH_ROW_HEIGHT
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


def _render_speech_sheet(
    window: CompanionWindow,
    expressions: tuple[str, ...],
) -> QPixmap:
    sheet = QPixmap(
        4 * SPEECH_CELL_WIDTH,
        len(expressions) * SPEECH_ROW_HEIGHT,
    )
    sheet.fill(QColor("#0d1c27"))
    painter = QPainter(sheet)
    _configure_painter(painter, "Arial", 12)
    for row, expression in enumerate(expressions):
        _draw_speech_row(painter, window, row, expression)
    painter.end()
    return sheet


def render(output: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = _prepare_window(app)
        expressions = _available_expressions(window)
        sheet = _render_expression_sheet(window, app, expressions)
        output.parent.mkdir(parents=True, exist_ok=True)
        assert sheet.save(str(output))
        speech_sheet = _render_speech_sheet(window, expressions)
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
