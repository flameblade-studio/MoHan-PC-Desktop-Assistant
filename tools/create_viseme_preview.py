from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
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

CANVAS_WIDTH = 2140
CANVAS_HEIGHT = 1120
COLUMN_LABELS = (
    "閉嘴",
    "A 開口",
    "I 展唇",
    "U 小圓唇",
    "E 半開",
    "O 大圓唇",
)


@dataclass(frozen=True, slots=True)
class VisemeRow:
    label: str
    closed_name: str
    open_name: str
    round_name: str
    i_name: str
    o_name: str
    mid_name: str | None = None


def blended_mid(closed: QImage, opened: QImage) -> QImage:
    result = QImage(closed.size(), QImage.Format_ARGB32)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.drawImage(0, 0, closed)
    painter.setOpacity(0.48)
    painter.drawImage(0, 0, opened)
    painter.end()
    return result


def _font_family() -> str:
    font_id = QFontDatabase.addApplicationFont(
        r"C:\Windows\Fonts\NotoSansTC-VF.ttf"
    )
    if font_id < 0:
        return "Microsoft JhengHei"
    return QFontDatabase.applicationFontFamilies(font_id)[0]


def _rows() -> tuple[VisemeRow, ...]:
    return (
        VisemeRow(
            "托腮",
            "idle.png",
            "speaking.png",
            "viseme_round.png",
            "viseme_i.png",
            "viseme_o.png",
        ),
        VisemeRow(
            "倚靠",
            "idle_lean.png",
            "speaking_lean.png",
            "viseme_round_lean.png",
            "viseme_i_lean.png",
            "viseme_o_lean.png",
        ),
        VisemeRow(
            "正面",
            "idle_front.png",
            "viseme_wide_front.png",
            "viseme_round_front.png",
            "viseme_i_front.png",
            "viseme_o_front.png",
            "viseme_mid_front.png",
        ),
    )


def _row_images(source: Path, row: VisemeRow) -> tuple[QImage, ...]:
    closed = QImage(str(source / row.closed_name))
    opened = QImage(str(source / row.open_name))
    middle = (
        QImage(str(source / row.mid_name))
        if row.mid_name
        else blended_mid(closed, opened)
    )
    return (
        closed,
        opened,
        QImage(str(source / row.i_name)),
        QImage(str(source / row.round_name)),
        middle,
        QImage(str(source / row.o_name)),
    )


def _draw_headers(painter: QPainter, family: str) -> None:
    painter.setPen(QColor("#eaf5f8"))
    painter.setFont(QFont(family, 27, QFont.Bold))
    painter.drawText(
        QRect(0, 22, CANVAS_WIDTH, 50),
        Qt.AlignCenter,
        "墨寒｜電影級語音嘴型開發預覽",
    )
    painter.setFont(QFont(family, 17))
    painter.setPen(QColor("#8fc9e0"))
    for index, label in enumerate(COLUMN_LABELS):
        painter.drawText(
            QRect(125 + index * 330, 82, 310, 38),
            Qt.AlignCenter,
            label,
        )


def _draw_row(
    painter: QPainter,
    source: Path,
    family: str,
    row: VisemeRow,
    row_index: int,
) -> None:
    top = 130 + row_index * 320
    painter.setPen(QColor("#f1b4dc"))
    painter.setFont(QFont(family, 20, QFont.Bold))
    painter.drawText(QRect(5, top + 120, 115, 45), Qt.AlignCenter, row.label)
    for column_index, image in enumerate(_row_images(source, row)):
        painter.drawImage(
            QRect(125 + column_index * 330, top, 310, 310),
            image,
            image.rect(),
            Qt.AutoColor,
        )
    painter.setPen(QColor("#24495d"))
    painter.drawLine(120, top + 315, CANVAS_WIDTH - 30, top + 315)


def _render_preview(source: Path, family: str) -> QImage:
    canvas = QImage(CANVAS_WIDTH, CANVAS_HEIGHT, QImage.Format_ARGB32)
    canvas.fill(QColor("#0c1b27"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    _draw_headers(painter, family)
    for row_index, row in enumerate(_rows()):
        _draw_row(painter, source, family, row, row_index)
    painter.end()
    return canvas


def main() -> int:
    _app = QGuiApplication.instance() or QGuiApplication([])
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    canvas = _render_preview(source, _font_family())
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"無法輸出預覽：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
