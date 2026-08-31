from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import struct
import zipfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import least_squares

from slice_candidate_loops import stitch_segments, triangle_plane_segments


VERTEX_COUNT = 18_439
FACE_COUNT = 36_874
BODY_COEFFICIENTS = 20
TARGETS = {
    "height": 168.0,
    "bust_candidate": 86.0,
    "underbust_candidate": 71.0,
    "waist_candidate": 62.0,
    "hip_candidate": 90.0,
}
BAND_NAMES = ["bust_candidate", "underbust_candidate", "waist_candidate", "hip_candidate"]
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


def load_indexed_tsv(path: Path, rows: int, value_columns: int, dtype) -> np.ndarray:
    table = np.loadtxt(path, delimiter="\t", dtype=dtype)
    if table.shape != (rows, value_columns + 1):
        raise ValueError(f"Unexpected table shape {path}: {table.shape}")
    if not np.array_equal(table[:, 0], np.arange(rows, dtype=table.dtype)):
        raise ValueError(f"Non-sequential IDs: {path}")
    return table[:, 1:]


def load_offsets(path: Path) -> np.ndarray:
    offsets = np.zeros((BODY_COEFFICIENTS, VERTEX_COUNT, 3), dtype=np.float64)
    seen = np.zeros((BODY_COEFFICIENTS, VERTEX_COUNT), dtype=bool)
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        for row in reader:
            shape = int(row["shape_index"])
            if shape >= BODY_COEFFICIENTS:
                continue
            vertex = int(row["vertex_index"])
            if seen[shape, vertex]:
                raise ValueError(f"Duplicate sparse offset shape={shape} vertex={vertex}")
            seen[shape, vertex] = True
            offsets[shape, vertex] = (float(row["dx"]), float(row["dy"]), float(row["dz"]))
    if not np.isfinite(offsets).all() or not seen.any(axis=1).all():
        raise ValueError("Invalid/incomplete first-20 offset set")
    return offsets


def edge_intersection(vertices: np.ndarray, edge: tuple[int, int], plane_y: float) -> np.ndarray:
    a, b = vertices[edge[0]], vertices[edge[1]]
    t = (plane_y - a[1]) / (b[1] - a[1])
    return a + t * (b - a)


def fixed_torso_edge_loop(vertices: np.ndarray, faces: np.ndarray, fraction: float) -> list[tuple[int, int]]:
    plane = float(vertices[:, 1].min() + fraction * np.ptp(vertices[:, 1]))
    adjacency: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for face in faces:
        crossed = []
        for ia, ib in ((int(face[0]), int(face[1])), (int(face[1]), int(face[2])), (int(face[2]), int(face[0]))):
            a, b = (ia, ib) if ia < ib else (ib, ia)
            da, db = vertices[a, 1] - plane, vertices[b, 1] - plane
            if da * db < 0.0:
                crossed.append((a, b))
        if len(crossed) == 2:
            adjacency.setdefault(crossed[0], []).append(crossed[1])
            adjacency.setdefault(crossed[1], []).append(crossed[0])
    components = []
    visited = set()
    for start in adjacency:
        if start in visited:
            continue
        stack, component = [start], set()
        visited.add(start)
        while stack:
            node = stack.pop()
            component.add(node)
            for nxt in adjacency[node]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        if all(len(adjacency[node]) == 2 for node in component):
            order, previous, current = [start], None, start
            while True:
                nxt = next(node for node in adjacency[current] if node != previous)
                if nxt == start:
                    break
                order.append(nxt)
                previous, current = current, nxt
            points = np.asarray([edge_intersection(vertices, edge, plane)[[0, 2]] for edge in order])
            perimeter = float(np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1).sum())
            components.append((perimeter, order))
    if not components:
        raise ValueError("No fixed closed section loop")
    return max(components, key=lambda item: item[0])[1]


def torch_loop_points(vertices: torch.Tensor, edges: torch.Tensor, plane: torch.Tensor) -> torch.Tensor:
    a, b = vertices[edges[:, 0]], vertices[edges[:, 1]]
    t = (plane - a[:, 1]) / (b[:, 1] - a[:, 1])
    points = a + t[:, None] * (b - a)
    return points[:, [0, 2]]


