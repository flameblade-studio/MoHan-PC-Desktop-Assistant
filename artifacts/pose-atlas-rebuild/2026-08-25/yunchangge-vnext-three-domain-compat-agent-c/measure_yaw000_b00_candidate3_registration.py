from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


CANVAS = (1024, 1536)
BODY_CENTER_CONSTANT = (512, 1292)
DIRECT_TRANSFER_THRESHOLDS = {
    "silhouette_iou_min": 0.95,
    "centroid_delta_max_px": 2.0,
    "bbox_edge_delta_max_px": 3,
    "regional_outside_b00_max_ratio": 0.01,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 255 if value else 0)


def count(mask: Image.Image) -> int:
    return mask.histogram()[255]


def centroid(mask: Image.Image) -> tuple[float, float] | None:
    bbox = mask.getbbox()
    if bbox is None:
        return None
    pixels = mask.load()
    sx = sy = total = 0
    for y in range(bbox[1], bbox[3]):
        for x in range(bbox[0], bbox[2]):
            if pixels[x, y]:
                sx += x
                sy += y
                total += 1
    return (sx / total, sy / total) if total else None


def bbox_metrics(mask: Image.Image) -> dict[str, object]:
    bbox = mask.getbbox()
    center = centroid(mask)
    if bbox is None or center is None:
        return {"bbox": None, "centroid": None, "bbox_center": None, "bottom_center": None}
    left, top, right, bottom = bbox
    return {
        "bbox": [left, top, right, bottom],
        "centroid": [center[0], center[1]],
        "bbox_center": [(left + right - 1) / 2, (top + bottom - 1) / 2],
        "bottom_center": [(left + right - 1) / 2, bottom - 1],
    }


def delta(a: list[float], b: list[float]) -> dict[str, float]:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return {"dx": dx, "dy": dy, "euclidean": math.hypot(dx, dy)}


def overlap(reference: Image.Image, candidate: Image.Image) -> dict[str, float | int]:
    intersection = ImageChops.multiply(reference, candidate)
    union = ImageChops.lighter(reference, candidate)
    reference_count = count(reference)
    candidate_count = count(candidate)
    intersection_count = count(intersection)
    union_count = count(union)
    return {
        "reference_pixels": reference_count,
        "candidate_pixels": candidate_count,
        "intersection_pixels": intersection_count,
        "union_pixels": union_count,
        "iou": intersection_count / union_count if union_count else 0.0,
        "dice": 2 * intersection_count / (reference_count + candidate_count) if reference_count + candidate_count else 0.0,
        "candidate_inside_reference_ratio": intersection_count / candidate_count if candidate_count else 0.0,
        "reference_covered_by_candidate_ratio": intersection_count / reference_count if reference_count else 0.0,
    }


def region_metrics(region: Image.Image, b00: Image.Image) -> dict[str, object]:
    region_count = count(region)
    inside = count(ImageChops.multiply(region, b00))
    data = bbox_metrics(region)
    data.update(
        {
            "pixels": region_count,
            "inside_b00_alpha_pixels": inside,
            "outside_b00_alpha_pixels": region_count - inside,
            "outside_b00_ratio": (region_count - inside) / region_count if region_count else 1.0,
            "truth_boundary": "containment in B00 alpha is not proof of anatomical pixel correspondence",
        }
    )
    return data


