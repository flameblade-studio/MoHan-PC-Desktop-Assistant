from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from morph_body_candidate2 import (
    FACE_COUNT,
    FRACTIONS,
    TARGETS,
    TARGET_HEIGHT,
    VERTEX_COUNT,
    apply_morph,
    central_torso_component,
    draw_overlay,
    exact_sections,
    load_indexed_tsv,
    write_obj,
    write_vertices_bin,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_joint_positions(path: Path, scale: float) -> dict[str, np.ndarray]:
    result = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            result[row["bone_name"]] = np.asarray([float(row["x"]), float(row["y"]), float(row["z"])]) * scale
    required = {"l_upleg", "r_upleg", "c_spine0", "c_spine1", "c_spine2", "c_spine3"}
    missing = required - result.keys()
    if missing:
        raise ValueError(f"Missing official joints: {sorted(missing)}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--skeleton", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = load_indexed_tsv(args.vertices, VERTEX_COUNT, 3, np.float64)
    faces = load_indexed_tsv(args.faces, FACE_COUNT, 3, np.uint32)
    base_scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))
    base = raw * base_scale
    joints = load_joint_positions(args.skeleton, base_scale)
    base_actual, base_details = exact_sections(base, faces)
    ordered = sorted(FRACTIONS, key=FRACTIONS.get)
    anchor_y = np.asarray([base_details[name]["plane_y"] for name in ordered])
    center_x = np.zeros(len(ordered), dtype=np.float64)

    spine_names = ["c_spine0", "c_spine1", "c_spine2", "c_spine3"]
    spine_y = np.asarray([joints[name][1] for name in spine_names])
    spine_z = np.asarray([joints[name][2] for name in spine_names])
    hip_y = float((joints["l_upleg"][1] + joints["r_upleg"][1]) / 2)
    hip_z = float((joints["l_upleg"][2] + joints["r_upleg"][2]) / 2)
    extended_y = np.concatenate(([hip_y], spine_y))
    extended_z = np.concatenate(([hip_z], spine_z))
    center_z = np.interp(anchor_y, extended_y, extended_z)

    support_low = float(base[:, 1].min() + 0.44 * TARGET_HEIGHT)
    support_high = float(base[:, 1].min() + 0.79 * TARGET_HEIGHT)
    weight, component_report = central_torso_component(base, faces, base_details, support_low, support_high)
    anchor_scale = np.asarray([TARGETS[name] / base_actual[name] for name in ordered])
    history = []
    final = base
    final_spline = None
    for iteration in range(12):
        final, final_spline = apply_morph(
            base, weight, anchor_y, anchor_scale, center_x, center_z, support_low, support_high
        )
        actual, details = exact_sections(final, faces)
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
        raise RuntimeError(f"Candidate3 failed convergence: {history[-1]}")

    displacement = np.linalg.norm(final - base, axis=1)
    if float(displacement[weight == 0].max(initial=0.0)) != 0.0:
        raise ValueError("Protected vertex changed")
    obj = args.output_dir / "candidate3.obj"
    vertices_bin = args.output_dir / "candidate3-vertices.bin"
    overlay = args.output_dir / "candidate3-wireframe-sections.png"
    report_path = args.output_dir / "candidate3-report.json"
    write_obj(obj, final, faces)
    write_vertices_bin(vertices_bin, final)
    draw_overlay(
        overlay,
        final,
        faces,
        details,
        actual,
        title="MHR BODY MORPH CANDIDATE-3",
        subtitle="OFFICIAL SKELETON-AXIS CENTERED C2 LOCAL TORSO MORPH",
    )
    sample_y = np.linspace(support_low, support_high, 1025)
    report = {
        "status": "CANDIDATE_3_SECTION_TARGETS_PASS_PENDING_ANATOMY_AUDIT",
        "reason": "candidate2 front/back depth ratio drifted because its surface-centroid scale center did not follow the official central skeleton axis",
        "base_uniform_scale_to_168": base_scale,
        "height": float(np.ptp(final[:, 1])),
        "fractions": FRACTIONS,
        "targets": TARGETS,
        "actual": actual,
        "signed_errors": {name: actual[name] - TARGETS[name] for name in TARGETS},
        "all_section_errors_le_0_5_cm": all(abs(actual[name] - TARGETS[name]) <= 0.5 for name in TARGETS),
        "iterations": len(history),
        "history": history,
        "local_scale_anchor_order": ordered,
        "local_scale_anchor_values": anchor_scale.tolist(),
        "scale_center": {
            "x": center_x.tolist(),
            "z": center_z.tolist(),
            "source": "interpolation from official FBX l/r_upleg mean through c_spine0..c_spine3",
        },
        "spline": {
            "type": "SciPy CubicSpline C2 with dense linear knots",
            "support_low_y": support_low,
            "support_high_y": support_high,
            "sampled_min_scale": float(final_spline(sample_y).min()),
            "sampled_max_scale": float(final_spline(sample_y).max()),
        },
        "central_torso_component": component_report,
        "protected_zero_weight_vertices": int(np.count_nonzero(weight == 0)),
        "protected_vertices_max_displacement": float(displacement[weight == 0].max(initial=0.0)),
        "topology": {"vertices": VERTEX_COUNT, "triangles": FACE_COUNT, "unchanged": True},
        "inputs_sha256": {
            "vertices": sha256(args.vertices),
            "faces": sha256(args.faces),
            "skeleton": sha256(args.skeleton),
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(report_path.resolve()),
        "obj": str(obj.resolve()),
        "vertices_bin": str(vertices_bin.resolve()),
        "overlay": str(overlay.resolve()),
        "actual": actual,
        "errors": report["signed_errors"],
        "iterations": len(history),
    }, indent=2))


if __name__ == "__main__":
    main()
