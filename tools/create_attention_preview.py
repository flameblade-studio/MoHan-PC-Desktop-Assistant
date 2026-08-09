from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QPainter,
)


def load_image(path: Path) -> QImage:
    return QImage(str(path)).convertToFormat(QImage.Format_ARGB32)


def attention_frame(
    base: QImage,
    face: QImage,
    eyes: QImage,
    gaze_x: float,
    gaze_y: float,
) -> QImage:
    frame = QImage(base.size(), QImage.Format_ARGB32)
    frame.fill(0)
    painter = QPainter(frame)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    body_x = round(gaze_x * 4.2)
    painter.drawImage(body_x, 0, base)
    face_x = body_x + round(gaze_x * 2.4)
    face_y = round(gaze_y * 1.5)
    painter.drawImage(face_x, face_y, face)
    painter.drawImage(
        face_x + round(gaze_x * 3.6),
        face_y + round(gaze_y * 2.3),
        eyes,
    )
    painter.end()
    return frame


def main() -> int:
    _app = QGuiApplication.instance() or QGuiApplication([])
    font_id = QFontDatabase.addApplicationFont(
        r"C:\Windows\Fonts\NotoSansTC-VF.ttf"
    )
    family = (
        QFontDatabase.applicationFontFamilies(font_id)[0]
        if font_id >= 0
        else "Microsoft JhengHei"
    )
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    rows = (
        ("托腮", "idle.png", ""),
        ("倚靠", "idle_lean.png", "_lean"),
        ("正視", "idle_front.png", "_front"),
    )
    gazes = ((-1.0, -0.25), (0.0, 0.0), (1.0, 0.25))
    labels = ("注視左側滑鼠", "自然正視", "注視右側滑鼠")
    canvas = QImage(1500, 1150, QImage.Format_ARGB32)
    canvas.fill(QColor("#0c1b27"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setFont(QFont(family, 26, QFont.Bold))
    painter.setPen(QColor("#eaf5f8"))
    painter.drawText(
        QRect(0, 22, canvas.width(), 50),
        Qt.AlignCenter,
        "墨寒・眼球追蹤、臉部視差與身體微轉向",
    )
    painter.setFont(QFont(family, 17))
    painter.setPen(QColor("#8fc9e0"))
    for index, label in enumerate(labels):
        painter.drawText(
            QRect(155 + index * 440, 82, 410, 35),
            Qt.AlignCenter,
            label,
        )
    for row_index, (row_label, base_name, suffix) in enumerate(rows):
        top = 125 + row_index * 330
        painter.setFont(QFont(family, 20, QFont.Bold))
        painter.setPen(QColor("#f1b4dc"))
        painter.drawText(
            QRect(10, top + 130, 130, 45),
            Qt.AlignCenter,
            row_label,
        )
        base = load_image(source / base_name)
        face = load_image(source / f"physics_face{suffix}.png")
        eyes = load_image(source / f"physics_eyes{suffix}.png")
        for column_index, gaze in enumerate(gazes):
            frame = attention_frame(base, face, eyes, *gaze)
            painter.drawImage(
                QRect(155 + column_index * 440, top, 410, 310),
                frame,
                frame.rect(),
            )
        painter.setPen(QColor("#24495d"))
        painter.drawLine(140, top + 315, canvas.width() - 30, top + 315)
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save preview: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
