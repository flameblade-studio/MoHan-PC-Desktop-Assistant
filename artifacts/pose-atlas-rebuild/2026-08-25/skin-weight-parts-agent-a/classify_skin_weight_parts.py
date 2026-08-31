from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
FACES = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/run-fixed-clone/mhr-lod1.faces.tsv"
PARTS = {
    1: "head", 2: "torso",
    3: "left_upper_arm", 4: "left_lower_arm", 5: "left_hand",
    6: "right_upper_arm", 7: "right_lower_arm", 8: "right_hand",
    9: "left_upper_leg", 10: "left_lower_leg", 11: "left_foot",
    12: "right_upper_leg", 13: "right_lower_leg", 14: "right_foot",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bone_part(name: str) -> int | None:
    if name in {"c_head", "c_jaw"}: return 1
    if name == "root" or name.startswith("c_spine") or name.startswith("c_neck") or name in {"l_clavicle", "r_clavicle"}: return 2
    for side, offset in (("l_", 0), ("r_", 3)):
        if name.startswith(side + "uparm"): return 3 + offset
        if name.startswith(side + "lowarm"): return 4 + offset
        if any(name.startswith(side + stem) for stem in ("wrist", "thumb", "index", "middle", "ring", "pinky")): return 5 + offset
    for side, offset in (("l_", 0), ("r_", 3)):
        if name.startswith(side + "upleg"): return 9 + offset
        if name.startswith(side + "lowleg"): return 10 + offset
        if any(name.startswith(side + stem) for stem in ("foot", "talocrural", "subtalar", "transversetarsal", "ball")): return 11 + offset
    return None


def main() -> int:
    clusters = list(csv.DictReader((HERE / "skin-clusters.tsv").open(encoding="utf-8"), delimiter="\t"))
    if len(clusters) != 127: raise ValueError("cluster count")
    cluster_map = {int(row["cluster_index"]): bone_part(row["bone_name"]) for row in clusters}
    bone_map = [{"cluster_index": int(row["cluster_index"]), "bone_name": row["bone_name"], "part_id": cluster_map[int(row["cluster_index"])], "part_name": PARTS.get(cluster_map[int(row["cluster_index"])])} for row in clusters]
    accum: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    totals: dict[int, float] = defaultdict(float)
    with (HERE / "vertex-skin-weights.tsv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            vertex, cluster, weight = int(row["vertex_index"]), int(row["cluster_index"]), float(row["weight"])
            totals[vertex] += weight
            part = cluster_map[cluster]
            if part is not None: accum[vertex][part] += weight
    assignments: list[int] = []
    records = []
    confidence = Counter()
    unknown_weight_vertices = unweighted = ambiguous = 0
    for vertex in range(18439):
        total = totals.get(vertex, 0.0)
        if total <= 0.0:
            unweighted += 1; assignments.append(0); records.append((vertex, 0, "unknown", 0.0, 0.0, total, "unweighted")); continue
        ranked = sorted(accum[vertex].items(), key=lambda item: (-item[1], item[0]))
        known = sum(value for _, value in ranked)
        if known / total < 0.999 or not ranked:
            unknown_weight_vertices += 1; assignments.append(0); records.append((vertex, 0, "unknown", 0.0, 0.0, total, "unknown_bone_weight")); continue
        top_part, top_weight = ranked[0]
        second_weight = ranked[1][1] if len(ranked) > 1 else 0.0
        share, margin = top_weight / known, (top_weight - second_weight) / known
        if share < 0.55 or margin < 0.10:
            ambiguous += 1; assignments.append(255); records.append((vertex, 255, "ambiguous", share, margin, total, "joint_boundary")); continue
        level = "high" if share >= 0.85 and margin >= 0.70 else "medium"
        confidence[level] += 1
        assignments.append(top_part); records.append((vertex, top_part, PARTS[top_part], share, margin, total, level))
    counts = Counter(assignments)
    coverage = sum(counts[part] for part in PARTS) / 18439
    ambiguity = counts[255] / 18439
    gate = {
        "unweighted_fraction_le_0_001": unweighted / 18439 <= 0.001,
        "unknown_weight_fraction_le_0_005": unknown_weight_vertices / 18439 <= 0.005,
        "ambiguous_fraction_le_0_08": ambiguity <= 0.08,
        "assigned_coverage_ge_0_92": coverage >= 0.92,
        "all_14_parts_nonempty": all(counts[part] > 0 for part in PARTS),
    }
    passed = all(gate.values())
    with (HERE / "vertex-part-ids.tsv").open("w", encoding="utf-8", newline="") as output:
        output.write("vertex_index\tpart_id\tpart_name\tdominant_share\tmargin\ttotal_weight\tboundary_confidence\n")
        for row in records: output.write("\t".join(map(str, row)) + "\n")
    face_parts = []
    with FACES.open(encoding="utf-8", newline="") as source:
        for row in csv.reader(source, delimiter="\t"):
            face_index, a, b, c = map(int, row)
            parts = (assignments[a], assignments[b], assignments[c])
            part = parts[0] if parts[0] == parts[1] == parts[2] and parts[0] not in {0, 255} else 255
            face_parts.append(part)
            if face_index + 1 != len(face_parts): raise ValueError("face index order")
    with (HERE / "face-part-ids.tsv").open("w", encoding="utf-8", newline="") as output:
        output.write("face_index\tpart_id\n")
        for index, part in enumerate(face_parts): output.write(f"{index}\t{part}\n")
    manifest = {
        "schema": "mohan.mhr.skin-weight-derived-parts.v1",
        "status": "PASS_FOR_CONTROL_MASKS" if passed else "FAIL_CLOSED",
        "derivation": "Only exact FBX bone names and cumulative per-vertex skin weights; no coordinate rules.",
        "thresholds": {"known_weight_ratio": 0.999, "dominant_share": 0.55, "dominant_margin": 0.10, "max_ambiguous_fraction": 0.08, "min_assigned_coverage": 0.92},
        "parts": [{"part_id": part, "part_name": name, "vertex_count": counts[part], "coverage": counts[part] / 18439} for part, name in PARTS.items()],
        "special": {"unknown_part_id": 0, "ambiguous_boundary_part_id": 255, "unweighted_vertices": unweighted, "unknown_weight_vertices": unknown_weight_vertices, "ambiguous_vertices": counts[255], "ambiguous_fraction": ambiguity, "assigned_coverage": coverage, "boundary_confidence_counts": dict(confidence)},
        "gate": gate,
        "bone_mapping": bone_map,
        "unsupported": {"eyes": "UNKNOWN_ZERO_WEIGHT_EYE_BONES", "teeth": "UNKNOWN_ZERO_WEIGHT_TEETH_BONE", "tongue": "NOT_REQUESTED_ZERO_WEIGHT_BONES"},
        "files": {"clusters_sha256": digest(HERE / "skin-clusters.tsv"), "weights_sha256": digest(HERE / "vertex-skin-weights.tsv"), "candidate3_vertices_sha256": "23C5ECB3E943089954459F9F16E5551F0413571F5BACF85E3C3A6DCF155318A4", "topology_faces_sha256": digest(FACES)},
    }
    (HERE / "skin-weight-part-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "assigned_coverage": coverage, "ambiguous_fraction": ambiguity, "unweighted": unweighted, "unknown_weight": unknown_weight_vertices, "face_ambiguous": Counter(face_parts)[255]}, sort_keys=True))
    return 0 if passed else 3


if __name__ == "__main__": sys.exit(main())
