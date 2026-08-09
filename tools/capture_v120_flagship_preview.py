from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter
lazy from PySide6.QtWidgets import QApplication

lazy from app import STYLE, CompanionWindow


def background(width: int, height: int, kind: str) -> QImage:
    image = QImage(width, height, QImage.Format_ARGB32)
    painter = QPainter(image)
    if kind == "light":
        painter.fillRect(image.rect(), QColor("#f2eee7"))
    elif kind == "dark":
        painter.fillRect(image.rect(), QColor("#101a25"))
    else:
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor("#6d1f47"))
        gradient.setColorAt(0.45, QColor("#176b78"))
        gradient.setColorAt(1.0, QColor("#d39d3c"))
        painter.fillRect(image.rect(), gradient)
    painter.end()
    return image


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        app.setStyleSheet(STYLE)
        window = CompanionWindow(startup_speech=False)
        window.show()
        window.bubble.hide()
        window.state = "idle"
        captures = []
        for pose, expression in (
            ("cheek", "idle"),
            ("lean", "idle_lean"),
            ("front", "idle_front"),
        ):
            window.idle_pose = pose
            window._set_expression(expression, fade=False)
            window.gaze_x = 0.92
            window.gaze_y = -0.65
            window.ornament_angle = 1.05
            window.hair_left_angle = 0.30
            window.hair_right_angle = -0.28
            window.sleeve_left_angle = 0.145
            window.sleeve_right_angle = -0.135
            window.current_breath = 0.92
            window._render_sleeve_layers(force=True)
            window._render_hair_layers(force=True)
            window._render_physics_layer(force=True)
            window._render_attention_layers(force=True)
            window._attention_tick()
            app.processEvents()
            captures.append(
                window.grab()
                .toImage()
                .convertToFormat(QImage.Format_ARGB32)
                .copy(QRect(0, window.character_base_y, 470, 465))
            )

        margin = 20
        label_height = 48
        cell_width = 470
        cell_height = 465
        canvas = QImage(
            cell_width * 3 + margin * 4,
            (cell_height + label_height) * 3 + margin * 4,
            QImage.Format_ARGB32,
        )
        canvas.fill(QColor("#263746"))
        painter = QPainter(canvas)
        backgrounds = (
            ("light", "淺色桌布"),
            ("dark", "深色桌布"),
            ("color", "彩色桌布"),
        )
        poses = ("托腮姿勢", "倚靠姿勢", "正面姿勢")
        for row, (pose_label, captured) in enumerate(zip(poses, captures)):
            for index, (kind, label) in enumerate(backgrounds):
                x = margin + index * (cell_width + margin)
                y = (
                    margin
                    + row * (cell_height + label_height + margin)
                    + label_height
                )
                painter.drawImage(
                    x, y, background(cell_width, cell_height, kind)
                )
                painter.drawImage(x, y, captured)
                painter.setPen(QColor("#f5fbff"))
                painter.setFont(QFont("Microsoft JhengHei UI", 15))
                painter.drawText(
                    QRect(x, y - label_height, cell_width, label_height),
                    Qt.AlignCenter,
                    f"{pose_label}｜{label}",
                )
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not canvas.save(str(output), "PNG"):
            raise RuntimeError(f"Failed to save preview: {output}")
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
