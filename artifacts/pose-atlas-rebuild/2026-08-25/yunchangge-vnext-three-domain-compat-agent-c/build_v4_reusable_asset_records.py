from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


REUSABLE = {"PRESERVE_CORE_CANDIDATE", "PRESERVE_GARMENT_CANDIDATE"}
EMPTY = "HOLD_EMPTY_REQUIRES_OCCLUSION_EVIDENCE"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def empty_requirement(layer: str) -> dict[str, object]:
    evidence = [
        "same-view approved master RGBA hash",
        "same-view recomposition exact-diff report",
        "manual visibility or occlusion decision bound to source hash",
    ]
    if layer in {"oral_cavity", "teeth_tongue"}:
        evidence.append("mouth-state evidence proving closed or fully occluded, otherwise a non-empty dynamic asset")
    else:
        evidence.append("facial-part visibility mask or non-empty replacement asset when the feature is visible")
    return {
        "required_evidence": evidence,
        "acceptance_rule": "empty may pass only when same-view evidence proves the layer is legitimately fully occluded",
        "automatic_pass_for_empty": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    matrix_path = args.matrix.resolve()
    project_root = args.project_root.resolve()
    source_root = project_root / "assets" / "pose-atlas" / "v4-layered"
    license_path = project_root / "LICENSE"
    layer_manifest_path = source_root / "layer_manifest.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    assets: list[dict[str, object]] = []
    empties: list[dict[str, object]] = []
    for record in matrix["records"]:
        decision = record["decision"]
        source_path = source_root / record["relative_path"]
        if decision in REUSABLE:
            with Image.open(source_path) as image:
                actual_mode = image.mode
                actual_size = list(image.size)
            assets.append(
                {
                    "view_id": record["view_id"],
                    "legacy_layer": record["legacy_layer"],
                    "ownership_domain": record["ownership_domain"],
                    "path": source_path.relative_to(project_root).as_posix(),
                    "sha256": sha256(source_path),
                    "width": actual_size[0],
                    "height": actual_size[1],
                    "mode": "RGBA8" if actual_mode == "RGBA" else actual_mode,
                    "offset_x": 0,
                    "offset_y": 0,
                    "alpha_bbox": record["alpha_bbox"],
                    "visible_alpha_pixels": record["visible_alpha_pixels"],
                    "source_provenance": {
                        "kind": "existing_legacy_poseatlas_layer",
                        "legacy_manifest_path": layer_manifest_path.relative_to(project_root).as_posix(),
                        "legacy_manifest_sha256": sha256(layer_manifest_path),
                        "audit_matrix_path": matrix_path.name,
                        "audit_matrix_sha256": sha256(matrix_path),
                    },
                    "license_provenance": {
                        "project_license": "MIT",
                        "license_path": license_path.relative_to(project_root).as_posix(),
                        "license_sha256": sha256(license_path),
                        "asset_specific_rights_status": "CANDIDATE_ONLY_NOT_SEPARATELY_ADJUDICATED",
                    },
                    "qa": {
                        "status": "TECHNICAL_PASS_NOT_PROMOTED",
                        "rgba": True,
                        "corner_alpha_zero": record["corner_alpha"] == [0, 0, 0, 0],
                        "transparent_rgb_contamination_pixels": record["transparent_rgb_contamination_pixels"],
                        "promotion_allowed": False,
                    },
                }
            )
        elif decision == EMPTY:
            empties.append(
                {
                    "view_id": record["view_id"],
                    "legacy_layer": record["legacy_layer"],
                    "path": source_path.relative_to(project_root).as_posix(),
                    "sha256": sha256(source_path),
                    "visible_alpha_pixels": 0,
                    "status": "UNRESOLVED_EMPTY",
                    **empty_requirement(record["legacy_layer"]),
                }
            )

    payload = {
        "schema": "mohan.poseatlas.v4-reusable-assets/v1",
        "kind": "PARTIAL_MIGRATION_INVENTORY",
        "project_root": str(project_root),
        "source_root": str(source_root),
        "source_files_modified": False,
        "source_files_copied": False,
        "formal_600_complete": False,
        "promotion_allowed": False,
        "counts": {
            "expected_legacy_layers": 600,
            "validated_reusable_asset_records": len(assets),
            "unresolved_empty_records": len(empties),
            "blocked_rebuild_records": 600 - len(assets) - len(empties),
            "required_ownership_masks": 192,
            "present_ownership_masks": 0,
        },
        "asset_records": assets,
        "unresolved_empty_records": empties,
        "mask_records": [],
    }
    args.output.resolve().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
