from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image


YAWS = np.arange(-180, 180, 15, dtype=np.int32)
VIEW_IDS = tuple(f"yaw{int(yaw):+04d}-pitch+00" for yaw in YAWS)
WIDTH, HEIGHT, MARGIN = 1024, 1536, 24.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_vertices(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:8] != b"MHRVTX2\0":
        raise ValueError("Expected MHRVTX2 candidate3 vertices")
    count, components = struct.unpack("<II", data[8:16])
    if count != 18_439 or components != 3 or len(data) != 16 + count * components * 8:
        raise ValueError("Invalid candidate3 vertex binary contract")
    result = np.frombuffer(data, dtype="<f8", offset=16).reshape(count, components).copy()
    if not np.isfinite(result).all():
        raise ValueError("Non-finite candidate vertices")
    return result


def silhouette_metrics(path: Path) -> dict:
    with Image.open(path) as image:
        if image.size != (WIDTH, HEIGHT) or image.mode != "L":
            raise ValueError(f"Unexpected silhouette format: {path} {image.size} {image.mode}")
        mask = np.asarray(image) > 0
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError(f"Empty silhouette: {path}")
    return {
        "bbox": np.asarray([xs.min(), ys.min(), xs.max(), ys.max()], dtype=np.float64),
        "centroid": np.asarray([xs.mean(), ys.mean()], dtype=np.float64),
        "foreground_pixels": int(mask.sum()),
        "sha256": sha256(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--legacy-qa", type=Path, required=True)
    parser.add_argument("--projections", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    vertices = load_vertices(args.vertices)
    y_min, y_max = float(vertices[:, 1].min()), float(vertices[:, 1].max())
    radial = np.hypot(vertices[:, 0], vertices[:, 2])
    radial_max = float(radial.max())
    scale = min((WIDTH - 2 * MARGIN) / (2 * radial_max), (HEIGHT - 2 * MARGIN) / (y_max - y_min))
    y_center = (y_min + y_max) / 2

    world_xz = np.empty((24, len(vertices), 2), dtype=np.float64)
    screen_xy = np.empty((24, len(vertices), 2), dtype=np.float64)
    camera_depth = np.empty((24, len(vertices)), dtype=np.float64)
    topology_bbox = np.empty((24, 4), dtype=np.float64)
    topology_centroid = np.empty((24, 2), dtype=np.float64)
    silhouette_bbox = np.empty((24, 4), dtype=np.float64)
    silhouette_centroid = np.empty((24, 2), dtype=np.float64)
    silhouette_records = []

    for index, yaw in enumerate(YAWS):
        radians = math.radians(float(yaw))
        cosine, sine = math.cos(radians), math.sin(radians)
        rotated_x = cosine * vertices[:, 0] + sine * vertices[:, 2]
        rotated_z = -sine * vertices[:, 0] + cosine * vertices[:, 2]
        world_xz[index, :, 0] = rotated_x
        world_xz[index, :, 1] = rotated_z
        screen_xy[index, :, 0] = WIDTH / 2 + rotated_x * scale
        screen_xy[index, :, 1] = HEIGHT / 2 - (vertices[:, 1] - y_center) * scale
        camera_depth[index] = rotated_z
        topology_bbox[index] = [
            screen_xy[index, :, 0].min(),
            screen_xy[index, :, 1].min(),
            screen_xy[index, :, 0].max(),
            screen_xy[index, :, 1].max(),
        ]
        topology_centroid[index] = screen_xy[index].mean(axis=0)
        path = args.controls / f"{VIEW_IDS[index]}_silhouette.png"
        metrics = silhouette_metrics(path)
        silhouette_bbox[index] = metrics["bbox"]
        silhouette_centroid[index] = metrics["centroid"]
        silhouette_records.append({
            "view_id": VIEW_IDS[index],
            "path": str(path.resolve()),
            "sha256": metrics["sha256"],
            "bbox": metrics["bbox"].tolist(),
            "centroid": metrics["centroid"].tolist(),
            "foreground_pixels": metrics["foreground_pixels"],
        })

    np.savez_compressed(
        args.projections,
        yaw_degrees=YAWS,
        vertex_indices=np.arange(len(vertices), dtype=np.uint32),
        world_xz=world_xz,
        screen_xy=screen_xy,
        camera_depth=camera_depth,
        topology_bbox_xyxy=topology_bbox,
        topology_centroid_xy=topology_centroid,
    )

    delta = math.radians(15.0)
    cosine, sine = math.cos(delta), math.sin(delta)
    row_step = np.asarray([[cosine, -sine], [sine, cosine]], dtype=np.float64)
    global_screen_bound = 2 * radial_max * math.sin(delta / 2) * scale
    global_depth_bound = 2 * radial_max * math.sin(delta / 2)
    transitions = []
    errors = []
    for index, view_id in enumerate(VIEW_IDS):
        following = (index + 1) % 24
        predicted = world_xz[index] @ row_step
        recurrence_error = np.linalg.norm(predicted - world_xz[following], axis=1)
        fitted, _, _, _ = np.linalg.lstsq(world_xz[index], world_xz[following], rcond=None)
        determinant = float(np.linalg.det(fitted))
        inferred_step = math.degrees(math.atan2(float(fitted[1, 0]), float(fitted[0, 0])))
        screen_displacement = np.linalg.norm(screen_xy[following] - screen_xy[index], axis=1)
        depth_change = np.abs(camera_depth[following] - camera_depth[index])
        bbox_delta = topology_bbox[following] - topology_bbox[index]
        centroid_delta = topology_centroid[following] - topology_centroid[index]
        silhouette_bbox_delta = silhouette_bbox[following] - silhouette_bbox[index]
        silhouette_centroid_delta = silhouette_centroid[following] - silhouette_centroid[index]
        raster_bbox_error = np.abs(silhouette_bbox[index] - topology_bbox[index])
        gates = {
            "analytic_recurrence_max_le_1e_10": float(recurrence_error.max()) <= 1e-10,
            "rotation_determinant_positive_unit": determinant > 0.0 and abs(determinant - 1.0) <= 1e-12,
            "inferred_step_is_positive_15": abs(inferred_step - 15.0) <= 1e-10,
            "screen_displacement_within_analytic_bound": float(screen_displacement.max()) <= global_screen_bound + 1e-9,
            "depth_change_within_analytic_bound": float(depth_change.max()) <= global_depth_bound + 1e-12,
            "topology_bbox_first_difference_bounded": float(np.abs(bbox_delta).max()) <= global_screen_bound + 1e-9,
            "topology_centroid_first_difference_bounded": float(np.linalg.norm(centroid_delta)) <= global_screen_bound + 1e-9,
            "vertical_projection_invariant": float(np.abs(screen_xy[following, :, 1] - screen_xy[index, :, 1]).max()) == 0.0,
        }
        if not all(gates.values()):
            errors.append({"transition": [view_id, VIEW_IDS[following]], "gates": gates})
        transitions.append({
            "from": view_id,
            "to": VIEW_IDS[following],
            "wrap": index == 23,
            "yaw_step_degrees": 15,
            "inferred_step_degrees": inferred_step,
            "rotation_determinant": determinant,
            "analytic_recurrence_world_max": float(recurrence_error.max()),
            "analytic_recurrence_world_rms": float(np.sqrt(np.mean(recurrence_error ** 2))),
            "screen_displacement_px": {
                "mean": float(screen_displacement.mean()),
                "p95": float(np.quantile(screen_displacement, 0.95)),
                "max": float(screen_displacement.max()),
                "analytic_global_bound": global_screen_bound,
            },
            "absolute_depth_change_world": {
                "mean": float(depth_change.mean()),
                "p95": float(np.quantile(depth_change, 0.95)),
                "max": float(depth_change.max()),
                "analytic_global_bound": global_depth_bound,
            },
            "topology_bbox_xyxy": topology_bbox[index].tolist(),
            "topology_bbox_first_difference": bbox_delta.tolist(),
            "topology_centroid_xy": topology_centroid[index].tolist(),
            "topology_centroid_first_difference": centroid_delta.tolist(),
            "silhouette_bbox_xyxy": silhouette_bbox[index].tolist(),
            "silhouette_bbox_first_difference": silhouette_bbox_delta.tolist(),
            "silhouette_centroid_xy": silhouette_centroid[index].tolist(),
            "silhouette_centroid_first_difference": silhouette_centroid_delta.tolist(),
            "raster_vs_topology_bbox_abs_error": raster_bbox_error.tolist(),
            "gates": gates,
        })

    # Circular second differences establish sinusoidal continuity independently
    # of visibility/self-occlusion changes in the rasterized silhouette.
    screen_second = np.roll(screen_xy, -1, axis=0) - 2 * screen_xy + np.roll(screen_xy, 1, axis=0)
    depth_second = np.roll(camera_depth, -1, axis=0) - 2 * camera_depth + np.roll(camera_depth, 1, axis=0)
    analytic_screen_second_bound = 4 * radial_max * math.sin(delta / 2) ** 2 * scale
    analytic_depth_second_bound = 4 * radial_max * math.sin(delta / 2) ** 2
    circular_gates = {
        "screen_second_difference_bounded": float(np.linalg.norm(screen_second, axis=2).max()) <= analytic_screen_second_bound + 1e-9,
        "depth_second_difference_bounded": float(np.abs(depth_second).max()) <= analytic_depth_second_bound + 1e-12,
        "view_ids_exact_order": list(VIEW_IDS) == [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)],
        "wrap_is_plus_165_to_minus_180_equivalent_plus_15": transitions[-1]["from"] == "yaw+165-pitch+00" and transitions[-1]["to"] == "yaw-180-pitch+00" and transitions[-1]["gates"]["inferred_step_is_positive_15"],
        "no_mirror_transition": all(item["rotation_determinant"] > 0.0 for item in transitions),
    }
    if not all(circular_gates.values()):
        errors.append({"circular_gates": circular_gates})

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    legacy = json.loads(args.legacy_qa.read_text(encoding="utf-8"))
    legacy_failed = [error for error in legacy.get("errors", []) if "continuity" in error]
    source_hash = manifest["source"]["vertices"]["sha256"].upper()
    expected_hash = sha256(args.vertices)
    source_gate = source_hash == expected_hash
    if not source_gate:
        errors.append({"source_hash_mismatch": [source_hash, expected_hash]})

    report = {
        "status": "PASS_INDEPENDENT_TOPOLOGY_CORRESPONDENCE_GATE" if not errors else "FAIL",
        "scope": "same-topology 3D rotation continuity; does not replace legacy silhouette IoU gate or final-art continuity",
        "candidate3": {
            "vertices": str(args.vertices.resolve()),
            "sha256": expected_hash,
            "vertex_count": len(vertices),
            "manifest_source_matches": source_gate,
        },
        "camera": {
            "width": WIDTH,
            "height": HEIGHT,
            "margin": MARGIN,
            "orthographic_scale": scale,
            "y_center": y_center,
            "radial_max": radial_max,
            "rotation_formula": "x'=cos(yaw)*x+sin(yaw)*z; z'=-sin(yaw)*x+cos(yaw)*z",
        },
        "projection_artifact": {
            "path": str(args.projections.resolve()),
            "sha256": sha256(args.projections),
            "format": "NPZ: yaw_degrees[24], vertex_indices[18439], world_xz[24,18439,2], screen_xy[24,18439,2], camera_depth[24,18439]",
        },
        "analytic_bounds": {
            "per_step_screen_displacement_px": global_screen_bound,
            "per_step_depth_change_world": global_depth_bound,
            "circular_screen_second_difference_px": analytic_screen_second_bound,
            "circular_depth_second_difference_world": analytic_depth_second_bound,
        },
        "circular_gates": circular_gates,
        "transitions": transitions,
        "wrap_transition": transitions[-1],
        "observed": {
            "analytic_recurrence_world_max": max(item["analytic_recurrence_world_max"] for item in transitions),
            "rotation_determinant_range": [min(item["rotation_determinant"] for item in transitions), max(item["rotation_determinant"] for item in transitions)],
            "inferred_step_range_degrees": [min(item["inferred_step_degrees"] for item in transitions), max(item["inferred_step_degrees"] for item in transitions)],
            "screen_displacement_max_range_px": [min(item["screen_displacement_px"]["max"] for item in transitions), max(item["screen_displacement_px"]["max"] for item in transitions)],
            "depth_change_max_range_world": [min(item["absolute_depth_change_world"]["max"] for item in transitions), max(item["absolute_depth_change_world"]["max"] for item in transitions)],
            "topology_bbox_first_difference_abs_max_px": max(max(abs(value) for value in item["topology_bbox_first_difference"]) for item in transitions),
            "topology_centroid_first_difference_norm_max_px": max(float(np.linalg.norm(item["topology_centroid_first_difference"])) for item in transitions),
            "screen_second_difference_max_px": float(np.linalg.norm(screen_second, axis=2).max()),
            "depth_second_difference_max_world": float(np.abs(depth_second).max()),
        },
        "legacy_iou_gate": {
            "retained": True,
            "status": legacy.get("status"),
            "report": str(args.legacy_qa.resolve()),
            "sha256": sha256(args.legacy_qa),
            "failed_transition_count": len(legacy_failed),
            "iou_range": legacy.get("observed", {}).get("iou_range"),
            "centroid_shift_px_range": legacy.get("observed", {}).get("centroid_shift_px_range"),
            "explanation": "T-pose arm and hand visibility changes rapidly near side views; raster silhouette overlap remains failed/informational and is not overwritten by the topology gate.",
        },
        "silhouettes": silhouette_records,
        "errors": errors,
    }
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "projection_sha256": report["projection_artifact"]["sha256"],
        "observed": report["observed"],
        "wrap": {
            "from": transitions[-1]["from"],
            "to": transitions[-1]["to"],
            "inferred_step": transitions[-1]["inferred_step_degrees"],
            "determinant": transitions[-1]["rotation_determinant"],
            "recurrence_max": transitions[-1]["analytic_recurrence_world_max"],
            "gates": transitions[-1]["gates"],
        },
        "legacy_iou_gate": report["legacy_iou_gate"],
    }, indent=2))
    if report["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
