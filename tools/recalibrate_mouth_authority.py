"""Recalibrate mouth_authority_manifest.json from golden lip layers.

Ruling 2026-08-28: the previous 13-view calibration was measured from the
mirrored-defect lip layers, so its 474->553 sweep ran opposite to the real
photographs (565->467).  After the face-detail layers are rebuilt from the
half-body source via landmark affine, this tool re-measures every visible
view's alpha-weighted lip centroid and rewrites the manifest.  Rear views
stay untrusted with no visible mouth.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from datetime import date
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYER_DIR = ROOT / "assets/pose-atlas/v4-layered"
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
                "reason": "rear view: lip layers are empty, no visible mouth",
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
                "alpha-weighted centroid x of golden lip_upper+lip_lower "
                f"(landmark-affine rebuild, {today})"
            ),
        }
    return {
        "schema_version": 1,
        "views": views,
        "notes": {
            "recalibration_2026_08_28": (
                "Face-detail layers rebuilt from the half-body front source "
                "via a five-point YuNet landmark affine; the previous "
                "calibration was measured from mirrored-defect lip layers "
                "and swept in the OPPOSITE direction to the photographs. "
                "All visible views recalibrated, including yaw+000 (its old "
                "contract value inherited the same offset defect)."
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
