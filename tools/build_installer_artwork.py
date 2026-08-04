from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "mohan.png"
SMALL_SOURCE = ROOT / "assets" / "expressions" / "idle_front.png"
OUTPUT = ROOT / "installer" / "artwork"


def _background(width: int, height: int) -> QImage:
    image = QImage(width, height, QImage.Format_ARGB32)
    painter = QPainter(image)
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#dce9f4"))
    gradient.setColorAt(0.58, QColor("#edf3f7"))
    gradient.setColorAt(1.0, QColor("#f7eee7"))
    painter.fillRect(image.rect(), gradient)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor(180, 145, 83, 58), max(2, width // 260)))
    for inset in (28, 62, 96):
        painter.drawEllipse(
            QRectF(
                -width * 0.60 + inset,
                height * 0.08 + inset,
                width * 1.55,
                width * 1.55,
            )
        )
    painter.setPen(QPen(QColor(47, 105, 135, 32), max(1, width // 380)))
    spacing = max(72, width // 7)
    for offset in range(-height, width + height, spacing):
        painter.drawLine(QPointF(offset, 0), QPointF(offset + height, height))
    painter.end()
    return image


def build() -> tuple[Path, Path]:
    source = QImage(str(SOURCE))
    if source.isNull():
        raise RuntimeError(f"MoHan artwork could not be loaded: {SOURCE}")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    large_path = OUTPUT / "wizard-hero.png"
    large = _background(656, 1256)
    painter = QPainter(large)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    hero = source.scaled(610, 1200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter.drawImage((656 - hero.width()) // 2 + 8, 48, hero)
    painter.end()
    if not large.save(str(large_path), "PNG"):
        raise RuntimeError(f"Could not save installer artwork: {large_path}")

    small_path = OUTPUT / "wizard-small.png"
    small = _background(512, 512)
    small_source = QImage(str(SMALL_SOURCE))
    if small_source.isNull():
        raise RuntimeError(f"MoHan portrait could not be loaded: {SMALL_SOURCE}")
    painter = QPainter(small)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    portrait = small_source.scaled(
        448,
        448,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    painter.drawImage((512 - portrait.width()) // 2, 38, portrait)
    painter.end()
    if not small.save(str(small_path), "PNG"):
        raise RuntimeError(f"Could not save installer artwork: {small_path}")
    return large_path, small_path


if __name__ == "__main__":
    large, small = build()
    print(f"INSTALLER_ARTWORK_OK {large.name} {small.name}")
