from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


EXPECTED_VERTICES = 18_439
EXPECTED_FACES = 36_874
COLORS = {
    "bust_candidate": (215, 65, 65),
    "underbust_candidate": (40, 170, 110),
    "waist_candidate": (235, 145, 30),
    "hip_candidate": (200, 70, 210),
}


@dataclass(frozen=True)
class Loop:
    points: np.ndarray
    perimeter: float
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_indexed_tsv(path: Path, rows: int, columns: int, dtype) -> np.ndarray:
    table = np.loadtxt(path, delimiter="\t", dtype=dtype)
    if table.shape != (rows, columns + 1):
        raise ValueError(f"Unexpected {path.name} shape: {table.shape}")
    expected_ids = np.arange(rows, dtype=table.dtype)
    if not np.array_equal(table[:, 0], expected_ids):
        raise ValueError(f"Non-sequential IDs in {path}")
    return table[:, 1:]


def load_neutral_obj_vertices(path: Path) -> np.ndarray:
    vertices = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                values = line.split()
                if len(values) != 4:
                    raise ValueError(f"Malformed OBJ vertex: {line.rstrip()}")
                vertices.append(tuple(float(value) for value in values[1:]))
    result = np.asarray(vertices, dtype=np.float64)
    if result.shape != (EXPECTED_VERTICES, 3):
        raise ValueError(f"Unexpected neutral OBJ vertices: {result.shape}")
    if not np.isfinite(result).all():
        raise ValueError("Neutral vertices contain non-finite values")
    return result


def triangle_plane_segments(
    vertices: np.ndarray, faces: np.ndarray, plane_y: float, epsilon: float = 1e-9
) -> tuple[list[tuple[np.ndarray, np.ndarray]], int, int]:
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    coplanar_edges = 0
    ambiguous_triangles = 0
    for face in faces:
        tri = vertices[face]
        points: list[np.ndarray] = []
        for edge_a, edge_b in ((0, 1), (1, 2), (2, 0)):
            a = tri[edge_a]
            b = tri[edge_b]
            da = float(a[1] - plane_y)
            db = float(b[1] - plane_y)
            if abs(da) <= epsilon and abs(db) <= epsilon:
                coplanar_edges += 1
                continue
            if (da < -epsilon and db > epsilon) or (da > epsilon and db < -epsilon):
                t = da / (da - db)
                point = a + t * (b - a)
                points.append(point[[0, 2]])
            elif abs(da) <= epsilon:
                points.append(a[[0, 2]])
            elif abs(db) <= epsilon:
                points.append(b[[0, 2]])

        unique: list[np.ndarray] = []
        for point in points:
            if not any(np.linalg.norm(point - other) <= 1e-8 for other in unique):
                unique.append(point)
        if len(unique) == 2 and np.linalg.norm(unique[0] - unique[1]) > 1e-10:
            segments.append((unique[0], unique[1]))
        elif len(unique) not in (0, 1):
            ambiguous_triangles += 1
    return segments, coplanar_edges, ambiguous_triangles


def stitch_segments(
    segments: list[tuple[np.ndarray, np.ndarray]], tolerance: float = 1e-6
) -> tuple[list[Loop], int, dict[int, int]]:
    def key(point: np.ndarray) -> tuple[int, int]:
        return tuple(np.rint(point / tolerance).astype(np.int64).tolist())

    point_sums: dict[tuple[int, int], np.ndarray] = defaultdict(lambda: np.zeros(2))
    point_counts: dict[tuple[int, int], int] = defaultdict(int)
    adjacency: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for a, b in segments:
        ka, kb = key(a), key(b)
        if ka == kb:
            continue
        for k, point in ((ka, a), (kb, b)):
            point_sums[k] += point
            point_counts[k] += 1
        edge = (ka, kb) if ka < kb else (kb, ka)
        if edge in edges:
            continue
        edges.add(edge)
        adjacency[ka].append(kb)
        adjacency[kb].append(ka)

    degree_hist: dict[int, int] = defaultdict(int)
    for neighbors in adjacency.values():
        degree_hist[len(neighbors)] += 1

    visited_nodes: set[tuple[int, int]] = set()
    closed_loops: list[Loop] = []
    open_components = 0
    for start in adjacency:
        if start in visited_nodes:
            continue
        component: set[tuple[int, int]] = set()
        queue = deque([start])
        visited_nodes.add(start)
        while queue:
            node = queue.popleft()
            component.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    queue.append(neighbor)
        if not all(len(adjacency[node]) == 2 for node in component):
            open_components += 1
            continue

        ordered = [start]
        previous = None
        current = start
        while True:
            choices = [node for node in adjacency[current] if node != previous]
            next_node = choices[0]
            if next_node == start:
                break
            if next_node in ordered:
                open_components += 1
                ordered = []
                break
            ordered.append(next_node)
            previous, current = current, next_node
        if not ordered:
            continue
        points = np.asarray(
            [point_sums[node] / point_counts[node] for node in ordered], dtype=np.float64
        )
        shifted = np.roll(points, -1, axis=0)
        perimeter = float(np.linalg.norm(shifted - points, axis=1).sum())
        centroid = tuple(points.mean(axis=0).tolist())
        bbox = (
            float(points[:, 0].min()),
            float(points[:, 1].min()),
            float(points[:, 0].max()),
            float(points[:, 1].max()),
        )
        closed_loops.append(Loop(points, perimeter, centroid, bbox))
    closed_loops.sort(key=lambda loop: loop.perimeter, reverse=True)
    return closed_loops, open_components, dict(sorted(degree_hist.items()))


