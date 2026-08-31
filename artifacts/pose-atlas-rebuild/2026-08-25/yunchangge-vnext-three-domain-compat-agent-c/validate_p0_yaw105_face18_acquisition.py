"""Validate the yaw-105 face18 acquisition workpack without generating assets."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT = Path(__file__).resolve().parents[4]
WORKPACK = HERE / "p0-yaw-105-face18-acquisition-workpack.json"
EXPECTED = [
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def structural_errors(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("view_id") != "yaw-105-pitch+00":
        errors.append("wrong view_id")
    ids = [entry.get("layer_id") for entry in data.get("layers", [])]
    if ids != EXPECTED:
        errors.append("face18 layer order or membership mismatch")
    if len(set(ids)) != 18:
        errors.append("face18 layer IDs must be unique")
    coarse = data.get("existing_control_evidence", {}).get("coarse_part_id", {})
    if coarse.get("fine_face_mask_eligible") is not False:
        errors.append("MHR coarse part-ID must be explicitly ineligible for fine-face masks")
    for name, evidence in data.get("existing_control_evidence", {}).items():
        path_value = evidence.get("path")
        if not path_value:
            continue
        path = PROJECT / path_value
        if not path.is_file():
            errors.append(f"missing control evidence: {name}")
        elif sha256(path) != evidence.get("sha256"):
            errors.append(f"control evidence hash drift: {name}")
    return errors


def production_errors(data: dict[str, Any]) -> list[str]:
    errors = structural_errors(data)
    binding = data.get("current_binding", {})
    required_counts = {
        "fine_mask_count": 18,
        "dynamic_evidence_count": 18,
        "output_count": 18,
        "manual_overlay_pass_count": 18,
    }
    if binding.get("accepted_same_view_mother") in (None, "MISSING"):
        errors.append("accepted same-view mother is missing")
    for key, expected in required_counts.items():
        if binding.get(key) != expected:
            errors.append(f"{key} must equal {expected}")
    for entry in data.get("layers", []):
        if entry.get("status") != "READY_WITH_REAL_HASHED_EVIDENCE":
            errors.append(f"{entry.get('layer_id')}: acquisition evidence missing")
        mask = entry.get("mask_binding", {})
        if mask.get("path") == data["existing_control_evidence"]["coarse_part_id"]["path"]:
            errors.append(f"{entry.get('layer_id')}: MHR coarse part-ID cannot be used as fine mask")
        if mask.get("kind") in ("COARSE_HEAD", "MHR_PART_ID", "GEOMETRY_CONTROL_ONLY"):
            errors.append(f"{entry.get('layer_id')}: forbidden coarse mask kind")
    if data.get("promotion_allowed") is not False:
        errors.append("this acquisition workpack must not enable promotion")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structure-only", action="store_true")
    parser.add_argument("--negative-coarse-part-id", action="store_true")
    args = parser.parse_args()
    data = json.loads(WORKPACK.read_text(encoding="utf-8"))
    if args.negative_coarse_part_id:
        data = copy.deepcopy(data)
        data["layers"][4]["status"] = "READY_WITH_REAL_HASHED_EVIDENCE"
        data["layers"][4]["mask_binding"] = {
            "path": data["existing_control_evidence"]["coarse_part_id"]["path"],
            "kind": "MHR_PART_ID",
        }
    errors = structural_errors(data) if args.structure_only else production_errors(data)
    result = {
        "mode": "STRUCTURE_ONLY" if args.structure_only else "PRODUCTION_GATE",
        "negative_fixture": args.negative_coarse_part_id,
        "errors": errors,
        "status": "PASS_STRUCTURE_ONLY" if args.structure_only and not errors else "BLOCK",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.structure_only:
        return 0 if not errors else 4
    return 4 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
