from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QPainter,
)


def physics_frame(
    base: QImage,
    ornament: QImage,
    ornament_anchor: QPoint,
    ornament_angle: float,
    left_hair: QImage,
    right_hair: QImage,
    left_hair_anchor: QPoint,
    right_hair_anchor: QPoint,
    left_hair_angle: float,
    right_hair_angle: float,
    left_sleeve: QImage,
    right_sleeve: QImage,
    left_sleeve_anchor: QPoint,
    right_sleeve_anchor: QPoint,
    left_sleeve_angle: float,
    right_sleeve_angle: float,
    breath_lift: float,
) -> QImage:
    cleaned = base.copy()
    painter = QPainter(cleaned)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    for layer in (
        ornament,
        left_hair,
        right_hair,
        left_sleeve,
        right_sleeve,
    ):
        painter.drawImage(0, 0, layer)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    for layer, anchor, angle in (
        (left_sleeve, left_sleeve_anchor, left_sleeve_angle),
        (right_sleeve, right_sleeve_anchor, right_sleeve_angle),
    ):
        painter.save()
        painter.translate(0.0, -breath_lift)
        painter.translate(anchor)
        painter.rotate(angle)
        painter.translate(-anchor)
        painter.drawImage(0, 0, layer)
        painter.restore()
    for layer, anchor, angle in (
        (left_hair, left_hair_anchor, left_hair_angle),
        (right_hair, right_hair_anchor, right_hair_angle),
    ):
        painter.save()
        painter.translate(anchor)
        painter.rotate(angle)
        painter.translate(-anchor)
        painter.drawImage(0, 0, layer)
        painter.restore()
    painter.translate(ornament_anchor)
    painter.rotate(ornament_angle)
    painter.translate(-ornament_anchor)
    painter.drawImage(0, 0, ornament)
    painter.end()
    return cleaned


def load_image(path: Path) -> QImage:
    return QImage(str(path)).convertToFormat(QImage.Format_ARGB32)


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
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
        (
            "托腮",
            "idle.png",
            "",
            QPoint(850, 260),
            QPoint(505, 480),
            QPoint(723, 450),
            QPoint(356, 682),
            QPoint(890, 645),
        ),
        (
            "倚靠",
            "idle_lean.png",
            "_lean",
            QPoint(825, 260),
            QPoint(477, 468),
            QPoint(685, 438),
            QPoint(350, 680),
            QPoint(878, 645),
        ),
        (
            "正視",
            "idle_front.png",
            "_front",
            QPoint(790, 194),
            QPoint(492, 460),
            QPoint(750, 452),
            QPoint(353, 682),
            QPoint(898, 682),
        ),
    )
    angles = (-2.2, 0.0, 2.2)
    labels = ("向左回彈", "自然呼吸", "向右回彈")
    canvas = QImage(1500, 1150, QImage.Format_ARGB32)
    canvas.fill(QColor("#0c1b27"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setFont(QFont(family, 26, QFont.Bold))
    painter.setPen(QColor("#eaf5f8"))
    painter.drawText(
        QRect(0, 22, canvas.width(), 50),
        Qt.AlignCenter,
        "墨寒 2.5D 衣袖、長髮、流蘇與呼吸物理",
    )
    painter.setFont(QFont(family, 17))
    painter.setPen(QColor("#8fc9e0"))
    for index, label in enumerate(labels):
        painter.drawText(
            QRect(155 + index * 440, 82, 410, 35),
            Qt.AlignCenter,
            label,
        )
    for row_index, row in enumerate(rows):
        (
            row_label,
            base_name,
            suffix,
            ornament_anchor,
            left_hair_anchor,
            right_hair_anchor,
            left_sleeve_anchor,
            right_sleeve_anchor,
        ) = row
        top = 125 + row_index * 330
        painter.setFont(QFont(family, 20, QFont.Bold))
        painter.setPen(QColor("#f1b4dc"))
        painter.drawText(
            QRect(10, top + 130, 130, 45),
            Qt.AlignCenter,
            row_label,
        )
        base = load_image(source / base_name)
        ornament = load_image(source / f"physics_ornament{suffix}.png")
        left_hair = load_image(source / f"physics_hair_left{suffix}.png")
        right_hair = load_image(source / f"physics_hair_right{suffix}.png")
        left_sleeve = load_image(
            source / f"physics_sleeve_left{suffix}.png"
        )
        right_sleeve = load_image(
            source / f"physics_sleeve_right{suffix}.png"
        )
        for column_index, angle in enumerate(angles):
            frame = physics_frame(
                base,
                ornament,
                ornament_anchor,
                angle,
                left_hair,
                right_hair,
                left_hair_anchor,
                right_hair_anchor,
                angle * 0.34,
                angle * -0.29,
                left_sleeve,
                right_sleeve,
                left_sleeve_anchor,
                right_sleeve_anchor,
                angle * 0.14,
                angle * -0.13,
                0.0 if column_index != 1 else 1.4,
            )
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