def draw_overlay(
    vertices: np.ndarray,
    band_reports: list[dict],
    loops_by_band: dict[str, list[Loop]],
    output: Path,
) -> None:
    width, height = 1800, 1350
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=14)
    draw.text((35, 20), "MHR ZERO-NEUTRAL HORIZONTAL SECTION CANDIDATES", fill=(20, 20, 20), font=font)
    draw.text((35, 48), "GEOMETRY CANDIDATES ONLY - NOT ANATOMICAL LANDMARKS", fill=(175, 25, 25), font=small)

    front_box = (35, 90, 750, 1300)
    x_min, y_min = vertices[:, :2].min(axis=0)
    x_max, y_max = vertices[:, :2].max(axis=0)

    def front(point_x: float, point_y: float) -> tuple[float, float]:
        px = front_box[0] + 25 + (point_x - x_min) / (x_max - x_min) * (front_box[2] - front_box[0] - 50)
        py = front_box[3] - 25 - (point_y - y_min) / (y_max - y_min) * (front_box[3] - front_box[1] - 50)
        return px, py

    draw.rectangle(front_box, outline=(90, 90, 90), width=1)
    for x, y, _ in vertices[::4]:
        px, py = front(float(x), float(y))
        draw.point((px, py), fill=(35, 70, 120))
    for report in band_reports:
        color = COLORS[report["name"]]
        _, py = front(0.0, report["plane_y"])
        draw.line((front_box[0] + 5, py, front_box[2] - 5, py), fill=color, width=3)
        draw.text((front_box[0] + 12, py - 23), report["name"], fill=color, font=small)

    all_points = np.concatenate(
        [loop.points for loops in loops_by_band.values() for loop in loops], axis=0
    )
    section_x_min, section_z_min = all_points.min(axis=0)
    section_x_max, section_z_max = all_points.max(axis=0)
    panel_left, panel_right = 790, 1765
    panel_width = panel_right - panel_left
    panel_height = 280

    for index, report in enumerate(band_reports):
        top = 90 + index * 300
        box = (panel_left, top, panel_right, top + panel_height)
        draw.rectangle(box, outline=(90, 90, 90), width=1)
        loops = loops_by_band[report["name"]]

        def section(point: np.ndarray) -> tuple[float, float]:
            px = box[0] + 30 + (point[0] - section_x_min) / (section_x_max - section_x_min) * (panel_width - 60)
            py = box[3] - 30 - (point[1] - section_z_min) / (section_z_max - section_z_min) * (panel_height - 70)
            return px, py

        for loop_index, loop in enumerate(loops):
            points = [section(point) for point in loop.points]
            points.append(points[0])
            color = COLORS[report["name"]] if loop_index == 0 else (90, 120, 150)
            draw.line(points, fill=color, width=4 if loop_index == 0 else 2)
        label = (
            f'{report["name"]} y={report["plane_y"]:.4f} | closed={report["closed_loop_count"]} '
            f'open={report["open_component_count"]} | torso perimeter={report["largest_torso_loop_perimeter"]:.4f}'
        )
        draw.text((box[0] + 12, box[1] + 8), label, fill=(20, 20, 20), font=small)
        risk = f'limb-like secondary loops={report["limb_like_secondary_loop_count"]}; clothing geometry expected=false'
        draw.text((box[0] + 12, box[1] + 31), risk, fill=(130, 45, 45), font=small)
    image.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--neutral-obj", type=Path, required=True)
    parser.add_argument("--band-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    base_vertices = load_indexed_tsv(args.base_vertices, EXPECTED_VERTICES, 3, np.float64)
    faces_u64 = load_indexed_tsv(args.faces, EXPECTED_FACES, 3, np.uint64)
    if faces_u64.max() >= EXPECTED_VERTICES:
        raise ValueError("Face index is out of range")
    faces = faces_u64.astype(np.uint32)
    neutral_vertices = load_neutral_obj_vertices(args.neutral_obj)
    if base_vertices.shape != neutral_vertices.shape:
        raise ValueError("Base/neutral vertex index contracts differ")

    summary = json.loads(args.band_summary.read_text(encoding="utf-8"))
    fractions = summary["candidate_bands_fraction_above_y_min"]
    planes = summary["candidate_bands_world_y"]
    names = ["bust_candidate", "underbust_candidate", "waist_candidate", "hip_candidate"]
    loops_by_band: dict[str, list[Loop]] = {}
    reports = []
    geometry_json = {"warning": "candidate geometry only; not anatomical landmarks", "bands": {}}
    for name in names:
        segments, coplanar, ambiguous = triangle_plane_segments(
            neutral_vertices, faces, float(planes[name])
        )
        loops, open_components, degree_hist = stitch_segments(segments)
        if not loops:
            raise ValueError(f"No closed loops for {name}")
        torso = loops[0]
        torso_half_width = max(abs(torso.bbox[0]), abs(torso.bbox[2]))
        secondary = loops[1:]
        limb_like = [
            loop
            for loop in secondary
            if abs(loop.centroid[0]) > max(10.0, torso_half_width * 0.75)
        ]
        report = {
            "name": name,
            "source_fraction_above_y_min": float(fractions[name]),
            "plane_y": float(planes[name]),
            "segment_count": len(segments),
            "closed_loop_count": len(loops),
            "open_component_count": open_components,
            "graph_degree_histogram": {str(key): value for key, value in degree_hist.items()},
            "coplanar_edge_count": coplanar,
            "ambiguous_triangle_count": ambiguous,
            "largest_torso_loop_perimeter": torso.perimeter,
            "largest_torso_loop_centroid_xz": list(torso.centroid),
            "largest_torso_loop_bbox_xz": list(torso.bbox),
            "secondary_loop_count": len(secondary),
            "limb_like_secondary_loop_count": len(limb_like),
            "limb_or_hand_intersection_risk": len(limb_like) > 0,
            "clothing_geometry_present": False,
            "clothing_note": "Source is the neutral MHR body geometry; no garment mesh was supplied.",
            "anatomical_accuracy": "NOT_VALIDATED",
        }
        reports.append(report)
        loops_by_band[name] = loops
        geometry_json["bands"][name] = {
            "plane_y": float(planes[name]),
            "closed_loops_xz": [loop.points.tolist() for loop in loops],
        }

    overlay = args.output_dir / "mhr-horizontal-section-candidates.png"
    draw_overlay(neutral_vertices, reports, loops_by_band, overlay)
    loops_path = args.output_dir / "section-loops.json"
    loops_path.write_text(json.dumps(geometry_json, indent=2), encoding="utf-8", newline="\n")
    report_path = args.output_dir / "section-report.json"
    report = {
        "status": "CANDIDATE_GEOMETRY_ONLY",
        "warning": "Band heights come from the existing pointcloud proportion sheet and are not validated anatomical landmarks.",
        "units": "MHR model units; do not treat as certified tape-measure centimeters without a separate scale contract.",
        "inputs": {
            "base_vertices_tsv": str(args.base_vertices.resolve()),
            "base_vertices_sha256": sha256(args.base_vertices),
            "faces_tsv": str(args.faces.resolve()),
            "faces_sha256": sha256(args.faces),
            "neutral_obj": str(args.neutral_obj.resolve()),
            "neutral_obj_sha256": sha256(args.neutral_obj),
            "band_summary": str(args.band_summary.resolve()),
            "band_summary_sha256": sha256(args.band_summary),
        },
        "vertex_count": len(neutral_vertices),
        "face_count": len(faces),
        "base_neutral_index_contract_shape_match": True,
        "bands": reports,
        "outputs": {
            "overlay": str(overlay.resolve()),
            "loops": str(loops_path.resolve()),
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(report_path), "overlay": str(overlay), "bands": reports}, indent=2))


if __name__ == "__main__":
    main()
