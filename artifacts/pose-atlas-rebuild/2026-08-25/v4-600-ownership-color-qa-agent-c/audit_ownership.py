from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
SOURCE = PROJECT / "assets/pose-atlas/v4-layered"
HERE = Path(__file__).resolve().parent
VIEWS = [
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
]
LAYERS = ("body", "sleeve_left", "sleeve_right", "ornament")
THRESHOLDS = {"body_garment": 500, "body_shoe": 20, "sleeve_fabric": 500, "ornament_skin": 20}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def is_blue(r: int, g: int, b: int) -> bool:
    return b >= 40 and b - r >= 12 and b - g >= 5 and max(r, g, b) - min(r, g, b) >= 15


def is_white(r: int, g: int, b: int) -> bool:
    return min(r, g, b) >= 150 and max(r, g, b) - min(r, g, b) <= 50


def is_skin(r: int, g: int, b: int) -> bool:
    return r >= 100 and g >= 55 and b >= 35 and r >= g + 8 and g >= b + 4 and r - b >= 18


def inspect(path: Path, layer: str) -> tuple[dict[str, object], Image.Image]:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    counts = {"alpha_pixels": 0, "blue_pixels": 0, "white_pixels": 0, "lower_white_pixels": 0, "skin_like_pixels": 0}
    highlighted = image.copy()
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    if bbox:
        crop = image.crop(bbox)
        marked = []
        x0, y0, _, _ = bbox
        for index, (r, g, b, a) in enumerate(crop.getdata()):
            if a < 64:
                marked.append((0, 0, 0, 0))
                continue
            counts["alpha_pixels"] += 1
            blue = is_blue(r, g, b)
            white = is_white(r, g, b)
            skin = is_skin(r, g, b)
            y = y0 + index // crop.width
            lower_white = white and y >= 1380
            counts["blue_pixels"] += int(blue)
            counts["white_pixels"] += int(white)
            counts["lower_white_pixels"] += int(lower_white)
            counts["skin_like_pixels"] += int(skin)
            color = (0, 0, 0, 0)
            if layer == "body" and lower_white:
                color = (255, 0, 0, 220)
            elif layer == "body" and blue:
                color = (255, 0, 255, 205)
            elif layer == "body" and white:
                color = (255, 220, 0, 205)
            elif layer.startswith("sleeve") and (blue or white):
                color = (255, 0, 255, 205)
            elif layer == "ornament" and skin:
                color = (0, 255, 80, 220)
            marked.append(color)
        mark_crop = Image.new("RGBA", crop.size)
        mark_crop.putdata(marked)
        overlay.paste(mark_crop, bbox[:2])
        highlighted = Image.alpha_composite(highlighted, overlay)

    if layer == "body":
        issue_count = counts["blue_pixels"] + counts["white_pixels"]
        issues = {
            "garment_color_evidence": issue_count >= THRESHOLDS["body_garment"],
            "shoe_color_evidence": counts["lower_white_pixels"] >= THRESHOLDS["body_shoe"],
        }
    elif layer.startswith("sleeve"):
        issue_count = counts["blue_pixels"] + counts["white_pixels"]
        issues = {"fabric_color_evidence": issue_count >= THRESHOLDS["sleeve_fabric"]}
    else:
        issue_count = counts["skin_like_pixels"]
        issues = {"skin_color_evidence": issue_count >= THRESHOLDS["ornament_skin"]}
    record = {
        "path": str(path), "sha256": sha256(path), "mode": "RGBA", "size": [1024, 1536],
        "alpha_bbox": list(bbox) if bbox else None, "counts": counts, "issues": issues,
        "gate": "FAIL" if any(issues.values()) else "NO_COLOR_EVIDENCE",
        "truth_boundary": "Color evidence is a QA signal, not a formal ownership mask or semantic segmentation.",
    }
    return record, highlighted


def contact_sheet(previews: list[tuple[str, str, Image.Image, dict[str, object]]], path: Path) -> None:
    thumb_w, thumb_h, label_h, columns = 160, 240, 34, 8
    rows = (len(previews) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (28, 32, 38))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (view, layer, preview, record) in enumerate(previews):
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + label_h)
        base = Image.new("RGBA", preview.size, (24, 24, 24, 255))
        base.alpha_composite(preview)
        thumb = base.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        counts = record["counts"]
        code = {"body": "B", "sleeve_left": "SL", "sleeve_right": "SR", "ornament": "O"}[layer]
        label = f"{view[3:7]} {code} {record['gate']}"
        metric = counts["skin_like_pixels"] if layer == "ornament" else counts["blue_pixels"] + counts["white_pixels"]
        draw.text((x + 3, y + thumb_h + 2), label, fill=(255, 255, 255), font=font)
        draw.text((x + 3, y + thumb_h + 17), f"suspect={metric}", fill=(255, 210, 80), font=font)
    sheet.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=VIEWS)
    parser.add_argument("--output", default="ownership-color-qa.json")
    parser.add_argument("--contact", default="ownership-color-contact.png")
    args = parser.parse_args()
    views = [args.only] if args.only else VIEWS
    report: dict[str, object] = {
        "schema": "mohan.pose-atlas.v4.ownership-color-qa.v1",
        "source": str(SOURCE), "source_png_count": len(list(SOURCE.glob("*.png"))),
        "views_requested": views, "layers": list(LAYERS), "thresholds": THRESHOLDS,
        "truth_boundary": "Deterministic color evidence only. It cannot be promoted to a formal ownership mask.",
        "results": [],
    }
    previews = []
    failed = 0
    for view in views:
        layer_results = {}
        for layer in LAYERS:
            path = SOURCE / f"{view}_{layer}.png"
            if not path.is_file():
                layer_results[layer] = {"path": str(path), "gate": "FAIL_MISSING"}
                failed += 1
                continue
            record, preview = inspect(path, layer)
            layer_results[layer] = record
            failed += int(record["gate"] == "FAIL")
            previews.append((view, layer, preview, record))
        report["results"].append({"view_id": view, "layers": layer_results})
    report["summary"] = {
        "views": len(views), "layer_files_checked": len(views) * len(LAYERS),
        "failed_layer_gates": failed, "status": "FAIL_OWNERSHIP_COLOR_EVIDENCE" if failed else "NO_COLOR_EVIDENCE",
        "promotion_allowed": False,
    }
    output = HERE / args.output
    contact = HERE / args.contact
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contact_sheet(previews, contact)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 4 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
