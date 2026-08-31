from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
REGISTRATION = PARENT / "alternate-source-registration-feasibility-agent-b" / "registration-feasibility.json"
R10 = PARENT / "mohan-v3-pure-face-mask-r10-agent-b"

CASES = {
    "seq09": {
        "base": R10 / "seq09-pure-face-rgba-r10.png",
        "roi_polygons": [
            [[54, 205], [126, 205], [126, 374], [78, 390], [52, 336]],
            [[278, 205], [350, 205], [350, 336], [320, 390], [274, 374]],
        ],
        "protected_center": [126, 210, 278, 478],
        "prompt": "Locally reconstruct only the missing bilateral temple hair and natural ear-side boundary. Preserve the exact central face, eyes, nose, mouth, chin, crown ornament and physical ornament side. No rectangular cut edge, no background patch, no clothing.",
    },
    "seq15": {
        "base": R10 / "seq15-pure-face-rgba-r10.png",
        "roi_polygons": [
            [[116, 225], [202, 225], [218, 430], [180, 472], [118, 414], [108, 320]],
            [[300, 225], [350, 225], [352, 340], [326, 385], [294, 365]],
        ],
        "protected_center": [202, 215, 300, 480],
        "prompt": "Locally reconstruct only clean long black hair and natural ear-side boundaries. Remove source-scene ambiguity and preserve the exact central face, lips, chin, upper hair, crown ornament and physical ornament side. No background rectangle, no clothing, no whole-face redraw.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_case(name: str, case: dict[str, object], registration: dict[str, object]) -> dict[str, object]:
    output_dir = ROOT / name
    output_dir.mkdir(parents=True, exist_ok=True)
    base_path = Path(case["base"])
    base = Image.open(base_path).convert("RGBA")
    neutral = Image.new("RGBA", base.size, (112, 112, 112, 255))
    input_rgb = Image.alpha_composite(neutral, base).convert("RGB")
    input_path = output_dir / "input-neutral-rgb.png"
    input_rgb.save(input_path)

    hard = Image.new("L", base.size, 0)
    draw = ImageDraw.Draw(hard)
    for polygon in case["roi_polygons"]:
        draw.polygon([tuple(point) for point in polygon], fill=255)
    draw.rectangle(tuple(case["protected_center"]), fill=0)
    hard_path = output_dir / "repair-roi-hard.png"
    hard.save(hard_path)
    soft = hard.filter(ImageFilter.GaussianBlur(8.0))
    soft_path = output_dir / "repair-roi-soft.png"
    soft.save(soft_path)

    overlay = input_rgb.copy()
    overlay_pixels = np.asarray(overlay, dtype=np.uint8).copy()
    hard_values = np.asarray(hard, dtype=np.uint8) > 0
    overlay_pixels[hard_values] = ((overlay_pixels[hard_values].astype(np.uint16) + np.array([255, 50, 50])) // 2).astype(np.uint8)
    overlay = Image.fromarray(overlay_pixels, "RGB")
    overlay_draw = ImageDraw.Draw(overlay)
    registration_record = next(record for record in registration["records"] if record["sequence"] == name)
    for x, y in registration_record["manual_five_point_target_xy"]:
        overlay_draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(0, 255, 0), width=2)
    overlay_path = output_dir / "repair-control-overlay.png"
    overlay.save(overlay_path)

    manifest = {
        "schema": "mohan.nonpaste_local_repair_control/v1",
        "sequence": name,
        "canvas": [512, 512],
        "crop_box_xyxy": [0, 0, 512, 512],
        "base_rgba": str(base_path.resolve()), "base_rgba_sha256": sha256(base_path),
        "input_rgb": str(input_path.resolve()), "input_rgb_sha256": sha256(input_path),
        "hard_mask": str(hard_path.resolve()), "hard_mask_sha256": sha256(hard_path),
        "soft_mask": str(soft_path.resolve()), "soft_mask_sha256": sha256(soft_path),
        "control_overlay": str(overlay_path.resolve()), "control_overlay_sha256": sha256(overlay_path),
        "roi_polygons_xy": case["roi_polygons"],
        "protected_center_xyxy": case["protected_center"],
        "registration_transform": registration_record["similarity_transform_source_panel_to_target"],
        "five_point_target_xy": registration_record["manual_five_point_target_xy"],
        "ear_hair_contour_rms_px": registration_record["ear_hair_contour_rms_px"],
        "registered_reference_source": registration_record["alternate_source_path"],
        "registered_reference_sha256": registration_record["alternate_source_sha256"],
        "prompt": case["prompt"],
        "negative_prompt": "whole face redraw, changed identity, changed mouth, changed chin, changed ornament, background rectangle, clothing, mirrored ornament",
        "direct_pixel_paste_allowed": False,
        "formal_promotion": False,
    }
    manifest_path = output_dir / "control-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["manifest_sha256"] = sha256(manifest_path)
    return manifest


def main() -> int:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    records = [build_case(name, case, registration) for name, case in CASES.items()]
    contact = Image.new("RGB", (2048, 548 * len(records)), (25, 25, 25))
    draw = ImageDraw.Draw(contact)
    font = ImageFont.load_default()
    for row, record in enumerate(records):
        panels = [
            Image.open(record["input_rgb"]).convert("RGB"),
            Image.open(record["hard_mask"]).convert("RGB"),
            Image.open(record["soft_mask"]).convert("RGB"),
            Image.open(record["control_overlay"]).convert("RGB"),
        ]
        y = row * 548 + 28
        for column, panel in enumerate(panels):
            contact.paste(panel, (column * 512, y))
        draw.text((8, row * 548 + 6), f"{record['sequence']} | neutral input | hard ROI | soft ROI | protected-center overlay", fill="white", font=font)
    contact_path = ROOT / "nonpaste-local-repair-control-contact.png"
    contact.save(contact_path)
    index = {
        "schema": "mohan.nonpaste_local_repair_control_index/v1",
        "registration_report": str(REGISTRATION.resolve()), "registration_report_sha256": sha256(REGISTRATION),
        "records": records,
        "contact_sheet": {"path": str(contact_path.resolve()), "sha256": sha256(contact_path)},
        "generated_candidate_count": 0,
        "formal_promotion": False,
        "exit_code": 0,
    }
    (ROOT / "control-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("status=PASS_CONTROL_BUILD candidates=0 promotion=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
