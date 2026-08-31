from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
EVIDENCE_ROOT = ROOT / "yunchangge-vnext-three-domain-compat-agent-c"
OUTPUT = EVIDENCE_ROOT / "yaw-105-pitch+00.candidate-v3.birefnet-rgba-staging.png"
REPORT_PATH = EVIDENCE_ROOT / "yaw-105-v3-alpha-output-qa.json"
ROIS = {
    "shoe_left": (385, 1380, 515, 1475),
    "shoe_right": (500, 1380, 650, 1475),
    "hem": (290, 1220, 710, 1455),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def nonzero_alpha(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    alpha = image.getchannel("A").crop(box)
    return sum(1 for value in alpha.getdata() if value > 0)


def main() -> int:
    errors: list[str] = []
    report: dict[str, object] = {
        "schema": "mohan.yaw105.v3.alpha-output-qa/v1",
        "output": str(OUTPUT),
        "promotion_allowed": False,
        "identity_gate": "NOT_ACCEPTED",
        "angle_gate": "NOT_ACCEPTED",
        "manual_art_gate": "REQUIRED",
    }
    if not OUTPUT.is_file():
        report.update(
            {
                "technical_status": "BLOCK_OUTPUT_MISSING",
                "inference_run": False,
                "errors": ["staged RGBA output does not exist; BiRefNet was not run by this task"],
            }
        )
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4

    with Image.open(OUTPUT) as source:
        image = source.copy()
    if image.size != (1024, 1536):
        errors.append("output dimensions are not 1024x1536")
    if image.mode != "RGBA":
        errors.append("output mode is not RGBA")
        report.update({"technical_status": "BLOCK", "errors": errors})
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    corners = [
        alpha.getpixel((0, 0)),
        alpha.getpixel((image.width - 1, 0)),
        alpha.getpixel((0, image.height - 1)),
        alpha.getpixel((image.width - 1, image.height - 1)),
    ]
    pixels = image.getdata()
    transparent_rgb_nonzero = sum(
        1 for red, green, blue, value in pixels if value == 0 and (red != 0 or green != 0 or blue != 0)
    )
    border_nonzero = sum(1 for value in alpha.crop((0, 0, image.width, 1)).getdata() if value > 0)
    border_nonzero += sum(1 for value in alpha.crop((0, image.height - 1, image.width, image.height)).getdata() if value > 0)
    border_nonzero += sum(1 for value in alpha.crop((0, 0, 1, image.height)).getdata() if value > 0)
    border_nonzero += sum(1 for value in alpha.crop((image.width - 1, 0, image.width, image.height)).getdata() if value > 0)
    roi_counts = {name: nonzero_alpha(image, box) for name, box in ROIS.items()}

    if corners != [0, 0, 0, 0]:
        errors.append("one or more corner alpha values are nonzero")
    if transparent_rgb_nonzero != 0:
        errors.append("transparent RGB contamination is nonzero")
    if bbox is None:
        errors.append("alpha foreground is empty")
    elif bbox[3] < 1460:
        errors.append("foreground bottom is too high; shoes or hem may be removed")
    if border_nonzero != 0:
        errors.append("foreground touches canvas boundary")
    if roi_counts["shoe_left"] < 500:
        errors.append("left shoe ROI has insufficient nonzero alpha")
    if roi_counts["shoe_right"] < 500:
        errors.append("right shoe ROI has insufficient nonzero alpha")
    if roi_counts["hem"] < 20000:
        errors.append("hem ROI has insufficient nonzero alpha")

    report.update(
        {
            "technical_status": "PASS_TECHNICAL_ONLY" if not errors else "BLOCK",
            "inference_run": True,
            "sha256": sha256(OUTPUT),
            "mode": image.mode,
            "size": [image.width, image.height],
            "corner_alpha": corners,
            "foreground_bbox": list(bbox) if bbox else None,
            "nonzero_border_pixel_observations": border_nonzero,
            "transparent_rgb_nonzero_pixels": transparent_rgb_nonzero,
            "roi_nonzero_alpha": roi_counts,
            "roi_contract": {name: list(box) for name, box in ROIS.items()},
            "manual_checks_still_required": [
                "both shoes are complete low white cloth shoes",
                "skirt hem has no erosion, rectangular cut, or hard saw edge",
                "hair strands and fixed ornament are complete",
                "identity, angle, clothing order, neck and hands require owner review",
            ],
            "errors": errors,
        }
    )
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 4


if __name__ == "__main__":
    raise SystemExit(main())
