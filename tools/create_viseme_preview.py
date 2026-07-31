from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QPainter,
)


def blended_mid(closed: QImage, opened: QImage) -> QImage:
    result = QImage(closed.size(), QImage.Format_ARGB32)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.drawImage(0, 0, closed)
    painter.setOpacity(0.48)
    painter.drawImage(0, 0, opened)
    painter.end()
    return result


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    font_id = QFontDatabase.addApplicationFont(
        r"C:\Windows\Fonts\NotoSansTC-VF.ttf"
    )
    font_family = (
        QFontDatabase.applicationFontFamilies(font_id)[0]
        if font_id >= 0
        else "Microsoft JhengHei"
    )
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    columns = (
        "閉嘴",
        "A 開口",
        "I 展唇",
        "U 小圓唇",
        "E 半開",
        "O 大圓唇",
    )
    rows = (
        (
            "托腮",
            "idle.png",
            "speaking.png",
            "viseme_round.png",
            "viseme_i.png",
            "viseme_o.png",
            None,
        ),
        (
            "倚靠",
            "idle_lean.png",
            "speaking_lean.png",
            "viseme_round_lean.png",
            "viseme_i_lean.png",
            "viseme_o_lean.png",
            None,
        ),
        (
            "正面",
            "idle_front.png",
            "viseme_wide_front.png",
            "viseme_round_front.png",
            "viseme_i_front.png",
            "viseme_o_front.png",
            "viseme_mid_front.png",
        ),
    )
    width, height = 2140, 1120
    canvas = QImage(width, height, QImage.Format_ARGB32)
    canvas.fill(QColor("#0c1b27"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setPen(QColor("#eaf5f8"))
    painter.setFont(QFont(font_family, 27, QFont.Bold))
    painter.drawText(QRect(0, 22, width, 50), Qt.AlignCenter, "墨寒｜電影級語音嘴型開發預覽")
    painter.setFont(QFont(font_family, 17))
    painter.setPen(QColor("#8fc9e0"))
    for index, label in enumerate(columns):
        painter.drawText(
            QRect(125 + index * 330, 82, 310, 38),
            Qt.AlignCenter,
            label,
        )

    for row_index, row in enumerate(rows):
        (
            label,
            closed_name,
            open_name,
            round_name,
            i_name,
            o_name,
            mid_name,
        ) = row
        top = 130 + row_index * 320
        painter.setPen(QColor("#f1b4dc"))
        painter.setFont(QFont(font_family, 20, QFont.Bold))
        painter.drawText(QRect(5, top + 120, 115, 45), Qt.AlignCenter, label)
        closed = QImage(str(source / closed_name))
        opened = QImage(str(source / open_name))
        images = (
            closed,
            opened,
            QImage(str(source / i_name)),
            QImage(str(source / round_name)),
            QImage(str(source / mid_name))
            if mid_name
            else blended_mid(closed, opened),
            QImage(str(source / o_name)),
        )
        for column_index, image in enumerate(images):
            target = QRect(125 + column_index * 330, top, 310, 310)
            painter.drawImage(
                target,
                image,
                image.rect(),
                Qt.AutoColor,
            )
        painter.setPen(QColor("#24495d"))
        painter.drawLine(120, top + 315, width - 30, top + 315)
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"無法輸出預覽：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
