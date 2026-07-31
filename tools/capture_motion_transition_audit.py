from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow, STYLE
from db import StudioDB


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
            window.grab()
            .toImage()
            .convertToFormat(QImage.Format_ARGB32)
            .copy(QRect(0, window.character_base_y, window.width(), 465))
        )
    return frames


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = (
            Path(temp_dir)
            / "YanJianStudio"
            / "MoHan"
            / "mohan.db"
        )
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

        frames = gesture_frames + pose_frames
        columns = 5
        rows = 4
        cell_width = window.width()
        cell_height = 465
        label_height = 28
        canvas = QImage(
            columns * cell_width,
            rows * (cell_height + label_height),
            QImage.Format_ARGB32,
        )
        canvas.fill(QColor("#122330"))
        painter = QPainter(canvas)
        painter.setFont(QFont("Microsoft JhengHei UI", 11))
        for index, frame in enumerate(frames):
            column = index % columns
            row = index // columns
            x = column * cell_width
            y = row * (cell_height + label_height)
            painter.drawImage(x, y, frame)
            painter.setPen(QColor("#e7f6ff"))
            phase = "gesture" if index < 10 else "pose"
            number = index + 1 if index < 10 else index - 9
            painter.drawText(
                QRect(x, y + cell_height, cell_width, label_height),
                Qt.AlignCenter,
                f"{phase} {number:02d}",
            )
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not canvas.save(str(output), "PNG"):
            raise RuntimeError(f"Failed to save {output}")
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
