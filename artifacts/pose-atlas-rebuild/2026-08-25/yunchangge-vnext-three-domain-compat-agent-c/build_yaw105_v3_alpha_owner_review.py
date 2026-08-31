from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
EVIDENCE_ROOT = ROOT / "yunchangge-vnext-three-domain-compat-agent-c"
TEMPLATE_PATH = EVIDENCE_ROOT / "yaw-105-v3-alpha-owner-review-template.json"
OUTPUT = EVIDENCE_ROOT / "yaw-105-pitch+00.candidate-v3.birefnet-rgba-staging.png"
BOARD_PATH = EVIDENCE_ROOT / "yaw-105-v3-alpha-owner-review-board.jpg"
REPORT_PATH = EVIDENCE_ROOT / "yaw-105-v3-alpha-owner-review-build.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def count_nonzero_alpha(alpha: Image.Image, box: tuple[int, int, int, int]) -> int:
    return sum(value > 0 for value in alpha.crop(box).getdata())


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (30, 34, 39))
    x = (size[0] - copy.width) // 2
    y = (size[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def composite(rgba: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", rgba.size, (*background, 255))
    return Image.alpha_composite(base, rgba).convert("RGB")


def build_board(rgba: Image.Image, template: dict[str, object]) -> None:
    board = Image.new("RGB", (1800, 1800), (30, 34, 39))
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    draw.text((30, 18), "yaw-105 v3 ALPHA OWNER REVIEW | IDENTITY HOLD | ANGLE HOLD | NO PROMOTION", fill=(255, 210, 80), font=font)

    backgrounds = template["full_preview_slots"]
    assert isinstance(backgrounds, list)
    for index, slot in enumerate(backgrounds):
        assert isinstance(slot, dict)
        rgb = tuple(slot["rgb"])
        preview = fit(composite(rgba, rgb), (560, 830))
        x = 20 + index * 590
        board.paste(preview, (x, 55))
        draw.text((x, 895), str(slot["id"]), fill=(240, 240, 240), font=font)

    roi_slots = template["roi_slots"]
    assert isinstance(roi_slots, list)
    for index, slot in enumerate(roi_slots):
        assert isinstance(slot, dict)
        box = tuple(slot["box"])
        crop = composite(rgba, (24, 24, 24)).crop(box)
        preview = fit(crop, (420, 620))
        x = 20 + index * 445
        board.paste(preview, (x, 955))
        draw.text((x, 1585), str(slot["id"]), fill=(240, 240, 240), font=font)
        draw.text((x, 1610), str(slot["manual_gate"]), fill=(210, 210, 210), font=font)

    draw.text((30, 1745), "Board is review evidence only. Technical PASS cannot accept identity, angle or art.", fill=(255, 160, 160), font=font)
    board.save(BOARD_PATH, quality=94, subsampling=0)


def main() -> int:
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not OUTPUT.is_file():
        report = {
            "schema": "mohan.yaw105.v3.alpha-owner-review-build/v1",
            "status": "BLOCK_OUTPUT_MISSING",
            "inference_run": False,
            "staging_rgba_exists": False,
            "review_board_created": False,
            "review_board_path": str(BOARD_PATH),
            "identity_status": "HOLD_NOT_ACCEPTED",
            "angle_status": "HOLD_NOT_ACCEPTED",
            "promotion_allowed": False,
            "errors": ["staging RGBA does not exist; no preview or ROI board was fabricated"],
        }
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4

    with Image.open(OUTPUT) as source:
        rgba = source.copy()
    errors: list[str] = []
    if rgba.mode != "RGBA":
        errors.append("staging output is not RGBA")
    if rgba.size != (1024, 1536):
        errors.append("staging output is not 1024x1536")
    if errors:
        report = {
            "schema": "mohan.yaw105.v3.alpha-owner-review-build/v1",
            "status": "BLOCK_INVALID_OUTPUT",
            "staging_rgba_exists": True,
            "review_board_created": False,
            "promotion_allowed": False,
            "errors": errors,
        }
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4

    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    corners = [
        alpha.getpixel((0, 0)),
        alpha.getpixel((rgba.width - 1, 0)),
        alpha.getpixel((0, rgba.height - 1)),
        alpha.getpixel((rgba.width - 1, rgba.height - 1)),
    ]
    transparent_rgb = sum(
        1
        for red, green, blue, value in rgba.getdata()
        if value == 0 and (red != 0 or green != 0 or blue != 0)
    )
    border_nonzero = sum(value > 0 for value in alpha.crop((0, 0, rgba.width, 1)).getdata())
    border_nonzero += sum(
        value > 0 for value in alpha.crop((0, rgba.height - 1, rgba.width, rgba.height)).getdata()
    )
    border_nonzero += sum(value > 0 for value in alpha.crop((0, 0, 1, rgba.height)).getdata())
    border_nonzero += sum(
        value > 0 for value in alpha.crop((rgba.width - 1, 0, rgba.width, rgba.height)).getdata()
    )
    automatic_qa = {
        "mode": rgba.mode,
        "size": list(rgba.size),
        "corner_alpha": corners,
        "transparent_rgb_nonzero_pixels": transparent_rgb,
        "nonzero_border_pixel_observations": border_nonzero,
        "foreground_bbox": list(bbox) if bbox else None,
        "roi_nonzero_alpha": {
            "shoe_left": count_nonzero_alpha(alpha, (385, 1380, 515, 1475)),
            "shoe_right": count_nonzero_alpha(alpha, (500, 1380, 650, 1475)),
            "hem": count_nonzero_alpha(alpha, (290, 1220, 710, 1455)),
        },
    }
    contract = template["automatic_qa_required"]
    assert isinstance(contract, dict)
    if corners != [0, 0, 0, 0]:
        errors.append("corner alpha gate failed")
    if transparent_rgb != 0:
        errors.append("transparent RGB gate failed")
    if border_nonzero != 0:
        errors.append("foreground touches canvas boundary")
    if bbox is None or bbox[3] < int(contract["foreground_bbox_min_bottom"]):
        errors.append("foreground bbox bottom gate failed")
    if automatic_qa["roi_nonzero_alpha"]["shoe_left"] < int(contract["shoe_left_min_nonzero_alpha"]):
        errors.append("left shoe alpha gate failed")
    if automatic_qa["roi_nonzero_alpha"]["shoe_right"] < int(contract["shoe_right_min_nonzero_alpha"]):
        errors.append("right shoe alpha gate failed")
    if automatic_qa["roi_nonzero_alpha"]["hem"] < int(contract["hem_min_nonzero_alpha"]):
        errors.append("hem alpha gate failed")

    if errors:
        status = "BLOCK_AUTOMATIC_QA"
        board_created = False
    else:
        build_board(rgba, template)
        status = "HOLD_OWNER_REVIEW"
        board_created = True
    report = {
        "schema": "mohan.yaw105.v3.alpha-owner-review-build/v1",
        "status": status,
        "staging_rgba_exists": True,
        "staging_rgba_sha256": sha256(OUTPUT),
        "automatic_qa": automatic_qa,
        "review_board_created": board_created,
        "review_board_path": str(BOARD_PATH) if board_created else None,
        "review_board_sha256": sha256(BOARD_PATH) if board_created else None,
        "identity_status": "HOLD_NOT_ACCEPTED",
        "angle_status": "HOLD_NOT_ACCEPTED",
        "owner_review_required": True,
        "promotion_allowed": False,
        "errors": errors,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
