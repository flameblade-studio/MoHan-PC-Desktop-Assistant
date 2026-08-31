#!/usr/bin/env python3
"""Composite a refined face without crossing asset ownership boundaries.

The face edit is restricted to ``face_mask AND core_mask`` and explicitly
excludes outfit, hair, and ornament ownership.  Deterministic film grain is a
separate final pass over visible RGB; alpha and all ownership masks are never
modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


CANVAS = (1024, 1536)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--face-refined", type=Path, required=True)
    parser.add_argument("--face-mask", type=Path, required=True)
    parser.add_argument("--core-mask", type=Path, required=True)
    parser.add_argument("--outfit-mask", type=Path, required=True)
    parser.add_argument("--hair-mask", type=Path, required=True)
    parser.add_argument("--ornament-mask", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--grain-sigma", type=float, default=1.25)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    if image.size != CANVAS:
        raise ValueError(f"{path}: expected {CANVAS}, got {image.size}")
    return np.asarray(image, dtype=np.uint8).copy()


def mask(path: Path) -> np.ndarray:
    image = Image.open(path)
    if image.size != CANVAS:
        raise ValueError(f"{path}: expected {CANVAS}, got {image.size}")
    if image.mode == "RGBA":
        channel = np.asarray(image.getchannel("A"), dtype=np.uint8)
    else:
        channel = np.asarray(image.convert("L"), dtype=np.uint8)
    return channel


def save_rgba(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array, "RGBA").save(path)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    base = rgba(args.base)
    refined = rgba(args.face_refined)
    face = mask(args.face_mask)
    core = mask(args.core_mask)
    outfit = mask(args.outfit_mask)
    hair = mask(args.hair_mask)
    ornament = mask(args.ornament_mask)

    protected = np.maximum.reduce((outfit, hair, ornament))
    ownership_overlap = int(
        np.count_nonzero(
            ((outfit > 0).astype(np.uint8)
             + (hair > 0).astype(np.uint8)
             + (ornament > 0).astype(np.uint8)) > 1
        )
    )
    if ownership_overlap:
        raise ValueError(f"ownership masks overlap at {ownership_overlap} pixels")

    allowed = np.minimum(face, core)
    allowed[protected > 0] = 0
    if not np.any(allowed):
        raise ValueError("face mask has no pixels inside unprotected core ownership")

    weight = allowed.astype(np.float32)[..., None] / 255.0
    composited = base.copy()
    blended = np.rint(
        base[..., :3].astype(np.float32) * (1.0 - weight)
        + refined[..., :3].astype(np.float32) * weight
    )
    composited[..., :3] = np.clip(blended, 0, 255).astype(np.uint8)
    composited[..., 3] = base[..., 3]
    composited[base[..., 3] == 0, :3] = 0

    protected_pixels = protected > 0
    protected_diff = int(
        np.max(
            np.abs(
                composited[protected_pixels, :3].astype(np.int16)
                - base[protected_pixels, :3].astype(np.int16)
            )
        ) if np.any(protected_pixels) else 0
    )
    alpha_diff = int(
        np.max(np.abs(composited[..., 3].astype(np.int16) - base[..., 3].astype(np.int16)))
    )
    if protected_diff or alpha_diff:
        raise AssertionError(
            f"face composite crossed boundary: protected_diff={protected_diff}, alpha_diff={alpha_diff}"
        )

    pregrain_path = args.output_dir / "face-only-composited-rgba.png"
    save_rgba(composited, pregrain_path)

    final = composited.copy()
    visible = base[..., 3] > 0
    if args.grain_sigma < 0:
        raise ValueError("grain-sigma must be non-negative")
    if args.grain_sigma:
        generator = np.random.default_rng(args.seed)
        noise = generator.normal(0.0, args.grain_sigma, size=base.shape[:2])
        rgb = final[..., :3].astype(np.float32)
        rgb[visible] += noise[visible, None]
        final[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    final[..., 3] = base[..., 3]
    final[~visible, :3] = 0

    final_alpha_diff = int(
        np.max(np.abs(final[..., 3].astype(np.int16) - base[..., 3].astype(np.int16)))
    )
    if final_alpha_diff:
        raise AssertionError(f"film grain changed alpha: {final_alpha_diff}")

    final_path = args.output_dir / "face-only-composited-filmgrain-rgba.png"
    save_rgba(final, final_path)

    evidence = {
        "accepted": False,
        "formal": False,
        "canvas": [CANVAS[0], CANVAS[1]],
        "face_edit_pixels": int(np.count_nonzero(allowed)),
        "face_edit_outside_core_pixels": int(np.count_nonzero((allowed > 0) & (core == 0))),
        "face_edit_in_protected_pixels": int(np.count_nonzero((allowed > 0) & protected_pixels)),
        "ownership_overlap_pixels": ownership_overlap,
        "pregrain_protected_rgb_max_diff": protected_diff,
        "pregrain_alpha_max_diff": alpha_diff,
        "final_alpha_max_diff": final_alpha_diff,
        "transparent_rgb_nonzero_channels": int(np.count_nonzero(final[~visible, :3])),
        "grain": {"seed": args.seed, "sigma": args.grain_sigma, "scope": "visible_rgb_only"},
        "inputs": {
            "base": {"path": str(args.base.resolve()), "sha256": sha256(args.base)},
            "face_refined": {"path": str(args.face_refined.resolve()), "sha256": sha256(args.face_refined)},
            "face_mask": {"path": str(args.face_mask.resolve()), "sha256": sha256(args.face_mask)},
            "core_mask": {"path": str(args.core_mask.resolve()), "sha256": sha256(args.core_mask)},
            "outfit_mask": {"path": str(args.outfit_mask.resolve()), "sha256": sha256(args.outfit_mask)},
            "hair_mask": {"path": str(args.hair_mask.resolve()), "sha256": sha256(args.hair_mask)},
            "ornament_mask": {"path": str(args.ornament_mask.resolve()), "sha256": sha256(args.ornament_mask)},
        },
        "outputs": {
            "pregrain": {"path": str(pregrain_path.resolve()), "sha256": sha256(pregrain_path)},
            "final": {"path": str(final_path.resolve()), "sha256": sha256(final_path)},
        },
    }
    evidence_path = args.output_dir / "face-only-composite-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
