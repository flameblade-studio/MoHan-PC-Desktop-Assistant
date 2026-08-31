from __future__ import annotations

import csv
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
BASE = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
FACES = BASE / "run-fixed-clone/mhr-lod1.faces.tsv"
VERTICES = BASE / "body-morph-candidate3/candidate3-vertices.bin"
CONTROLS = BASE / "candidate3-yaw-controls-24/candidate3-camera-anchor-control-manifest.json"
EXPECTED_VERTICES = 18439
EXPECTED_FACES = 36874


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_faces() -> list[tuple[int, int, int]]:
    result = []
    with FACES.open(encoding="utf-8", newline="") as source:
        for row in csv.reader(source, delimiter="\t"):
            face_index, a, b, c = map(int, row)
            if face_index != len(result):
                raise ValueError("non-contiguous face indices")
            result.append((a, b, c))
    if len(result) != EXPECTED_FACES:
        raise ValueError("face count mismatch")
    return result


def verify_candidate3() -> None:
    data = VERTICES.read_bytes()
    if data[:8] != b"MHRVTX2\0":
        raise ValueError("candidate3 vertex header mismatch")
    count, dimensions = struct.unpack_from("<II", data, 8)
    if (count, dimensions) != (EXPECTED_VERTICES, 3) or len(data) != 16 + count * dimensions * 8:
        raise ValueError("candidate3 vertex payload mismatch")


def components(faces: list[tuple[int, int, int]]) -> tuple[list[int], list[int]]:
    parent = list(range(EXPECTED_VERTICES))
    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for a, b, c in faces:
        union(a, b); union(b, c)
    roots = [find(index) for index in range(EXPECTED_VERTICES)]
    ordered = {root: index for index, root in enumerate(sorted(set(roots)))}
    vertex_component = [ordered[root] for root in roots]
    face_component = []
    for face in faces:
        ids = {vertex_component[index] for index in face}
        if len(ids) != 1:
            raise ValueError("face crosses topology components")
        face_component.append(ids.pop())
    return vertex_component, face_component


def main() -> int:
    verify_candidate3()
    faces = read_faces()
    vertex_component, face_component = components(faces)
    vertex_counts = Counter(vertex_component)
    face_counts = Counter(face_component)
    nodes = list(csv.DictReader((HERE / "mhr-lod1.nodes.tsv").open(encoding="utf-8"), delimiter="\t"))
    materials = list(csv.DictReader((HERE / "mhr-lod1.materials.tsv").open(encoding="utf-8"), delimiter="\t"))
    groups = list(csv.DictReader((HERE / "mhr-lod1.face-groups.tsv").open(encoding="utf-8"), delimiter="\t"))
    if len(nodes) != 1 or nodes[0]["node_name"] != "body_mesh":
        raise ValueError("unexpected MHR node evidence")
    controls = json.loads(CONTROLS.read_text(encoding="utf-8"))
    views = controls["views"]
    if len(views) != 24:
        raise ValueError("candidate3 control view count mismatch")
    with (HERE / "topology-component-vertices.tsv").open("w", encoding="utf-8", newline="") as output:
        output.write("vertex_index\ttopology_component_id\n")
        for index, component in enumerate(vertex_component): output.write(f"{index}\t{component}\n")
    with (HERE / "topology-component-faces.tsv").open("w", encoding="utf-8", newline="") as output:
        output.write("face_index\ttopology_component_id\n")
        for index, component in enumerate(face_component): output.write(f"{index}\t{component}\n")
    manifest = {
        "schema": "mohan.mhr.candidate3.part-id-manifest.v1",
        "status": "WHOLE_NODE_AND_TOPOLOGY_COMPONENTS_ONLY_NO_ANATOMICAL_SEGMENTATION",
        "source": {
            "fbx": str(PROJECT / "artifacts/third-party-downloads/MHR-v1.0.1-assets/extracted/assets/lod1.fbx"),
            "ufbx_version": "0.23.0",
            "candidate3_vertices": str(VERTICES),
            "candidate3_vertices_sha256": digest(VERTICES),
            "faces_sha256": digest(FACES),
            "topology": {"vertices": EXPECTED_VERTICES, "faces": EXPECTED_FACES},
        },
        "fbx_evidence": {"mesh_nodes": nodes, "materials": materials, "face_groups": groups},
        "render_part_ids": [
            {"id": 0, "name": "background", "source": "renderer"},
            {"id": 1, "name": "body_mesh", "source": "FBX node exact name", "node_element_id": 527, "semantic_scope": "whole_unsegmented_mesh", "vertex_count": EXPECTED_VERTICES, "face_count": EXPECTED_FACES},
        ],
        "topology_components": [
            {"component_id": component, "vertex_count": vertex_counts[component], "face_count": face_counts[component], "semantic_label": None, "semantic_claim_allowed": False}
            for component in sorted(vertex_counts)
        ],
        "requested_semantic_parts": {
            key: {"status": "UNAVAILABLE_NO_FBX_NODE_MATERIAL_OR_GROUP_EVIDENCE", "indices": None}
            for key in ("head", "torso", "arm_left", "arm_right", "hand_left", "hand_right", "leg_left", "leg_right", "foot_left", "foot_right", "eyes", "teeth")
        },
        "clothing": {"introduced_by_this_extraction": False, "separate_fbx_node_material_or_group_found": False, "note": "No clothing part is created or labeled. Absence of a named material/group is not semantic proof about every polygon."},
        "index_files": {"vertices": "topology-component-vertices.tsv", "faces": "topology-component-faces.tsv"},
    }
    (HERE / "part-id-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    feasibility = {
        "schema": "mohan.mhr.candidate3.part-id-mask-feasibility.v1",
        "status": "OBJECT_ID_FEASIBLE_ANATOMICAL_PART_ID_BLOCKED",
        "view_count": 24,
        "views": [
            {"view_id": view["view_id"], "whole_body_object_id_mask": "FEASIBLE_RE_RENDER_ID_1", "topology_component_mask": "FEASIBLE_ONLY_AFTER_CPU_RENDERER_FACE_ID_EXTENSION", "anatomical_part_id_mask": "BLOCKED_NO_SEMANTIC_FACE_INDICES"}
            for view in views
        ],
        "existing_controls_are_not_part_ids": True,
        "reason": "Candidate3 silhouettes contain binary occupancy only; depth/normal do not retain face or semantic identity.",
        "minimum_safe_next_step": "Obtain an authoritative MHR body-part mapping tied to the exact 18439/36874 topology, or author and visually validate one without inferring anatomy from coordinates alone.",
        "not_generated": "No 24 semantic part-ID masks were generated because that would fabricate unavailable labels."
    }
    (HERE / "24-view-part-id-mask-feasibility.json").write_text(json.dumps(feasibility, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_WITH_SEMANTIC_GAP", "components": len(vertex_counts), "materials": len(materials), "face_groups": len(groups), "views": len(views)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
