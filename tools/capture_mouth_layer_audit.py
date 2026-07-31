from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow


POSES = (
    ("cheek", "", QRect(145, 140, 145, 125)),
    ("lean", "_lean", QRect(137, 140, 145, 125)),
    ("front", "_front", QRect(174, 140, 145, 125)),
)


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.bubble.hide()
        isolate_face = os.getenv("AUDIT_ALL_PHYSICS", "0") != "1"
        for timer in window.findChildren(QTimer):
            timer.stop()
        if isolate_face:
            for overlay in (
                window.sleeve_left_overlay,
                window.sleeve_right_overlay,
                window.hair_left_overlay,
                window.hair_right_overlay,
                window.physics_overlay,
            ):
                overlay.hide()

        all_rows: list[tuple[str, list[QImage]]] = []
        for pose, suffix, crop in POSES:
            window.state = "speaking"
            window.idle_pose = pose
            window.speech_pose_suffix = suffix
            window.speech_closed_expression = f"idle{suffix}"
            window.speech_mid_expression = f"mouth_mid{suffix}"
            window.speech_open_expression = f"speaking{suffix}"
            window.speech_gesture_expression = None
            window._start_mouth_animation(audio_driven=True)
            frames: list[QImage] = []
            cues = (
                ("CLOSED", 0.0),
                ("A", 0.62),
                ("A", 0.62),
                ("I", 0.55),
                ("I", 0.55),
                ("O", 0.68),
                ("O", 0.68),
                ("CLOSED", 0.0),
                ("CLOSED", 0.0),
                ("CLOSED", 0.0),
            )
            for vowel, level in cues:
                window._audio_viseme_cue(level, vowel)
                QTest.qWait(24)
                if window.mouth_visual_timer.isActive():
                    window._render_audio_mouth_transition()
                window._render_attention_layers(force=True)
                window._attention_tick()
                if isolate_face:
                    for overlay in (
                        window.sleeve_left_overlay,
                        window.sleeve_right_overlay,
                        window.hair_left_overlay,
                        window.hair_right_overlay,
                        window.physics_overlay,
                    ):
                        overlay.hide()
                app.processEvents()
                frame_rect = crop.translated(
                    window.character.x(),
                    window.character.y(),
                )
                captured = window.grab()
                ratio = captured.devicePixelRatio()
                physical_rect = QRect(
                    round(frame_rect.x() * ratio),
                    round(frame_rect.y() * ratio),
                    round(frame_rect.width() * ratio),
                    round(frame_rect.height() * ratio),
                )
                frames.append(
                    captured.toImage()
                    .copy(physical_rect)
                    .scaled(
                        QSize(232, 200),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            window._stop_mouth_animation()
            all_rows.append((pose, frames))

        cell_width, cell_height = 232, 200
        title_height, margin = 25, 8
        columns = 5
        canvas = QImage(
            columns * cell_width + (columns + 1) * margin,
            len(all_rows) * 2 * (cell_height + title_height + margin) + margin,
            QImage.Format_ARGB32,
        )
        canvas.fill(QColor("#0d2130"))
        painter = QPainter(canvas)
        painter.setFont(QFont("Arial", 10))
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for pose_index, (pose, frames) in enumerate(all_rows):
            for index, frame in enumerate(frames):
                local_row, column = divmod(index, columns)
                row = pose_index * 2 + local_row
                x = margin + column * (cell_width + margin)
                y = margin + row * (cell_height + title_height + margin)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(
                    QRect(x, y, cell_width, title_height),
                    Qt.AlignCenter,
                    f"{pose} {index * 24:03d} ms",
                )
                painter.drawImage(x, y + title_height, frame)
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not canvas.save(str(output)):
            raise RuntimeError(f"Could not save {output}")
        window.close()
        app.processEvents()


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "tmp" / "mouth-layer-audit.png"
    )
    render(target)
    print(target)
