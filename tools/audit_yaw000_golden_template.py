"""Fail-closed audit for the yaw+000 25-layer golden template."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

lazy from build_yaw000_golden_template import LAYERS, VIEW


def _rgba(path: Path) -> np.ndarray:
    image = Image.open(path)
    if image.mode != "RGBA":
        raise ValueError(f"{path.name}: expected RGBA, got {image.mode}")
    return np.asarray(image, dtype=np.uint8)


def _hash_pixels(array: np.ndarray) -> str:
    return hashlib.sha256(array.tobytes()).hexdigest()


def _bbox(mask: np.ndarray):
    ys, xs = np.where(mask)
    return None if not xs.size else [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def _intersects(a, b) -> bool:
    return bool(a and b and max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]))


def audit(repo: Path, layer_dir: Path) -> dict:
    authority_path = repo / "assets/pose-atlas/v4-working" / (
        f"{VIEW}.user-approved-generated-alpha-clean-v3-20260823.png"
    )
    authority = _rgba(authority_path)
    failures: list[str] = []
    layers = {}
    alpha_sum = np.zeros(authority.shape[:2], np.uint16)
    reconstruction = np.zeros_like(authority)
    for name in LAYERS:
        path = layer_dir / f"{VIEW}_{name}.png"
        if not path.is_file():
            failures.append(f"missing:{name}")
            continue
        arr = _rgba(path)
        if arr.shape != (1536, 1024, 4):
            failures.append(f"shape:{name}:{arr.shape}")
            continue
        alpha = arr[:, :, 3]
        contamination = int(np.count_nonzero((alpha == 0) & np.any(arr[:, :, :3] != 0, axis=2)))
        if contamination:
            failures.append(f"transparent_rgb:{name}:{contamination}")
        count = int(np.count_nonzero(alpha))
        if name != "teeth_tongue" and count == 0:
            failures.append(f"blank:{name}")
        if name == "teeth_tongue" and count != 0:
            failures.append("teeth_tongue:not-neutral-transparent")
        overlap = (alpha_sum > 0) & (alpha > 0)
        if np.any(overlap):
            failures.append(f"layer_overlap:{name}:{int(np.count_nonzero(overlap))}")
        use = alpha > 0
        reconstruction[use] = arr[use]
        alpha_sum += use.astype(np.uint16)
        layers[name] = {"alpha_pixels": count, "bbox": _bbox(use), "pixel_hash": _hash_pixels(arr)}

    if len(layers) == len(LAYERS):
        diff = np.abs(reconstruction.astype(np.int16) - authority.astype(np.int16))
        diff_pixels = int(np.count_nonzero(np.any(diff != 0, axis=2)))
        max_error = int(diff.max())
        if diff_pixels or max_error:
            failures.append(f"recompose:{diff_pixels}:max={max_error}")

        if layers["lip_upper"]["pixel_hash"] == layers["lip_lower"]["pixel_hash"]:
            failures.append("lip_upper_lower_identical")
        lip_mask = (_rgba(layer_dir / f"{VIEW}_lip_upper.png")[:, :, 3] > 0) | (_rgba(layer_dir / f"{VIEW}_lip_lower.png")[:, :, 3] > 0)
        oral_mask = _rgba(layer_dir / f"{VIEW}_oral_cavity.png")[:, :, 3] > 0
        if not _intersects(_bbox(lip_mask), _bbox(oral_mask)):
            failures.append("oral_cavity_not_aligned")
        # The oral cavity may own the seam, so require adjacency/containment in
        # the combined mouth envelope rather than alpha overlap.
        mouth_envelope = np.zeros_like(lip_mask)
        lip_box = _bbox(lip_mask)
        if lip_box:
            mouth_envelope[lip_box[1]:lip_box[3], lip_box[0]:lip_box[2]] = True
        if np.any(oral_mask & ~mouth_envelope):
            failures.append("oral_cavity_outside_lip_envelope")

        ornament = _rgba(layer_dir / f"{VIEW}_ornament.png")[:, :, 3] > 0
        face = (_rgba(layer_dir / f"{VIEW}_base.png")[:, :, 3] > 0) | (_rgba(layer_dir / f"{VIEW}_jaw.png")[:, :, 3] > 0)
        if np.any(ornament & face):
            failures.append(f"ornament_face_overlap:{int(np.count_nonzero(ornament & face))}")

        lip_rgba = reconstruction.copy()
        lip_region = lip_mask | oral_mask
        rgb = lip_rgba[:, :, :3]
        # Cyan/green contaminant: green materially exceeds both red and blue.
        green_cyan = lip_region & (rgb[:, :, 1].astype(int) > rgb[:, :, 0].astype(int) + 18) & (rgb[:, :, 1].astype(int) > rgb[:, :, 2].astype(int) + 10)
        green_count = int(np.count_nonzero(green_cyan))
        if green_count:
            failures.append(f"lip_green_cyan:{green_count}")

        fg = reconstruction[:, :, 3] > 0
        bottom = _bbox(fg)[3] if _bbox(fg) else 0
        if bottom >= authority.shape[0]:
            failures.append(f"shoe_bottom_clipped:{bottom}")
    else:
        diff_pixels = None
        max_error = None
        green_count = None
        bottom = None

    report = {
        "schema": "mohan.yaw000-golden-audit.v1", "view_id": VIEW,
        "passed": not failures, "failures": failures, "layer_count": len(layers),
        "metrics": {"recompose_diff_pixels": diff_pixels, "recompose_max_channel_error": max_error,
                    "lip_green_cyan_pixels": green_count, "foreground_bottom_exclusive": bottom},
        "layers": layers,
    }
    out = layer_dir.parent / "audit-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--layers", type=Path)
    args = parser.parse_args()
    layer_dir = args.layers or args.repo / "work/full-body-yaw000-golden/layers"
    report = audit(args.repo.resolve(), layer_dir.resolve())
    print(json.dumps({"passed": report["passed"], "failures": report["failures"], "metrics": report["metrics"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
