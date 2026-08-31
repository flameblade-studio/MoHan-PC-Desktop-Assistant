from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image


YAWS = tuple(range(-180, 180, 15))
VIEW_IDS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in YAWS)
KINDS = ("silhouette", "depth", "normal")
MODES = {"silhouette": "L", "depth": "L", "normal": "RGB"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def resolve(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_file():
        raise ValueError(f"Missing manifest reference: {relative}")
    return candidate


def require(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(message)
    checks.append(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.manifest.parent
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    checks: list[str] = []
    require(manifest["schema"] == "flameblade.mohan.geometry-camera-anchor-controls" and manifest["version"] == 1, "schema/version exact", checks)
    require(manifest["status"] == "candidate3_only_geometry_control_authority", "candidate3 is sole geometry control authority", checks)
    require(manifest["notice"] == "GEOMETRY CONTROL ONLY - NOT FINAL ART" and manifest["formal_art_acceptance"] is False, "not final art", checks)
    schema_path = resolve(root, manifest["schema_file"]["path"])
    require(sha256(schema_path) == manifest["schema_file"]["sha256"], "schema hash exact", checks)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    require(schema["properties"]["schema"]["const"] == manifest["schema"], "schema const agrees", checks)
    require(manifest["canvas"] ["width"] == 1024 and manifest["canvas"]["height"] == 1536, "canvas 1024x1536", checks)
    require(manifest["view_ids"] == list(VIEW_IDS), "24 view IDs in exact ascending yaw order", checks)
    require(manifest["control_kinds"] == list(KINDS), "control kinds exact", checks)
    require(manifest["anchor_contract"]["BODY_CENTER_CONSTANT"] == [512, 1292], "BODY_CENTER_CONSTANT metadata exact", checks)
    require(manifest["anchor_contract"]["applied_to_geometry_control_rasters"] is False, "BODY_CENTER metadata not misapplied to control raster", checks)
    require(manifest["anchor_contract"]["geometry_control_offsets"] == {"offset_x": 0, "offset_y": 0}, "control offsets are zero", checks)
    require(manifest["authority"]["unique_geometry_control_parent"] is True, "unique control parent flag true", checks)
    require(manifest["authority"]["clothing_baked_into_body_mesh"] is False, "no clothing baked into body mesh", checks)
    require(manifest["authority"]["mesh_vertices"] == 18_439 and manifest["authority"]["mesh_triangles"] == 36_874, "topology count exact", checks)

    for key in ("candidate3_vertices", "candidate3_obj", "candidate3_report", "candidate3_anatomy_audit"):
        entry = manifest["authority"][key]
        path = resolve(root, entry["path"])
        require(sha256(path) == entry["sha256"], f"authority hash exact: {key}", checks)
    rejection = manifest["rejected_predecessor"]
    require(rejection["id"] == "mhr-candidate2" and rejection["status"] == "rejected" and rejection["must_not_be_used_as_geometry_control_parent"] is True, "candidate2 explicitly rejected", checks)
    rejection_path = resolve(root, rejection["report"]["path"])
    require(sha256(rejection_path) == rejection["report"]["sha256"], "candidate2 rejection hash exact", checks)
    rejection_report = json.loads(rejection_path.read_text(encoding="utf-8"))
    require(rejection_report["status"] == "FAIL", "candidate2 referenced report is fail", checks)

    camera = manifest["camera_contract"]
    scale = float(camera["orthographic_scale_pixels_per_world_unit"])
    radial_max = float(camera["radial_max_world"])
    y_center = float(camera["y_center_world"])
    expected_projection = np.asarray([
        [2 * scale / 1024, 0.0, 0.0, 0.0],
        [0.0, 2 * scale / 1536, 0.0, 0.0],
        [0.0, 0.0, 1.0 / radial_max, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    require(len(manifest["views"]) == 24, "24 view records", checks)
    referenced_controls = set()
    for index, (yaw, view_id, entry) in enumerate(zip(YAWS, VIEW_IDS, manifest["views"], strict=True)):
        require(entry["view_id"] == view_id and entry["yaw_degrees"] == yaw and entry["pitch_degrees"] == 0, f"view identity exact: {view_id}", checks)
        radians = math.radians(yaw)
        cosine, sine = math.cos(radians), math.sin(radians)
        expected_view = np.asarray([
            [cosine, 0.0, sine, 0.0],
            [0.0, 1.0, 0.0, -y_center],
            [-sine, 0.0, cosine, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        actual_view = np.asarray(entry["view_matrix_row_major"], dtype=np.float64)
        actual_projection = np.asarray(entry["orthographic_projection_matrix_row_major"], dtype=np.float64)
        actual_combined = np.asarray(entry["world_to_ndc_matrix_row_major"], dtype=np.float64)
        require(np.allclose(actual_view, expected_view, atol=1e-15, rtol=0.0), f"view matrix exact: {view_id}", checks)
        require(np.allclose(actual_projection, expected_projection, atol=1e-15, rtol=0.0), f"projection matrix exact: {view_id}", checks)
        require(np.allclose(actual_combined, expected_projection @ expected_view, atol=1e-15, rtol=0.0), f"combined matrix exact: {view_id}", checks)
        require(np.linalg.det(actual_view[:3, :3]) > 0.999999999999 and np.linalg.det(actual_view[:3, :3]) < 1.000000000001, f"no mirror matrix: {view_id}", checks)
        for kind in KINDS:
            control = entry["controls"][kind]
            path = resolve(root, control["path"])
            require("candidate2" not in control["path"].lower(), f"view control excludes candidate2: {view_id}/{kind}", checks)
            require(control["path"] not in referenced_controls, f"unique view control path: {view_id}/{kind}", checks)
            referenced_controls.add(control["path"])
            require(sha256(path) == control["sha256"], f"control hash exact: {view_id}/{kind}", checks)
            with Image.open(path) as image:
                require(image.size == (1024, 1536) and image.mode == MODES[kind], f"control format exact: {view_id}/{kind}", checks)
                if kind == "silhouette":
                    mask = np.asarray(image) > 0
                    ys, xs = np.where(mask)
                    require(entry["silhouette_bbox_xyxy_inclusive"] == [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], f"silhouette bbox exact: {view_id}", checks)
                    centroid = [float(xs.mean()), float(ys.mean())]
                    require(np.allclose(entry["silhouette_centroid_xy"], centroid, atol=1e-12, rtol=0.0), f"silhouette centroid exact: {view_id}", checks)
    require(len(referenced_controls) == 72, "exact 72 unique control references", checks)
    require(manifest["transition_contract"]["yaw_step_degrees"] == 15 and manifest["transition_contract"]["wrap"] == {"from": "yaw+165-pitch+00", "to": "yaw-180-pitch+00", "equivalent_step_degrees": 15}, "15 degree order and wrap exact", checks)

    topology_ref = manifest["qa_references"]["candidate3_topology_continuity"]
    topology_path = resolve(root, topology_ref["path"])
    require(sha256(topology_path) == topology_ref["sha256"], "topology QA hash exact", checks)
    require(json.loads(topology_path.read_text(encoding="utf-8"))["status"] == "PASS_INDEPENDENT_TOPOLOGY_CORRESPONDENCE_GATE", "topology QA pass retained", checks)
    legacy_ref = manifest["qa_references"]["legacy_raster_iou"]
    legacy_path = resolve(root, legacy_ref["path"])
    require(sha256(legacy_path) == legacy_ref["sha256"], "legacy IoU QA hash exact", checks)
    require(json.loads(legacy_path.read_text(encoding="utf-8"))["status"] == "FAIL" and legacy_ref["retained"] is True, "legacy IoU fail retained", checks)

    result = {
        "status": "PASS",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256(args.manifest),
        "schema": str(schema_path),
        "schema_sha256": sha256(schema_path),
        "check_count": len(checks),
        "views": 24,
        "controls": 72,
        "candidate3_only": True,
        "candidate2_rejected": True,
        "clothing_baked_into_body_mesh": False,
        "BODY_CENTER_CONSTANT": [512, 1292],
        "checks": checks,
    }
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "manifest_sha256", "schema_sha256", "check_count", "views", "controls", "candidate3_only", "candidate2_rejected")}, indent=2))


if __name__ == "__main__":
    main()
