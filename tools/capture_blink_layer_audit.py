from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from app import CompanionWindow


FACE_RECTS = {
    "cheek": QRect(120, 100, 170, 155),
    "lean": QRect(112, 100, 170, 155),
    "front": QRect(146, 96, 170, 160),
}


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.bubble.hide()
        for timer in window.findChildren(QTimer):
            timer.stop()
        window.physics_features["physics_face_parallax"] = True
        window.physics_features["physics_eye_tracking"] = True
        window.gaze_x = 0.68
        window.gaze_y = -0.34
        isolate_face = os.getenv("AUDIT_ALL_PHYSICS", "0") != "1"
        if isolate_face:
            # Isolate the face/eye composite. Hair, sleeve and ornament
            # physics have their own audits.
            for overlay in (
                window.sleeve_left_overlay,
                window.sleeve_right_overlay,
                window.hair_left_overlay,
                window.hair_right_overlay,
                window.physics_overlay,
            ):
                overlay.hide()

        rows: list[tuple[str, QImage, QImage]] = []
        for pose, expression in (
            ("cheek", "idle"),
            ("lean", "idle_lean"),
            ("front", "idle_front"),
        ):
            window.state = "idle"
            window.idle_pose = pose
            window.idle_blinking = False
            window.speech_blinking = False
            window._set_expression(expression, fade=False)
            if isolate_face:
                for overlay in (
                    window.sleeve_left_overlay,
                    window.sleeve_right_overlay,
                    window.hair_left_overlay,
                    window.hair_right_overlay,
                    window.physics_overlay,
                ):
                    overlay.hide()
            window._render_attention_layers(force=True)
            window._attention_tick()
            app.processEvents()
            open_frame = window.grab().toImage()
            window._blink()
            app.processEvents()
            blink_frame = window.grab().toImage()
            rows.append((pose, open_frame, blink_frame))
            window._finish_blink(expression, window.blink_generation)

        cell_width, cell_height = 390, 360
        sheet = QImage(
            cell_width * 2,
            cell_height * len(rows),
            QImage.Format_ARGB32,
        )
        sheet.fill(QColor("#0d2130"))
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setFont(QFont("Microsoft JhengHei UI", 14))
        painter.setPen(QColor("#e7f4f8"))
        for row, (pose, open_frame, blink_frame) in enumerate(rows):
            face_rect = FACE_RECTS[pose].translated(
                window.character_base_x,
                window.character_base_y,
            )
            for column, (label, frame) in enumerate(
                (("睜眼", open_frame), ("雙眼眨眼", blink_frame))
            ):
                face = frame.copy(face_rect).scaled(
                    350,
                    300,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                x = column * cell_width + 20
                y = row * cell_height
                painter.drawImage(x, y, face)
                painter.drawText(
                    QRect(column * cell_width, y + 305, cell_width, 40),
                    Qt.AlignCenter,
                    f"{pose}｜{label}",
                )
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not sheet.save(str(output)):
            raise RuntimeError(f"Could not save {output}")
        window.close()
        app.processEvents()


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "tmp" / "blink-layer-audit.png"
    )
    render(target)
    print(target)
