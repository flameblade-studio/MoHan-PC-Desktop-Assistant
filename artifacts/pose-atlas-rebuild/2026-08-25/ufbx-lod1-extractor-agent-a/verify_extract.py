from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

import numpy as np


EXPECTED_VERTICES = 18_439
EXPECTED_FACES = 36_874


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_mhr_parser(path: Path):
    spec = importlib.util.spec_from_file_location("mhr_build_lod_topology", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load parser: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def raw_geometry(parser, fbx_path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    with fbx_path.open("rb") as stream:
        if parser._read_exact(stream, len(parser.FBX_HEADER)) != parser.FBX_HEADER:
            raise ValueError("Not binary FBX")
        version = struct.unpack("<I", parser._read_exact(stream, 4))[0]
        nodes = []
        while True:
            node = parser._read_node(stream, version)
            if node is None:
                break
            nodes.append(node)

    matches = []
    for geometry in (node for node in parser._walk(nodes) if node.name == "Geometry"):
        vertices_node = parser._child(geometry, "Vertices")
        indices_node = parser._child(geometry, "PolygonVertexIndex")
        if vertices_node is None or indices_node is None:
            continue
        vertices = np.asarray(vertices_node.properties[0], dtype=np.float64).reshape(-1, 3)
        if len(vertices) == EXPECTED_VERTICES:
            faces = parser._triangulate(indices_node.properties[0])
            matches.append((vertices, faces))
    if len(matches) != 1:
        raise ValueError(f"Expected one {EXPECTED_VERTICES}-vertex geometry, got {len(matches)}")
    return matches[0][0], matches[0][1], version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--mhr-parser", type=Path, required=True)
    args = parser.parse_args()

    extracted_vertices_table = np.loadtxt(args.vertices, delimiter="\t", dtype=np.float64)
    extracted_faces_table = np.loadtxt(args.faces, delimiter="\t", dtype=np.uint64)
    if extracted_vertices_table.shape != (EXPECTED_VERTICES, 4):
        raise ValueError(f"Unexpected vertex TSV shape: {extracted_vertices_table.shape}")
    if extracted_faces_table.shape != (EXPECTED_FACES, 4):
        raise ValueError(f"Unexpected face TSV shape: {extracted_faces_table.shape}")

    expected_vertex_ids = np.arange(EXPECTED_VERTICES, dtype=np.float64)
    expected_face_ids = np.arange(EXPECTED_FACES, dtype=np.uint64)
    vertex_ids_exact = np.array_equal(extracted_vertices_table[:, 0], expected_vertex_ids)
    face_ids_exact = np.array_equal(extracted_faces_table[:, 0], expected_face_ids)
    raw_vertices, raw_faces, fbx_version = raw_geometry(
        load_mhr_parser(args.mhr_parser), args.fbx
    )
    extracted_vertices = extracted_vertices_table[:, 1:4]
    extracted_faces = extracted_faces_table[:, 1:4].astype(np.uint32)
    vertices_exact = np.array_equal(extracted_vertices, raw_vertices)
    faces_exact = np.array_equal(extracted_faces, raw_faces)
    if not (vertex_ids_exact and face_ids_exact and vertices_exact and faces_exact):
        raise ValueError("Extracted TSV does not exactly preserve raw FBX order/data")

    result = {
        "status": "PASS",
        "fbx_version": fbx_version,
        "vertices_shape": list(extracted_vertices.shape),
        "faces_shape": list(extracted_faces.shape),
        "vertex_ids_exact": vertex_ids_exact,
        "face_ids_exact": face_ids_exact,
        "vertices_exact_roundtrip": vertices_exact,
        "faces_exact_order": faces_exact,
        "vertex_min": extracted_vertices.min(axis=0).tolist(),
        "vertex_max": extracted_vertices.max(axis=0).tolist(),
        "face_index_min": int(extracted_faces.min()),
        "face_index_max": int(extracted_faces.max()),
        "degenerate_faces": int(
            (
                (extracted_faces[:, 0] == extracted_faces[:, 1])
                | (extracted_faces[:, 1] == extracted_faces[:, 2])
                | (extracted_faces[:, 2] == extracted_faces[:, 0])
            ).sum()
        ),
        "input_fbx_sha256": sha256(args.fbx),
        "vertices_tsv_sha256": sha256(args.vertices),
        "faces_tsv_sha256": sha256(args.faces),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
