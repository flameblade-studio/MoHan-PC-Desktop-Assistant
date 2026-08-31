#!/usr/bin/env python3
"""Render a B00-coloured MHR mesh with back-face culling and a real z-buffer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

WIDTH, HEIGHT = 1024, 1536
MARGIN = 24.0
ARM_BONE_TOKENS = (
    "uparm", "lowarm", "wrist", "thumb", "index", "middle", "ring", "pinky"
)


def existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise argparse.ArgumentTypeError(f"expected existing absolute file: {value}")
    return path


def absent_output(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or path.drive.upper() != "D:":
        raise argparse.ArgumentTypeError("output must be an absolute D-drive path")
    if path.exists():
        raise argparse.ArgumentTypeError("output directory must not exist")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices", required=True, type=existing_file)
    parser.add_argument("--faces", required=True, type=existing_file)
    parser.add_argument("--skin-weights", required=True, type=existing_file)
    parser.add_argument("--vertex-parts", required=True, type=existing_file)
    parser.add_argument("--b00", required=True, type=existing_file)
    parser.add_argument("--jaw13-candidates", required=True, type=existing_file)
    parser.add_argument("--step16-identity", required=True, type=existing_file)
    parser.add_argument("--idle-front", required=True, type=existing_file)
    parser.add_argument("--idle-lean", required=True, type=existing_file)
    parser.add_argument("--profile-062", required=True, type=existing_file)
    parser.add_argument("--output-root", required=True, type=absent_output)
    parser.add_argument("--yaw", required=True, type=int, choices=range(-180, 180))
    parser.add_argument("--arm-drop-degrees", type=float, default=42.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def load_vertices(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:8] != b"MHRVRTX1":
        raise ValueError("FAIL_CLOSED_VERTEX_MAGIC")
    count = struct.unpack_from("<I", data, 8)[0]
    vertices = np.frombuffer(data, dtype="<f8", offset=12).reshape(count, 3).copy()
    if count != 18439 or not np.isfinite(vertices).all():
        raise ValueError("FAIL_CLOSED_VERTEX_PAYLOAD")
    return vertices


def load_faces(path: Path, vertex_count: int) -> np.ndarray:
    table = np.loadtxt(path, delimiter="\t", dtype=np.int32)
    if table.ndim != 2 or table.shape[1] != 4:
        raise ValueError("FAIL_CLOSED_FACE_TOPOLOGY")
    if not np.array_equal(table[:, 0], np.arange(table.shape[0])):
        raise ValueError("FAIL_CLOSED_FACE_SEQUENCE")
    faces = table[:, 1:]
    if faces.min() < 0 or faces.max() >= vertex_count:
        raise ValueError("FAIL_CLOSED_FACE_VERTEX_RANGE")
    return faces


def load_parts(path: Path, vertex_count: int) -> np.ndarray:
    parts = np.full(vertex_count, 255, dtype=np.uint8)
    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        for expected, row in enumerate(rows):
            index = int(row["vertex_index"])
            if index != expected:
                raise ValueError("FAIL_CLOSED_PART_SEQUENCE")
            parts[index] = int(row["part_id"])
    if expected + 1 != vertex_count:
        raise ValueError("FAIL_CLOSED_PART_COUNT")
    return parts


def load_arm_influences(path: Path, vertex_count: int) -> tuple[np.ndarray, np.ndarray]:
    left = np.zeros(vertex_count, dtype=np.float64)
    right = np.zeros(vertex_count, dtype=np.float64)
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            bone = row["bone_name"]
            if not any(token in bone for token in ARM_BONE_TOKENS):
                continue
            target = left if bone.startswith("l_") else right if bone.startswith("r_") else None
            if target is not None:
                target[int(row["vertex_index"])] += float(row["weight"])
    np.clip(left, 0.0, 1.0, out=left)
    np.clip(right, 0.0, 1.0, out=right)
    if np.count_nonzero(left) < 3000 or np.count_nonzero(right) < 3000:
        raise ValueError("FAIL_CLOSED_ARM_SKIN_WEIGHTS")
    return left, right


def rotate_xy_about(points: np.ndarray, pivot: np.ndarray, degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    result = points.copy()
    delta = points[:, :2] - pivot[:2]
    result[:, 0] = pivot[0] + delta[:, 0] * cosine - delta[:, 1] * sine
    result[:, 1] = pivot[1] + delta[:, 0] * sine + delta[:, 1] * cosine
    return result


def natural_arm_pose(
    vertices: np.ndarray, left_weight: np.ndarray, right_weight: np.ndarray, drop: float
) -> np.ndarray:
    posed = vertices.copy()
    for weights, x_sign, angle in (
        (left_weight, 1.0, -drop),
        (right_weight, -1.0, drop),
    ):
        # Candidate3 is an A-pose. Its actual shoulder centres are near +/-20, 136.
        shoulder_vertices = vertices[(np.sign(vertices[:, 0]) == x_sign) & (vertices[:, 1] > 130.0)]
        shoulder_x = x_sign * float(np.quantile(np.abs(shoulder_vertices[:, 0]), 0.28))
        pivot = np.asarray([shoulder_x, 136.0, 4.0], dtype=np.float64)
        rotated = rotate_xy_about(vertices, pivot, angle)
        blend = weights[:, None]
        posed = posed * (1.0 - blend) + rotated * blend
    return posed


def yaw_rotation(yaw: int) -> np.ndarray:
    angle = math.radians(yaw)
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.asarray(
        [[cosine, 0.0, sine], [0.0, 1.0, 0.0], [-sine, 0.0, cosine]],
        dtype=np.float64,
    )


def projection_contract(vertices: np.ndarray) -> tuple[float, float]:
    radial = np.sqrt(vertices[:, 0] ** 2 + vertices[:, 2] ** 2).max()
    y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
    scale = min((WIDTH - 2 * MARGIN) / (2 * radial), (HEIGHT - 2 * MARGIN) / (y_max - y_min))
    return float(scale), float(0.5 * (y_min + y_max))


def project(vertices: np.ndarray, yaw: int, scale: float, y_center: float) -> tuple[np.ndarray, np.ndarray]:
    camera = vertices @ yaw_rotation(yaw).T
    xy = np.column_stack(
        (WIDTH * 0.5 + camera[:, 0] * scale, HEIGHT * 0.5 - (camera[:, 1] - y_center) * scale)
    )
    return camera, xy


def authority_jaw_target() -> np.ndarray:
    """Return the measured Step16/idle jaw arc, corrected by the 062 profile.

    These are normalized contour coordinates, not MediaPipe or FLAME indices.
    The 13 real MHR c_jaw vertices only provide topology correspondence.  The
    target shape was measured from the owner-approved Step16/idle face and the
    forehead/nose/lip/chin transition was checked against 062.
    """
    return np.asarray(
        [
            (0.55, 0.73), (0.58, 0.81), (0.62, 0.88), (0.66, 0.94),
            (0.70, 0.98), (0.74, 1.00), (0.78, 0.995), (0.82, 0.98),
            (0.86, 0.95), (0.89, 0.91), (0.92, 0.86), (0.945, 0.80),
            (0.96, 0.73),
        ],
        dtype=np.float64,
    )


def apply_authority_jaw13(
    vertices: np.ndarray,
    parts: np.ndarray,
    yaw: int,
    scale: float,
    y_center: float,
    candidates_path: Path,
) -> tuple[np.ndarray, dict[str, object]]:
    """Move the actual lower-face surface using 13 real topology anchors.

    A regularised thin-plate spline transfers the authority contour to nearby
    lower-face vertices.  The deformation is applied in camera space, then
    transformed back to mesh space before normals and rasterisation.
    """
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    if payload.get("formal_yaw") != yaw or payload.get("candidate_count") != 13:
        raise ValueError("FAIL_CLOSED_JAW13_VIEW")
    if "MESH_CANDIDATE" not in payload.get("truth_boundary", ""):
        raise ValueError("FAIL_CLOSED_JAW13_TRUTH_BOUNDARY")
    ids = np.asarray([int(item["vertex_id"]) for item in payload["candidates"]], dtype=np.int32)
    if len(np.unique(ids)) != 13 or ids.min() < 0 or ids.max() >= len(vertices):
        raise ValueError("FAIL_CLOSED_JAW13_VERTEX_IDS")

    rotation = yaw_rotation(yaw)
    camera = vertices @ rotation.T
    xy = np.column_stack(
        (WIDTH * 0.5 + camera[:, 0] * scale, HEIGHT * 0.5 - (camera[:, 1] - y_center) * scale)
    )
    head_xy = xy[parts == 1]
    head_min, head_max = head_xy.min(axis=0), head_xy.max(axis=0)
    target_norm = authority_jaw_target()
    target = head_min + target_norm * (head_max - head_min)
    source = xy[ids]

    anchor_displacement = target - source
    anchor_length = np.linalg.norm(anchor_displacement, axis=1, keepdims=True)
    # The authority may be a different crop and must never drag topology by
    # dozens of pixels.  Six pixels is enough to alter the real silhouette at
    # 1024px while preserving the MHR surface and rotation continuity.
    anchor_displacement *= np.minimum(1.0, 6.0 / np.maximum(anchor_length, 1e-9))
    head_indices = np.flatnonzero(parts == 1)
    query = xy[head_indices]
    query_radius = np.linalg.norm(query[:, None, :] - source[None, :, :], axis=2)
    local_weight = np.exp(-0.5 * (query_radius / 18.0) ** 2)
    displacement = (local_weight @ anchor_displacement) / np.maximum(
        local_weight.sum(axis=1, keepdims=True), 1e-9
    )
    locality = np.clip(1.0 - query_radius.min(axis=1) / 32.0, 0.0, 1.0)
    displacement *= locality[:, None]
    # Affect only the lower face.  Scalp and forehead remain untouched.
    lower_start = head_min[1] + 0.57 * (head_max[1] - head_min[1])
    lower_full = head_min[1] + 0.76 * (head_max[1] - head_min[1])
    taper = np.clip((query[:, 1] - lower_start) / max(lower_full - lower_start, 1e-6), 0.0, 1.0)
    taper = taper * taper * (3.0 - 2.0 * taper)
    displacement *= taper[:, None]
    camera[head_indices, 0] += displacement[:, 0] / scale
    camera[head_indices, 1] -= displacement[:, 1] / scale
    deformed = camera @ rotation

    _, after_xy = project(deformed, yaw, scale, y_center)
    movement = np.linalg.norm(after_xy[ids] - source, axis=1)
    return deformed, {
        "candidate_vertex_ids": ids.tolist(),
        "target_source": "Step16+idle_front+idle_lean authority contour; 062 profile curve correction",
        "mapping_scope": "MHR topology correspondence only; not MediaPipe/FLAME landmarks",
        "candidate_mean_movement_px": float(movement.mean()),
        "candidate_max_movement_px": float(movement.max()),
    }


def semantic_colours(parts: np.ndarray) -> np.ndarray:
    """Clean colour ownership cues; never project B00 facial pixels onto mesh."""
    colours = np.tile(np.asarray([42, 75, 122], dtype=np.float64), (len(parts), 1))
    colours[np.isin(parts, (1, 5, 8))] = np.asarray([205, 174, 160], dtype=np.float64)
    colours[parts == 2] = np.asarray([235, 238, 242], dtype=np.float64)
    colours[np.isin(parts, (10, 11, 13, 14))] = np.asarray([226, 230, 236], dtype=np.float64)
    colours[parts == 255] = np.asarray([38, 68, 112], dtype=np.float64)
    return colours


def smooth_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    face_normals = np.cross(b - a, c - a)
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], face_normals)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals /= np.maximum(lengths, 1e-12)
    return normals


def rasterize(
    camera: np.ndarray,
    xy: np.ndarray,
    faces: np.ndarray,
    colours: np.ndarray,
    vertex_normals: np.ndarray,
    parts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    rgba = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    depth_buffer = np.full((HEIGHT, WIDTH), -np.inf, dtype=np.float64)
    normal_buffer = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float64)
    part_buffer = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    # Caller supplies normals already rotated into the same camera coordinates.
    camera_normals = vertex_normals
    face_a, face_b, face_c = camera[faces[:, 0]], camera[faces[:, 1]], camera[faces[:, 2]]
    face_normals = np.cross(face_b - face_a, face_c - face_a)
    front_facing = face_normals[:, 2] > 1e-10
    drawn = 0
    rejected = int(np.count_nonzero(~front_facing))

    for face_index in np.flatnonzero(front_facing):
        indices = faces[face_index]
        tri = xy[indices]
        min_x = max(0, int(math.floor(float(tri[:, 0].min()))))
        max_x = min(WIDTH - 1, int(math.ceil(float(tri[:, 0].max()))))
        min_y = max(0, int(math.floor(float(tri[:, 1].min()))))
        max_y = min(HEIGHT - 1, int(math.ceil(float(tri[:, 1].max()))))
        if min_x > max_x or min_y > max_y:
            continue
        x0, y0 = tri[0]
        x1, y1 = tri[1]
        x2, y2 = tri[2]
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denominator) < 1e-10:
            continue
        grid_y, grid_x = np.mgrid[min_y : max_y + 1, min_x : max_x + 1]
        sample_x = grid_x + 0.5
        sample_y = grid_y + 0.5
        w0 = ((y1 - y2) * (sample_x - x2) + (x2 - x1) * (sample_y - y2)) / denominator
        w1 = ((y2 - y0) * (sample_x - x2) + (x0 - x2) * (sample_y - y2)) / denominator
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-8) & (w1 >= -1e-8) & (w2 >= -1e-8)
        if not np.any(inside):
            continue
        z = w0 * camera[indices[0], 2] + w1 * camera[indices[1], 2] + w2 * camera[indices[2], 2]
        local_depth = depth_buffer[min_y : max_y + 1, min_x : max_x + 1]
        update = inside & (z > local_depth)
        if not np.any(update):
            continue
        local_depth[update] = z[update]
        weights = np.stack((w0, w1, w2), axis=-1)
        interpolated_colour = weights @ colours[indices]
        local_rgba = rgba[min_y : max_y + 1, min_x : max_x + 1]
        interpolated_normal = weights @ camera_normals[indices]
        length = np.linalg.norm(interpolated_normal, axis=-1, keepdims=True)
        interpolated_normal /= np.maximum(length, 1e-12)
        light = np.clip(0.78 + 0.22 * interpolated_normal[..., 2:3], 0.62, 1.0)
        shaded_colour = interpolated_colour * light
        local_rgba[update, :3] = np.clip(shaded_colour[update], 0, 255).astype(np.uint8)
        local_rgba[update, 3] = 255
        normal_buffer[min_y : max_y + 1, min_x : max_x + 1][update] = interpolated_normal[update]
        dominant_corner = np.argmax(weights, axis=-1)
        triangle_parts = parts[indices]
        interpolated_parts = triangle_parts[dominant_corner]
        part_buffer[min_y : max_y + 1, min_x : max_x + 1][update] = interpolated_parts[update]
        drawn += 1

    visible = np.isfinite(depth_buffer)
    depth_image = np.zeros((HEIGHT, WIDTH), dtype=np.uint16)
    if np.any(visible):
        near, far = depth_buffer[visible].min(), depth_buffer[visible].max()
        scaled = (depth_buffer[visible] - near) / max(far - near, 1e-12)
        depth_image[visible] = np.rint(1 + scaled * 65534).astype(np.uint16)
    normal_image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    normal_image[visible] = np.rint((normal_buffer[visible] * 0.5 + 0.5) * 255).astype(np.uint8)
    return rgba, depth_image, normal_image, part_buffer, {
        "triangles_total": int(len(faces)),
        "triangles_backface_culled": rejected,
        "triangles_rasterized": drawn,
        "visible_pixels": int(np.count_nonzero(visible)),
    }


def checker_composite(rgba: np.ndarray) -> Image.Image:
    y, x = np.mgrid[:HEIGHT, :WIDTH]
    checker = np.where(((x // 32 + y // 32) % 2)[..., None] == 0, 220, 180).astype(np.uint8)
    checker = np.repeat(checker, 3, axis=2)
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba[..., :3].astype(np.float32) * alpha + checker.astype(np.float32) * (1.0 - alpha)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def build_contact(rgba: np.ndarray, depth: np.ndarray, normal: np.ndarray, part_id: np.ndarray, yaw: int) -> Image.Image:
    panels = [
        ("RGBA / checker", checker_composite(rgba)),
        ("z-buffer depth", Image.fromarray((depth >> 8).astype(np.uint8), "L").convert("RGB")),
        ("front normals", Image.fromarray(normal, "RGB")),
        ("part ID", Image.fromarray((part_id.astype(np.uint16) * 17 % 256).astype(np.uint8), "L").convert("RGB")),
    ]
    contact = Image.new("RGB", (1024, 1664), (24, 28, 34))
    draw = ImageDraw.Draw(contact)
    draw.text((16, 12), f"{view_id(yaw)} | natural arms | backface cull + pixel z-buffer", fill="white")
    for index, (label, panel) in enumerate(panels):
        thumb = panel.copy()
        thumb.thumbnail((496, 768))
        left = 8 + (index % 2) * 508
        top = 48 + (index // 2) * 808
        contact.paste(thumb, (left, top))
        draw.text((left + 4, top + 772), label, fill="white")
    return contact


def main() -> int:
    args = parse_args()
    vertices = load_vertices(args.vertices)
    faces = load_faces(args.faces, len(vertices))
    parts = load_parts(args.vertex_parts, len(vertices))
    left, right = load_arm_influences(args.skin_weights, len(vertices))
    posed = natural_arm_pose(vertices, left, right, args.arm_drop_degrees)
    scale, y_center = projection_contract(posed)
    with Image.open(args.b00) as image:
        if image.size != (WIDTH, HEIGHT) or image.mode != "RGBA":
            raise ValueError("FAIL_CLOSED_B00_RGBA")
        b00 = np.asarray(image, dtype=np.uint8).copy()
    for authority_path in (args.step16_identity, args.idle_front, args.idle_lean, args.profile_062):
        with Image.open(authority_path) as authority:
            authority.verify()
    posed, jaw_contract = apply_authority_jaw13(
        posed, parts, args.yaw, scale, y_center, args.jaw13_candidates
    )
    colours = semantic_colours(parts)
    camera, xy = project(posed, args.yaw, scale, y_center)
    normals = smooth_vertex_normals(posed, faces) @ yaw_rotation(args.yaw).T
    rgba, depth, normal, part_id, statistics = rasterize(camera, xy, faces, colours, normals, parts)
    if np.count_nonzero(rgba[..., 3]) < 40000:
        raise ValueError("FAIL_CLOSED_TOO_FEW_VISIBLE_PIXELS")

    args.output_root.mkdir(parents=True, exist_ok=False)
    stem = view_id(args.yaw)
    outputs: dict[str, dict[str, str]] = {}
    arrays = (
        ("rgba", Image.fromarray(rgba, "RGBA")),
        ("depth", Image.fromarray(depth, "I;16")),
        ("normal", Image.fromarray(normal, "RGB")),
        ("part-id", Image.fromarray(part_id, "L")),
        ("contact", build_contact(rgba, depth, normal, part_id, args.yaw)),
    )
    for label, image in arrays:
        path = args.output_root / f"{stem}_{label}.png"
        image.save(path)
        outputs[label] = {"path": str(path), "sha256": sha256(path)}
    result = {
        "status": "STAGING_TRUE_3D_COLOURED_CONTROL",
        "formal_pass": False,
        "view_id": stem,
        "yaw": args.yaw,
        "mirror": False,
        "pose": {"arm_drop_degrees": args.arm_drop_degrees, "source": "MHR skin weights"},
        "jaw13_geometry": jaw_contract,
        "visibility": {"backface_culling": True, "per_pixel_z_buffer": True, **statistics},
        "sources": {
            "vertices": {"path": str(args.vertices), "sha256": sha256(args.vertices)},
            "faces": {"path": str(args.faces), "sha256": sha256(args.faces)},
            "skin_weights": {"path": str(args.skin_weights), "sha256": sha256(args.skin_weights)},
            "vertex_parts": {"path": str(args.vertex_parts), "sha256": sha256(args.vertex_parts)},
            "b00": {"path": str(args.b00), "sha256": sha256(args.b00)},
            "jaw13_candidates": {"path": str(args.jaw13_candidates), "sha256": sha256(args.jaw13_candidates)},
            "step16_identity": {"path": str(args.step16_identity), "sha256": sha256(args.step16_identity)},
            "idle_front": {"path": str(args.idle_front), "sha256": sha256(args.idle_front)},
            "idle_lean": {"path": str(args.idle_lean), "sha256": sha256(args.idle_lean)},
            "profile_062": {"path": str(args.profile_062), "sha256": sha256(args.profile_062)},
        },
        "outputs": outputs,
    }
    result_path = args.output_root / "render-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
