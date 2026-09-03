"""Derive the 21 ``v120_*`` physics cutouts from a half-body layered rig.

The legacy pipeline cut the physics layers with hand-tuned per-pose boxes and
colour gates (``tools/extract_physics_layers.py``) and then feathered them
(``tools/build_v120_physics_layers.py``).  This builder takes the masks from
the rig produced by ``tools/build_half_body_layered_rig.py`` instead:

* ``hair_left`` / ``hair_right`` / ``sleeve_left`` / ``sleeve_right`` /
  ``ornament`` come from the layer of the same name;
* ``face`` is the union of the 18 facial layers, ``eyes`` the union of the
  six eye layers.

Every mask is feathered exactly like ``build_v120_physics_layers.save_layer``
and RGB is taken from the authority portrait, so the integrity contract
(original colours only, transparent RGB zeroed) holds by construction.  A rig
layer that is empty (a sleeveless top has no sleeves) yields a fully
transparent cutout: no pixels are invented, and the report lists which files
would fail the ``visible_count`` clause of ``tests/test_v120_asset_integrity.py``
so that contract can be changed deliberately.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

lazy from build_half_body_layered_rig import CANVAS, EYE_LAYERS
lazy from build_v120_physics_layers import LAYER_SETTINGS, expanded_mask, save_layer
lazy from infrastructure.layered_face_calibration import FACIAL_LAYERS

# (pose id, v120 file suffix, authority file name) — the legacy binding in
# ``build_v120_physics_layers.POSES`` keyed by suffix.
POSES = (
    ("cheek", "", "idle.png"),
    ("lean", "_lean", "idle_lean.png"),
    ("front", "_front", "idle_front.png"),
)
PHYSICS_LAYERS = tuple(LAYER_SETTINGS)
# (dilate radius, gaussian blur, peak alpha) for the attention layers, in the
# ``LAYER_SETTINGS`` format.  The peak matches the legacy ellipse masks (242).
ATTENTION_SETTINGS = {
    "face": (15, 12.0, 242),
    "eyes": (9, 6.0, 242),
}
V120_LAYERS = PHYSICS_LAYERS + tuple(ATTENTION_SETTINGS)
# Mirrors of the thresholds in tests/test_v120_asset_integrity.py so the
# report can say in advance which files that gate would reject.
FEATHER_ALPHA_THRESHOLD = 220
MIN_VISIBLE_PIXELS = 100
MIN_FEATHER_PIXELS = 80
REPORT_SCHEMA = "mohan.half-body-v120-report.v1"
INTEGRITY_TEST = "tests/test_v120_asset_integrity.py"


def _alpha(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)[:, :, 3]


def _union_image(rig_dir: Path, pose: str, layers: tuple[str, ...]) -> Image.Image:
    """Return an RGBA image whose alpha is the union of the named rig layers."""
    alpha = np.zeros((CANVAS, CANVAS), np.uint8)
    for layer in layers:
        alpha = np.maximum(alpha, _alpha(rig_dir / f"{pose}_{layer}.png"))
    rgba = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def _mask_source(rig_dir: Path, pose: str, name: str) -> tuple[Image.Image, str]:
    if name == "face":
        return _union_image(rig_dir, pose, tuple(sorted(FACIAL_LAYERS))), "union(18 facial layers)"
    if name == "eyes":
        return _union_image(rig_dir, pose, EYE_LAYERS), "union(6 eye layers)"
    return Image.open(rig_dir / f"{pose}_{name}.png").convert("RGBA"), f"{pose}_{name}.png"


def _stats(path: Path, authority: np.ndarray) -> dict:
    array = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
    if array.shape != authority.shape:
        raise ValueError(f"{path.name}: shape {array.shape} != authority {authority.shape}")
    alpha = array[:, :, 3]
    visible = alpha > 0
    rgb_mismatch = int((visible & (array[:, :, :3] != authority[:, :, :3]).any(axis=2)).sum())
    transparent_rgb = int((~visible & (array[:, :, :3] != 0).any(axis=2)).sum())
    visible_count = int(visible.sum())
    feather_count = int((visible & (alpha < FEATHER_ALPHA_THRESHOLD)).sum())
    return {
        "visible_count": visible_count,
        "feather_count": feather_count,
        "rgb_mismatch_pixels": rgb_mismatch,
        "transparent_rgb_nonzero_pixels": transparent_rgb,
        "empty": visible_count == 0,
        "passes_visible_clause": visible_count > MIN_VISIBLE_PIXELS,
        "passes_feather_clause": feather_count > MIN_FEATHER_PIXELS,
    }


def build_pose(
    pose: str,
    suffix: str,
    authority_path: Path,
    rig_dir: Path,
    output: Path,
) -> dict:
    source = Image.open(authority_path).convert("RGBA")
    if source.size != (CANVAS, CANVAS):
        raise ValueError(f"{authority_path.name}: expected {CANVAS}x{CANVAS}, got {source.size}")
    authority = np.asarray(source, dtype=np.uint8)
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict] = {}
    for name in V120_LAYERS:
        radius, blur, peak = {**LAYER_SETTINGS, **ATTENTION_SETTINGS}[name]
        image, origin = _mask_source(rig_dir, pose, name)
        target = output / f"v120_{name}{suffix}.png"
        save_layer(source, expanded_mask(image, radius, blur, peak), target)
        files[target.name] = {"mask_source": origin, **_stats(target, authority)}
    return {"pose": pose, "authority": authority_path.name, "files": files}


def build(authority_dir: Path, rig_dir: Path, output: Path) -> dict:
    poses = [
        build_pose(pose, suffix, authority_dir / filename, rig_dir, output)
        for pose, suffix, filename in POSES
    ]
    failing = sorted(
        name
        for pose in poses
        for name, stats in pose["files"].items()
        if not (stats["passes_visible_clause"] and stats["passes_feather_clause"])
    )
    for pose in poses:
        for name, stats in pose["files"].items():
            if stats["rgb_mismatch_pixels"] or stats["transparent_rgb_nonzero_pixels"]:
                raise RuntimeError(f"{name}: colour contract violated")
    return {
        "schema": REPORT_SCHEMA,
        "files": sum(len(pose["files"]) for pose in poses),
        "poses": poses,
        "integrity_contract": {
            "test": INTEGRITY_TEST,
            "files_failing_visible_or_feather_clause": failing,
            "required_change": (
                "These cutouts are genuinely empty on the bun / sleeveless base and "
                "no pixels were invented.  Installing them requires a deliberate "
                f"contract change in {INTEGRITY_TEST}: either declare the empty "
                "files as licensed-empty (assert visible_count == 0 for them and keep "
                "the > MIN_VISIBLE_PIXELS / > MIN_FEATHER_PIXELS clauses for the rest) "
                "or drop them from LAYERS and lower EXPECTED_CHECKED_COUNT.  The "
                "runtime loaders (presentation/companion_visual_physics.py) tolerate "
                "a fully transparent pixmap."
            ) if failing else "none: all 21 cutouts satisfy the current contract",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--authority-dir", type=Path, required=True,
        help="新權威 idle.png／idle_lean.png／idle_front.png 所在目錄",
    )
    parser.add_argument(
        "--rig-dir", type=Path, required=True,
        help="build_half_body_layered_rig.py 產出的 75 層目錄",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = build(args.authority_dir.resolve(), args.rig_dir.resolve(), args.output.resolve())
    report_path = args.report or args.output.resolve().parent / f"{args.output.name}-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for pose in report["poses"]:
        print(json.dumps(pose, ensure_ascii=False))
    print(json.dumps(report["integrity_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
