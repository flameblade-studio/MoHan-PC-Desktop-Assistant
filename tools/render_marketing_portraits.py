"""Render the composed half-body portraits used by README, installer and icon art.

Marketing surfaces use the product half-body renderer after activating the
selected character. Its installed V5 complete-expression frames provide the
face and body; the official default outfit and built-in ``classic`` makeup use
the same defaults as the approved product golden. Portrait resizing and canvas
placement happen only after the product renderer has composed the appearance.

Output is deterministic: the overlay paints fixed layers with fixed opacities
and Qt's PNG encoder omits timestamp and software chunks, so re-running the
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
lazy from dataclasses import replace
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QSize, Qt
lazy from PySide6.QtGui import QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from application.character_runtime_bootstrap import activate_product_character_runtime
lazy from domain.companion_animation_contract import (
    EXPRESSION_POSES, SPEECH_FRAME_MARKER, outfit_silhouette,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.golden_render import render_half_blink
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from infrastructure.layered_face_assets import load_layered_face_assets
lazy from domain.face_motion import VISEME_MOUTH_TARGETS, FaceMotionController
lazy from domain.face_rig import Viseme
lazy from domain.character_runtime import CHARACTER_ASSET_PATHS
lazy from domain.outfit_pack import restore_builtin_outfit
lazy from domain.outfit_pack_makeup import (
    DEFAULT_MAKEUP_INTENSITY, DEFAULT_SLOT_INTENSITIES_V2,
    select_builtin_makeup, write_makeup_intensity, write_makeup_slot_intensity,
)

OUTPUT_ROOT = ROOT / "docs" / "media" / "portraits"
PORTRAIT_SIZE = (1254, 1254)
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
# Speech frame suffixes map to the mouth family the complete renderer selects
# (``small``/``a``/``o``); blink frames reuse the idle endpoint closed-eyed.
SPEECH_FRAME_VISEMES = {"mid": "I", "open": "A", "round": "O"}
BLINK_FRAME_PREFIX = "blink"
IDLE_FRAME_PREFIX = "idle"
CLOSED_EYE_STATE = "closed"


def silhouette_for(expression: str) -> str:
    """Appearance silhouette dressing ``expression``; unlisted sprites are front-pose."""
    return outfit_silhouette(expression, EXPRESSION_POSES.get(expression, FRONT_POSE))


def prepare_marketing_store(store: Path) -> None:
    """Select the same official outfit and classic defaults as the product golden."""
    activate_product_character_runtime(ROOT)
    restore_builtin_outfit(store)
    write_makeup_intensity(store, DEFAULT_MAKEUP_INTENSITY)
    for slot, intensity in DEFAULT_SLOT_INTENSITIES_V2.items():
        write_makeup_slot_intensity(store, slot, intensity)
    select_builtin_makeup(store, "classic")


def portrait_renderer(overlay: ActiveOutfitOverlay) -> LayeredParametricFaceRenderer:
    """Build the product half-body renderer after character activation."""
    activate_product_character_runtime(ROOT)
    return LayeredParametricFaceRenderer(
        manifest=load_layered_face_assets(ROOT / CHARACTER_ASSET_PATHS["halfbody_layers"]),
        outfit_overlay=overlay,
        authority_dir=ROOT / CHARACTER_ASSET_PATHS["halfbody_root"],
        detachable_dir=ROOT / CHARACTER_ASSET_PATHS["halfbody_detachable"],
    )


def portrait_motion(expression: str) -> tuple[str, str | None, str]:
    """Split a sprite name into (emotion, speech mouth frame, eye state)."""
    if expression.startswith(BLINK_FRAME_PREFIX):
        return IDLE_FRAME_PREFIX + expression.removeprefix(BLINK_FRAME_PREFIX), None, CLOSED_EYE_STATE
    emotion, marker, frame = expression.partition(SPEECH_FRAME_MARKER)
    if not marker:
        return expression, None, "rest"
    if frame not in SPEECH_FRAME_VISEMES:
        raise ValueError(f"Unsupported speech frame for marketing portraits: {expression}")
    return emotion, expression, "rest"


def render_portrait(
    overlay: ActiveOutfitOverlay,
    expression: str,
    *,
    renderer: LayeredParametricFaceRenderer | None = None,
    size: tuple[int, int] = PORTRAIT_SIZE,
) -> QImage:
    activate_product_character_runtime(ROOT)
    emotion, speech_frame, eye_state = portrait_motion(expression)
    pose = EXPRESSION_POSES.get(emotion, FRONT_POSE)
    motion = replace(
        FaceMotionController().close(pose=pose, expression=emotion), breath=0.0,
    )
    layers = None
    if speech_frame is not None:
        viseme = Viseme(SPEECH_FRAME_VISEMES[speech_frame.rpartition("_")[2]])
        motion = replace(motion, viseme=viseme, mouth=VISEME_MOUTH_TARGETS[viseme])
        layers = SimpleNamespace(mouth_expression=speech_frame)
    base = QPixmap(*size)
    base.fill(Qt.GlobalColor.transparent)
    active_renderer = renderer or portrait_renderer(overlay)
    composed = active_renderer.render(base, motion, layers)
    if composed.isNull():
        raise RuntimeError(f"Product renderer returned an empty portrait: {expression}")
    if eye_state != "rest":
        blinked = render_half_blink(ROOT, active_renderer, emotion, eye_state)
        if blinked.isNull():
            raise RuntimeError(f"Product blink compositor returned an empty portrait: {expression}")
        composed = blinked.scaled(*size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return composed.toImage()


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
        raise RuntimeError("Composed portrait requires visible pixels")
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
        store = Path(temporary) / "store"
        prepare_marketing_store(store)
        overlay = ActiveOutfitOverlay(
            store,
            ROOT,
            official_pack_root=ROOT / "assets" / "official-packs",
        )
        renderer = portrait_renderer(overlay)
        for expression, name in zip(expressions, names, strict=True):
            if Path(name).name != name or not name.endswith(".png"):
                raise ValueError(f"output name must be a PNG filename: {name}")
            image = _resize_portrait(
                render_portrait(overlay, expression, renderer=renderer),
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
        help="Product expression names (default: the README six plus idle_front).",
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
    activate_product_character_runtime(ROOT)
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
