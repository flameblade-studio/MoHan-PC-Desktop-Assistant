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

lazy from companion_window import CompanionWindow
lazy from infrastructure.app_resources import STYLE


def main() -> int:
    output = Path(sys.argv[1])
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        app.setStyleSheet(STYLE)
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        startup = window.grab().toImage().convertToFormat(
            QImage.Format_ARGB32
        )
        canvas = QImage(1000, 760, QImage.Format_ARGB32)
        canvas.fill(QColor("#101a25"))
        painter = QPainter(canvas)
        painter.fillRect(QRect(20, 60, 470, 680), QColor("#f3eee6"))
        painter.fillRect(QRect(510, 60, 470, 680), QColor("#16212d"))
        painter.drawImage(20, 60, startup)
        painter.drawImage(510, 60, startup)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft JhengHei UI", 15))
        painter.drawText(QRect(20, 12, 470, 38), Qt.AlignCenter, "亮色桌布")
        painter.drawText(QRect(510, 12, 470, 38), Qt.AlignCenter, "深色桌布")
        painter.end()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not canvas.save(str(output), "PNG"):
            raise RuntimeError(f"Failed to save preview: {output}")
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
