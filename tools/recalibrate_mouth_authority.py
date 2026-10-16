"""Measure mouth centers from the supplied, visually reviewed native lip layers.

Measure each visible view's alpha-weighted lip centroid. Source hashes record
the exact calibration inputs; visual acceptance is a caller prerequisite.
Rear views retain their untrusted status with the mouth outside the visible surface.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy from datetime import date
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME

DEFAULT_LAYER_DIR = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
DEFAULT_MANIFEST = DEFAULT_LAYER_DIR / "mouth_authority_manifest.json"
VISIBLE_MAX_ABS_YAW = 90
ALL_YAWS = tuple(range(-180, 180, 15))


def _lip_centroid_x(layer_dir: Path, view_id: str) -> float | None:
    total_alpha = 0.0
    weighted = 0.0
    for layer in ("lip_upper", "lip_lower"):
        path = layer_dir / f"{view_id}_{layer}.png"
        image = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
        alpha = image[:, :, 3].astype(np.float64)
        columns = np.arange(image.shape[1], dtype=np.float64)
        total_alpha += float(alpha.sum())
        weighted += float((alpha.sum(axis=0) * columns).sum())
    if total_alpha <= 0.0:
        return None
    return weighted / total_alpha


def build_manifest(layer_dir: Path) -> dict:
    views: dict[str, dict] = {}
    today = date.today().isoformat()
    for yaw in ALL_YAWS:
        view_id = f"yaw{yaw:+04d}-pitch+00"
        if abs(yaw) > VISIBLE_MAX_ABS_YAW:
            views[view_id] = {
                "trusted": False,
                "mouth_center_x": None,
                "reason": "rear view: lip layers are transparent; mouth lies outside the visible surface",
            }
            continue
        center = _lip_centroid_x(layer_dir, view_id)
        if center is None:
            views[view_id] = {
                "trusted": False,
                "mouth_center_x": None,
                "reason": "lip layers empty; calibration unavailable",
            }
            continue
        views[view_id] = {
            "trusted": True,
            "mouth_center_x": round(center, 4),
            "method": (
                "alpha-weighted centroid x of supplied lip_upper+lip_lower "
                f"(measured {today})"
            ),
            "source_layers": {
                layer: {
                    "path": f"{view_id}_{layer}.png",
                    "sha256": hashlib.sha256(
                        (layer_dir / f"{view_id}_{layer}.png").read_bytes()
                    ).hexdigest(),
                }
                for layer in ("lip_upper", "lip_lower")
            },
        }
    return {
        "schema_version": 1,
        "views": views,
        "notes": {
            "calibration_inputs": (
                "Centers are measured from the supplied layer files. "
                "Source layer hashes identify the exact inputs; their generation "
                "method and appearance acceptance have separate provenance."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer-dir", type=Path, default=DEFAULT_LAYER_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    arguments = parser.parse_args()
    manifest = build_manifest(arguments.layer_dir)
    arguments.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    calibrated_views = sum(
        1 for view in manifest["views"].values() if view["trusted"]
    )
    print(f"MOUTH_AUTHORITY_RECALIBRATED: {calibrated_views} calibrated views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
