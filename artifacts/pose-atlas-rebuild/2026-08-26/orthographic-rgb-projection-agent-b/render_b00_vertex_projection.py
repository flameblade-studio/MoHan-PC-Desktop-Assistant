#!/usr/bin/env python3
"""Rasterize B00-derived vertex colours through candidate3 orthographic views."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

CANVAS = (1024, 1536)
PALETTE = {
    0: (57, 82, 122), 1: (200, 163, 151), 2: (57, 82, 122),
    3: (45, 71, 118), 4: (45, 71, 118), 5: (200, 163, 151),
    6: (46, 74, 122), 7: (46, 74, 122), 8: (200, 163, 151),
    9: (32, 56, 91), 10: (18, 39, 68), 11: (16, 36, 63),
    12: (33, 55, 88), 13: (18, 40, 70), 14: (14, 34, 63),
    255: (34, 61, 99),
}


def file_path(value: str) -> Path:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projections", required=True, type=file_path)
    parser.add_argument("--faces", required=True, type=file_path)
    parser.add_argument("--vertex-parts", required=True, type=file_path)
    parser.add_argument("--b00", required=True, type=file_path)
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--yaw", required=True, action="append", type=int)
    return parser.parse_args()


def load_faces(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t", dtype=np.int32)
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("FAIL_CLOSED_FACE_TOPOLOGY")
    if not np.array_equal(values[:, 0], np.arange(values.shape[0])):
        raise ValueError("FAIL_CLOSED_FACE_INDEX_SEQUENCE")
    return values[:, 1:]


def load_vertex_parts(path: Path, count: int) -> np.ndarray:
    result = np.zeros(count, dtype=np.uint8)
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        seen = 0
        for row in rows:
            index = int(row["vertex_index"])
            if index != seen or index >= count:
                raise ValueError("FAIL_CLOSED_VERTEX_PART_SEQUENCE")
            result[index] = int(row["part_id"])
            seen += 1
    if seen != count:
        raise ValueError("FAIL_CLOSED_VERTEX_PART_COUNT")
    return result


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def load_bundle(root: Path, yaw: int) -> tuple[dict[str, object], Path]:
    manifest = root / view_id(yaw) / "control-bundle.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"FAIL_CLOSED_BUNDLE {manifest}")
    bundle = json.loads(manifest.read_text(encoding="utf-8"))
    if bundle.get("formal_yaw") != yaw or bundle.get("mirror") is not False:
        raise ValueError("FAIL_CLOSED_NON_MIRRORED_YAW_CONTRACT")
    return bundle, manifest


def control(bundle: dict[str, object], key: str) -> Path:
    files = bundle.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(key), dict):
        raise ValueError(f"FAIL_CLOSED_CONTROL {key}")
    record = files[key]
    path = Path(str(record.get("path", "")))
    if not path.is_file() or sha256(path) != record.get("sha256"):
        raise ValueError(f"FAIL_CLOSED_CONTROL_HASH {key}")
    return path


def source_vertex_colours(
    screen_xy: np.ndarray, b00: np.ndarray, parts: np.ndarray
) -> np.ndarray:
    points = np.rint(screen_xy).astype(np.int32)
    x = np.clip(points[:, 0], 0, CANVAS[0] - 1)
    y = np.clip(points[:, 1], 0, CANVAS[1] - 1)
    sampled = b00[y, x]
    colours = sampled[:, :3].astype(np.float32)
    invalid = sampled[:, 3] < 32
    for part, fallback in PALETTE.items():
        replace = invalid & (parts == part)
        colours[replace] = fallback
    colours[invalid & ~np.isin(parts, list(PALETTE))] = PALETTE[0]
    return colours


def rasterize(
    xy: np.ndarray, depth: np.ndarray, faces: np.ndarray,
    vertex_colours: np.ndarray, silhouette: np.ndarray,
    part_id: np.ndarray, normal: np.ndarray,
) -> np.ndarray:
    height, width = silhouette.shape
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    face_depth = depth[faces].mean(axis=1)
    for face_index in np.argsort(face_depth):
        vertex_indices = faces[face_index]
        points = np.rint(xy[vertex_indices]).astype(np.int32)
        colour = np.rint(vertex_colours[vertex_indices].mean(axis=0)).astype(np.uint8)
        cv2.fillConvexPoly(rgb, points, tuple(int(v) for v in colour), lineType=cv2.LINE_8)

    target = silhouette > 0
    empty = target & np.all(rgb == 0, axis=2)
    for current_part, colour in PALETTE.items():
        rgb[empty & (part_id == current_part)] = colour

    normals = normal.astype(np.float32) / 127.5 - 1.0
    light = np.asarray([0.20, 0.25, 0.95], dtype=np.float32)
    light /= np.linalg.norm(light)
    lambert = np.clip((normals * light).sum(axis=2), 0.0, 1.0)
    shaded = rgb.astype(np.float32) * (0.90 + 0.10 * lambert)[..., None]
    shaded[~target] = 0
    return np.dstack((np.clip(shaded, 0, 255).astype(np.uint8), silhouette))


def main() -> int:
    args = parse_args()
    if not args.bundle_root.is_absolute() or not args.output_root.is_absolute():
        raise ValueError("bundle/output roots must be absolute")
    if args.output_root.drive.upper() != "D:":
        raise ValueError("output root must be on D drive")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise FileExistsError("output root must be absent or empty")

    projections = np.load(args.projections)
    yaw_values = projections["yaw_degrees"].astype(int)
    screen = projections["screen_xy"]
    depth = projections["camera_depth"]
    if screen.shape[1:] != (18439, 2):
        raise ValueError("FAIL_CLOSED_PROJECTION_SHAPE")
    faces = load_faces(args.faces)
    parts = load_vertex_parts(args.vertex_parts, screen.shape[1])
    with Image.open(args.b00) as image:
        if image.size != CANVAS or image.mode != "RGBA":
            raise ValueError("FAIL_CLOSED_B00_RGBA")
        b00 = np.asarray(image, dtype=np.uint8).copy()
    zero_indices = np.where(yaw_values == 0)[0]
    if zero_indices.size != 1:
        raise ValueError("FAIL_CLOSED_YAW_ZERO_PROJECTION")
    vertex_colours = source_vertex_colours(screen[zero_indices[0]], b00, parts)

    args.output_root.mkdir(parents=True, exist_ok=False)
    records = []
    for yaw in args.yaw:
        projection_indices = np.where(yaw_values == yaw)[0]
        if projection_indices.size != 1:
            raise ValueError(f"FAIL_CLOSED_YAW_PROJECTION {yaw}")
        bundle, bundle_path = load_bundle(args.bundle_root, yaw)
        silhouette_path = control(bundle, "silhouette")
        depth_path = control(bundle, "depth")
        normal_path = control(bundle, "normal")
        part_id_path = control(bundle, "part_id")
        silhouette = np.asarray(Image.open(silhouette_path).convert("L"), dtype=np.uint8)
        normal = np.asarray(Image.open(normal_path).convert("RGB"), dtype=np.uint8)
        part_id = np.asarray(Image.open(part_id_path).convert("L"), dtype=np.uint8)
        index = projection_indices[0]
        rgba = rasterize(
            screen[index], depth[index], faces, vertex_colours,
            silhouette, part_id, normal,
        )
        output_dir = args.output_root / view_id(yaw)
        output_dir.mkdir()
        outputs = {}
        for label, image_array, mode in (
            ("rgba", rgba, "RGBA"),
            ("depth", np.asarray(Image.open(depth_path).convert("L")), "L"),
            ("normal", normal, "RGB"),
            ("part-id", part_id, "L"),
        ):
            path = output_dir / f"{view_id(yaw)}_{label}.png"
            Image.fromarray(image_array, mode=mode).save(path)
            outputs[label] = {"path": str(path), "sha256": sha256(path)}
        records.append({
            "view_id": view_id(yaw), "yaw": yaw, "mirror": False,
            "bundle": str(bundle_path), "outputs": outputs,
        })

    result = {
        "status": "PASS_ORTHOGRAPHIC_VERTEX_RGB_STAGING",
        "generated_model_used": False,
        "source_b00": {"path": str(args.b00), "sha256": sha256(args.b00)},
        "source_projections": {"path": str(args.projections), "sha256": sha256(args.projections)},
        "source_faces": {"path": str(args.faces), "sha256": sha256(args.faces)},
        "texture_policy": "B00_TO_VERTEX_PROJECTIVE_COLOUR_NO_LOCAL_MATERIAL_TEXTURE_EXISTS",
        "records": records,
    }
    result_path = args.output_root / "render-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
