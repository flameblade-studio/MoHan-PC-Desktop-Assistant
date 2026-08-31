from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
OUT = Path(__file__).resolve().parent
QA = ROOT / r"artifacts\pose-atlas-rebuild\2026-08-26\mhr-candidate3-full-ring-qa-agent-b\full-ring-validation.json"
QA_CONTACT = ROOT / r"artifacts\pose-atlas-rebuild\2026-08-26\mhr-candidate3-full-ring-qa-agent-b\formal-24-yaw-control-contact.png"
FORMAL_YAWS = list(range(-180, 180, 15))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    if not QA.is_file() or not QA_CONTACT.is_file():
        return 4
    qa = json.loads(QA.read_text(encoding="utf-8"))
    if qa.get("status") != "PASS_GEOMETRY_CONTROL_FULL_RING_ONLY" or qa.get("failures"):
        return 4
    records = qa.get("records", [])
    adjacency = qa.get("adjacent_continuity", [])
    by_view: dict[str, dict[str, dict]] = {}
    for record in records:
        by_view.setdefault(record["formal_view_id"], {})[record["kind"]] = record
    adjacency_by_yaw = {item["from_formal_yaw"]: item for item in adjacency}
    views = []
    for yaw in FORMAL_YAWS:
        view_id = f"yaw{yaw:+04d}-pitch+00"
        kinds = by_view.get(view_id, {})
        controls = {}
        for kind in ("silhouette", "depth", "normal"):
            record = kinds.get(kind)
            if not record:
                return 4
            controls[kind] = {
                "path": record["path"],
                "sha256": record["sha256"],
                "width": record["size"][0],
                "height": record["size"][1],
                "mode": record["mode"],
                "format": "PPM" if kind == "normal" else "PGM",
                "bbox": record["bbox"],
                "bbox_touches_canvas": record["bbox_touches_canvas"]
            }
        edge = adjacency_by_yaw[yaw]
        views.append({
            "view_id": view_id,
            "formal_yaw_degrees": yaw,
            "pitch_degrees": 0,
            "source_renderer_yaw_degrees": -180 if yaw == -180 else -yaw,
            "renderer_mapping": "renderer_yaw=-formal_yaw; -180 endpoint canonicalized to renderer -180",
            "mirror": False,
            "canvas": [1024, 1536],
            "body_center_constant": [512, 1292],
            "body_center_semantic": "runtime_full_canvas_registration_anchor_not_mesh_bbox_center",
            "controls": controls,
            "part_id": {
                "hair": "BLOCKED_NO_AUTHORITATIVE_PART_ID",
                "clothing": "BLOCKED_NO_AUTHORITATIVE_PART_ID",
                "ornament": "BLOCKED_NO_AUTHORITATIVE_PART_ID"
            },
            "outgoing_continuity": {
                "to_formal_yaw": edge["to_formal_yaw"],
                "wrap": edge["wrap"],
                "silhouette_iou": edge["silhouette_iou"],
                "symmetric_contour_mean_displacement_px": edge["symmetric_contour_mean_displacement_px"],
                "symmetric_contour_p95_displacement_px": edge["symmetric_contour_p95_displacement_px"],
                "status": edge["status"],
                "source_qa_path": str(QA),
                "source_qa_sha256": sha256(QA)
            },
            "status": "PASS_GEOMETRY_CONTROL_ONLY_NOT_FORMAL_MOHAN"
        })
    manifest = {
        "schema": "mohan.candidate3_24yaw_control_manifest.v1",
        "status": "PASS_CONTROL_MANIFEST_ONLY_NOT_FORMAL_MOHAN",
        "formal_24_complete": False,
        "purpose": "Inputs for future licensed generation only; nude MHR candidate3 controls are not MoHan artwork.",
        "canvas": {"width": 1024, "height": 1536},
        "view_step_degrees": 15,
        "view_count": 24,
        "control_count": 72,
        "body_center_contract": {
            "value": [512, 1292],
            "semantic": "runtime_full_canvas_registration_anchor_not_mesh_bbox_center",
            "offset_policy": {"offset_x": 0, "offset_y": 0, "full_canvas_registered": True}
        },
        "part_id": {
            "hair": "BLOCKED_NO_AUTHORITATIVE_PART_ID",
            "clothing": "BLOCKED_NO_AUTHORITATIVE_PART_ID",
            "ornament": "BLOCKED_NO_AUTHORITATIVE_PART_ID",
            "reason": "MHR mesh/control renderer has no verified MoHan hair, garment or ornament topology/mapping."
        },
        "continuity_qa": {
            "path": str(QA),
            "sha256": sha256(QA),
            "contact_sheet": str(QA_CONTACT),
            "contact_sheet_sha256": sha256(QA_CONTACT),
            "status": qa["status"],
            "wrap_pair": qa["wrap_pair"]
        },
        "views": views
    }
    (OUT / "candidate3-24yaw-control-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
