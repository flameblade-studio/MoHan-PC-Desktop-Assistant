"""Build the half-body 25-layer parametric rig from new authority portraits.

The builder never synthesises pixels.  For each of the three half-body poses
it solves a five-point YuNet affine from the OLD authority portrait (the one
the current ``assets/expressions/layered`` masks were cut from) to the NEW
authority, warps the 25 old alpha masks by that affine, rebuilds the eye and
mouth partitions deterministically, assigns every authority-opaque pixel to
exactly one layer and re-cuts the new authority pixels into those layers.
Recomposition of the 25 cutouts is therefore lossless.

Layers the new body does not have (a sleeveless top has no sleeves, a bun has
no hanging hairpin) are declared empty on the command line; ``hair_left`` and
``hair_right`` are auto-detected from where their warped masks land on the new
portrait and the decision is reported, never guessed silently.

Usage::

    py -3.15 tools/build_half_body_layered_rig.py \
        --authority-dir work/half-body-v2/authority \
        --output work/half-body-v2/layered
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import sys
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

lazy from audit_layered_full_body_semantics import _skin
lazy from build_yaw000_golden_template import (
    LAYERS,
    _bbox,
    _face_alignment_matrix,
    _face_evidence,
    _partition_eye_layers,
    _rebuild_mouth_partitions,
    _reclaim_face_pixels,
    _rgba,
    _warp_mask,
)
lazy from extract_physics_layers import (
    DARK_HAIR_BRIGHTNESS_MAX,
    DARK_HAIR_SPREAD_MAX,
    MIN_OPAQUE_ALPHA,
)
lazy from infrastructure.layered_face_calibration import (
    FACIAL_LAYERS,
    MAX_ANCHOR_DRIFT_PIXELS,
    LayerAnchor,
    _center_escape,
)

CANVAS = 1254
# (pose id, authority file name) — the same binding as
# ``infrastructure.layered_face_renderer.FACE_AUTHORITY_FILES``.
POSES = (
    ("cheek", "idle.png"),
    ("lean", "idle_lean.png"),
    ("front", "idle_front.png"),
)
DEFAULT_MASK_SOURCE = REPO_ROOT / "assets" / "expressions" / "layered"
DEFAULT_MASK_AUTHORITY_DIR = REPO_ROOT / "assets" / "expressions"
DEFAULT_EMPTY_LAYERS = ("sleeve_left", "sleeve_right", "ornament")
# Layers whose presence on the new body is decided per pose from evidence.
AUTO_EMPTY_LAYERS = ("hair_left", "hair_right")
# A warped strand mask whose area lands mostly on transparent background no
# longer has a strand under it.
MOSTLY_TRANSPARENT_RATIO = 0.5
# ...and one that lands on opaque skin/cloth instead of hair-coloured pixels
# has no strand either (the old strands hung over the robe; the new body is
# bare there).  Both criteria are reported.
MIN_HAIR_COLOUR_RATIO = 0.25
# ``extract_physics_layers`` keeps the blue/red ratio of its dark-hair gate
# inline; it is named here so the two classifiers stay comparable.
DARK_HAIR_BLUE_TO_RED_MIN = 0.82
# ``teeth_tongue`` must stay non-empty for calibration; when its warped mask
# collapses it takes the central part of the oral seam.
TEETH_TONGUE_CENTRAL_SPAN = 0.5
# Skin inside the YuNet face box padded by these fractions (sideways and
# upward; the same padding the full-body remap uses) that no warped mask
# claims is face skin — forehead above the old hairline, ears, cheek edges —
# and belongs to ``base``, not to the hair/body fallback.
FACE_ZONE_PAD_X = 0.25
FACE_ZONE_PAD_UP = 0.25
EYE_LAYERS = (
    "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right",
)
# Fine features win over skin, skin over hair, hair over body — the same
# ordering as the full-body golden builder, plus ``teeth_tongue``, which the
# half-body calibration requires to be non-empty.
OWNERSHIP_PRIORITY = (
    "brow_left", "brow_right", "eyeliner_left", "eyeliner_right",
    "eyelid_left", "eyelid_right", "iris_left", "iris_right", "blush_left",
    "blush_right", "corner_left", "corner_right", "teeth_tongue", "lip_upper",
    "lip_lower", "oral_cavity", "jaw", "base", "ornament", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "hair_back", "body",
)
IDENTITY_SAMPLE_STEP = 4
REPORT_SCHEMA = "mohan.half-body-layered-rig-report.v1"


def _dark_hair(authority: np.ndarray) -> np.ndarray:
    """Return the dark-hair classifier used by the physics extraction."""
    rgb = authority[:, :, :3].astype(np.int16)
    brightness = rgb.max(axis=2)
    spread = brightness - rgb.min(axis=2)
    return (
        (authority[:, :, 3] > MIN_OPAQUE_ALPHA)
        & (brightness <= DARK_HAIR_BRIGHTNESS_MAX)
        & (spread <= DARK_HAIR_SPREAD_MAX)
        & (rgb[:, :, 2] >= rgb[:, :, 0] * DARK_HAIR_BLUE_TO_RED_MIN)
    )


def _face_zone_skin(
    authority: np.ndarray,
    face_box: tuple[float, float, float, float],
    dark_hair: np.ndarray,
) -> np.ndarray:
    """Return skin-classified pixels inside the padded face zone."""
    x, y, w, h = face_box
    rows, columns = authority.shape[:2]
    zone = np.zeros((rows, columns), bool)
    y0 = max(0, int(y - h * FACE_ZONE_PAD_UP))
    y1 = min(rows, int(y + h))
    x0 = max(0, int(x - w * FACE_ZONE_PAD_X))
    x1 = min(columns, int(x + w * (1.0 + FACE_ZONE_PAD_X)))
    zone[y0:y1, x0:x1] = True
    # The audit classifier consumes cv2-ordered BGRA; this builder decodes RGBA.
    return zone & _skin(authority[:, :, [2, 1, 0, 3]]) & ~dark_hair


def _alignment(old_authority: Path, new_authority: Path) -> tuple[np.ndarray, dict]:
    """Solve the old->new affine over the five YuNet landmarks."""
    old = _face_evidence(old_authority)
    new = _face_evidence(new_authority)
    matrix = _face_alignment_matrix(old, new)
    source = np.asarray(old.landmarks, dtype=np.float64)
    target = np.asarray(new.landmarks, dtype=np.float64)
    projected = source @ matrix[:, :2].T + matrix[:, 2]
    residual = np.abs(projected - target).max(axis=1)
    evidence = {
        "method": "yunet-5-point-affine",
        "matrix": [[round(float(v), 6) for v in row] for row in matrix],
        "old_face_box": [round(float(v), 1) for v in old.box],
        "new_face_box": [round(float(v), 1) for v in new.box],
        "landmark_residual_px": [round(float(v), 2) for v in residual],
        "max_landmark_residual_px": round(float(residual.max()), 2),
    }
    return matrix, {"alignment": evidence, "face_box": tuple(new.box)}


def _warped_masks(
    mask_source: Path,
    pose: str,
    matrix: np.ndarray,
    size: tuple[int, int],
) -> dict[str, np.ndarray]:
    """Warp the 25 old alpha masks; NOT yet clipped to the new foreground."""
    warped: dict[str, np.ndarray] = {}
    for layer in LAYERS:
        source = _rgba(mask_source / f"{pose}_{layer}.png")
        warped[layer] = _warp_mask(source[:, :, 3] > 0, matrix, size)
    return warped


def _hair_split_y(
    dark_hair: np.ndarray,
    face_box: tuple[float, float, float, float],
) -> tuple[int, tuple[int, int, int, int]]:
    """Return the hair/body split row and the head-hair (bun) bounding box.

    The head hair is the largest connected dark-hair component that starts
    above the bottom of the detected face box; unowned pixels above the
    bottom of that component default to ``hair_back``, everything below to
    ``body``.  This replaces the full-body builder's hard split constant.
    """

    face_bottom = int(face_box[1] + face_box[3])
    yy = np.indices(dark_hair.shape)[0]
    head = (dark_hair & (yy < face_bottom)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(head, connectivity=8)
    if count <= 1:
        raise ValueError("no dark-hair component found above the face box")
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    bun = _bbox(labels == largest)
    return bun[3], bun


def _auto_empty_decisions(
    warped_masks: dict[str, np.ndarray],
    foreground: np.ndarray,
    dark_hair: np.ndarray,
) -> dict[str, dict]:
    """Decide from the RAW warped masks whether a strand layer still exists."""
    decisions: dict[str, dict] = {}
    for layer in AUTO_EMPTY_LAYERS:
        warped = warped_masks[layer]
        area = int(warped.sum())
        transparent = int((warped & ~foreground).sum())
        hair = int((warped & dark_hair).sum())
        transparent_ratio = transparent / area if area else 1.0
        hair_ratio = hair / area if area else 0.0
        empty = (
            transparent_ratio > MOSTLY_TRANSPARENT_RATIO
            or hair_ratio < MIN_HAIR_COLOUR_RATIO
        )
        decisions[layer] = {
            "warped_mask_pixels": area,
            "transparent_ratio": round(transparent_ratio, 3),
            "hair_colour_ratio": round(hair_ratio, 3),
            "empty": empty,
        }
    return decisions


def _partition_teeth_tongue(
    candidates: dict[str, np.ndarray],
    warped_teeth_tongue: np.ndarray,
) -> str:
    """Keep ``teeth_tongue`` non-empty without inventing pixels.

    Preferred: the warped old mask, minus the corners and the oral seam.
    Fallback: the central half of the oral seam (or its median row) when the
    warped mask collapses into pixels the lips already own.
    """

    corners = candidates["corner_left"] | candidates["corner_right"]
    mouth = candidates["lip_upper"] | candidates["lip_lower"] | candidates["oral_cavity"]
    teeth = warped_teeth_tongue & mouth & ~corners & ~candidates["oral_cavity"]
    mode = "warped-mask"
    if not teeth.any():
        oral = candidates["oral_cavity"]
        if not oral.any():
            raise RuntimeError("oral cavity is empty; cannot seat teeth_tongue")
        x0, _y0, x1, _y1 = _bbox(oral)
        xx = np.indices(oral.shape)[1]
        half_span = (x1 - x0) * TEETH_TONGUE_CENTRAL_SPAN / 2.0
        centre = (x0 + x1) / 2.0
        teeth = oral & (np.abs(xx - centre) <= half_span)
        mode = "oral-seam-central-span"
        if not teeth.any() or not (oral & ~teeth).any():
            ys = np.where(oral)[0]
            median_row = int(np.median(ys))
            teeth = oral & (np.indices(oral.shape)[0] == median_row)
            mode = "oral-seam-median-row"
        if not teeth.any() or not (oral & ~teeth).any():
            raise RuntimeError("cannot split a non-empty teeth_tongue from the oral seam")
    for layer in ("lip_upper", "lip_lower", "oral_cavity"):
        candidates[layer] &= ~teeth
        if not candidates[layer].any():
            raise RuntimeError(f"{layer} emptied by the teeth_tongue partition")
    candidates["teeth_tongue"] = teeth
    return mode


def _exclusive_ownership(
    candidates: dict[str, np.ndarray],
    foreground: np.ndarray,
    split_y: int,
) -> dict[str, np.ndarray]:
    h, w = foreground.shape
    owned: dict[str, np.ndarray] = {}
    claimed = np.zeros((h, w), bool)
    for name in OWNERSHIP_PRIORITY:
        own = candidates[name] & ~claimed
        owned[name] = own
        claimed |= own
    missing = foreground & ~claimed
    yy = np.indices((h, w))[0]
    owned["hair_back"] |= missing & (yy < split_y)
    owned["body"] |= missing & (yy >= split_y)
    return owned


def _anchor(mask: np.ndarray) -> LayerAnchor | None:
    if not mask.any():
        return None
    x0, y0, x1, y1 = _bbox(mask)
    return LayerAnchor(x0, y0, x1, y1)


def _drift_report(owned: dict[str, np.ndarray]) -> dict[str, float]:
    base = _anchor(owned["base"])
    if base is None:
        raise RuntimeError("base layer is empty")
    drift: dict[str, float] = {}
    for layer in sorted(FACIAL_LAYERS):
        if layer == "base":
            continue
        anchor = _anchor(owned[layer])
        if anchor is None:
            raise RuntimeError(f"facial layer is empty: {layer}")
        drift[layer] = round(_center_escape(base, anchor), 2)
    return drift


def _reconstruction_report(output: Path, pose: str, authority: np.ndarray) -> dict:
    """Recompose the written cutouts and measure them against the authority.

    ``sampled_*`` uses the same 4-px grid over authority-opaque pixels and the
    same max-channel error as ``tests/test_layered_face_assets.py``.
    """

    composite = np.zeros_like(authority)
    owners = np.zeros(authority.shape[:2], np.uint8)
    for layer in LAYERS:
        array = _rgba(output / f"{pose}_{layer}.png")
        visible = array[:, :, 3] > 0
        composite[visible] = array[visible]
        owners += visible
    foreground = authority[:, :, 3] > 0
    error = np.abs(composite.astype(np.int16) - authority.astype(np.int16)).max(axis=2)
    step = IDENTITY_SAMPLE_STEP
    grid = np.zeros_like(foreground)
    grid[::step, ::step] = True
    sampled = foreground & grid
    return {
        "mean_error_all_opaque": round(float(error[foreground].mean()), 4),
        "sampled_mean_error": round(float(error[sampled].mean()), 4),
        "sampled_transparent_ratio": round(
            float((composite[:, :, 3][sampled] == 0).mean()), 6
        ),
        "unowned_opaque_pixels": int((foreground & (owners == 0)).sum()),
        "multi_owned_pixels": int((owners > 1).sum()),
        "owned_outside_authority": int((~foreground & (owners > 0)).sum()),
    }


def _write_layers(
    owned: dict[str, np.ndarray],
    authority: np.ndarray,
    output: Path,
    pose: str,
) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for layer in LAYERS:
        cutout = np.zeros_like(authority)
        mask = owned[layer]
        if mask.any():
            cutout[mask] = authority[mask]
        cutout[cutout[:, :, 3] == 0, :3] = 0
        Image.fromarray(cutout, "RGBA").save(output / f"{pose}_{layer}.png", optimize=False)
        counts[layer] = int(np.count_nonzero(cutout[:, :, 3]))
    return counts


def _apply_empty_layers(
    candidates: dict[str, np.ndarray],
    empty_layers: tuple[str, ...],
    decisions: dict[str, dict],
) -> list[str]:
    emptied: list[str] = []
    for layer in empty_layers:
        if layer not in candidates:
            raise ValueError(f"unknown layer in empty_layers: {layer}")
        candidates[layer][:] = False
        emptied.append(layer)
    for layer, decision in decisions.items():
        if decision["empty"] and layer not in emptied:
            candidates[layer][:] = False
            emptied.append(layer)
    return emptied


def build_pose(
    pose: str,
    authority_path: Path,
    old_authority_path: Path,
    mask_source: Path,
    output: Path,
    empty_layers: tuple[str, ...] = DEFAULT_EMPTY_LAYERS,
) -> dict:
    """Build the 25 cutouts for one pose and return its JSON-able report."""

    authority = _rgba(authority_path)
    if authority.shape != (CANVAS, CANVAS, 4):
        raise ValueError(
            f"{authority_path.name}: expected {CANVAS}x{CANVAS} RGBA, got {authority.shape}"
        )
    foreground = authority[:, :, 3] > 0
    matrix, evidence = _alignment(old_authority_path, authority_path)
    warped = _warped_masks(mask_source, pose, matrix, (CANVAS, CANVAS))
    dark_hair = _dark_hair(authority)
    split_y, bun_box = _hair_split_y(dark_hair, evidence["face_box"])
    decisions = _auto_empty_decisions(warped, foreground, dark_hair)
    candidates = {layer: mask & foreground for layer, mask in warped.items()}
    emptied = _apply_empty_layers(candidates, empty_layers, decisions)
    face_skin = _face_zone_skin(authority, evidence["face_box"], dark_hair)
    skin_added_to_base = int((face_skin & ~candidates["base"]).sum())
    candidates["base"] |= face_skin
    # Back hair may only own hair-coloured pixels of the head; the rest of
    # its warped (long-hair) mask lies over the new torso and falls to body.
    candidates["hair_back"] &= dark_hair & (np.indices(foreground.shape)[0] < split_y)
    warped_teeth_tongue = candidates["teeth_tongue"].copy()
    _partition_eye_layers(candidates)
    _rebuild_mouth_partitions(candidates, authority)
    teeth_mode = _partition_teeth_tongue(candidates, warped_teeth_tongue)
    owned = _exclusive_ownership(candidates, foreground, split_y)
    _reclaim_face_pixels(owned, authority)
    counts = _write_layers(owned, authority, output, pose)
    drift = _drift_report(owned)
    return {
        "pose": pose,
        "authority": authority_path.name,
        **{key: value for key, value in evidence.items() if key != "face_box"},
        "hair_body_split_y": int(split_y),
        "bun_bbox": [int(v) for v in bun_box],
        "auto_empty": decisions,
        "empty_layers": emptied,
        "face_zone_skin_added_to_base": skin_added_to_base,
        "teeth_tongue_mode": teeth_mode,
        "layer_pixels": counts,
        "facial_center_escape_px": drift,
        "max_facial_center_escape_px": max(drift.values()),
        "reconstruction": _reconstruction_report(output, pose, authority),
    }


def build(
    authority_dir: Path,
    output: Path,
    mask_source: Path = DEFAULT_MASK_SOURCE,
    mask_authority_dir: Path = DEFAULT_MASK_AUTHORITY_DIR,
    empty_layers: tuple[str, ...] = DEFAULT_EMPTY_LAYERS,
) -> dict:
    """Build all three poses and return the combined report."""

    poses = [
        build_pose(
            pose,
            authority_dir / filename,
            mask_authority_dir / filename,
            mask_source,
            output,
            empty_layers,
        )
        for pose, filename in POSES
    ]
    report = {
        "schema": REPORT_SCHEMA,
        "canvas": CANVAS,
        "layers": len(LAYERS),
        "files": len(LAYERS) * len(POSES),
        "max_anchor_drift_px": MAX_ANCHOR_DRIFT_PIXELS,
        "poses": poses,
    }
    for pose in poses:
        if pose["max_facial_center_escape_px"] > MAX_ANCHOR_DRIFT_PIXELS:
            raise RuntimeError(
                f"{pose['pose']}: facial centre escape "
                f"{pose['max_facial_center_escape_px']} px exceeds calibration"
            )
    return report


def _parse_layers(text: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in text.split(",") if name.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--authority-dir", type=Path, required=True,
        help="目錄內須有新權威 idle.png／idle_lean.png／idle_front.png（1254²）",
    )
    parser.add_argument(
        "--mask-source", type=Path, default=DEFAULT_MASK_SOURCE,
        help="舊 25 層集合，其 alpha 即為權威遮罩",
    )
    parser.add_argument(
        "--mask-authority-dir", type=Path, default=DEFAULT_MASK_AUTHORITY_DIR,
        help="舊遮罩所對應的舊權威肖像目錄（解 YuNet 仿射的來源）",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--empty-layers", default=",".join(DEFAULT_EMPTY_LAYERS),
        help="逗號分隔；新素體沒有的實體層，候選歸零並把像素交還 body",
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="JSON 報告輸出路徑（預設 <output>/../<output 名稱>-report.json）",
    )
    args = parser.parse_args()
    report = build(
        args.authority_dir.resolve(),
        args.output.resolve(),
        mask_source=args.mask_source.resolve(),
        mask_authority_dir=args.mask_authority_dir.resolve(),
        empty_layers=_parse_layers(args.empty_layers),
    )
    report_path = args.report or args.output.resolve().parent / f"{args.output.name}-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for pose in report["poses"]:
        print(json.dumps(pose, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
