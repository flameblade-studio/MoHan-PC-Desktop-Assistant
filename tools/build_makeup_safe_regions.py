"""Derive the per-silhouette makeup safe regions from the layered rigs.

Each slot's region is the union, per side, of the alpha bounding boxes of the
rig cut-outs that belong to it (``domain.outfit_pack_makeup.SLOT_RIG_LAYERS``),
dilated by the slot margin and clamped to the canvas.  The four gesture
silhouettes reuse the front half-body rig.  The result is written to
``assets/makeup-safe-regions.json``; ``--check`` verifies the committed file.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtGui import QImage

lazy from domain.outfit_pack import MAKEUP_CANVASES, POSE_ATLAS_SILHOUETTES, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack_makeup import (
    SAFE_REGION_FILE,
    SAFE_REGION_SCHEMA,
    SLOT_MARGINS_PX,
    SLOT_RIG_LAYERS,
    expected_makeup_rig,
)


def alpha_bounds(path: Path) -> tuple[int, int, int, int] | None:
    """Tight (x, y, w, h) of every non-transparent pixel, or None for an empty layer."""
    image = QImage(str(path))
    if image.isNull():
        return None
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    width, height, stride = alpha.width(), alpha.height(), alpha.bytesPerLine()
    raw = bytes(alpha.constBits())
    top = bottom = None
    left, right = width, -1
    for row in range(height):
        line = raw[row * stride : row * stride + width]
        stripped = line.lstrip(b"\x00")
        if not stripped:
            continue
        top = row if top is None else top
        bottom = row
        left = min(left, width - len(stripped))
        right = max(right, len(line.rstrip(b"\x00")) - 1)
    if top is None:
        return None
    return (left, top, right - left + 1, bottom - top + 1)


def _union(rects: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    left = min(rect[0] for rect in rects)
    top = min(rect[1] for rect in rects)
    right = max(rect[0] + rect[2] for rect in rects)
    bottom = max(rect[1] + rect[3] for rect in rects)
    return (left, top, right - left, bottom - top)


def _dilated(rect: tuple[int, int, int, int], margin: int, canvas: tuple[int, int]) -> list[int]:
    left = max(0, rect[0] - margin)
    top = max(0, rect[1] - margin)
    right = min(canvas[0], rect[0] + rect[2] + margin)
    bottom = min(canvas[1], rect[1] + rect[3] + margin)
    return [left, top, right - left, bottom - top]


def rig_prefix(silhouette: str) -> str:
    return expected_makeup_rig(silhouette)


def silhouette_regions(root: Path, silhouette: str) -> dict[str, object]:
    prefix = rig_prefix(silhouette)
    canvas = MAKEUP_CANVASES["full-body" if silhouette in POSE_ATLAS_SILHOUETTES else "half-body"]
    base = QImage(str(root / f"{prefix}_base.png"))
    if base.isNull() or (base.width(), base.height()) != canvas:
        raise RuntimeError(f"Rig base for {silhouette} is missing or off-canvas: {prefix}_base.png")
    slots: dict[str, list[list[int]]] = {}
    for slot, groups in SLOT_RIG_LAYERS.items():
        rects: list[list[int]] = []
        for layers in groups:
            bounds = [
                found for found in (alpha_bounds(root / f"{prefix}_{layer}.png") for layer in layers)
                if found is not None
            ]
            if bounds:
                rects.append(_dilated(_union(bounds), SLOT_MARGINS_PX[slot], canvas))
        slots[slot] = rects
    return {"canvas": list(canvas), "rig": prefix, "slots": slots}


def build_makeup_safe_regions(root: Path) -> dict[str, object]:
    return {
        "schema": SAFE_REGION_SCHEMA,
        "generated_by": "tools/build_makeup_safe_regions.py",
        "margins_px": dict(SLOT_MARGINS_PX),
        "rig_layers": {slot: [list(group) for group in groups] for slot, groups in SLOT_RIG_LAYERS.items()},
        "silhouettes": {silhouette: silhouette_regions(root, silhouette) for silhouette in REQUIRED_SILHOUETTES},
    }


def render(document: dict[str, object]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="project root holding assets/")
    parser.add_argument("--output", type=Path, default=None, help=f"defaults to <root>/assets/{SAFE_REGION_FILE}")
    parser.add_argument("--check", action="store_true", help="fail when the committed document is stale")
    arguments = parser.parse_args(argv)
    output = arguments.output or arguments.root / "assets" / SAFE_REGION_FILE
    text = render(build_makeup_safe_regions(arguments.root))
    if arguments.check:
        current = output.read_text(encoding="utf-8") if output.is_file() else ""
        if current != text:
            print(f"MAKEUP_SAFE_REGIONS_STALE {output}")
            return 1
        print(f"MAKEUP_SAFE_REGIONS_OK {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