def overlay_panel(reference: Image.Image, candidate: Image.Image, label: str) -> Image.Image:
    intersection = ImageChops.multiply(reference, candidate)
    reference_only = ImageChops.subtract(reference, intersection)
    candidate_only = ImageChops.subtract(candidate, intersection)
    panel = Image.new("RGB", CANVAS, (14, 17, 22))
    panel.paste((30, 100, 255), mask=reference_only)
    panel.paste((255, 125, 20), mask=candidate_only)
    panel.paste((35, 220, 100), mask=intersection)
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 1023, 58), fill=(0, 0, 0))
    draw.text((18, 18), label, fill=(255, 255, 255))
    draw.line((BODY_CENTER_CONSTANT[0] - 16, BODY_CENTER_CONSTANT[1], BODY_CENTER_CONSTANT[0] + 16, BODY_CENTER_CONSTANT[1]), fill=(255, 0, 255), width=3)
    draw.line((BODY_CENTER_CONSTANT[0], BODY_CENTER_CONSTANT[1] - 16, BODY_CENTER_CONSTANT[0], BODY_CENTER_CONSTANT[1] + 16), fill=(255, 0, 255), width=3)
    return panel.resize((512, 768), Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b00", type=Path, required=True)
    parser.add_argument("--silhouette", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    b00_path = args.b00.resolve()
    silhouette_path = args.silhouette.resolve()
    controls = {
        "core": args.control_root.resolve() / "yaw+000-pitch+00_core_body_geometry-control-mask.png",
        "hand_left": args.control_root.resolve() / "yaw+000-pitch+00_hand_left_geometry-control-mask.png",
        "hand_right": args.control_root.resolve() / "yaw+000-pitch+00_hand_right_geometry-control-mask.png",
        "foot_left": args.control_root.resolve() / "yaw+000-pitch+00_foot_left_geometry-control-mask.png",
        "foot_right": args.control_root.resolve() / "yaw+000-pitch+00_foot_right_geometry-control-mask.png",
    }
    inputs = [b00_path, silhouette_path, *controls.values()]
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise SystemExit("missing inputs: " + ", ".join(missing))

    with Image.open(b00_path) as image:
        if image.mode != "RGBA" or image.size != CANVAS:
            raise SystemExit("B00 must be RGBA 1024x1536")
        b00 = binary(image.getchannel("A"))
    with Image.open(silhouette_path) as image:
        if image.size != CANVAS:
            raise SystemExit("silhouette canvas mismatch")
        silhouette = binary(image)
    control_masks: dict[str, Image.Image] = {}
    for name, path in controls.items():
        with Image.open(path) as image:
            if image.size != CANVAS:
                raise SystemExit(f"{name} canvas mismatch")
            control_masks[name] = binary(image)

    b00_geometry = bbox_metrics(b00)
    mhr_geometry = bbox_metrics(silhouette)
    overlap_metrics = overlap(b00, silhouette)
    centroid_delta = delta(mhr_geometry["centroid"], b00_geometry["centroid"])
    bbox_delta = [mhr_geometry["bbox"][index] - b00_geometry["bbox"][index] for index in range(4)]
    b00_anchor_delta = delta(b00_geometry["bottom_center"], list(BODY_CENTER_CONSTANT))
    mhr_anchor_delta = delta(mhr_geometry["bottom_center"], list(BODY_CENTER_CONSTANT))
    regions = {name: region_metrics(mask, b00) for name, mask in control_masks.items()}

    transfer_checks = {
        "silhouette_iou": overlap_metrics["iou"] >= DIRECT_TRANSFER_THRESHOLDS["silhouette_iou_min"],
        "centroid_delta": centroid_delta["euclidean"] <= DIRECT_TRANSFER_THRESHOLDS["centroid_delta_max_px"],
        "bbox_edge_delta": max(abs(value) for value in bbox_delta) <= DIRECT_TRANSFER_THRESHOLDS["bbox_edge_delta_max_px"],
        "regional_outside": all(item["outside_b00_ratio"] <= DIRECT_TRANSFER_THRESHOLDS["regional_outside_b00_max_ratio"] for item in regions.values()),
        "authoritative_b00_hand_foot_correspondence_available": False,
    }
    spec = {
        "schema": "mohan.poseatlas.yaw000-registration-preflight/v1",
        "canvas": [1024, 1536],
        "body_center_constant": list(BODY_CENTER_CONSTANT),
        "binary_rule": "B00 alpha > 0; MHR/control grayscale > 0",
        "metrics": ["silhouette IoU/Dice", "binary centroid delta", "bbox edge delta", "bottom-center diagnostic", "regional containment"],
        "direct_transfer_thresholds": DIRECT_TRANSFER_THRESHOLDS,
        "fail_closed_rules": [
            "all transfer checks must pass",
            "same-view authoritative B00 hand/foot correspondences must exist",
            "MHR control masks cannot be promoted directly when registration fails",
        ],
        "authority_mask_generated": False,
    }
    report = {
        "schema": "mohan.poseatlas.yaw000-b00-candidate3-registration-report/v1",
        "status": "BLOCKED_REGISTRATION",
        "exit_code": 4,
        "formal_assets_modified": False,
        "authority_mask_generated": False,
        "inputs": {str(path): digest(path) for path in inputs},
        "b00": b00_geometry,
        "candidate3_silhouette": mhr_geometry,
        "silhouette_overlap": overlap_metrics,
        "registration_error": {
            "centroid_delta_candidate_minus_b00": centroid_delta,
            "bbox_edge_delta_candidate_minus_b00": bbox_delta,
            "b00_bottom_center_minus_body_constant": b00_anchor_delta,
            "candidate_bottom_center_minus_body_constant": mhr_anchor_delta,
        },
        "regions": regions,
        "transfer_checks": transfer_checks,
        "all_transfer_checks_pass": all(transfer_checks.values()),
        "truth_boundary": "No authoritative B00 hand/foot/core masks exist, so regional containment cannot validate pixel correspondence.",
        "formal_600_complete": False,
        "promotion_allowed": False,
    }
    spec_path = output / "yaw000-b00-candidate3-registration-preflight-spec.json"
    report_path = output / "yaw000-b00-candidate3-registration-report.json"
    contact_path = output / "yaw000-b00-candidate3-registration-contact.png"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hands = ImageChops.lighter(control_masks["hand_left"], control_masks["hand_right"])
    feet = ImageChops.lighter(control_masks["foot_left"], control_masks["foot_right"])
    panels = [
        overlay_panel(b00, silhouette, "B00 alpha vs candidate3 silhouette"),
        overlay_panel(b00, control_masks["core"], "B00 alpha vs MHR core control"),
        overlay_panel(b00, hands, "B00 alpha vs MHR left/right hands"),
        overlay_panel(b00, feet, "B00 alpha vs MHR left/right feet"),
    ]
    contact = Image.new("RGB", (1024, 1536), (0, 0, 0))
    for index, panel in enumerate(panels):
        contact.paste(panel, ((index % 2) * 512, (index // 2) * 768))
    contact.save(contact_path, format="PNG", optimize=False)
    print(json.dumps({"status": report["status"], "iou": overlap_metrics["iou"], "centroid_delta": centroid_delta, "bbox_edge_delta": bbox_delta, "all_transfer_checks_pass": False}, ensure_ascii=False))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
