from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCES = {
    "idle_front": ROOT / "assets" / "expressions" / "idle_front.png",
    "idle_lean": ROOT / "assets" / "expressions" / "idle_lean.png",
}
EXPECTED = {
    "idle_front": "5A5970C1E91B3A89A8CC4EFD8E3BB72B417F4B644C73A6074CD073D577EAB373",
    "idle_lean": "784D023CC3F8AE35CB8A3C38B15175CD1B6F62E80D226E6B1339DAA802579FD6",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


CONTROLS = {
    "idle_front": {
        "crop_box_ltrb": [390, 30, 875, 720],
        "jaw_chin_polyline": [[470,421],[476,492],[497,555],[540,609],[588,640],[625,650],[662,640],[711,609],[753,555],[773,492],[779,421]],
        "jaw_chin_semantics": ["left_preauricular","left_mandibular_upper","left_jaw_angle","left_prechin","left_chin","menton","right_chin","right_prechin","right_jaw_angle","right_mandibular_upper","right_preauricular"],
        "neck_skin_keep_polygon": [[540,609],[588,640],[625,650],[662,640],[711,609],[695,686],[670,720],[580,720],[555,686]],
        "collar_exclusion_polygons": [
            [[505,643],[540,609],[555,686],[580,720],[520,720],[495,680]],
            [[711,609],[745,643],[755,680],[730,720],[670,720],[695,686]],
        ],
        "protected_hair_corridors": [
            [[390,370],[486,370],[520,720],[390,720]],
            [[765,370],[875,370],[875,720],[730,720]],
        ],
    },
    "idle_lean": {
        "crop_box_ltrb": [390, 85, 900, 720],
        "jaw_chin_polyline": [[440,403],[432,474],[440,552],[463,602],[493,633],[514,642],[548,634],[590,615],[632,584],[671,548],[711,486]],
        "jaw_chin_semantics": ["far_preauricular","far_mandibular_upper","far_jaw_angle","far_prechin","far_chin","menton","near_chin","near_prechin","near_jaw_angle","near_mandibular_lower","near_preauricular"],
        "neck_skin_keep_polygon": [[548,634],[590,615],[632,584],[652,615],[642,690],[625,720],[545,720],[522,682],[514,642]],
        "collar_exclusion_polygons": [
            [[485,642],[514,642],[522,682],[545,720],[490,720],[475,680]],
            [[632,584],[665,605],[685,660],[680,720],[625,720],[642,690]],
        ],
        "protected_hair_corridors": [
            [[390,330],[454,330],[490,720],[390,720]],
            [[684,330],[900,330],[900,720],[680,720]],
        ],
    },
}


def draw_overlay(source: Path, name: str, control: dict[str, object]) -> Path:
    image = Image.open(source).convert("RGBA")
    canvas = Image.alpha_composite(Image.new("RGBA", image.size, (40,40,40,255)), image)
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()
    for polygon in control["protected_hair_corridors"]:
        draw.polygon(polygon, fill=(255,215,0,28), outline=(255,215,0,220), width=3)
    for polygon in control["collar_exclusion_polygons"]:
        draw.polygon(polygon, fill=(255,40,40,55), outline=(255,40,40,240), width=4)
    draw.polygon(control["neck_skin_keep_polygon"], fill=(40,255,80,36), outline=(40,255,80,240), width=4)
    points = control["jaw_chin_polyline"]
    draw.line(points, fill=(0,235,255,255), width=5, joint="curve")
    for index, (x, y) in enumerate(points):
        draw.ellipse((x-6,y-6,x+6,y+6), fill=(0,235,255,255), outline=(0,0,0,255), width=2)
        draw.text((x+8,y-8), str(index), fill=(255,255,255,255), stroke_width=2, stroke_fill=(0,0,0,255), font=font)
    draw.rectangle(control["crop_box_ltrb"], outline=(255,255,255,230), width=3)
    draw.rectangle((18,18,560,92), fill=(0,0,0,190))
    draw.text((30,28), f"{name}: cyan=jaw/chin, green=neck keep", fill="white", font=font)
    draw.text((30,50), "red=collar exclude, yellow=hair protect", fill="white", font=font)
    draw.text((30,72), "MANUAL SOURCE-SPACE CONTROLS; NOT MEDIAPIPE", fill=(255,210,80), font=font)
    output = HERE / f"{name}.jaw-chin-collar-overlay.png"
    canvas.save(output, format="PNG", optimize=True)
    return output


def main() -> int:
    records = []
    for name, source in SOURCES.items():
        actual = sha256(source)
        if actual != EXPECTED[name]:
            raise RuntimeError(f"source hash mismatch: {name}: {actual}")
        with Image.open(source) as image:
            if image.size != (1254,1254):
                raise RuntimeError(f"unexpected source dimensions: {name}: {image.size}")
        control = CONTROLS[name]
        for key in ("jaw_chin_polyline", "neck_skin_keep_polygon"):
            if any(not (0 <= x < 1254 and 0 <= y < 1254) for x, y in control[key]):
                raise RuntimeError(f"out-of-bounds point: {name}/{key}")
        overlay = draw_overlay(source, name, control)
        records.append({
            "id": name, "source_path": str(source), "source_sha256": actual,
            "source_dimensions": [1254,1254], "coordinate_space": "source_pixel_xy_origin_top_left",
            **control, "overlay_path": str(overlay), "overlay_sha256": sha256(overlay),
            "review_status": "MANUAL_CONTROL_POINTS_READY_FOR_MAIN_AGENT_VISUAL_REVIEW",
        })
    payload = {
        "schema": "mohan.authority_jaw_chin_mask_controls.v1",
        "status": "READONLY_SOURCE_CONTROLS_NO_TRAINING",
        "landmark_provenance": {
            "method": "MANUAL_VISUAL_SOURCE_SPACE_CONTROL_POINTS",
            "mediapipe_source_tied_landmarks_found": False,
            "mediapipe_mapping": None,
            "reason": "No existing landmark or overlay file traceable to these exact source hashes was found locally; no MediaPipe indices are fabricated.",
        },
        "mask_contract": {
            "horizontal_chin_cut_forbidden": True,
            "horizontal_mirror_forbidden": True,
            "jaw_chin_polyline_is_protected": True,
            "neck_skin_keep_polygon_is_protected": True,
            "collar_exclusion_must_be_clipped_against_protected_hair_corridors": True,
            "recommended_feather_px_in_source_space": 4,
            "apply_order": ["protect jaw/chin and neck skin", "protect hair corridors", "neutral-fill only collar exclusion remainder", "verify lips and menton remain unchanged"],
        },
        "records": records,
        "side_effects": {"source_images_modified": False, "training_started": False, "images_generated": False},
    }
    output = HERE / "authority-jaw-chin-mask-controls.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "exit-code.txt").write_text("0\n", encoding="utf-8")
    print(output)
    print(sha256(output))
    for record in records:
        print(record["overlay_path"])
        print(record["overlay_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
