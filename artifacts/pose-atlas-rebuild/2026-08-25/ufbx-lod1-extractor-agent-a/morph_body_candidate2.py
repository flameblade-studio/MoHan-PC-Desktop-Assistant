from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import CubicSpline

from slice_candidate_loops import stitch_segments, triangle_plane_segments


VERTEX_COUNT = 18_439
FACE_COUNT = 36_874
TARGET_HEIGHT = 168.0
FRACTIONS = {
    "hip_candidate": 0.50,
    "waist_candidate": 0.62,
    "underbust_candidate": 0.70,
    "bust_candidate": 0.74,
}
TARGETS = {
    "bust_candidate": 86.0,
    "underbust_candidate": 71.0,
    "waist_candidate": 62.0,
    "hip_candidate": 90.0,
}
DISPLAY_ORDER = ["bust_candidate", "underbust_candidate", "waist_candidate", "hip_candidate"]
COLORS = {
    "bust_candidate": (215, 65, 65),
    "underbust_candidate": (40, 170, 110),
    "waist_candidate": (235, 145, 30),
    "hip_candidate": (200, 70, 210),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_indexed_tsv(path: Path, rows: int, values: int, dtype) -> np.ndarray:
    table = np.loadtxt(path, delimiter="\t", dtype=dtype)
    if table.shape != (rows, values + 1):
        raise ValueError(f"Unexpected shape for {path}: {table.shape}")
    if not np.array_equal(table[:, 0], np.arange(rows, dtype=table.dtype)):
        raise ValueError(f"Non-sequential IDs: {path}")
    result = table[:, 1:]
    if not np.isfinite(result).all():
        raise ValueError(f"Non-finite values: {path}")
    return result


def exact_sections(vertices: np.ndarray, faces: np.ndarray) -> tuple[dict[str, float], dict[str, dict]]:
    height = float(np.ptp(vertices[:, 1]))
    actual = {"height": height}
    details: dict[str, dict] = {}
    for name, fraction in FRACTIONS.items():
        plane_y = float(vertices[:, 1].min() + fraction * height)
        segments, coplanar, ambiguous = triangle_plane_segments(vertices, faces, plane_y)
        loops, open_components, _ = stitch_segments(segments)
        if not loops:
            raise ValueError(f"No closed section loop for {name}")
        torso = loops[0]
        actual[name] = torso.perimeter
        details[name] = {
            "plane_y": plane_y,
            "closed_loop_count": len(loops),
            "open_component_count": open_components,
            "coplanar_edge_count": coplanar,
            "ambiguous_triangle_count": ambiguous,
            "largest_torso_loop_perimeter": torso.perimeter,
            "points": torso.points,
            "centroid_xz": list(torso.centroid),
            "bbox_xz": list(torso.bbox),
        }
    return actual, details


def interpolate_envelope(y: np.ndarray, anchors_y: np.ndarray, anchor_values: np.ndarray) -> np.ndarray:
    return np.interp(y, anchors_y, anchor_values, left=anchor_values[0], right=anchor_values[-1])


def central_torso_component(
    vertices: np.ndarray, faces: np.ndarray, details: dict[str, dict], support_low: float, support_high: float
) -> tuple[np.ndarray, dict]:
    ordered = sorted(FRACTIONS, key=FRACTIONS.get)
    anchors_y = np.asarray([details[name]["plane_y"] for name in ordered])
    centers_x = np.asarray([details[name]["centroid_xz"][0] for name in ordered])
    centers_z = np.asarray([details[name]["centroid_xz"][1] for name in ordered])
    half_x = np.asarray([(details[name]["bbox_xz"][2] - details[name]["bbox_xz"][0]) / 2 for name in ordered])
    half_z = np.asarray([(details[name]["bbox_xz"][3] - details[name]["bbox_xz"][1]) / 2 for name in ordered])
    y = vertices[:, 1]
    cx = interpolate_envelope(y, anchors_y, centers_x)
    cz = interpolate_envelope(y, anchors_y, centers_z)
    hx = np.maximum(interpolate_envelope(y, anchors_y, half_x), 1e-6)
    hz = np.maximum(interpolate_envelope(y, anchors_y, half_z), 1e-6)
    # A rectangular normalized envelope keeps every point of the measured torso
    # loop at full influence; an ellipse would incorrectly attenuate bbox corners.
    radial = np.maximum(np.abs((vertices[:, 0] - cx) / hx), np.abs((vertices[:, 2] - cz) / hz))
    eligible = (y >= support_low) & (y <= support_high) & (radial <= 1.30)

    adjacency: dict[int, list[int]] = defaultdict(list)
    for face in faces:
        for ia, ib in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            a, b = int(ia), int(ib)
            if eligible[a] and eligible[b]:
                adjacency[a].append(b)
                adjacency[b].append(a)
    components: list[list[int]] = []
    visited: set[int] = set()
    for start in np.flatnonzero(eligible):
        start = int(start)
        if start in visited:
            continue
        queue = deque([start])
        visited.add(start)
        component: list[int] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    if not components:
        raise ValueError("No central torso component")
    largest = max(components, key=len)
    component_mask = np.zeros(len(vertices), dtype=bool)
    component_mask[largest] = True

    # Full influence covers the measured torso surface; the outer 5%-30% envelope
    # is a cosine falloff that prevents a hard topology-space cut near the shoulders.
    radial_weight = np.ones(len(vertices), dtype=np.float64)
    transition = radial > 1.05
    radial_weight[transition] = 0.5 * (
        1.0 + np.cos(np.pi * np.clip((radial[transition] - 1.05) / 0.25, 0.0, 1.0))
    )
    radial_weight[radial >= 1.30] = 0.0
    radial_weight[~component_mask] = 0.0
    report = {
        "eligible_vertices": int(eligible.sum()),
        "connected_components": len(components),
        "selected_component_vertices": len(largest),
        "nonzero_weight_vertices": int(np.count_nonzero(radial_weight)),
        "full_weight_vertices": int(np.count_nonzero(radial_weight >= 1.0 - 1e-12)),
        "support_low_y": support_low,
        "support_high_y": support_high,
        "radial_full_until": 1.05,
        "radial_zero_at": 1.30,
    }
    return radial_weight, report


def make_scale_spline(anchor_y: np.ndarray, anchor_scale: np.ndarray, support_low: float, support_high: float) -> CubicSpline:
    sparse_y = np.concatenate(([support_low], anchor_y, [support_high]))
    sparse_scale = np.concatenate(([1.0], anchor_scale, [1.0]))
    # Densify each segment with its linear interpolant before building one C2
    # cubic spline. This limits cubic overshoot at the waist while preserving
    # continuous first and second derivatives and exact anchor values.
    dense_y = []
    dense_scale = []
    for index in range(len(sparse_y) - 1):
        segment_y = np.linspace(sparse_y[index], sparse_y[index + 1], 5)
        segment_scale = np.linspace(sparse_scale[index], sparse_scale[index + 1], 5)
        if index:
            segment_y = segment_y[1:]
            segment_scale = segment_scale[1:]
        dense_y.extend(segment_y.tolist())
        dense_scale.extend(segment_scale.tolist())
    knots_y = np.asarray(dense_y)
    knots_scale = np.asarray(dense_scale)
    if not np.all(np.diff(knots_y) > 0):
        raise ValueError("Scale spline knots are not strictly increasing")
    return CubicSpline(knots_y, knots_scale, bc_type=((1, 0.0), (1, 0.0)), extrapolate=False)


def apply_morph(
    base: np.ndarray,
    weight: np.ndarray,
    anchor_y: np.ndarray,
    anchor_scale: np.ndarray,
    centers_x: np.ndarray,
    centers_z: np.ndarray,
    support_low: float,
    support_high: float,
) -> tuple[np.ndarray, CubicSpline]:
    spline = make_scale_spline(anchor_y, anchor_scale, support_low, support_high)
    y = base[:, 1]
    local_scale = np.ones(len(base), dtype=np.float64)
    inside = (y >= support_low) & (y <= support_high)
    local_scale[inside] = spline(y[inside])
    if np.any(local_scale < 0.55) or np.any(local_scale > 1.10):
        raise ValueError(f"Unsafe local scale range: {local_scale.min()}..{local_scale.max()}")
    blended = 1.0 + weight * (local_scale - 1.0)
    cx = np.interp(y, anchor_y, centers_x, left=centers_x[0], right=centers_x[-1])
    cz = np.interp(y, anchor_y, centers_z, left=centers_z[0], right=centers_z[-1])
    result = base.copy()
    result[:, 0] = cx + (base[:, 0] - cx) * blended
    result[:, 2] = cz + (base[:, 2] - cz) * blended
    result[weight == 0.0] = base[weight == 0.0]
    return result, spline


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# MHR deterministic local torso morph candidate-2\n")
        stream.write("o mhr_body_morph_candidate2\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.17g} {y:.17g} {z:.17g}\n")
        for a, b, c in faces:
            stream.write(f"f {int(a)+1} {int(b)+1} {int(c)+1}\n")


def write_vertices_bin(path: Path, vertices: np.ndarray) -> None:
    with path.open("wb") as stream:
        stream.write(b"MHRVTX2\0")
        stream.write(struct.pack("<II", len(vertices), 3))
        stream.write(np.asarray(vertices, dtype="<f8").tobytes(order="C"))


def draw_overlay(
    path: Path,
    vertices: np.ndarray,
    faces: np.ndarray,
    details: dict,
    actual: dict,
    title: str = "MHR BODY MORPH CANDIDATE-2",
    subtitle: str = "DETERMINISTIC LOCAL TORSO MORPH - CANDIDATE SECTION HEIGHTS",
) -> None:
    image = Image.new("RGB", (1800, 1350), "white")
    draw = ImageDraw.Draw(image)
    font, small = ImageFont.load_default(size=18), ImageFont.load_default(size=14)
    draw.text((30, 20), title, fill=(20, 20, 20), font=font)
    draw.text((30, 48), subtitle, fill=(175, 25, 25), font=small)
    unique_edges = set()
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            unique_edges.add(tuple(sorted((int(a), int(b)))))
    edges = np.asarray(sorted(unique_edges), dtype=np.uint32)

    def panel(box, axes, label):
        draw.rectangle(box, outline=(90, 90, 90))
        points = vertices[:, axes]
        lo, hi = points.min(axis=0), points.max(axis=0)
        def project(point):
            px = box[0] + 20 + (point[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0] - 40)
            py = box[3] - 20 - (point[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1] - 50)
            return px, py
        for a, b in edges[::2]:
            draw.line((*project(points[a]), *project(points[b])), fill=(125, 150, 175), width=1)
        draw.text((box[0] + 10, box[1] + 8), label, fill=(20, 20, 20), font=small)
    panel((30, 85, 580, 1315), (0, 1), "FRONT X/Y WIREFRAME")
    panel((600, 85, 1050, 1315), (2, 1), "SIDE Z/Y WIREFRAME")

    all_points = np.concatenate([details[name]["points"] for name in DISPLAY_ORDER])
    lo, hi = all_points.min(axis=0), all_points.max(axis=0)
    for index, name in enumerate(DISPLAY_ORDER):
        box = (1080, 85 + 305 * index, 1770, 370 + 305 * index)
        draw.rectangle(box, outline=(90, 90, 90))
        points = details[name]["points"]
        mapped = []
        for point in points:
            px = box[0] + 30 + (point[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0] - 60)
            py = box[3] - 30 - (point[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1] - 75)
            mapped.append((px, py))
        mapped.append(mapped[0])
        draw.line(mapped, fill=COLORS[name], width=4)
        error = actual[name] - TARGETS[name]
        draw.text((box[0] + 10, box[1] + 8), f"{name}: target={TARGETS[name]:.2f} actual={actual[name]:.4f} error={error:+.4f}", fill=(20, 20, 20), font=small)
        draw.text((box[0] + 10, box[1] + 31), f"closed loops={details[name]['closed_loop_count']} (largest torso shown)", fill=(130, 45, 45), font=small)
    image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw_vertices = load_indexed_tsv(args.vertices, VERTEX_COUNT, 3, np.float64)
    faces = load_indexed_tsv(args.faces, FACE_COUNT, 3, np.uint32)
    base_scale = TARGET_HEIGHT / float(np.ptp(raw_vertices[:, 1]))
    base = raw_vertices * base_scale
    base_actual, base_details = exact_sections(base, faces)

    ordered = sorted(FRACTIONS, key=FRACTIONS.get)
    anchor_y = np.asarray([base_details[name]["plane_y"] for name in ordered])
    centers_x = np.asarray([base_details[name]["centroid_xz"][0] for name in ordered])
    centers_z = np.asarray([base_details[name]["centroid_xz"][1] for name in ordered])
    support_low = float(base[:, 1].min() + 0.44 * TARGET_HEIGHT)
    support_high = float(base[:, 1].min() + 0.79 * TARGET_HEIGHT)
    weight, component_report = central_torso_component(base, faces, base_details, support_low, support_high)

    anchor_scale = np.asarray([TARGETS[name] / base_actual[name] for name in ordered])
    history = []
    final_vertices = base
    final_spline = None
    for iteration in range(12):
        final_vertices, final_spline = apply_morph(
            base, weight, anchor_y, anchor_scale, centers_x, centers_z, support_low, support_high
        )
        actual, details = exact_sections(final_vertices, faces)
        errors = {name: actual[name] - TARGETS[name] for name in ordered}
        history.append({
            "iteration": iteration,
            "anchor_scale": anchor_scale.tolist(),
            "actual": {name: actual[name] for name in ordered},
            "signed_errors": errors,
            "max_abs_error": max(abs(value) for value in errors.values()),
        })
        if max(abs(value) for value in errors.values()) <= 0.5:
            break
        for index, name in enumerate(ordered):
            anchor_scale[index] *= TARGETS[name] / actual[name]
    else:
        raise RuntimeError(f"Candidate-2 failed convergence: {history[-1]}")

    if final_spline is None:
        raise AssertionError("Missing final spline")
    height = float(np.ptp(final_vertices[:, 1]))
    if abs(height - TARGET_HEIGHT) > 1e-9:
        raise ValueError(f"Height changed: {height}")
    unchanged = weight == 0.0
    unchanged_max = float(np.max(np.linalg.norm(final_vertices[unchanged] - base[unchanged], axis=1)))
    if unchanged_max != 0.0:
        raise ValueError(f"Protected vertices changed: {unchanged_max}")

    obj_path = args.output_dir / "candidate2.obj"
    bin_path = args.output_dir / "candidate2-vertices.bin"
    png_path = args.output_dir / "candidate2-wireframe-sections.png"
    json_path = args.output_dir / "candidate2-report.json"
    write_obj(obj_path, final_vertices, faces)
    write_vertices_bin(bin_path, final_vertices)
    draw_overlay(png_path, final_vertices, faces, details, actual)

    sample_y = np.linspace(support_low, support_high, 1025)
    sample_scale = final_spline(sample_y)
    first = final_spline(sample_y, 1)
    second = final_spline(sample_y, 2)
    report = {
        "status": "CANDIDATE_2_SECTION_TARGETS_PASS_NOT_ANATOMICALLY_VALIDATED",
        "base_uniform_scale_to_168": base_scale,
        "height": height,
        "fractions": FRACTIONS,
        "targets": TARGETS,
        "actual": actual,
        "signed_errors": {name: actual[name] - TARGETS[name] for name in TARGETS},
        "all_section_errors_le_0_5_cm": all(abs(actual[name] - TARGETS[name]) <= 0.5 for name in TARGETS),
        "iterations": len(history),
        "history": history,
        "local_scale_anchor_order": ordered,
        "local_scale_anchor_values": anchor_scale.tolist(),
        "spline": {
            "type": "SciPy CubicSpline C2",
            "boundary_condition": "first derivative zero at support endpoints",
            "support_low_y": support_low,
            "support_high_y": support_high,
            "sampled_min_scale": float(sample_scale.min()),
            "sampled_max_scale": float(sample_scale.max()),
            "integral_first_derivative_squared": float(np.trapezoid(first * first, sample_y)),
            "integral_second_derivative_squared": float(np.trapezoid(second * second, sample_y)),
        },
        "central_torso_component": component_report,
        "protected_zero_weight_vertices": int(unchanged.sum()),
        "protected_vertices_max_displacement": unchanged_max,
        "topology": {"vertices": VERTEX_COUNT, "triangles": FACE_COUNT, "unchanged": True},
        "sections": {
            name: {key: value for key, value in details[name].items() if key != "points"}
            for name in details
        },
        "vertices_bin_contract": {
            "magic": "MHRVTX2\\0",
            "header": "8-byte magic, uint32-le vertex_count, uint32-le components",
            "payload": "vertex_count x 3 float64-le XYZ in exact ufbx vertex order",
        },
        "inputs_sha256": {"vertices": sha256(args.vertices), "faces": sha256(args.faces)},
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {
        "report": str(json_path.resolve()),
        "obj": str(obj_path.resolve()),
        "vertices_bin": str(bin_path.resolve()),
        "overlay": str(png_path.resolve()),
        "actual": actual,
        "errors": report["signed_errors"],
        "iterations": len(history),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
