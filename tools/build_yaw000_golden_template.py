"""Build the deterministic yaw+000 25-layer golden template.

The builder never synthesizes pixels.  It transfers the existing layer masks
to the user-approved RGBA authority and re-cuts authority pixels into mutually
exclusive layers, so recomposition is lossless and checkerboard pixels can
never enter RGB.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy from PIL import Image


VIEW = "yaw+000-pitch+00"
# Rows above this line default to hair_back ownership; rows below to body.
HAIR_BODY_SPLIT_Y = 410
LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)


def _rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not xs.size:
        raise ValueError("empty authority alpha")
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


def _partition_eye_layers(candidates: dict[str, np.ndarray]) -> None:
    """Split overlapping legacy eye supports into deterministic disjoint layers."""
    yy, xx = np.indices(next(iter(candidates.values())).shape)
    for side in ("left", "right"):
        names = (f"iris_{side}", f"eyelid_{side}", f"eyeliner_{side}")
        support = np.logical_or.reduce([candidates[name] for name in names])
        x0, y0, x1, y1 = _bbox(support)
        width, height = x1 - x0, y1 - y0
        liner_bottom = y0 + max(1, int(round(height * 0.20)))
        eyeliner = support & (yy < liner_bottom)
        cx, cy = x0 + (width - 1) * 0.50, y0 + (height - 1) * 0.58
        rx, ry = max(2.0, width * 0.22), max(2.0, height * 0.30)
        iris = support & ((((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) <= 1.0)
        iris &= ~eyeliner
        eyelid = support & ~eyeliner & ~iris
        if not eyeliner.any() or not iris.any() or not eyelid.any():
            raise RuntimeError(f"failed to partition {side} eye support")
        candidates[f"eyeliner_{side}"] = eyeliner
        candidates[f"iris_{side}"] = iris
        candidates[f"eyelid_{side}"] = eyelid


def _bbox_affine(src_alpha: np.ndarray, dst_alpha: np.ndarray) -> np.ndarray:
    sx0, sy0, sx1, sy1 = _bbox(src_alpha > 0)
    dx0, dy0, dx1, dy1 = _bbox(dst_alpha > 0)
    scale_x = (dx1 - dx0) / float(sx1 - sx0)
    scale_y = (dy1 - dy0) / float(sy1 - sy0)
    return np.array([[scale_x, 0.0, dx0 - scale_x * sx0],
                     [0.0, scale_y, dy0 - scale_y * sy0]], dtype=np.float32)


def _warp_mask(mask: np.ndarray, matrix: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.warpAffine(mask.astype(np.uint8), matrix, size,
                          flags=cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _warped_layer_candidates(
    layer_dir: Path,
    matrix: np.ndarray,
    foreground: np.ndarray,
) -> dict[str, np.ndarray]:
    h, w = foreground.shape
    candidates: dict[str, np.ndarray] = {}
    for layer in LAYERS:
        source = _rgba(layer_dir / f"{VIEW}_{layer}.png")
        candidates[layer] = _warp_mask(source[:, :, 3] > 0, matrix, (w, h)) & foreground

    # The neutral frame intentionally has no visible teeth/tongue.
    candidates["teeth_tongue"][:] = False

    # Ornament is rigid jewellery only.  Explicitly subtract the facial skin
    # support and a two-pixel guard band so it can never carry face pixels.
    face_support = candidates["base"] | candidates["jaw"]
    face_guard = cv2.dilate(face_support.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    candidates["ornament"] &= ~face_guard
    return candidates


def _darkest_oral_band(
    inner: np.ndarray,
    authority: np.ndarray,
    yy: np.ndarray,
    y_mid: int,
) -> np.ndarray:
    mouth_rgb = authority[:, :, :3].astype(np.int16)
    luminance = (54 * mouth_rgb[:, :, 2] + 183 * mouth_rgb[:, :, 1] +
                 19 * mouth_rgb[:, :, 0]) // 256
    oral = inner & (yy >= y_mid - 1) & (yy <= y_mid + 1)
    if np.any(oral):
        threshold = int(np.percentile(luminance[oral], 55))
        oral &= luminance <= threshold
    return oral


def _clamp_oral_to_lips(
    oral: np.ndarray,
    upper: np.ndarray,
    lower: np.ndarray,
    xx: np.ndarray,
    yy: np.ndarray,
    y_mid: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lx0, ly0, lx1, ly1 = _bbox(upper | lower)
    kept_oral = oral & (xx >= lx0) & (xx < lx1) & (yy >= ly0) & (yy < ly1)
    rejected_oral = oral & ~kept_oral
    upper = upper | (rejected_oral & (yy < y_mid))
    lower = lower | (rejected_oral & (yy >= y_mid))
    return kept_oral, upper, lower


def _rebuild_mouth_partitions(
    candidates: dict[str, np.ndarray],
    authority: np.ndarray,
) -> None:
    h, w = authority.shape[:2]
    # Rebuild the closed neutral mouth deterministically from authority pixels.
    # The current upper/lower masks are identical; split the shared support at
    # its vertical median, then reserve the darkest central strip as the oral
    # cavity.  This yields distinct upper/lower layers without invented pixels.
    mouth = (candidates["lip_upper"] | candidates["lip_lower"] |
             candidates["corner_left"] | candidates["corner_right"])
    x0, y0, x1, y1 = _bbox(mouth)
    yy, xx = np.indices((h, w))
    y_mid = int(round(float(np.median(np.where(mouth)[0]))))
    corner_width = max(2, int(round((x1 - x0) * 0.12)))
    corner_left = mouth & (xx < x0 + corner_width)
    corner_right = mouth & (xx >= x1 - corner_width)
    inner = mouth & ~corner_left & ~corner_right
    oral = _darkest_oral_band(inner, authority, yy, y_mid)
    upper = inner & (yy < y_mid) & ~oral
    lower = inner & (yy >= y_mid) & ~oral
    kept_oral, upper, lower = _clamp_oral_to_lips(oral, upper, lower, xx, yy, y_mid)
    if not upper.any() or not lower.any() or not corner_left.any() or not corner_right.any():
        raise RuntimeError("failed to partition mouth support")
    candidates["oral_cavity"] = kept_oral
    candidates["lip_upper"] = upper
    candidates["lip_lower"] = lower
    candidates["corner_left"] = corner_left
    candidates["corner_right"] = corner_right


def _exclusive_ownership(
    candidates: dict[str, np.ndarray],
    foreground: np.ndarray,
) -> dict[str, np.ndarray]:
    h, w = foreground.shape
    # Exclusive ownership is required for lossless alpha recomposition.
    # Fine features win over skin/hair/body.  Missing one-pixel authority edge
    # samples caused by registration are assigned to a deterministic substrate.
    priority = (
        "ornament", "brow_left", "brow_right", "eyeliner_left", "eyeliner_right",
        "eyelid_left", "eyelid_right", "iris_left", "iris_right", "blush_left",
        "blush_right", "corner_left", "corner_right", "lip_upper", "lip_lower",
        "oral_cavity", "jaw", "base", "hair_left", "hair_right", "sleeve_left",
        "sleeve_right", "hair_back", "body",
    )
    owned: dict[str, np.ndarray] = {name: np.zeros((h, w), bool) for name in LAYERS}
    claimed = np.zeros((h, w), bool)
    for name in priority:
        own = candidates[name] & ~claimed
        owned[name] = own
        claimed |= own
    missing = foreground & ~claimed
    yy = np.indices((h, w))[0]
    owned["hair_back"] |= missing & (yy < HAIR_BODY_SPLIT_Y)
    owned["body"] |= missing & (yy >= HAIR_BODY_SPLIT_Y)
    return owned


def build(repo: Path, output: Path) -> dict:
    canonical_path = repo / "assets/pose-atlas/v4" / f"{VIEW}.png"
    authority_path = repo / "assets/pose-atlas/v4-working" / (
        f"{VIEW}.user-approved-generated-alpha-clean-v3-20260823.png"
    )
    layer_dir = repo / "assets/pose-atlas/v4-layered"
    canonical = _rgba(canonical_path)
    authority = _rgba(authority_path)
    if authority.shape != (1536, 1024, 4):
        raise ValueError(f"authority shape must be 1536x1024 RGBA, got {authority.shape}")
    h, w = authority.shape[:2]
    foreground = authority[:, :, 3] > 0
    matrix = _bbox_affine(canonical[:, :, 3], authority[:, :, 3])

    candidates = _warped_layer_candidates(layer_dir, matrix, foreground)

    # Legacy eye masks overlap exactly.  Assign every authority pixel once so
    # blink and gaze layers remain independently addressable at runtime.
    _partition_eye_layers(candidates)

    _rebuild_mouth_partitions(candidates, authority)

    # The legacy ornament mask also contains fragments of the facial feature
    # masks.  Ornament owns only rigid jewellery: it must never pre-empt eyes,
    # brows, blush or mouth pixels.  Subtract the deterministic feature union
    # after the eye/mouth partitions have been rebuilt so every removed pixel
    # is retained by its semantic facial layer during exclusive ownership.
    facial_features = np.logical_or.reduce([
        candidates[name] for name in (
            "brow_left", "brow_right", "eyeliner_left", "eyeliner_right",
            "eyelid_left", "eyelid_right", "iris_left", "iris_right",
            "blush_left", "blush_right", "corner_left", "corner_right",
            "lip_upper", "lip_lower", "oral_cavity",
        )
    ])
    candidates["ornament"] &= ~facial_features

    owned = _exclusive_ownership(candidates, foreground)

    output.mkdir(parents=True, exist_ok=True)
    records = []
    for name in LAYERS:
        out = np.zeros_like(authority)
        if np.any(owned[name]):
            out[owned[name]] = authority[owned[name]]
        out[out[:, :, 3] == 0, :3] = 0
        path = output / f"{VIEW}_{name}.png"
        Image.fromarray(out, "RGBA").save(path, optimize=False)
        records.append({
            "layer": name,
            "path": str(path),
            "alpha_pixels": int(np.count_nonzero(out[:, :, 3])),
            "mode": "transparent-neutral" if name == "teeth_tongue" else "authority-pixel-recut",
        })

    action_manifest = {
        "schema": "mohan.yaw000-golden-action.v1",
        "view_id": VIEW,
        "authority": {
            "path": str(authority_path), "sha256": _sha256(authority_path),
            "qualification": "user-approved, Pillow RGBA, alpha-clean v3",
        },
        "registration": {"method": "alpha-bbox affine mask transfer", "matrix": matrix.tolist()},
        "actions": {
            "deterministic_recut": [name for name in LAYERS if name != "teeth_tongue"],
            "preserve_transparent_neutral": ["teeth_tongue"],
            "generative_redraw": [],
            "special_contract_repairs": {
                "lip_upper/lip_lower": "split authority mouth support; masks and hashes must differ",
                "oral_cavity": "dark central mouth seam aligned inside combined lip support",
                "ornament": "authority jewellery pixels with dilated base/jaw face support removed",
            },
        },
        "output": str(output),
        "records": records,
    }
    manifest_path = output.parent / "action-manifest.json"
    manifest_path.write_text(json.dumps(action_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return action_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.repo / "work/full-body-yaw000-golden/layers"
    manifest = build(args.repo.resolve(), output.resolve())
    print(json.dumps({"output": manifest["output"], "layers": len(manifest["records"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
