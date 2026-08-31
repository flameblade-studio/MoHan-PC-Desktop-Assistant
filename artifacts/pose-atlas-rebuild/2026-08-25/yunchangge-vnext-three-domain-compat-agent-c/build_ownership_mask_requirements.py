from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


VIEWS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)
FIELDS = (
    "core_mask", "hand_left_mask", "hand_right_mask", "foot_left_mask", "foot_right_mask",
    "garment_mask", "ornament_fixed_mask", "ornament_swappable_mask",
)
DOMAIN = {
    "core_mask": "core_anatomy", "hand_left_mask": "core_anatomy",
    "hand_right_mask": "core_anatomy", "foot_left_mask": "core_anatomy",
    "foot_right_mask": "core_anatomy", "garment_mask": "garment",
    "ornament_fixed_mask": "ornament_fixed", "ornament_swappable_mask": "ornament_swappable",
}
REQUIREMENT = {
    "core_mask": "skin/anatomy only; exclude every garment, shoe, hair and ornament pixel",
    "hand_left_mask": "physical left hand only; exclude sleeve fabric and jewelry",
    "hand_right_mask": "physical right hand only; exclude sleeve fabric and jewelry",
    "foot_left_mask": "physical left anatomical foot only; exclude shoe and skirt pixels",
    "foot_right_mask": "physical right anatomical foot only; exclude shoe and skirt pixels",
    "garment_mask": "all replaceable innerwear, outerwear, skirt, sleeves and shoes; exclude anatomy",
    "ornament_fixed_mask": "only the identity-fixed physical-side hairpin/crown components",
    "ornament_swappable_mask": "only replaceable headwear and jewelry; exclude fixed hairpin and skin",
}
YAW000_CONTROL = {
    "core_mask": "yaw+000-pitch+00_core_body_geometry-control-mask.png",
    "hand_left_mask": "yaw+000-pitch+00_hand_left_geometry-control-mask.png",
    "hand_right_mask": "yaw+000-pitch+00_hand_right_geometry-control-mask.png",
    "foot_left_mask": "yaw+000-pitch+00_foot_left_geometry-control-mask.png",
    "foot_right_mask": "yaw+000-pitch+00_foot_right_geometry-control-mask.png",
    "garment_mask": "yaw+000-pitch+00_garment_geometry-control-mask.png",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def evidence(path: Path, role: str) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": digest(path),
        "role": role,
        "sufficient_for_authority_mask": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--reusable-records", type=Path, required=True)
    parser.add_argument("--controls-manifest", type=Path, required=True)
    parser.add_argument("--yaw000-control-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = args.project_root.resolve()
    reusable = args.reusable_records.resolve()
    controls_manifest = args.controls_manifest.resolve()
    yaw000_root = args.yaw000_control_root.resolve()
    controls = json.loads(controls_manifest.read_text(encoding="utf-8"))
    by_view = {item["formal_view_id"]: item for item in controls["views"]}
    yaw000_report = yaw000_root / "yaw000-mhr-object-id-ownership-report.json"
    records: list[dict[str, object]] = []

    for view in VIEWS:
        silhouette = Path(by_view[view]["outputs"]["silhouette"]["absolute_path"])
        for field in FIELDS:
            current_path: Path | None = None
            status = "BLOCKED_NO_AUTHORITY_MASK"
            source_evidence = [
                evidence(reusable, "existing 336 reusable layer inventory; pixels are not ownership masks"),
                evidence(silhouette, "MHR whole-body silhouette control; not a domain separation mask"),
            ]
            if view == "yaw+000-pitch+00" and field in YAW000_CONTROL:
                current_path = yaw000_root / YAW000_CONTROL[field]
                source_evidence.append(evidence(yaw000_report, "MHR object-ID control report"))
                source_evidence.append(evidence(current_path, "MHR geometry control only; not registered to B00 art pixels"))
                status = "BLOCKED_EXISTING_CONTROL_NOT_REGISTERED_TO_ART"
                if field == "garment_mask":
                    status = "BLOCKED_ZERO_GARMENT_CONTROL_IS_NOT_ART_SEGMENTATION"
            qa = {
                "path_verified": current_path is not None and current_path.is_file(),
                "hash_verified": current_path is not None and current_path.is_file(),
                "canvas_verified": False,
                "manual_separation_qa": "NOT_RUN_NO_AUTHORITY_MASK",
                "promotion_allowed": False,
            }
            if current_path is not None:
                with Image.open(current_path) as image:
                    qa["canvas_verified"] = image.size == (1024, 1536)
                    qa["existing_mode"] = image.mode
            records.append(
                {
                    "view_id": view,
                    "domain": DOMAIN[field],
                    "mask_field": field,
                    "path_if_exists": str(current_path) if current_path else None,
                    "sha256_if_exists": digest(current_path) if current_path else None,
                    "source_evidence": source_evidence,
                    "required_separation": REQUIREMENT[field],
                    "qa": qa,
                    "authority_mask": False,
                    "status": status,
                }
            )

    payload = {
        "schema": "mohan.poseatlas.vnext.ownership-mask-requirements/v1",
        "views": list(VIEWS),
        "mask_fields": list(FIELDS),
        "records": records,
        "counts": {
            "required": len(VIEWS) * len(FIELDS),
            "records": len(records),
            "authority_masks": 0,
            "existing_control_only_paths": sum(item["path_if_exists"] is not None for item in records),
            "blocked": sum(str(item["status"]).startswith("BLOCKED") for item in records),
        },
        "formal_600_complete": False,
        "promotion_allowed": False,
    }
    args.output.resolve().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
