"""Render the composed half-body portraits used by README, installer and icon art.

The runtime sprites under ``assets/expressions/`` are the bare generation-2
base (bun, grey top, no makeup); the official default outfit pack and the
built-in ``classic`` makeup are composited over them at runtime by
``infrastructure.active_outfit_overlay.ActiveOutfitOverlay``.  Marketing
surfaces (README expression cards, installer wizard art, taskbar icon) must
show that composed look, so this tool drives the very same overlay with a
fresh, empty store -- which resolves to the official pack plus ``classic``
makeup at 100 % intensity -- and writes the results to
``docs/media/portraits/{expression}.png``.

Output is deterministic: the overlay paints fixed layers with fixed opacities
and Qt's PNG encoder writes no timestamp or software chunk, so re-running the
tool over unchanged sprites and packs reproduces the same bytes.  The
installer-art and app-icon builders consume ``idle_front.png`` from here.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import os
lazy import sys
lazy from collections.abc import Sequence
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QSize, Qt
lazy from PySide6.QtGui import QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import EXPRESSION_POSES, outfit_silhouette
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay

SPRITE_ROOT = ROOT / "assets" / "expressions"
OUTPUT_ROOT = ROOT / "docs" / "media" / "portraits"
PORTRAIT_SIZE = (1254, 1254)
CLOSED_EYE_MAKEUP_SLOTS = frozenset({"eyes"})
# The six README expression cards plus the canonical idle portrait that the
# installer artwork and the taskbar icon are derived from.
DEFAULT_EXPRESSIONS = (
    "proud_front",
    "thinking_front",
    "shy_cute_front",
    "mock_hit_front",
    "gentle_smile_front",
    "worried_front",
    "idle_front",
)
FRONT_POSE = "front"


def silhouette_for(expression: str) -> str:
    """Appearance silhouette dressing ``expression``; unlisted sprites are front-pose."""
    return outfit_silhouette(expression, EXPRESSION_POSES.get(expression, FRONT_POSE))


def render_portrait(overlay: ActiveOutfitOverlay, expression: str) -> QImage:
    source = SPRITE_ROOT / f"{expression}.png"
    sprite = QPixmap(str(source))
    if sprite.isNull():
        raise RuntimeError(f"Half-body sprite could not be loaded: {source}")
    if sprite.size().toTuple() != PORTRAIT_SIZE:
        raise RuntimeError(f"Half-body sprite is not {PORTRAIT_SIZE}: {source}")
    silhouette = silhouette_for(expression)
    suppressed_makeup_slots = (
        CLOSED_EYE_MAKEUP_SLOTS
        if expression.startswith("blink") or expression.endswith("_speech_blink")
        else frozenset()
    )
    composed = overlay.apply(
        sprite,
        silhouette,
        suppress_makeup_slots=suppressed_makeup_slots,
    )
    if overlay.layer_count(
        silhouette,
        suppress_makeup_slots=suppressed_makeup_slots,
    ) == 0:
        raise RuntimeError(
            f"No appearance layers were composited for {expression} ({silhouette}); "
            "the official default pack or the built-in makeup is missing."
        )
    return composed.toImage().convertToFormat(QImage.Format_ARGB32)


def _alpha_bounds(image: QImage):
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = bytes(rgba.constBits())
    stride = rgba.bytesPerLine()
    left, top = rgba.width(), rgba.height()
    right = bottom = -1
    for y in range(rgba.height()):
        row = y * stride
        for x in range(rgba.width()):
            if data[row + x * 4 + 3]:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left or bottom < top:
        raise RuntimeError("Composed portrait has no visible pixels")
    return (left, top, right - left + 1, bottom - top + 1)


def _resize_portrait(
    image: QImage,
    output_size: tuple[int, int] | None,
    *,
    crop_alpha: bool,
    content_size: tuple[int, int] | None,
    content_offset: tuple[int, int],
) -> QImage:
    if crop_alpha:
        left, top, width, height = _alpha_bounds(image)
        image = image.copy(left, top, width, height)
    if content_size is not None:
        image = image.scaled(
            QSize(*content_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if output_size is None:
        return image
    if content_size is None:
        return image.scaled(
            QSize(*output_size),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    canvas = QImage(*output_size, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    x = (canvas.width() - image.width()) // 2 + content_offset[0]
    y = content_offset[1]
    painter.drawImage(x, y, image)
    painter.end()
    return canvas


def render_all(
    expressions: Sequence[str],
    output_root: Path,
    *,
    output_size: tuple[int, int] | None = None,
    output_names: Sequence[str] | None = None,
    crop_alpha: bool = False,
    content_size: tuple[int, int] | None = None,
    content_offset: tuple[int, int] = (0, 0),
) -> list[tuple[Path, str]]:
    QApplication.instance() or QApplication([])
    output_root.mkdir(parents=True, exist_ok=True)
    names = tuple(
        output_names
        or (f"{expression}.png" for expression in expressions)
    )
    if len(names) != len(expressions):
        raise ValueError("output names must match the expression count")
    written: list[tuple[Path, str]] = []
    with TemporaryDirectory(prefix="mohan-marketing-portraits-") as temporary:
        # A fresh store: no active.json / makeup.json, so the selection resolves
        # to the official pack and the built-in classic makeup at intensity 1.
        overlay = ActiveOutfitOverlay(Path(temporary) / "store", ROOT)
        for expression, name in zip(expressions, names):
            if Path(name).name != name or not name.endswith(".png"):
                raise ValueError(f"output name must be a PNG filename: {name}")
            image = _resize_portrait(
                render_portrait(overlay, expression),
                output_size,
                crop_alpha=crop_alpha,
                content_size=content_size,
                content_offset=content_offset,
            )
            target = output_root / name
            if not image.save(str(target), "PNG"):
                raise RuntimeError(f"Could not save portrait: {target}")
            written.append((target, hashlib.sha256(target.read_bytes()).hexdigest()))
    return written


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", maxsplit=1)
        size = (int(width_text), int(height_text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "size must be WIDTHxHEIGHT, for example 640x640"
        ) from exc
    if min(size) <= 0:
        raise argparse.ArgumentTypeError("size dimensions must be positive")
    return size


def _parse_offset(value: str) -> tuple[int, int]:
    try:
        x_text, y_text = value.split(",", maxsplit=1)
        return int(x_text), int(y_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "offset must be X,Y, for example 0,20"
        ) from exc


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument(
        "expressions",
        nargs="*",
        default=list(DEFAULT_EXPRESSIONS),
        help="Sprite names under assets/expressions/ (default: the README six plus idle_front).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_ROOT,
        help="Directory the composed PNGs are written to (default: docs/media/portraits).",
    )
    parser.add_argument(
        "--size",
        type=_parse_size,
        default=None,
        metavar="WIDTHxHEIGHT",
        help="Resize each composed output to the exact requested size.",
    )
    parser.add_argument(
        "--output-name",
        action="append",
        dest="output_names",
        help="Override an output filename; repeat once per expression.",
    )
    parser.add_argument(
        "--crop-alpha",
        action="store_true",
        help="Crop each composed portrait to its visible alpha bounds.",
    )
    parser.add_argument(
        "--content-size",
        type=_parse_size,
        default=None,
        metavar="WIDTHxHEIGHT",
        help="Fit a cropped portrait inside this content box before canvas placement.",
    )
    parser.add_argument(
        "--content-offset",
        type=_parse_offset,
        default=(0, 0),
        metavar="X,Y",
        help="Add an explicit content offset after horizontal centering.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    for target, digest in render_all(
        tuple(arguments.expressions),
        arguments.output,
        output_size=arguments.size,
        output_names=arguments.output_names,
        crop_alpha=arguments.crop_alpha,
        content_size=arguments.content_size,
        content_offset=arguments.content_offset,
    ):
        shown = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else target
        print(f"{digest}  {shown}")
    print(f"MARKETING_PORTRAITS_OK count={len(arguments.expressions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
