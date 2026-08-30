from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from slice_candidate_loops import stitch_segments, triangle_plane_segments


VERTEX_COUNT = 18_439
FACE_COUNT = 36_874
FRACTIONS = {
    "hip_candidate": 0.50,
    "waist_candidate": 0.62,
    "underbust_candidate": 0.70,
    "bust_candidate": 0.74,
}
COLORS = {
    "hip_candidate": (200, 70, 210),
    "waist_candidate": (235, 145, 30),
    "underbust_candidate": (40, 170, 110),
    "bust_candidate": (215, 65, 65),
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
        raise ValueError(f"Unexpected {path} shape {table.shape}")
    if not np.array_equal(table[:, 0], np.arange(rows, dtype=table.dtype)):
        raise ValueError(f"Non-sequential IDs in {path}")
    return table[:, 1:]


def load_vertices_bin(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        magic = stream.read(8)
        count, components = struct.unpack("<II", stream.read(8))
        payload = stream.read()
    if magic != b"MHRVTX2\0" or count != VERTEX_COUNT or components != 3:
        raise ValueError("Invalid candidate2 vertices binary")
    vertices = np.frombuffer(payload, dtype="<f8").reshape(count, components).copy()
    if not np.isfinite(vertices).all():
        raise ValueError("Candidate vertices contain non-finite values")
    return vertices


def load_skeleton(path: Path, scale: float) -> list[dict]:
    joints = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            joints.append({
                "index": int(row["cluster_index"]),
                "name": row["bone_name"],
                "parent": row["parent_name"],
                "position": np.asarray([float(row["x"]), float(row["y"]), float(row["z"])]) * scale,
                "weight_count": int(row["weight_count"]),
            })
    if len(joints) != 127 or [joint["index"] for joint in joints] != list(range(127)):
        raise ValueError("Official skeleton extraction is not exactly 127 ordered clusters")
    return joints


def exact_loops(vertices: np.ndarray, faces: np.ndarray) -> dict[str, dict]:
    minimum = float(vertices[:, 1].min())
    height = float(np.ptp(vertices[:, 1]))
    result = {}
    for name, fraction in FRACTIONS.items():
        plane_y = minimum + fraction * height
        segments, coplanar, ambiguous = triangle_plane_segments(vertices, faces, plane_y)
        loops, open_components, _ = stitch_segments(segments)
        if not loops:
            raise ValueError(f"No loop for {name}")
        result[name] = {
            "plane_y": plane_y,
            "perimeter": loops[0].perimeter,
            "points": loops[0].points,
            "closed_loops": len(loops),
            "open_components": open_components,
            "coplanar_edges": coplanar,
            "ambiguous_triangles": ambiguous,
        }
    return result


def triangle_quality(base: np.ndarray, candidate: np.ndarray, faces: np.ndarray) -> dict:
    base_tri = base[faces]
    cand_tri = candidate[faces]
    base_e1 = base_tri[:, 1] - base_tri[:, 0]
    base_e2 = base_tri[:, 2] - base_tri[:, 0]
    cand_e1 = cand_tri[:, 1] - cand_tri[:, 0]
    cand_e2 = cand_tri[:, 2] - cand_tri[:, 0]
    base_cross = np.cross(base_e1, base_e2)
    cand_cross = np.cross(cand_e1, cand_e2)
    base_norm = np.linalg.norm(base_cross, axis=1)
    cand_norm = np.linalg.norm(cand_cross, axis=1)
    if np.any(base_norm <= 1e-12) or np.any(cand_norm <= 1e-12):
        raise ValueError("Degenerate triangle detected")
    normal_dot = np.sum(base_cross * cand_cross, axis=1) / (base_norm * cand_norm)
    area_ratio = cand_norm / base_norm

    singular_values = np.empty((len(faces), 2), dtype=np.float64)
    determinants = np.empty(len(faces), dtype=np.float64)
    for index in range(len(faces)):
        bx = base_e1[index] / np.linalg.norm(base_e1[index])
        bn = base_cross[index] / base_norm[index]
        by = np.cross(bn, bx)
        source = np.asarray([
            [np.dot(base_e1[index], bx), np.dot(base_e2[index], bx)],
            [np.dot(base_e1[index], by), np.dot(base_e2[index], by)],
        ])
        cx = cand_e1[index] / np.linalg.norm(cand_e1[index])
        cn = cand_cross[index] / cand_norm[index]
        cy = np.cross(cn, cx)
        target = np.asarray([
            [np.dot(cand_e1[index], cx), np.dot(cand_e2[index], cx)],
            [np.dot(cand_e1[index], cy), np.dot(cand_e2[index], cy)],
        ])
        deformation = target @ np.linalg.inv(source)
        singular_values[index] = np.linalg.svd(deformation, compute_uv=False)
        determinants[index] = np.linalg.det(deformation)
    changed_triangles = np.any(np.linalg.norm(candidate[faces] - base[faces], axis=2) > 1e-12, axis=1)
    subset = changed_triangles
    return {
        "changed_triangle_count": int(subset.sum()),
        "degenerate_triangle_count": 0,
        "normal_flip_count": int(np.count_nonzero(normal_dot[subset] <= 0.0)),
        "normal_dot_min": float(normal_dot[subset].min()),
        "normal_dot_p01": float(np.quantile(normal_dot[subset], 0.01)),
        "area_ratio_min": float(area_ratio[subset].min()),
        "area_ratio_max": float(area_ratio[subset].max()),
        "jacobian_det_min": float(determinants[subset].min()),
        "jacobian_det_max": float(determinants[subset].max()),
        "singular_value_min": float(singular_values[subset].min()),
        "singular_value_max": float(singular_values[subset].max()),
        "triangle_flip_count": int(np.count_nonzero(determinants[subset] <= 0.0)),
    }


def segment_triangle(p0: np.ndarray, p1: np.ndarray, tri: np.ndarray, epsilon: float = 1e-9) -> bool:
    direction = p1 - p0
    edge1 = tri[1] - tri[0]
    edge2 = tri[2] - tri[0]
    h = np.cross(direction, edge2)
    determinant = float(np.dot(edge1, h))
    if abs(determinant) <= epsilon:
        return False
    inv = 1.0 / determinant
    s = p0 - tri[0]
    u = inv * float(np.dot(s, h))
    if u <= epsilon or u >= 1.0 - epsilon:
        return False
    q = np.cross(s, edge1)
    v = inv * float(np.dot(direction, q))
    if v <= epsilon or u + v >= 1.0 - epsilon:
        return False
    t = inv * float(np.dot(edge2, q))
    return epsilon < t < 1.0 - epsilon


def triangles_intersect(a: np.ndarray, b: np.ndarray) -> bool:
    for p0, p1 in ((a[0], a[1]), (a[1], a[2]), (a[2], a[0])):
        if segment_triangle(p0, p1, b):
            return True
    for p0, p1 in ((b[0], b[1]), (b[1], b[2]), (b[2], b[0])):
        if segment_triangle(p0, p1, a):
            return True
    return False


def local_self_intersections(base: np.ndarray, candidate: np.ndarray, faces: np.ndarray, cell_size: float = 4.0) -> dict:
    changed = np.any(np.linalg.norm(candidate[faces] - base[faces], axis=2) > 1e-12, axis=1)
    triangle_min = candidate[faces].min(axis=1)
    triangle_max = candidate[faces].max(axis=1)
    grid: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index in range(len(faces)):
        lo = np.floor(triangle_min[index] / cell_size).astype(int)
        hi = np.floor(triangle_max[index] / cell_size).astype(int)
        for ix in range(lo[0], hi[0] + 1):
            for iy in range(lo[1], hi[1] + 1):
                for iz in range(lo[2], hi[2] + 1):
                    grid[(ix, iy, iz)].append(index)
    pairs: set[tuple[int, int]] = set()
    for index in np.flatnonzero(changed):
        lo = np.floor(triangle_min[index] / cell_size).astype(int)
        hi = np.floor(triangle_max[index] / cell_size).astype(int)
        for ix in range(lo[0], hi[0] + 1):
            for iy in range(lo[1], hi[1] + 1):
                for iz in range(lo[2], hi[2] + 1):
                    for other in grid[(ix, iy, iz)]:
                        if other == index:
                            continue
                        pair = (min(int(index), other), max(int(index), other))
                        pairs.add(pair)
    intersections = []
    tested = 0
    for first, second in sorted(pairs):
        if np.intersect1d(faces[first], faces[second]).size:
            continue
        if np.any(triangle_max[first] < triangle_min[second]) or np.any(triangle_max[second] < triangle_min[first]):
            continue
        tested += 1
        if triangles_intersect(candidate[faces[first]], candidate[faces[second]]):
            intersections.append([first, second])
    return {
        "method": "4cm spatial hash broad phase; strict non-coplanar segment-triangle narrow phase; adjacent triangles excluded",
        "changed_triangles": int(changed.sum()),
        "broadphase_unique_pairs": len(pairs),
        "narrowphase_pairs_tested": tested,
        "strict_intersection_count": len(intersections),
        "first_intersection_pairs": intersections[:20],
        "limitation": "coplanar overlap and exact touching are not counted",
    }


def bone_zone_audit(joints: list[dict], loops: dict[str, dict]) -> dict:
    by_name = {joint["name"]: joint for joint in joints}
    required = ["l_upleg", "r_upleg", "c_spine0", "c_spine1", "c_spine2", "c_spine3", "l_clavicle", "r_clavicle"]
    missing = [name for name in required if name not in by_name]
    if missing:
        raise ValueError(f"Missing required official joints: {missing}")
    y = {name: float(by_name[name]["position"][1]) for name in required}
    hip_joint = (y["l_upleg"] + y["r_upleg"]) / 2
    zones = {
        "hip_candidate": {
            "rule": "within 8cm below to 3cm above mean upper-leg joint",
            "lower": hip_joint - 8.0,
            "upper": hip_joint + 3.0,
        },
        "waist_candidate": {
            "rule": "between c_spine1 and c_spine2",
            "lower": y["c_spine1"],
            "upper": y["c_spine2"],
        },
        "underbust_candidate": {
            "rule": "lower half of c_spine2 to c_spine3 interval",
            "lower": y["c_spine2"],
            "upper": y["c_spine2"] + 0.50 * (y["c_spine3"] - y["c_spine2"]),
        },
        "bust_candidate": {
            "rule": "middle c_spine2 to c_spine3 interval, below clavicles",
            "lower": y["c_spine2"] + 0.35 * (y["c_spine3"] - y["c_spine2"]),
            "upper": min(y["c_spine2"] + 0.85 * (y["c_spine3"] - y["c_spine2"]), (y["l_clavicle"] + y["r_clavicle"]) / 2),
        },
    }
    result = {}
    for name, zone in zones.items():
        plane = loops[name]["plane_y"]
        result[name] = {
            **zone,
            "plane_y": plane,
            "within_bone_bounded_zone": zone["lower"] <= plane <= zone["upper"],
            "normalized_position": (plane - zone["lower"]) / (zone["upper"] - zone["lower"]),
        }
    return {
        "required_joint_y": y,
        "zones": result,
        "all_within_bone_bounded_zones": all(item["within_bone_bounded_zone"] for item in result.values()),
        "scope_limit": "127-joint skeleton bounds plausible vertical regions; it does not provide breast apex, rib margin, iliac crest, or greater-trochanter surface landmarks",
    }


def front_back_ratios(base_loops: dict, candidate_loops: dict, joints: list[dict]) -> dict:
    by_name = {joint["name"]: joint for joint in joints}
    spine = [joint for joint in joints if joint["name"] in {"c_spine0", "c_spine1", "c_spine2", "c_spine3"}]
    spine.sort(key=lambda joint: joint["position"][1])
    hip_y = float((by_name["l_upleg"]["position"][1] + by_name["r_upleg"]["position"][1]) / 2)
    hip_z = float((by_name["l_upleg"]["position"][2] + by_name["r_upleg"]["position"][2]) / 2)
    sy = np.asarray([hip_y] + [joint["position"][1] for joint in spine])
    sz = np.asarray([hip_z] + [joint["position"][2] for joint in spine])
    result = {}
    for name in FRACTIONS:
        plane = candidate_loops[name]["plane_y"]
        center_z = float(np.interp(plane, sy, sz))
        entry = {"skeleton_center_z": center_z}
        for label, loops in (("base", base_loops), ("candidate", candidate_loops)):
            points = loops[name]["points"]
            back = center_z - float(points[:, 1].min())
            front = float(points[:, 1].max()) - center_z
            entry[label] = {"front_depth": front, "back_depth": back, "front_to_back_ratio": front / back}
        entry["ratio_change"] = entry["candidate"]["front_to_back_ratio"] - entry["base"]["front_to_back_ratio"]
        result[name] = entry
    return result


def draw_overlay(path: Path, candidate: np.ndarray, faces: np.ndarray, joints: list[dict], loops: dict, displacement: np.ndarray, label: str) -> None:
    image = Image.new("RGB", (1800, 1350), "white")
    draw = ImageDraw.Draw(image)
    font, small = ImageFont.load_default(size=18), ImageFont.load_default(size=14)
    draw.text((30, 20), f"MHR {label.upper()} ANATOMY / DEFORMATION AUDIT", fill=(20, 20, 20), font=font)
    draw.text((30, 48), "OFFICIAL 127-BONE FBX SKELETON; SURFACE LANDMARKS STILL LIMITED", fill=(175, 25, 25), font=small)
    edges = set()
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edges.add(tuple(sorted((int(a), int(b)))))
    edges = np.asarray(sorted(edges), dtype=np.uint32)
    by_name = {joint["name"]: joint for joint in joints}
    selected_names = {name for name in by_name if name.startswith("c_spine") or name in {"c_neck", "l_clavicle", "r_clavicle", "l_upleg", "r_upleg"}}

    def panel(box, axes, title):
        points = candidate[:, axes]
        lo, hi = points.min(axis=0), points.max(axis=0)
        draw.rectangle(box, outline=(90, 90, 90))
        def project(point):
            px = box[0] + 25 + (point[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0] - 50)
            py = box[3] - 25 - (point[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1] - 55)
            return px, py
        for a, b in edges[::2]:
            color = (195, 105, 60) if max(displacement[a], displacement[b]) > 1e-8 else (145, 165, 185)
            draw.line((*project(points[a]), *project(points[b])), fill=color, width=1)
        for name, loop in loops.items():
            _, py = project(np.asarray([0.0, loop["plane_y"]]))
            draw.line((box[0] + 5, py, box[2] - 5, py), fill=COLORS[name], width=3)
            draw.text((box[0] + 8, py - 20), name, fill=COLORS[name], font=small)
        for name in selected_names:
            joint = by_name[name]
            joint_point = joint["position"][[axes[0], axes[1]]]
            px, py = project(joint_point)
            if joint["parent"] in by_name and joint["parent"] in selected_names:
                parent = by_name[joint["parent"]]["position"][[axes[0], axes[1]]]
                draw.line((*project(parent), px, py), fill=(20, 40, 40), width=4)
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(20, 40, 40))
            if name in {"c_spine0", "c_spine1", "c_spine2", "c_spine3", "l_upleg"}:
                draw.text((px + 7, py - 8), name, fill=(20, 40, 40), font=small)
        draw.text((box[0] + 10, box[1] + 8), title, fill=(20, 20, 20), font=small)
    panel((30, 85, 810, 1315), (0, 1), "FRONT: orange=changed mesh; skeleton black")
    panel((840, 85, 1620, 1315), (2, 1), "SIDE: orange=changed mesh; skeleton black")
    draw.text((1640, 100), "SECTION", fill=(20, 20, 20), font=small)
    for index, name in enumerate(("bust_candidate", "underbust_candidate", "waist_candidate", "hip_candidate")):
        draw.rectangle((1640, 135 + index * 95, 1665, 160 + index * 95), fill=COLORS[name])
        draw.text((1675, 137 + index * 95), name.replace("_candidate", ""), fill=(20, 20, 20), font=small)
    image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--candidate-bin", type=Path, required=True)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--skeleton", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label", default="candidate2")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw_base = load_indexed_tsv(args.base_vertices, VERTEX_COUNT, 3, np.float64)
    faces = load_indexed_tsv(args.faces, FACE_COUNT, 3, np.uint32)
    candidate = load_vertices_bin(args.candidate_bin)
    candidate_report = json.loads(args.candidate_report.read_text(encoding="utf-8"))
    scale = float(candidate_report["base_uniform_scale_to_168"])
    base = raw_base * scale
    joints = load_skeleton(args.skeleton, scale)
    base_loops = exact_loops(base, faces)
    candidate_loops = exact_loops(candidate, faces)
    bone_zones = bone_zone_audit(joints, candidate_loops)
    quality = triangle_quality(base, candidate, faces)
    intersections = local_self_intersections(base, candidate, faces)
    proportions = front_back_ratios(base_loops, candidate_loops, joints)
    max_ratio_change = max(abs(entry["ratio_change"]) for entry in proportions.values())
    displacement = np.linalg.norm(candidate - base, axis=1)
    support_low = float(candidate_report["spline"]["support_low_y"])
    support_high = float(candidate_report["spline"]["support_high_y"])
    transition = {
        "support_low_y": support_low,
        "support_high_y": support_high,
        "below_support_max_displacement": float(displacement[base[:, 1] < support_low - 1e-12].max(initial=0.0)),
        "above_support_max_displacement": float(displacement[base[:, 1] > support_high + 1e-12].max(initial=0.0)),
        "max_displacement": float(displacement.max()),
        "changed_vertices": int(np.count_nonzero(displacement > 1e-12)),
    }
    gates = {
        "official_skeleton_127": len(joints) == 127,
        "section_bone_zones_plausible": bone_zones["all_within_bone_bounded_zones"],
        "no_degenerate_triangles": quality["degenerate_triangle_count"] == 0,
        "no_triangle_flips": quality["triangle_flip_count"] == 0,
        "no_normal_flips": quality["normal_flip_count"] == 0,
        "positive_local_jacobian": quality["jacobian_det_min"] > 0.0,
        "no_strict_new_local_self_intersections": intersections["strict_intersection_count"] == 0,
        "outside_vertical_support_unchanged": transition["below_support_max_displacement"] == 0.0 and transition["above_support_max_displacement"] == 0.0,
        "section_measurements_preserved": bool(candidate_report["all_section_errors_le_0_5_cm"]),
        "front_back_ratio_change_le_0_25": max_ratio_change <= 0.25,
    }
    report = {
        "status": "PASS_BONE_BOUNDED_PLAUSIBILITY_NOT_SURFACE_LANDMARK_VALIDATION" if all(gates.values()) else "FAIL",
        "gates": gates,
        "skeleton": {
            "count": len(joints),
            "source": str(args.skeleton.resolve()),
            "sha256": sha256(args.skeleton),
            "positions_scaled_by": scale,
        },
        "bone_zone_audit": bone_zones,
        "triangle_quality": quality,
        "local_self_intersection_audit": intersections,
        "transition_audit": transition,
        "front_back_proportions": proportions,
        "candidate3_required": args.label == "candidate2" and ((not bone_zones["all_within_bone_bounded_zones"]) or max_ratio_change > 0.25),
        "candidate3_created": args.label == "candidate3",
        "candidate3_decision": "required: candidate2 changed front/back depth ratio relative to the official central skeleton axis beyond 0.25" if max_ratio_change > 0.25 else ("not required" if bone_zones["all_within_bone_bounded_zones"] else "required: section zone"),
        "limitations": [
            "MHR's 127-joint skeleton does not encode breast apex, inframammary fold, rib margin, iliac crest, or greater trochanter skin landmarks.",
            "Self-intersection narrow phase counts strict non-coplanar crossings; coplanar overlaps and exact touching are outside this gate.",
            "Passing this audit establishes bounded plausibility and mesh integrity, not clinical or tailoring-grade anatomical landmark validation.",
        ],
        "inputs_sha256": {
            "base_vertices": sha256(args.base_vertices),
            "faces": sha256(args.faces),
            "candidate_bin": sha256(args.candidate_bin),
            "candidate_report": sha256(args.candidate_report),
        },
    }
    output_json = args.output_dir / f"{args.label}-anatomy-audit.json"
    output_png = args.output_dir / f"{args.label}-anatomy-skeleton-overlay.png"
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    draw_overlay(output_png, candidate, faces, joints, candidate_loops, displacement, args.label)
    print(json.dumps({
        "status": report["status"],
        "report": str(output_json.resolve()),
        "overlay": str(output_png.resolve()),
        "gates": gates,
        "candidate3_required": report["candidate3_required"],
    }, indent=2))
    if report["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
