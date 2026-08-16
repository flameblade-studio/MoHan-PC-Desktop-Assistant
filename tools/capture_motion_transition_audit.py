from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QFont, QImage, QPainter
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow
lazy from infrastructure.app_resources import STYLE
lazy from infrastructure.db import StudioDB

FRAME_COLUMNS = 5
FRAME_ROWS = 4
FRAME_HEIGHT = 465
LABEL_HEIGHT = 28


def capture_frames(
    app: QApplication,
    window: CompanionWindow,
    count: int,
    interval_ms: int,
) -> list[QImage]:
    frames = []
    for _ in range(count):
        QTest.qWait(interval_ms)
        app.processEvents()
        body_position = window.character.pos()
        assert all(
            layer.pos() == body_position
            for layer in (
                window.expression_overlay,
                window.sleeve_left_overlay,
                window.sleeve_right_overlay,
                window.hair_left_overlay,
                window.hair_right_overlay,
                window.physics_overlay,
                window.face_overlay,
                window.eye_overlay,
            )
        )
        frames.append(
            window
            .grab()
            .toImage()
            .convertToFormat(QImage.Format_ARGB32)
            .copy(QRect(0, window.character_base_y, window.width(), 465))
        )
    return frames


def create_audit_window(temp_dir: str) -> tuple[QApplication, CompanionWindow]:
    os.environ["LOCALAPPDATA"] = temp_dir
    db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
    db = StudioDB(db_path)
    db.set_setting("tts_enabled", False)
    db.close()

    app = QApplication([])
    app.setStyleSheet(STYLE)
    window = CompanionWindow(startup_speech=False)
    window.show()
    window.bubble.hide()
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=False)
    app.processEvents()
    return app, window


def capture_transition_frames(
    app: QApplication,
    window: CompanionWindow,
) -> list[QImage]:
    window.set_state(
        "thinking_front",
        source="user_direct",
        force=True,
    )
    gesture_frames = capture_frames(app, window, 10, 55)
    window.set_state("idle", force=True)
    window.idle_pose = "cheek"
    window._set_expression("idle", fade=True)
    pose_frames = capture_frames(app, window, 10, 25)
    return gesture_frames + pose_frames


def draw_labeled_frames(
    painter: QPainter,
    frames: list[QImage],
    cell_width: int,
) -> None:
    for index, frame in enumerate(frames):
        column = index % FRAME_COLUMNS
        row = index // FRAME_COLUMNS
        x = column * cell_width
        y = row * (FRAME_HEIGHT + LABEL_HEIGHT)
        painter.drawImage(x, y, frame)
        painter.setPen(QColor("#e7f6ff"))
        phase = "gesture" if index < 10 else "pose"
        number = index + 1 if index < 10 else index - 9
        painter.drawText(
            QRect(x, y + FRAME_HEIGHT, cell_width, LABEL_HEIGHT),
            Qt.AlignCenter,
            f"{phase} {number:02d}",
        )


def compose_audit_canvas(window: CompanionWindow, frames: list[QImage]) -> QImage:
    cell_width = window.width()
    canvas = QImage(
        FRAME_COLUMNS * cell_width,
        FRAME_ROWS * (FRAME_HEIGHT + LABEL_HEIGHT),
        QImage.Format_ARGB32,
    )
    canvas.fill(QColor("#122330"))
    painter = QPainter(canvas)
    painter.setFont(QFont("Microsoft JhengHei UI", 11))
    draw_labeled_frames(painter, frames, cell_width)
    painter.end()
    return canvas


def save_audit_canvas(canvas: QImage, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save {output}")


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        app, window = create_audit_window(temp_dir)
        frames = capture_transition_frames(app, window)
        save_audit_canvas(compose_audit_canvas(window, frames), output)
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
