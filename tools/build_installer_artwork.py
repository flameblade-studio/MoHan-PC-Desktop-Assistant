"""Build the Inno Setup wizard artwork from one MoHan half-body portrait.

The shipped ``installer/artwork/*`` is built from the generation-2 composed
portrait ``docs/media/portraits/idle_front.png`` (official default pack plus
built-in classic makeup, rendered by ``tools/render_marketing_portraits.py``)::

    py -3.15 tools/build_installer_artwork.py --source docs/media/portraits/idle_front.png

Without ``--source`` the bare runtime sprite ``assets/expressions/idle_front.png``
is used, which is what the artwork looked like before the composed portraits.
"""

from __future__ import annotations

lazy import argparse
lazy from collections.abc import Sequence
lazy from pathlib import Path

lazy from PySide6.QtCore import QPointF, QRectF, Qt
lazy from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "assets"
    / "expressions"
    / "idle_front.png"
)
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


def build(source_path: Path = SOURCE) -> tuple[Path, Path]:
    source = QImage(str(source_path))
    if source.isNull():
        raise RuntimeError(f"MoHan artwork could not be loaded: {source_path}")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    large_path = OUTPUT / "wizard-hero.png"
    large = _background(656, 1256)
    painter = QPainter(large)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    portrait_width = round(source.width() * 0.62)
    portrait = source.copy(
        (source.width() - portrait_width) // 2,
        0,
        portrait_width,
        source.height(),
    )
    hero = portrait.scaled(
        600,
        1000,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    painter.drawImage(
        (large.width() - hero.width()) // 2,
        large.height() - hero.height() - 80,
        hero,
    )
    painter.end()
    if not large.save(str(large_path), "PNG"):
        raise RuntimeError(f"Could not save installer artwork: {large_path}")

    small_path = OUTPUT / "wizard-small.png"
    small = _background(512, 512)
    small_source = source
    painter = QPainter(small)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    portrait = small_source.scaled(
        448,
        448,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    painter.drawImage(
        (small.width() - portrait.width()) // 2,
        (small.height() - portrait.height()) // 2,
        portrait,
    )
    painter.end()
    if not small.save(str(small_path), "PNG"):
        raise RuntimeError(f"Could not save installer artwork: {small_path}")
    return large_path, small_path


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Inno Setup wizard artwork.")
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE,
        help="Half-body portrait to draw (default: the bare runtime idle_front.png).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    large, small = build(_arguments(argv).source)
    print(f"INSTALLER_ARTWORK_OK {large.name} {small.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
