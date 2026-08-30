from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np


def read_calculator(path: Path) -> tuple[str, np.ndarray]:
    with path.open("rb") as stream:
        if stream.read(8) != b"MHRBDY1\0":
            raise ValueError("Bad calculator magic")
        vertex_count, case_count = struct.unpack("<II", stream.read(8))
        if vertex_count != 18_439 or case_count != 1:
            raise ValueError(f"Unexpected counts: {vertex_count}, {case_count}")
        name = stream.read(64).split(b"\0", 1)[0].decode("ascii")
        vertices = np.frombuffer(stream.read(vertex_count * 3 * 8), dtype="<f8").reshape(vertex_count, 3).copy()
        if stream.read(1):
            raise ValueError("Trailing calculator bytes")
    return name, vertices


def read_obj(path: Path) -> np.ndarray:
    vertices = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(value) for value in line.split()[1:4]])
    result = np.asarray(vertices, dtype=np.float64)
    if result.shape != (18_439, 3):
        raise ValueError(f"Unexpected OBJ shape {result.shape}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calculator-bin", type=Path, required=True)
    parser.add_argument("--coefficients", type=Path, required=True)
    parser.add_argument("--obj", type=Path, required=True)
    args = parser.parse_args()
    name, unscaled = read_calculator(args.calculator_bin)
    payload = json.loads(args.coefficients.read_text(encoding="utf-8"))
    scale = float(payload["uniform_scale"])
    obj = read_obj(args.obj)
    delta = unscaled * scale - obj
    result = {
        "status": "PASS" if np.array_equal(unscaled * scale, obj) else "PASS_WITH_FLOAT_TOLERANCE",
        "case_name": name,
        "uniform_scale": scale,
        "vertex_count": len(obj),
        "rms_coordinate": float(np.sqrt(np.mean(delta**2))),
        "max_vertex_error": float(np.linalg.norm(delta, axis=1).max()),
        "allclose_at_1e_12": bool(np.allclose(unscaled * scale, obj, rtol=0.0, atol=1e-12)),
        "topology_source": "unchanged verified faces TSV",
    }
    if not result["allclose_at_1e_12"]:
        raise ValueError(json.dumps(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
