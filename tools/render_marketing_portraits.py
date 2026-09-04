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

lazy from PySide6.QtGui import QImage, QPixmap
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


def render_all(expressions: Sequence[str], output_root: Path) -> list[tuple[Path, str]]:
    QApplication.instance() or QApplication([])
    output_root.mkdir(parents=True, exist_ok=True)
    written: list[tuple[Path, str]] = []
    with TemporaryDirectory(prefix="mohan-marketing-portraits-") as temporary:
        # A fresh store: no active.json / makeup.json, so the selection resolves
        # to the official pack and the built-in classic makeup at intensity 1.
        overlay = ActiveOutfitOverlay(Path(temporary) / "store", ROOT)
        for expression in expressions:
            image = render_portrait(overlay, expression)
            target = output_root / f"{expression}.png"
            if not image.save(str(target), "PNG"):
                raise RuntimeError(f"Could not save portrait: {target}")
            written.append((target, hashlib.sha256(target.read_bytes()).hexdigest()))
    return written


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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    for target, digest in render_all(tuple(arguments.expressions), arguments.output):
        shown = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else target
        print(f"{digest}  {shown}")
    print(f"MARKETING_PORTRAITS_OK count={len(arguments.expressions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
