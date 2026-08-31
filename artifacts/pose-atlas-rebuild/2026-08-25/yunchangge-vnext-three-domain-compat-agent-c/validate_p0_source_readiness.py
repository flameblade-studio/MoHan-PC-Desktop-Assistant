"""Fail closed if a P0 record is claimed repair-ready without real evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[4]
MATRIX = Path(__file__).resolve().parent / "p0-reusable-source-deterministic-matrix.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("p0_record_count") != 73:
        errors.append("P0 record count must be 73")
    if data.get("promotion_allowed") is not False:
        errors.append("current P0 matrix must keep promotion disabled")
    if data.get("immediately_repairable_formal_record_count") != 0:
        errors.append("formal-ready count must remain zero while evidence is missing")
    packages = data.get("packages", [])
    if sum(item.get("record_count", 0) for item in packages) != 73:
        errors.append("package records do not sum to 73")
    control_manifest = json.loads(
        (PROJECT / data["source_evidence"]["geometry_controls_manifest"]["path"]).read_text(encoding="utf-8")
    )
    control_views = {entry["formal_view_id"]: entry for entry in control_manifest["views"]}
    rigid_manifest = json.loads(
        (PROJECT / data["source_evidence"]["rigid_soft_manifest"]["path"]).read_text(encoding="utf-8")
    )
    rigid_views = {entry["view_id"]: entry for entry in rigid_manifest["views"]}
    for item in packages:
        view = item.get("view_id", "UNKNOWN")
        control_entry = control_views.get(view)
        if control_entry is None:
            errors.append(f"{view}: absent from geometry-control manifest")
        else:
            for kind in ("depth", "normal", "silhouette"):
                evidence = control_entry["outputs"][kind]
                path = Path(evidence["absolute_path"])
                if not path.is_file() or sha256(path).lower() != evidence["output_sha256"].lower():
                    errors.append(f"{view}: {kind} control missing or hash drift")
        rigid_entry = rigid_views.get(view)
        if rigid_entry is None:
            errors.append(f"{view}: absent from rigid/soft manifest")
        else:
            for kind in ("source", "rigid", "soft"):
                evidence = rigid_entry[kind]
                if kind == "source":
                    path = PROJECT / evidence["path"]
                else:
                    manifest_root = PROJECT / data["source_evidence"]["rigid_soft_manifest"]["path"]
                    path = manifest_root.parent / evidence["path"]
                if not path.is_file() or sha256(path).lower() != evidence["sha256"].lower():
                    errors.append(f"{view}: {kind} control missing or hash drift")
        for group in ("reusable_geometry_controls", "reusable_coarse_object_id", "reusable_geometry_rigid_soft"):
            records = item.get(group, {})
            for value in records.values():
                if not isinstance(value, dict) or "path" not in value:
                    continue
                path = PROJECT / value["path"]
                if not path.is_file():
                    errors.append(f"{view}: missing evidence file {value['path']}")
                elif sha256(path) != value.get("sha256"):
                    errors.append(f"{view}: hash drift {value['path']}")
        mother = item.get("candidate", item.get("closest_existing_mother_candidate", {}))
        path_value = mother.get("path")
        if path_value:
            path = PROJECT / path_value
            if not path.is_file() or sha256(path) != mother.get("sha256"):
                errors.append(f"{view}: candidate missing or hash drift")
        if item.get("formal_repair_now") is True:
            missing = item.get("missing_formal_inputs", {})
            if any(value == "MISSING" for value in missing.values()):
                errors.append(f"{view}: formal repair claimed with missing evidence")
            if mother.get("formal_pixel_authority") is not True:
                errors.append(f"{view}: formal repair claimed without pixel authority")
            if item.get("reusable_coarse_object_id", {}).get("sufficient_for_18_fine_face_layers") is not True:
                errors.append(f"{view}: coarse head part-ID cannot satisfy fine facial masks")
    for label, evidence in data.get("source_evidence", {}).items():
        path_value = evidence.get("path") if isinstance(evidence, dict) else None
        if not path_value:
            continue
        path = PROJECT / path_value
        if not path.is_file():
            errors.append(f"source evidence missing: {label}")
        elif sha256(path) != evidence.get("sha256"):
            errors.append(f"source evidence hash drift: {label}")
    return errors


def main() -> int:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    errors = validate(data)
    print(json.dumps({"matrix": str(MATRIX), "validation_errors": errors, "formal_gate": "BLOCK", "exit_code": 4 if not errors else 4}, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
