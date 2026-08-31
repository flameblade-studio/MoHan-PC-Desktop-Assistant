#!/usr/bin/env python3
"""Create a non-generative RGB base from canonical candidate3 raster outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

CANVAS = (1024, 1536)
VIEW_ID = "yaw+000-pitch+00"
PART_FALLBACK = {
    1: (200, 163, 151),  # head/skin; replaced by measured B00 median when present
    2: (57, 82, 122),
    3: (45, 71, 118),
    4: (45, 71, 118),
    5: (200, 163, 151),
    6: (46, 74, 122),
    7: (46, 74, 122),
    8: (200, 163, 151),
    9: (32, 56, 91),
    10: (18, 39, 68),
    11: (16, 36, 63),
    12: (33, 55, 88),
    13: (18, 40, 70),
    14: (14, 34, 63),
    255: (34, 61, 99),
}


def existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=existing_file)
    parser.add_argument("--b00", required=True, type=existing_file)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def load_control(bundle: dict[str, object], key: str) -> Path:
    files = bundle.get("files", {})
    if not isinstance(files, dict) or not isinstance(files.get(key), dict):
        raise ValueError(f"FAIL_CLOSED_MISSING_CONTROL {key}")
    record = files[key]
    path = Path(str(record.get("path", "")))
    if not path.is_file() or sha256(path) != record.get("sha256"):
        raise ValueError(f"FAIL_CLOSED_CONTROL_HASH {key}")
    return path


def save_copy(source: Path, destination: Path, mode: str) -> None:
    with Image.open(source) as image:
        if image.size != CANVAS:
            raise ValueError(f"FAIL_CLOSED_CONTROL_CANVAS {source}")
        image.convert(mode).save(destination)


def main() -> int:
    args = arguments()
    if not args.output_dir.is_absolute() or args.output_dir.drive.upper() != "D:":
        raise ValueError("output directory must be absolute on D drive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError("output directory must be absent or empty")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if (
        bundle.get("schema") != "mohan.canonical_control_bundle.v2"
        or bundle.get("formal_view_id") != VIEW_ID
        or bundle.get("mirror") is not False
    ):
        raise ValueError("FAIL_CLOSED_YAW000_CANONICAL_NON_MIRRORED_BUNDLE_REQUIRED")

    depth_path = load_control(bundle, "depth")
    normal_path = load_control(bundle, "normal")
    silhouette_path = load_control(bundle, "silhouette")
    part_id_path = load_control(bundle, "part_id")

    with Image.open(args.b00) as source_image:
        if source_image.size != CANVAS or source_image.mode != "RGBA":
            raise ValueError("FAIL_CLOSED_APPROVED_B00_1024X1536_RGBA_REQUIRED")
        b00 = np.asarray(source_image, dtype=np.uint8).copy()
    with Image.open(silhouette_path) as image:
        silhouette = np.asarray(image.convert("L"), dtype=np.uint8)
    with Image.open(normal_path) as image:
        normal = np.asarray(image.convert("RGB"), dtype=np.float32) / 127.5 - 1.0
    with Image.open(part_id_path) as image:
        part_id = np.asarray(image.convert("L"), dtype=np.uint8)

    # Candidate3 owns visibility. B00 supplies deterministic projected RGB only
    # where its real alpha says a source pixel exists. Candidate3 is in an
    # A-pose while B00 has lowered arms, so the uncovered limbs are completed
    # from measured per-part B00 colours instead of transparent RGB garbage.
    target = silhouette > 0
    known = target & (b00[..., 3] >= 32)
    missing = target & ~known
    rgb = np.zeros((*silhouette.shape, 3), dtype=np.float32)
    rgb[known] = b00[..., :3][known]
    measured_colours: dict[str, list[int]] = {}
    for current_part, fallback in PART_FALLBACK.items():
        part_pixels = part_id == current_part
        measured = part_pixels & known
        if measured.any():
            colour = np.median(b00[..., :3][measured], axis=0)
        else:
            colour = np.asarray(fallback, dtype=np.float32)
        measured_colours[str(current_part)] = np.rint(colour).astype(int).tolist()
        rgb[part_pixels & missing] = colour

    # Part 0 inside the raster is an unmapped boundary. Keep it visibly safe
    # and deterministic rather than leaking the transparent source RGB.
    rgb[missing & (part_id == 0)] = np.asarray(PART_FALLBACK[2], dtype=np.float32)
    alpha = silhouette.copy()
    light = np.asarray([0.20, 0.25, 0.95], dtype=np.float32)
    light /= np.linalg.norm(light)
    lambert = np.clip((normal * light).sum(axis=2), 0.0, 1.0)
    rgb *= (0.92 + 0.08 * lambert)[..., None]
    rgb[alpha == 0] = 0
    rgba = np.dstack((np.clip(rgb, 0, 255).astype(np.uint8), alpha))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rgba_path = args.output_dir / f"{VIEW_ID}_rgba.png"
    depth_out = args.output_dir / f"{VIEW_ID}_depth.png"
    normal_out = args.output_dir / f"{VIEW_ID}_normal.png"
    part_id_out = args.output_dir / f"{VIEW_ID}_part-id.png"
    Image.fromarray(rgba, mode="RGBA").save(rgba_path)
    save_copy(depth_path, depth_out, "L")
    save_copy(normal_path, normal_out, "RGB")
    save_copy(part_id_path, part_id_out, "L")

    outputs = {}
    for label, path in (
        ("rgba", rgba_path), ("depth", depth_out),
        ("normal", normal_out), ("part_id", part_id_out),
    ):
        with Image.open(path) as image:
            outputs[label] = {
                "path": str(path), "sha256": sha256(path),
                "mode": image.mode, "size": list(image.size),
            }
    result = {
        "status": "PASS_YAW000_ORTHOGRAPHIC_RGB_BASE_STAGING",
        "view_id": VIEW_ID,
        "mirror": False,
        "generated_model_used": False,
        "geometry_source": str(args.bundle),
        "rgb_projection_source": {"path": str(args.b00), "sha256": sha256(args.b00)},
        "texture_policy": "B00_SCREEN_SPACE_PROJECTIVE_ALBEDO_LOCAL_FBX_HAS_UV_BUT_NO_MATERIAL_OR_TEXTURE",
        "projection_coverage": {
            "geometry_pixels": int(target.sum()),
            "b00_valid_pixels": int(known.sum()),
            "part_completed_pixels": int(missing.sum()),
            "measured_part_colours_rgb": measured_colours,
        },
        "outputs": outputs,
    }
    result_path = args.output_dir / "render-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
