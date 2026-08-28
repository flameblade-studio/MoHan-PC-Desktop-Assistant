from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QFont, QImage, QPainter
lazy from PySide6.QtWidgets import QApplication

lazy from presentation.companion_window import CompanionWindow
lazy from infrastructure.app_resources import STYLE


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
        window.gaze_x = 0.72
        window.gaze_y = -0.38
        frames = []
        expressions = (
            "idle",
            "mouth_mid",
            "speaking",
            "mouth_i",
            "mouth_o",
            "mouth_round",
        )
        for expression in expressions:
            window._set_expression(expression, fade=False)
            window._render_attention_layers(force=True)
            window._attention_tick()
            app.processEvents()
            frames.append(
                window.grab()
                .toImage()
                .convertToFormat(QImage.Format_ARGB32)
                .copy(QRect(120, 330, 230, 220))
            )

        cell_width, cell_height = 230, 220
        title_height, margin = 36, 14
        canvas = QImage(
            cell_width * 3 + margin * 4,
            (cell_height + title_height) * 2 + margin * 3,
            QImage.Format_ARGB32,
        )
        canvas.fill(QColor("#253746"))
        painter = QPainter(canvas)
        painter.setFont(QFont("Microsoft JhengHei UI", 12))
        for index, (expression, frame) in enumerate(zip(expressions, frames, strict=False)):
            row, column = divmod(index, 3)
            x = margin + column * (cell_width + margin)
            y = margin + row * (cell_height + title_height + margin)
            painter.setPen(QColor("#f2f7fa"))
            painter.drawText(
                QRect(x, y, cell_width, title_height),
                Qt.AlignCenter,
                expression,
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