def exact_metrics(vertices: np.ndarray, faces: np.ndarray, fractions: dict[str, float]) -> tuple[dict, dict]:
    height = float(np.ptp(vertices[:, 1]))
    values = {"height": height}
    details = {}
    for name in BAND_NAMES:
        plane = float(vertices[:, 1].min() + fractions[name] * height)
        segments, coplanar, ambiguous = triangle_plane_segments(vertices, faces, plane)
        loops, open_components, _ = stitch_segments(segments)
        if not loops:
            raise ValueError(f"No exact loop for {name}")
        values[name] = loops[0].perimeter
        details[name] = {
            "plane_y": plane,
            "closed_loop_count": len(loops),
            "open_component_count": open_components,
            "coplanar_edge_count": coplanar,
            "ambiguous_triangle_count": ambiguous,
            "largest_torso_loop_perimeter": loops[0].perimeter,
            "torso_points_xz": loops[0].points,
        }
    return values, details


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# MHR body-fit candidate-1; geometry candidate only\n")
        stream.write("o mhr_body_fit_candidate1\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.17g} {y:.17g} {z:.17g}\n")
        for a, b, c in faces:
            stream.write(f"f {int(a)+1} {int(b)+1} {int(c)+1}\n")


def draw_overlay(path: Path, vertices: np.ndarray, faces: np.ndarray, details: dict, measurements: dict) -> None:
    image = Image.new("RGB", (1800, 1350), "white")
    draw = ImageDraw.Draw(image)
    font, small = ImageFont.load_default(size=18), ImageFont.load_default(size=14)
    draw.text((30, 20), "MHR BODY FIT CANDIDATE-1", fill=(20, 20, 20), font=font)
    draw.text((30, 48), "NOT ANATOMICALLY VALIDATED - FIRST 20 IDENTITY COEFFICIENTS ONLY", fill=(180, 25, 25), font=small)
    unique_edges = set()
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            unique_edges.add(tuple(sorted((int(a), int(b)))))
    edges = np.asarray(sorted(unique_edges), dtype=np.uint32)

    def panel(box, axes, label):
        draw.rectangle(box, outline=(90, 90, 90))
        points = vertices[:, axes]
        lo, hi = points.min(axis=0), points.max(axis=0)
        def project(p):
            x = box[0] + 20 + (p[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0] - 40)
            y = box[3] - 20 - (p[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1] - 50)
            return x, y
        for a, b in edges[::2]:
            draw.line((*project(points[a]), *project(points[b])), fill=(125, 150, 175), width=1)
        draw.text((box[0] + 10, box[1] + 8), label, fill=(20, 20, 20), font=small)
    panel((30, 85, 580, 1315), (0, 1), "FRONT X/Y WIREFRAME")
    panel((600, 85, 1050, 1315), (2, 1), "SIDE Z/Y WIREFRAME")

    all_points = np.concatenate([details[name]["torso_points_xz"] for name in BAND_NAMES])
    lo, hi = all_points.min(axis=0), all_points.max(axis=0)
    for index, name in enumerate(BAND_NAMES):
        box = (1080, 85 + 305 * index, 1770, 370 + 305 * index)
        draw.rectangle(box, outline=(90, 90, 90))
        points = details[name]["torso_points_xz"]
        mapped = []
        for point in points:
            x = box[0] + 30 + (point[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0] - 60)
            y = box[3] - 30 - (point[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1] - 75)
            mapped.append((x, y))
        mapped.append(mapped[0])
        draw.line(mapped, fill=COLORS[name], width=4)
        draw.text((box[0] + 10, box[1] + 8), f"{name}: target={TARGETS[name]:.2f} actual={measurements[name]:.4f}", fill=(20, 20, 20), font=small)
        draw.text((box[0] + 10, box[1] + 31), f"closed loops={details[name]['closed_loop_count']} (largest torso shown)", fill=(130, 45, 45), font=small)
    image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--offsets", type=Path, required=True)
    parser.add_argument("--bands", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--equivalence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    base = load_indexed_tsv(args.vertices, VERTEX_COUNT, 3, np.float64)
    faces = load_indexed_tsv(args.faces, FACE_COUNT, 3, np.uint64).astype(np.uint32)
    offsets = load_offsets(args.offsets)
    band_data = json.loads(args.bands.read_text(encoding="utf-8"))
    fractions = {name: float(band_data["candidate_bands_fraction_above_y_min"][name]) for name in BAND_NAMES}
    equivalence = json.loads(args.equivalence.read_text(encoding="utf-8"))

    fixed_edges = {name: fixed_torso_edge_loop(base, faces, fractions[name]) for name in BAND_NAMES}
    base_t = torch.tensor(base, dtype=torch.float64)
    offsets_t = torch.tensor(offsets, dtype=torch.float64)
    edge_tensors = {name: torch.tensor(edges, dtype=torch.long) for name, edges in fixed_edges.items()}
    raw = torch.zeros(BODY_COEFFICIENTS, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.Adam([raw], lr=0.04)
    target_t = torch.tensor([TARGETS[name] for name in BAND_NAMES], dtype=torch.float64)
    measurement_scales = torch.tensor([0.75, 0.75, 0.75, 0.75], dtype=torch.float64)
    history = []
    for iteration in range(1600):
        optimizer.zero_grad()
        coeffs = 3.0 * torch.tanh(raw)
        unscaled_vertices = base_t + torch.einsum("k,kvc->vc", coeffs, offsets_t)
        unscaled_height = unscaled_vertices[:, 1].max() - unscaled_vertices[:, 1].min()
        uniform_scale = TARGETS["height"] / unscaled_height
        vertices = unscaled_vertices * uniform_scale
        y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
        height = y_max - y_min
        metrics, symmetry = [], []
        for name in BAND_NAMES:
            plane = y_min + fractions[name] * height
            points = torch_loop_points(vertices, edge_tensors[name], plane)
            perimeter = torch.linalg.vector_norm(torch.roll(points, -1, 0) - points, dim=1).sum()
            metrics.append(perimeter)
            symmetry.extend([points[:, 0].mean(), points[:, 0].max() + points[:, 0].min()])
        metric_t = torch.stack(metrics)
        measurement_loss = torch.square((metric_t - target_t) / measurement_scales).mean()
        prior_loss = 0.05 * torch.square(coeffs).mean()
        symmetry_loss = 0.02 * torch.square(torch.stack(symmetry)).mean()
        loss = measurement_loss + prior_loss + symmetry_loss
        loss.backward()
        optimizer.step()
        if iteration % 100 == 0 or iteration == 1599:
            history.append({"iteration": iteration, "loss": float(loss.detach()), "uniform_scale": float(uniform_scale.detach()), "scaled_height": float(height.detach()), "scaled_circumferences": metric_t.detach().tolist(), "max_abs_coefficient": float(coeffs.detach().abs().max())})

    adam_coefficients = (3.0 * torch.tanh(raw)).detach().cpu().numpy()

    def scipy_residual(coefficients_np: np.ndarray) -> np.ndarray:
        unscaled = base + np.einsum("k,kvc->vc", coefficients_np, offsets)
        uniform = TARGETS["height"] / float(np.ptp(unscaled[:, 1]))
        scaled = unscaled * uniform
        y_min = float(scaled[:, 1].min())
        height_np = float(np.ptp(scaled[:, 1]))
        circumferences = []
        symmetry_values = []
        for section_name in BAND_NAMES:
            plane = y_min + fractions[section_name] * height_np
            section_points = np.asarray(
                [edge_intersection(scaled, edge, plane)[[0, 2]] for edge in fixed_edges[section_name]]
            )
            circumference = float(
                np.linalg.norm(np.roll(section_points, -1, axis=0) - section_points, axis=1).sum()
            )
            circumferences.append((circumference - TARGETS[section_name]) / 0.75)
            symmetry_values.extend(
                [float(section_points[:, 0].mean()), float(section_points[:, 0].max() + section_points[:, 0].min())]
            )
        prior = math.sqrt(0.05 / BODY_COEFFICIENTS) * coefficients_np
        symmetry_residual = math.sqrt(0.02 / len(symmetry_values)) * np.asarray(symmetry_values)
        return np.concatenate([np.asarray(circumferences), prior, symmetry_residual])

    scipy_result = least_squares(
        scipy_residual,
        adam_coefficients,
        bounds=(-3.0, 3.0),
        max_nfev=500,
        xtol=1e-11,
        ftol=1e-11,
        gtol=1e-11,
    )
    coefficients = scipy_result.x
    unscaled_fitted = base + np.einsum("k,kvc->vc", coefficients, offsets)
    unscaled_height = float(np.ptp(unscaled_fitted[:, 1]))
    uniform_scale = TARGETS["height"] / unscaled_height
    fitted = unscaled_fitted * uniform_scale
    exact, details = exact_metrics(fitted, faces, fractions)
    errors = {name: exact[name] - TARGETS[name] for name in TARGETS}

    # TorchScript is oracle-only: validate that the ufbx-linear result remains reconstructable/equivalent.
    with zipfile.ZipFile(args.archive) as archive:
        model_bytes = archive.read("assets/mhr_model.pt")
    model = torch.jit.load(io.BytesIO(model_bytes), map_location="cpu").eval()
    identity = torch.zeros((1, 45), dtype=torch.float32)
    identity[0, :20] = torch.tensor(coefficients, dtype=torch.float32)
    pose = torch.zeros((1, 204), dtype=torch.float32)
    expression = torch.zeros((1, 72), dtype=torch.float32)
    with torch.no_grad():
        oracle_vertices, _ = model(identity, pose, expression)
    oracle = oracle_vertices[0].double().numpy()
    transform = equivalence["fixed_transform"]
    fitted_to_oracle = unscaled_fitted[:, transform["permutation"]] * np.asarray(transform["signs"]) * float(transform["scale"]) + np.asarray(transform["translation"])
    oracle_delta = fitted_to_oracle - oracle
    oracle_rms = float(np.sqrt(np.mean(oracle_delta**2)))
    oracle_max = float(np.linalg.norm(oracle_delta, axis=1).max())

    coeff_path = args.output_dir / "candidate1-coefficients.json"
    coeff_tsv = args.output_dir / "candidate1-coefficients.tsv"
    obj_path = args.output_dir / "candidate1.obj"
    overlay_path = args.output_dir / "candidate1-wireframe-sections.png"
    coeff_tsv.write_text("candidate1\t" + "\t".join(f"{value:.17g}" for value in coefficients) + "\n", encoding="utf-8", newline="\n")
    write_obj(obj_path, fitted, faces)
    draw_overlay(overlay_path, fitted, faces, details, exact)
    payload = {
        "status": "CANDIDATE_1_NOT_ANATOMICALLY_VALIDATED",
        "coefficient_contract": {"optimized_indices": list(range(20)), "remaining_indices_20_44": [0.0] * 25, "bounds": [-3.0, 3.0]},
        "coefficients_0_19": coefficients.tolist(),
        "near_bound_abs_ge_2_95_count": int((np.abs(coefficients) >= 2.95).sum()),
        "uniform_scale": uniform_scale,
        "unscaled_height": unscaled_height,
        "targets": TARGETS,
        "actual": exact,
        "signed_errors": errors,
        "objective": {"optimizer": "PyTorch Adam warm start plus SciPy bounded least_squares refinement", "adam_iterations": 1600, "scipy_nfev": int(scipy_result.nfev), "scipy_status": int(scipy_result.status), "scipy_message": scipy_result.message, "height_policy": "identity coefficients fit shape only; each evaluation is uniformly scaled to height 168 before circumference measurement", "l2_prior_weight": 0.05, "symmetry_weight": 0.02, "measurement_scales": measurement_scales.tolist()},
        "history": history,
        "topology": {"vertices": VERTEX_COUNT, "triangles": FACE_COUNT, "unchanged": True, "secondary_loops_excluded_from_objective": True},
        "exact_sections": {name: {key: value for key, value in detail.items() if key != "torso_points_xz"} for name, detail in details.items()},
        "torchscript_oracle_only_equivalence": {"torch": torch.__version__, "device": "cpu", "rms_coordinate": oracle_rms, "max_vertex": oracle_max},
        "reconstruction": {"method": "ufbx base vertices plus first-20 blend-shape offsets times coefficients, followed by separate origin-centered uniform scale", "coefficients_tsv": str(coeff_tsv.resolve()), "uniform_scale": uniform_scale},
        "inputs_sha256": {"vertices": sha256(args.vertices), "faces": sha256(args.faces), "offsets": sha256(args.offsets), "archive": sha256(args.archive), "equivalence": sha256(args.equivalence)},
    }
    coeff_path.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"coefficients": str(coeff_path), "obj": str(obj_path), "overlay": str(overlay_path), "actual": exact, "errors": errors, "oracle_rms": oracle_rms, "oracle_max": oracle_max}, indent=2))


if __name__ == "__main__":
    main()
