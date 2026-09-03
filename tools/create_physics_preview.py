from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtCore import QPoint, QRect, Qt
lazy from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QPainter,
)

CANVAS_WIDTH = 1500
CANVAS_HEIGHT = 1150
COLUMN_ANGLES = (-2.2, 0.0, 2.2)
COLUMN_LABELS = ("向左回彈", "自然呼吸", "向右回彈")


@dataclass(frozen=True, slots=True)
class LayerMotion:
    image: QImage
    anchor: QPoint
    angle: float


@dataclass(frozen=True, slots=True)
class PosePreviewSpec:
    label: str
    base_name: str
    suffix: str
    ornament_anchor: QPoint
    hair_anchors: tuple[QPoint, QPoint]
    sleeve_anchors: tuple[QPoint, QPoint]


@dataclass(frozen=True, slots=True)
class PoseLayers:
    base: QImage
    ornament: QImage
    hair: tuple[QImage, QImage]
    sleeves: tuple[QImage, QImage]


def _draw_rotated_layer(
    painter: QPainter,
    motion: LayerMotion,
    vertical_offset: float | None = None,
) -> None:
    painter.save()
    if vertical_offset is not None:
        painter.translate(0.0, -vertical_offset)
    painter.translate(motion.anchor)
    painter.rotate(motion.angle)
    painter.translate(-motion.anchor)
    painter.drawImage(0, 0, motion.image)
    painter.restore()


def physics_frame(
    base: QImage,
    ornament: LayerMotion,
    hair: tuple[LayerMotion, LayerMotion],
    sleeves: tuple[LayerMotion, LayerMotion],
    breath_lift: float,
) -> QImage:
    cleaned = base.copy()
    painter = QPainter(cleaned)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    for motion in (ornament, *hair, *sleeves):
        painter.drawImage(0, 0, motion.image)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    for motion in sleeves:
        _draw_rotated_layer(painter, motion, breath_lift)
    for motion in hair:
        _draw_rotated_layer(painter, motion)
    _draw_rotated_layer(painter, ornament)
    painter.end()
    return cleaned


def load_image(path: Path) -> QImage:
    return QImage(str(path)).convertToFormat(QImage.Format_ARGB32)


def _font_family() -> str:
    font_id = QFontDatabase.addApplicationFont(
        r"C:\Windows\Fonts\NotoSansTC-VF.ttf"
    )
    if font_id < 0:
        return "Microsoft JhengHei"
    return QFontDatabase.applicationFontFamilies(font_id)[0]


def _pose_specs() -> tuple[PosePreviewSpec, ...]:
    return (
        PosePreviewSpec(
            "托腮",
            "idle.png",
            "",
            QPoint(850, 260),
            (QPoint(505, 480), QPoint(723, 450)),
            (QPoint(356, 682), QPoint(890, 645)),
        ),
        PosePreviewSpec(
            "倚靠",
            "idle_lean.png",
            "_lean",
            QPoint(825, 260),
            (QPoint(477, 468), QPoint(685, 438)),
            (QPoint(350, 680), QPoint(878, 645)),
        ),
        PosePreviewSpec(
            "正視",
            "idle_front.png",
            "_front",
            QPoint(790, 194),
            (QPoint(492, 460), QPoint(750, 452)),
            (QPoint(353, 682), QPoint(898, 682)),
        ),
    )


def _load_pose_layers(source: Path, spec: PosePreviewSpec) -> PoseLayers:
    return PoseLayers(
        base=load_image(source / spec.base_name),
        ornament=load_image(source / f"v120_ornament{spec.suffix}.png"),
        hair=(
            load_image(source / f"v120_hair_left{spec.suffix}.png"),
            load_image(source / f"v120_hair_right{spec.suffix}.png"),
        ),
        sleeves=(
            load_image(source / f"v120_sleeve_left{spec.suffix}.png"),
            load_image(source / f"v120_sleeve_right{spec.suffix}.png"),
        ),
    )


def _frame_for_column(
    layers: PoseLayers,
    spec: PosePreviewSpec,
    angle: float,
    column_index: int,
) -> QImage:
    ornament = LayerMotion(layers.ornament, spec.ornament_anchor, angle)
    hair = (
        LayerMotion(layers.hair[0], spec.hair_anchors[0], angle * 0.34),
        LayerMotion(layers.hair[1], spec.hair_anchors[1], angle * -0.29),
    )
    sleeves = (
        LayerMotion(layers.sleeves[0], spec.sleeve_anchors[0], angle * 0.14),
        LayerMotion(layers.sleeves[1], spec.sleeve_anchors[1], angle * -0.13),
    )
    breath_lift = 1.4 if column_index == 1 else 0.0
    return physics_frame(layers.base, ornament, hair, sleeves, breath_lift)


def _draw_headers(painter: QPainter, family: str) -> None:
    painter.setFont(QFont(family, 26, QFont.Bold))
    painter.setPen(QColor("#eaf5f8"))
    painter.drawText(
        QRect(0, 22, CANVAS_WIDTH, 50),
        Qt.AlignCenter,
        "墨寒 2.5D 衣袖、長髮、流蘇與呼吸物理",
    )
    painter.setFont(QFont(family, 17))
    painter.setPen(QColor("#8fc9e0"))
    for index, label in enumerate(COLUMN_LABELS):
        painter.drawText(
            QRect(155 + index * 440, 82, 410, 35),
            Qt.AlignCenter,
            label,
        )


def _draw_pose_row(
    painter: QPainter,
    source: Path,
    family: str,
    spec: PosePreviewSpec,
    row_index: int,
) -> None:
    top = 125 + row_index * 330
    painter.setFont(QFont(family, 20, QFont.Bold))
    painter.setPen(QColor("#f1b4dc"))
    painter.drawText(QRect(10, top + 130, 130, 45), Qt.AlignCenter, spec.label)
    layers = _load_pose_layers(source, spec)
    for column_index, angle in enumerate(COLUMN_ANGLES):
        frame = _frame_for_column(layers, spec, angle, column_index)
        painter.drawImage(
            QRect(155 + column_index * 440, top, 410, 310),
            frame,
            frame.rect(),
        )
    painter.setPen(QColor("#24495d"))
    painter.drawLine(140, top + 315, CANVAS_WIDTH - 30, top + 315)


def _render_preview(source: Path, family: str) -> QImage:
    canvas = QImage(CANVAS_WIDTH, CANVAS_HEIGHT, QImage.Format_ARGB32)
    canvas.fill(QColor("#0c1b27"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    _draw_headers(painter, family)
    for row_index, spec in enumerate(_pose_specs()):
        _draw_pose_row(painter, source, family, spec, row_index)
    painter.end()
    return canvas


def main() -> int:
    _app = QGuiApplication.instance() or QGuiApplication([])
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    canvas = _render_preview(source, _font_family())
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save preview: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
