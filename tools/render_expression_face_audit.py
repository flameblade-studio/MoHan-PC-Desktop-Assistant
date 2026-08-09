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

lazy from app import (
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    CompanionWindow,
)

CELL_WIDTH = 390
CELL_HEIGHT = 450
FACE_RECTS = {
    "cheek": QRect(118, 82, 185, 190),
    "lean": QRect(112, 82, 185, 190),
    "front": QRect(142, 78, 185, 195),
}


def _prepare_window() -> CompanionWindow:
    window = CompanionWindow(startup_speech=False)
    for timer in window.findChildren(QTimer):
        timer.stop()
    return window


def _available_expressions(window: CompanionWindow) -> tuple[str, ...]:
    return tuple(
        expression
        for expression in EXPRESSION_POSES
        if expression in window.expression_pixmaps
    )


def _expression_frames(
    window: CompanionWindow,
    expression: str,
) -> tuple[str, tuple[tuple[str, QPixmap], ...]]:
    pose = EXPRESSION_POSES[expression]
    frames = EXPRESSION_SPEECH_FRAMES[expression]
    window.state = "speaking"
    window.speech_closed_expression = expression
    window.speech_pose_suffix = window._pose_suffix(pose)
    window.speech_gesture_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    closed = window.expression_pixmaps[expression]
    middle = window._mouth_aperture_pixmap(window.speech_mid_expression, 0.48)
    opened = window._mouth_aperture_pixmap(window.speech_open_expression, 0.90)
    blink = window._blink_composite(opened, expression)
    return pose, (
        ("閉嘴", closed),
        ("半開", middle),
        ("張嘴", opened),
        ("張嘴＋眨眼", blink),
    )


def _draw_face_row(
    painter: QPainter,
    window: CompanionWindow,
    row: int,
    expression: str,
) -> None:
    pose, frames = _expression_frames(window, expression)
    for column, (label, frame) in enumerate(frames):
        face = frame.copy(FACE_RECTS[pose]).scaled(
            360,
            380,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        x = column * CELL_WIDTH + 15
        y = row * CELL_HEIGHT
        painter.drawPixmap(x, y, face)
        painter.drawText(
            QRect(column * CELL_WIDTH, y + 382, CELL_WIDTH, 26),
            Qt.AlignCenter,
            label,
        )
        painter.drawText(
            QRect(column * CELL_WIDTH, y + 410, CELL_WIDTH, 28),
            Qt.AlignCenter,
            expression,
        )


def _render_sheet(
    window: CompanionWindow,
    expressions: tuple[str, ...],
) -> QPixmap:
    sheet = QPixmap(CELL_WIDTH * 4, CELL_HEIGHT * len(expressions))
    sheet.fill(QColor("#0d1c27"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setFont(QFont("Microsoft JhengHei", 13))
    painter.setPen(QColor("#d8edf5"))
    for row, expression in enumerate(expressions):
        _draw_face_row(painter, window, row, expression)
    painter.end()
    return sheet


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = _prepare_window()
        sheet = _render_sheet(window, _available_expressions(window))
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
