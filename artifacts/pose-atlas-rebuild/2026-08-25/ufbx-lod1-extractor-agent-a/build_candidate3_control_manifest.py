from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from pathlib import Path

import numpy as np
from PIL import Image


YAWS = tuple(range(-180, 180, 15))
VIEW_IDS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in YAWS)
KINDS = ("silhouette", "depth", "normal")
EXPECTED_MODES = {"silhouette": "L", "depth": "L", "normal": "RGB"}
WIDTH, HEIGHT, MARGIN = 1024, 1536, 24.0
BODY_CENTER_CONSTANT = [512, 1292]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relative(path: Path, root: Path) -> str:
    return os.path.relpath(path.resolve(), root.resolve()).replace("\\", "/")


def load_vertices(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:8] != b"MHRVTX2\0":
        raise ValueError("Expected candidate3 MHRVTX2 binary")
    count, components = struct.unpack("<II", data[8:16])
    if count != 18_439 or components != 3 or len(data) != 16 + count * components * 8:
        raise ValueError("Invalid candidate3 binary contract")
    result = np.frombuffer(data, dtype="<f8", offset=16).reshape(count, components)
    if not np.isfinite(result).all():
        raise ValueError("Non-finite candidate3 vertices")
    return result


def matrix_rows(matrix: np.ndarray) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-dir", type=Path, required=True)
    parser.add_argument("--candidate3-bin", type=Path, required=True)
    parser.add_argument("--candidate3-obj", type=Path, required=True)
    parser.add_argument("--candidate3-report", type=Path, required=True)
    parser.add_argument("--candidate3-audit", type=Path, required=True)
    parser.add_argument("--candidate2-rejection", type=Path, required=True)
    parser.add_argument("--topology-qa", type=Path, required=True)
    parser.add_argument("--legacy-iou-qa", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_root = args.output.parent
    vertices = load_vertices(args.candidate3_bin)
    candidate3_report = json.loads(args.candidate3_report.read_text(encoding="utf-8"))
    candidate3_audit = json.loads(args.candidate3_audit.read_text(encoding="utf-8"))
    candidate2_rejection = json.loads(args.candidate2_rejection.read_text(encoding="utf-8"))
    topology_qa = json.loads(args.topology_qa.read_text(encoding="utf-8"))
    legacy_qa = json.loads(args.legacy_iou_qa.read_text(encoding="utf-8"))
    if candidate3_audit["status"] != "PASS_BONE_BOUNDED_PLAUSIBILITY_NOT_SURFACE_LANDMARK_VALIDATION":
        raise ValueError("Candidate3 audit is not the accepted bounded-plausibility result")
    if candidate2_rejection["status"] != "FAIL":
        raise ValueError("Candidate2 rejection reference is not a FAIL report")
    if topology_qa["status"] != "PASS_INDEPENDENT_TOPOLOGY_CORRESPONDENCE_GATE":
        raise ValueError("Candidate3 topology continuity gate did not pass")
    if legacy_qa["status"] != "FAIL":
        raise ValueError("Legacy IoU failure must remain retained")

    y_min, y_max = float(vertices[:, 1].min()), float(vertices[:, 1].max())
    y_center = (y_min + y_max) / 2
    radial_max = float(np.hypot(vertices[:, 0], vertices[:, 2]).max())
    scale = min((WIDTH - 2 * MARGIN) / (2 * radial_max), (HEIGHT - 2 * MARGIN) / (y_max - y_min))
    projection = np.asarray([
        [2 * scale / WIDTH, 0.0, 0.0, 0.0],
        [0.0, 2 * scale / HEIGHT, 0.0, 0.0],
        [0.0, 0.0, 1.0 / radial_max, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])

    views = []
    for yaw, view_id in zip(YAWS, VIEW_IDS, strict=True):
        radians = math.radians(yaw)
        cosine, sine = math.cos(radians), math.sin(radians)
        view = np.asarray([
            [cosine, 0.0, sine, 0.0],
            [0.0, 1.0, 0.0, -y_center],
            [-sine, 0.0, cosine, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        combined = projection @ view
        controls = {}
        silhouette_mask = None
        for kind in KINDS:
            path = args.controls_dir / f"{view_id}_{kind}.png"
            with Image.open(path) as image:
                if image.size != (WIDTH, HEIGHT) or image.mode != EXPECTED_MODES[kind]:
                    raise ValueError(f"Invalid control file {path}: {image.size} {image.mode}")
                array = np.asarray(image)
            controls[kind] = {
                "path": relative(path, manifest_root),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "width": WIDTH,
                "height": HEIGHT,
                "mode": EXPECTED_MODES[kind],
            }
            if kind == "silhouette":
                silhouette_mask = array > 0
        if silhouette_mask is None:
            raise AssertionError("Missing silhouette")
        ys, xs = np.where(silhouette_mask)
        views.append({
            "view_id": view_id,
            "yaw_degrees": yaw,
            "pitch_degrees": 0,
            "view_matrix_row_major": matrix_rows(view),
            "orthographic_projection_matrix_row_major": matrix_rows(projection),
            "world_to_ndc_matrix_row_major": matrix_rows(combined),
            "pixel_mapping": {
                "x": "pixel_x=(ndc_x+1)*width/2",
                "y": "pixel_y=(1-ndc_y)*height/2",
                "depth": "camera_z=view_z; visible byte=round(1+254*((camera_z+radial_max)/(2*radial_max))); background=0"
            },
            "silhouette_bbox_xyxy_inclusive": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "silhouette_centroid_xy": [float(xs.mean()), float(ys.mean())],
            "controls": controls,
        })

    candidate2_failed_transitions = sum("continuity" in error for error in legacy_qa.get("errors", []))
    manifest = {
        "schema": "flameblade.mohan.geometry-camera-anchor-controls",
        "version": 1,
        "schema_file": {"path": relative(args.schema, manifest_root), "sha256": sha256(args.schema)},
        "status": "candidate3_only_geometry_control_authority",
        "notice": "GEOMETRY CONTROL ONLY - NOT FINAL ART",
        "formal_art_acceptance": False,
        "authority": {
            "id": "mhr-candidate3",
            "mesh_vertices": 18_439,
            "mesh_triangles": 36_874,
            "candidate3_vertices": {"path": relative(args.candidate3_bin, manifest_root), "sha256": sha256(args.candidate3_bin), "format": "MHRVTX2 little-endian float64 XYZ in exact ufbx order"},
            "candidate3_obj": {"path": relative(args.candidate3_obj, manifest_root), "sha256": sha256(args.candidate3_obj)},
            "candidate3_report": {"path": relative(args.candidate3_report, manifest_root), "sha256": sha256(args.candidate3_report)},
            "candidate3_anatomy_audit": {"path": relative(args.candidate3_audit, manifest_root), "sha256": sha256(args.candidate3_audit), "status": candidate3_audit["status"]},
            "clothing_baked_into_body_mesh": False,
            "clothing_statement": "Candidate3 is the MHR body topology plus deterministic local torso X/Z morph only; no outfit or clothing geometry was introduced.",
            "unique_geometry_control_parent": True,
        },
        "canvas": {"width": WIDTH, "height": HEIGHT, "coordinate_origin": "top-left", "pixel_center": "integer+0.5"},
        "camera_contract": {
            "type": "orthographic",
            "world_axes": "X-right, Y-up, Z-depth",
            "yaw_axis": "Y",
            "pitch_degrees": 0,
            "margin_pixels": MARGIN,
            "orthographic_scale_pixels_per_world_unit": scale,
            "radial_max_world": radial_max,
            "y_min_world": y_min,
            "y_max_world": y_max,
            "y_center_world": y_center,
            "rotation_formula": "x'=cos(yaw)*x+sin(yaw)*z; y'=y; z'=-sin(yaw)*x+cos(yaw)*z",
            "orthographic_bounds_world": {
                "left": -WIDTH / (2 * scale),
                "right": WIDTH / (2 * scale),
                "bottom": -HEIGHT / (2 * scale),
                "top": HEIGHT / (2 * scale),
                "near": -radial_max,
                "far": radial_max
            },
            "fixed_rotation_pivot_world": [0.0, y_center, 0.0],
            "control_raster_projection_center_px": [WIDTH / 2, HEIGHT / 2]
        },
        "anchor_contract": {
            "BODY_CENTER_CONSTANT": BODY_CENTER_CONSTANT,
            "meaning": "downstream 1024x1536 final-art registration metadata",
            "applied_to_geometry_control_rasters": False,
            "geometry_control_offsets": {"offset_x": 0, "offset_y": 0},
            "runtime_translation_policy": "do not translate registered full-canvas final-art layers again; geometry controls remain camera-space references",
            "warning": "BODY_CENTER_CONSTANT is metadata here and must not be confused with the control raster projection center [512,768]."
        },
        "transition_contract": {
            "yaw_step_degrees": 15,
            "order": "ascending yaw from -180 through +165",
            "wrap": {"from": "yaw+165-pitch+00", "to": "yaw-180-pitch+00", "equivalent_step_degrees": 15},
            "interpolation_tick_hz": 50,
            "topology_correspondence": "same vertex index and triangle topology across every view",
            "raster_iou_gate": "retained failure; not replaced by topology gate"
        },
        "view_ids": list(VIEW_IDS),
        "control_kinds": list(KINDS),
        "encodings": {
            "silhouette": "L 8-bit; 0 background, 255 foreground",
            "depth": "L 8-bit quantized; 0 background, visible normalized to 1..255 using fixed radial range",
            "normal": "RGB 8-bit camera-facing geometric face normal encoded n*0.5+0.5"
        },
        "views": views,
        "rejected_predecessor": {
            "id": "mhr-candidate2",
            "status": "rejected",
            "must_not_be_used_as_geometry_control_parent": True,
            "report": {"path": relative(args.candidate2_rejection, manifest_root), "sha256": sha256(args.candidate2_rejection)},
            "reason": "front/back depth ratio drift relative to the official skeleton axis",
            "legacy_iou_failed_transition_count": candidate2_failed_transitions
        },
        "qa_references": {
            "candidate3_topology_continuity": {"path": relative(args.topology_qa, manifest_root), "sha256": sha256(args.topology_qa), "status": topology_qa["status"]},
            "legacy_raster_iou": {"path": relative(args.legacy_iou_qa, manifest_root), "sha256": sha256(args.legacy_iou_qa), "status": legacy_qa["status"], "retained": True},
            "limitations": [
                "Geometry controls are not final MoHan art.",
                "Legacy silhouette IoU remains failed near side-view T-pose self-occlusion.",
                "BODY_CENTER_CONSTANT has not been applied as a raster translation."
            ]
        }
    }
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "output": str(args.output.resolve()),
        "views": len(views),
        "controls": len(views) * len(KINDS),
        "candidate3_sha256": manifest["authority"]["candidate3_vertices"]["sha256"],
        "candidate2_status": manifest["rejected_predecessor"]["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
