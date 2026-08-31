from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
VIEW_IDS = [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)]
EXPECTED = {
    "normal": "RGB",
    "depth": "I;16",
    "silhouette": "L",
    "object_id": "I;16",
}
CANVAS = (1024, 1536)
MIN_ADJACENT_IOU = 0.85
MAX_CENTROID_SHIFT_PX = 16.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def internal_holes(mask: np.ndarray) -> tuple[int, int]:
    background = (~mask).astype(np.uint8)
    count, labels = cv2.connectedComponents(background, connectivity=8)
    border_labels = set(np.unique(labels[0, :]))
    border_labels.update(np.unique(labels[-1, :]))
    border_labels.update(np.unique(labels[:, 0]))
    border_labels.update(np.unique(labels[:, -1]))
    hole_labels = [label for label in range(1, count) if label not in border_labels]
    return len(hole_labels), int(sum(np.count_nonzero(labels == label) for label in hole_labels))


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    per_kind_counts = {kind: 0 for kind in EXPECTED}
    per_kind_hashes = {kind: set() for kind in EXPECTED}
    masks: list[np.ndarray] = []
    views: list[dict[str, object]] = []

    for view_id in VIEW_IDS:
        view_entry: dict[str, object] = {"view_id": view_id, "files": {}}
        for kind, expected_mode in EXPECTED.items():
            path = ROOT / view_id / f"{view_id}_{kind}.png"
            if not path.is_file():
                errors.append(f"missing:{path}")
                continue
            image = Image.open(path)
            per_kind_counts[kind] += 1
            digest = sha256(path)
            per_kind_hashes[kind].add(digest)
            if image.size != CANVAS:
                errors.append(f"size:{view_id}:{kind}:{image.size}")
            if image.mode != expected_mode:
                errors.append(f"mode:{view_id}:{kind}:{image.mode}")
            view_entry["files"][kind] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "mode": image.mode,
                "size": list(image.size),
                "bytes": path.stat().st_size,
                "sha256": digest,
            }

        silhouette_path = ROOT / view_id / f"{view_id}_silhouette.png"
        if silhouette_path.is_file():
            mask = np.asarray(Image.open(silhouette_path), dtype=np.uint8) > 0
            masks.append(mask)
            ys, xs = np.where(mask)
            if not len(xs):
                errors.append(f"empty_silhouette:{view_id}")
            else:
                hole_count, hole_pixels = internal_holes(mask)
                bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
                view_entry["silhouette_metrics"] = {
                    "bbox_xyxy_exclusive": bbox,
                    "foreground_pixels": int(mask.sum()),
                    "centroid_xy": [float(xs.mean()), float(ys.mean())],
                    "internal_hole_count": hole_count,
                    "internal_hole_pixels": hole_pixels,
                }
                if hole_count:
                    warnings.append(f"source_mesh_visible_holes:{view_id}:{hole_count}:{hole_pixels}px")
        views.append(view_entry)

    adjacency: list[dict[str, object]] = []
    if len(masks) == len(VIEW_IDS):
        for index, current_id in enumerate(VIEW_IDS):
            next_index = (index + 1) % len(VIEW_IDS)
            next_id = VIEW_IDS[next_index]
            current, following = masks[index], masks[next_index]
            intersection = int(np.logical_and(current, following).sum())
            union = int(np.logical_or(current, following).sum())
            xor_pixels = int(np.logical_xor(current, following).sum())
            iou = intersection / union
            current_y, current_x = np.where(current)
            next_y, next_x = np.where(following)
            centroid_shift = float(
                np.hypot(current_x.mean() - next_x.mean(), current_y.mean() - next_y.mean())
            )
            entry = {
                "from": current_id,
                "to": next_id,
                "wrap_transition": index == len(VIEW_IDS) - 1,
                "silhouette_iou": iou,
                "xor_over_union": xor_pixels / union,
                "centroid_shift_px": centroid_shift,
                "within_control_thresholds": iou >= MIN_ADJACENT_IOU
                and centroid_shift <= MAX_CENTROID_SHIFT_PX,
            }
            adjacency.append(entry)
            if not entry["within_control_thresholds"]:
                errors.append(f"adjacent_continuity:{current_id}:{next_id}:{iou}:{centroid_shift}")

    for kind, count in per_kind_counts.items():
        if count != 24:
            errors.append(f"file_count:{kind}:{count}")
        if len(per_kind_hashes[kind]) != 24:
            errors.append(f"unique_hash_count:{kind}:{len(per_kind_hashes[kind])}")

    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_view_ids = [entry["view_id"] for entry in manifest.get("views", [])]
    if manifest_view_ids != VIEW_IDS:
        errors.append("manifest_view_ids_mismatch")

    report = {
        "schema": "flameblade.instantmesh-geometry-controls.qa.v1",
        "status": "control_package_complete_with_source_mesh_defects" if not errors else "control_package_invalid",
        "formal_art_acceptance": False,
        "notice": "GEOMETRY CONTROL ONLY - NOT FINAL ART",
        "expected_view_ids": VIEW_IDS,
        "per_kind_file_counts": per_kind_counts,
        "per_kind_unique_hash_counts": {kind: len(values) for kind, values in per_kind_hashes.items()},
        "canvas": list(CANVAS),
        "expected_modes": EXPECTED,
        "continuity_thresholds_for_control_integrity_only": {
            "minimum_adjacent_silhouette_iou": MIN_ADJACENT_IOU,
            "maximum_adjacent_centroid_shift_px": MAX_CENTROID_SHIFT_PX,
        },
        "adjacent_transitions": adjacency,
        "wrap_transition": adjacency[-1] if adjacency else None,
        "observed_adjacent_iou_range": [
            min(entry["silhouette_iou"] for entry in adjacency),
            max(entry["silhouette_iou"] for entry in adjacency),
        ] if adjacency else None,
        "observed_centroid_shift_px_range": [
            min(entry["centroid_shift_px"] for entry in adjacency),
            max(entry["centroid_shift_px"] for entry in adjacency),
        ] if adjacency else None,
        "source_mesh_visible_holes_observed": bool(warnings),
        "warnings": warnings,
        "errors": errors,
        "views": views,
        "manifest": {
            "path": manifest_path.name,
            "sha256": sha256(manifest_path),
            "view_ids_match": manifest_view_ids == VIEW_IDS,
        },
    }
    destination = ROOT / "qa-summary.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
