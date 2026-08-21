"""Analyze the 600 full-body layered assets for alignment outliers.

Walks ``assets/pose-atlas/v4-layered/`` (24 views × 25 layers), computes each
PNG's alpha-trimmed bounding box, and reports:

* missing layers per view,
* per-layer relative center offsets against the ``body`` (torso) reference,
* cross-view symmetry outliers (a layer whose center drifts more than
  ``OUTLIER_THRESHOLD_PIXELS`` from the median across views),
* crop coordinates for every image so Codex can re-align the outliers.

Output is a JSON report written to ``--output`` (default
``layered_asset_analysis.json``). This is a standalone diagnostic tool; it does
not modify any asset.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import sys
lazy from collections import defaultdict
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

# The 24 authored views, in yaw order.
VIEW_IDS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)

# The 25 authored layers, in Z-order (bottom to top).
LAYER_NAMES = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)

# The torso layer is the alignment reference for every other layer.
REFERENCE_LAYER = "body"

# A layer whose center jumps more than this many pixels from the linear
# interpolation of its two neighbouring views is flagged as an outlier.
OUTLIER_THRESHOLD_PIXELS = 2

# A layer needs at least this many present views to run continuity detection.
MIN_VIEWS_FOR_CONTINUITY = 3

DEFAULT_ASSET_DIR = ROOT / "assets" / "pose-atlas" / "v4-layered"
DEFAULT_OUTPUT = ROOT / "layered_asset_analysis.json"


def _opaque_bounds(image: QImage) -> tuple[int, int, int, int] | None:
    """Return (left, top, right, bottom) of opaque pixels, or None if empty."""
    width = image.width()
    height = image.height()
    left = width
    top = height
    right = -1
    bottom = -1
    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() == 0:
                continue
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)
    if right < left or bottom < top:
        return None
    return (left, top, right, bottom)


def _center(bounds: tuple[int, int, int, int]) -> tuple[float, float]:
    left, top, right, bottom = bounds
    return ((left + right) / 2.0, (top + bottom) / 2.0)


def _parse_filename(name: str) -> tuple[str, str] | None:
    """Split ``{view_id}_{layer}.png`` into (view_id, layer)."""
    if not name.endswith(".png"):
        return None
    stem = name[:-4]
    for layer in LAYER_NAMES:
        if stem.endswith(f"_{layer}"):
            view_id = stem[: -(len(layer) + 1)]
            return view_id, layer
    return None


def _yaw_degrees(view_id: str) -> int:
    """Parse the signed yaw degrees from a ``yaw±NNN-pitch+00`` view id."""
    marker = "yaw"
    end = view_id.index("-pitch")
    return int(view_id[len(marker):end])


def analyze(asset_dir: Path) -> dict:
    """Analyze all layered assets and return a JSON-serializable report."""
    # Ensure a QApplication exists so QImage can decode pixels offscreen.
    QApplication.instance() or QApplication([])

    # bounds[view_id][layer] = (left, top, right, bottom)
    bounds: dict[str, dict[str, tuple[int, int, int, int]]] = defaultdict(dict)
    missing: list[str] = []
    unparsed: list[str] = []

    for path in sorted(asset_dir.glob("*.png")):
        parsed = _parse_filename(path.name)
        if parsed is None:
            unparsed.append(path.name)
            continue
        view_id, layer = parsed
        image = QImage(str(path))
        if image.isNull():
            missing.append(f"{path.name}: cannot decode")
            continue
        box = _opaque_bounds(image)
        if box is None:
            missing.append(f"{path.name}: fully transparent")
            continue
        bounds[view_id][layer] = box

    # Missing layers per view.
    missing_layers: dict[str, list[str]] = {}
    for view_id in VIEW_IDS:
        present = set(bounds.get(view_id, {}))
        absent = [layer for layer in LAYER_NAMES if layer not in present]
        if absent:
            missing_layers[view_id] = absent

    # Relative centers against the body reference, per view.
    relative_centers: dict[str, dict[str, tuple[float, float]]] = {}
    for view_id, layers in bounds.items():
        reference = layers.get(REFERENCE_LAYER)
        if reference is None:
            continue
        ref_cx, ref_cy = _center(reference)
        relative_centers[view_id] = {}
        for layer, box in layers.items():
            if layer == REFERENCE_LAYER:
                continue
            cx, cy = _center(box)
            relative_centers[view_id][layer] = (cx - ref_cx, cy - ref_cy)

    # Adjacent-view continuity outliers per layer.
    #
    # A layer's center should move *smoothly* across adjacent yaw views (the
    # character turns continuously). A genuine alignment error shows up as a
    # sudden jump: the center at one view deviates sharply from the linear
    # interpolation of its two neighbours. This avoids flagging the natural
    # drift of 3D hair/sleeves/ornament, which legitimately moves as the body
    # turns, and the intentionally transparent face layers on back views.
    outliers: list[dict] = []
    for layer in LAYER_NAMES:
        if layer == REFERENCE_LAYER:
            continue
        # Collect (yaw_degrees, view_id, center) for views that have this layer.
        present: list[tuple[int, str, tuple[float, float]]] = []
        for view_id in VIEW_IDS:
            if view_id not in relative_centers:
                continue
            if layer not in relative_centers[view_id]:
                continue
            yaw = _yaw_degrees(view_id)
            present.append((yaw, view_id, relative_centers[view_id][layer]))
        present.sort(key=lambda item: item[0])
        if len(present) < MIN_VIEWS_FOR_CONTINUITY:
            continue
        for index in range(1, len(present) - 1):
            prev_yaw, _prev_view, (prev_x, prev_y) = present[index - 1]
            curr_yaw, curr_view, (curr_x, curr_y) = present[index]
            next_yaw, _next_view, (next_x, next_y) = present[index + 1]
            # Linear interpolation of the two neighbours at the current yaw.
            span = next_yaw - prev_yaw
            if span == 0:
                continue
            t = (curr_yaw - prev_yaw) / span
            expected_x = prev_x + (next_x - prev_x) * t
            expected_y = prev_y + (next_y - prev_y) * t
            jump = max(abs(curr_x - expected_x), abs(curr_y - expected_y))
            if jump > OUTLIER_THRESHOLD_PIXELS:
                outliers.append(
                    {
                        "view_id": curr_view,
                        "layer": layer,
                        "yaw_degrees": curr_yaw,
                        "center": [round(curr_x, 2), round(curr_y, 2)],
                        "expected_center": [round(expected_x, 2), round(expected_y, 2)],
                        "jump_pixels": round(jump, 2),
                    }
                )

    # Crop coordinates for every image (tight alpha-trimmed box).
    crops: dict[str, dict[str, list[int]]] = {}
    for view_id, layers in bounds.items():
        crops[view_id] = {
            layer: [box[0], box[1], box[2] + 1, box[3] + 1]
            for layer, box in layers.items()
        }

    return {
        "asset_dir": str(asset_dir),
        "reference_layer": REFERENCE_LAYER,
        "outlier_threshold_pixels": OUTLIER_THRESHOLD_PIXELS,
        "total_views": len(VIEW_IDS),
        "total_layers_per_view": len(LAYER_NAMES),
        "views_found": sorted(bounds.keys()),
        "missing_layers": missing_layers,
        "unparsed_files": unparsed,
        "outliers": outliers,
        "outlier_count": len(outliers),
        "crop_coordinates": crops,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze full-body layered assets for alignment outliers."
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=DEFAULT_ASSET_DIR,
        help="Directory containing the layered PNGs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the JSON report.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=OUTLIER_THRESHOLD_PIXELS,
        help="Outlier drift threshold in pixels.",
    )
    arguments = parser.parse_args(tuple(argv or ()))

    report = analyze(arguments.asset_dir)
    report["outlier_threshold_pixels"] = arguments.threshold

    arguments.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {arguments.output}")
    print(f"  views found: {len(report['views_found'])}/{report['total_views']}")
    print(f"  missing layers: {sum(len(v) for v in report['missing_layers'].values())}")
    print(f"  outliers: {report['outlier_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
