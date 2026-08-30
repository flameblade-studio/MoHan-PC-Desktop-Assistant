from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np


def load_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices = []
    faces = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(value) for value in line.split()[1:]])
            elif line.startswith("f "):
                faces.append([int(value) - 1 for value in line.split()[1:]])
    return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.uint32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices-bin", type=Path, required=True)
    parser.add_argument("--obj", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    with args.vertices_bin.open("rb") as stream:
        magic = stream.read(8)
        count, components = struct.unpack("<II", stream.read(8))
        payload = stream.read()
    if magic != b"MHRVTX2\0" or count != 18_439 or components != 3:
        raise ValueError(f"Invalid binary header: {magic!r} {count} {components}")
    binary_vertices = np.frombuffer(payload, dtype="<f8").reshape(count, components)
    obj_vertices, obj_faces = load_obj(args.obj)
    face_table = np.loadtxt(args.faces, delimiter="\t", dtype=np.uint32)
    expected_faces = face_table[:, 1:]
    report = json.loads(args.report.read_text(encoding="utf-8"))
    difference = binary_vertices - obj_vertices
    rms = float(np.sqrt(np.mean(difference * difference)))
    maximum = float(np.linalg.norm(difference, axis=1).max())
    result = {
        "status": "PASS",
        "magic": "MHRVTX2\\0",
        "vertex_count": count,
        "components": components,
        "obj_vertex_count": len(obj_vertices),
        "obj_face_count": len(obj_faces),
        "topology_exact": bool(np.array_equal(obj_faces, expected_faces)),
        "bin_obj_rms_coordinate": rms,
        "bin_obj_max_vertex": maximum,
        "bin_obj_exact": bool(np.array_equal(binary_vertices, obj_vertices)),
        "height_168": abs(float(np.ptp(binary_vertices[:, 1])) - 168.0) <= 1e-12,
        "section_targets_pass": bool(report["all_section_errors_le_0_5_cm"]),
        "protected_vertices_exact": report["protected_vertices_max_displacement"] == 0.0,
    }
    if not all((result["topology_exact"], result["bin_obj_exact"], result["height_168"], result["section_targets_pass"], result["protected_vertices_exact"])):
        raise ValueError(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
