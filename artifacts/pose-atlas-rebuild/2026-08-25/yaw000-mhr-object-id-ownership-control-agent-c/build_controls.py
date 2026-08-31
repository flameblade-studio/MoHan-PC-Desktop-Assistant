from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[4]
PART_DIR = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
PART_ID = PART_DIR / "masks/yaw+000-pitch+00_part-id.png"
PART_MANIFEST = PART_DIR / "skin-weight-part-manifest.json"
PART_QA = PART_DIR / "part-id-mask-qa.json"
B00 = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-24/mother-views/yaw+000-pitch+00.approved-rgba.png"
MHR_ADMISSION = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/mhr-ufbx-production-admission/mhr-ufbx-production-admission.json"
MHR_FBX = PROJECT / "artifacts/third-party-downloads/MHR-v1.0.1-assets/extracted/assets/lod1.fbx"
MHR_LICENSE = PROJECT / "artifacts/third-party-downloads/MHR-v1.0.1-assets/extracted/assets/LICENSE.txt"
OUT = Path(__file__).resolve().parent

CORE_IDS = {1, 2, 3, 4, 6, 7, 9, 10, 12, 13}
LEFT_HAND_ID, RIGHT_HAND_ID = 5, 8
LEFT_FOOT_ID, RIGHT_FOOT_ID = 11, 14
AMBIGUOUS_ID = 255
PALETTE = {
    0: (0, 0, 0), 1: (245, 166, 35), 2: (80, 170, 255),
    3: (255, 112, 112), 4: (240, 80, 130), 5: (255, 220, 180),
    6: (112, 255, 130), 7: (60, 220, 110), 8: (195, 255, 200),
    9: (180, 120, 255), 10: (135, 75, 230), 11: (235, 190, 255),
    12: (255, 220, 80), 13: (230, 175, 40), 14: (255, 240, 165),
    255: (255, 255, 255),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def save_mask(name: str, mask: np.ndarray) -> Path:
    path = OUT / name
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path, optimize=True)
    return path


def save_rgb(name: str, array: np.ndarray) -> Path:
    path = OUT / name
    Image.fromarray(array, "RGB").save(path, optimize=True)
    return path


def thumbnail(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path)
    if image.mode == "RGBA":
        bg = Image.new("RGBA", image.size, (35, 39, 44, 255))
        bg.alpha_composite(image)
        image = bg.convert("RGB")
    else:
        image = image.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (24, 27, 31))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def contact(entries: list[tuple[str, Path]], path: Path) -> None:
    cell_w, cell_h, label_h, columns = 250, 375, 38, 4
    rows = 2
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (20, 23, 27))
    draw, font = ImageDraw.Draw(sheet), ImageFont.load_default()
    for index, (label, source) in enumerate(entries):
        x, y = (index % columns) * cell_w, (index // columns) * (cell_h + label_h)
        sheet.paste(thumbnail(source, (cell_w - 8, cell_h)), (x + 4, y))
        draw.text((x + 6, y + cell_h + 6), label, fill=(245, 245, 245), font=font)
    sheet.save(path, optimize=True)


def main() -> int:
    required = [PART_ID, PART_MANIFEST, PART_QA, B00, MHR_ADMISSION, MHR_FBX, MHR_LICENSE]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "BLOCKED_MISSING_INPUT", "missing": missing}))
        return 4
    ids = np.asarray(Image.open(PART_ID).convert("L"))
    if ids.shape != (1536, 1024):
        print(json.dumps({"status": "BLOCKED_BAD_DIMENSIONS", "shape": list(ids.shape)}))
        return 4
    present_ids = sorted(int(value) for value in np.unique(ids))
    expected = set(range(15)) | {255}
    if set(present_ids) != expected:
        print(json.dumps({"status": "BLOCKED_ID_SET", "ids": present_ids}))
        return 4

    masks = {
        "core_body": np.isin(ids, list(CORE_IDS)),
        "hand_left": ids == LEFT_HAND_ID,
        "hand_right": ids == RIGHT_HAND_ID,
        "foot_left": ids == LEFT_FOOT_ID,
        "foot_right": ids == RIGHT_FOOT_ID,
        "ambiguous_joint_boundaries": ids == AMBIGUOUS_ID,
        "garment": np.zeros_like(ids, dtype=bool),
    }
    paths: dict[str, Path] = {}
    for name, mask in masks.items():
        paths[name] = save_mask(f"yaw+000-pitch+00_{name}_geometry-control-mask.png", mask)
    hands_rgb = np.zeros((*ids.shape, 3), dtype=np.uint8)
    hands_rgb[masks["hand_left"]] = (255, 100, 120)
    hands_rgb[masks["hand_right"]] = (100, 255, 140)
    paths["hands_physical_side"] = save_rgb("yaw+000-pitch+00_hands-physical-side-control.png", hands_rgb)
    feet_rgb = np.zeros((*ids.shape, 3), dtype=np.uint8)
    feet_rgb[masks["foot_left"]] = (190, 120, 255)
    feet_rgb[masks["foot_right"]] = (255, 220, 80)
    paths["feet_physical_side"] = save_rgb("yaw+000-pitch+00_feet-physical-side-control.png", feet_rgb)
    palette = np.zeros((*ids.shape, 3), dtype=np.uint8)
    for value, color in PALETTE.items():
        palette[ids == value] = color
    paths["part_id_palette"] = save_rgb("yaw+000-pitch+00_part-id-palette.png", palette)

    b00_alpha = np.asarray(Image.open(B00).convert("RGBA"))[:, :, 3] > 0
    mhr_silhouette = ids != 0
    intersection = int((b00_alpha & mhr_silhouette).sum())
    union = int((b00_alpha | mhr_silhouette).sum())
    iou = intersection / union if union else 0.0
    overlay = np.zeros((*ids.shape, 3), dtype=np.uint8)
    overlay[b00_alpha & ~mhr_silhouette] = (255, 80, 80)
    overlay[mhr_silhouette & ~b00_alpha] = (80, 170, 255)
    overlay[b00_alpha & mhr_silhouette] = (245, 220, 80)
    paths["b00_mhr_overlay"] = save_rgb("yaw+000-pitch+00_b00-vs-mhr-silhouette-overlay.png", overlay)
    paths["b00"] = B00
    contact_path = OUT / "yaw+000-pitch+00_mhr-object-id-ownership-contact.png"
    contact([
        ("B00 AUTHORITY (CLOTHED)", B00),
        ("MHR EXACT PART-ID PALETTE", paths["part_id_palette"]),
        ("CORE BODY GEOMETRY", paths["core_body"]),
        ("HANDS: LEFT RED / RIGHT GREEN", paths["hands_physical_side"]),
        ("FEET: LEFT PURPLE / RIGHT GOLD", paths["feet_physical_side"]),
        ("AMBIGUOUS JOINT BOUNDARIES", paths["ambiguous_joint_boundaries"]),
        (f"B00 vs MHR SILHOUETTE IoU={iou:.4f}", paths["b00_mhr_overlay"]),
        ("GARMENT MASK: ABSENT IN MHR", paths["garment"]),
    ], contact_path)
    paths["contact"] = contact_path

    admission = json.loads(MHR_ADMISSION.read_text(encoding="utf-8"))
    part_manifest = json.loads(PART_MANIFEST.read_text(encoding="utf-8"))
    report = {
        "schema": "mohan.yaw000.mhr_object_id_ownership_control",
        "version": 1,
        "status": "PARTIAL_PASS_GEOMETRY_IDS_BLOCKED_FOR_GARMENT_AND_SHOES",
        "promotion_allowed": False,
        "formal_assets_modified": False,
        "no_color_heuristics_used": True,
        "admission": {
            "mhr_geometry": "ALLOW_APACHE_2_0",
            "ufbx_parser": "ALLOW_MIT_ALTERNATIVE_A",
            "source_admission_status": admission.get("status"),
            "mhr_fbx": {"path": str(MHR_FBX), "sha256": sha256(MHR_FBX)},
            "mhr_license": {"path": str(MHR_LICENSE), "sha256": sha256(MHR_LICENSE)},
        },
        "derivation": {
            "method": part_manifest.get("derivation"),
            "part_id_source": {"path": str(PART_ID), "sha256": sha256(PART_ID)},
            "part_manifest": {"path": str(PART_MANIFEST), "sha256": sha256(PART_MANIFEST)},
            "part_qa": {"path": str(PART_QA), "sha256": sha256(PART_QA)},
            "present_part_ids": present_ids,
        },
        "capabilities": {
            "core_body": "AVAILABLE_EXACT_SKIN_WEIGHT_DERIVED_CONTROL",
            "hand_left": "AVAILABLE_EXACT_PHYSICAL_SIDE_CONTROL",
            "hand_right": "AVAILABLE_EXACT_PHYSICAL_SIDE_CONTROL",
            "foot_left": "AVAILABLE_EXACT_ANATOMICAL_FOOT_CONTROL",
            "foot_right": "AVAILABLE_EXACT_ANATOMICAL_FOOT_CONTROL",
            "shoe_left": "BLOCKED_NO_SHOE_GEOMETRY_OR_SHOE_OBJECT_ID",
            "shoe_right": "BLOCKED_NO_SHOE_GEOMETRY_OR_SHOE_OBJECT_ID",
            "garment": "BLOCKED_MHR_SOURCE_HAS_NO_GARMENT_SURFACE_OR_GARMENT_OBJECT_ID",
        },
        "truth_boundaries": [
            "These controls belong to candidate3 MHR geometry, not B00 pixels.",
            "MHR foot IDs are anatomy and must not be renamed shoe IDs.",
            "The zero garment mask proves absence in this MHR source, not garment segmentation of B00.",
            "ID 255 contains ambiguous joint-boundary faces and requires reviewed ownership resolution.",
        ],
        "b00_registration_check": {
            "silhouette_iou": iou,
            "b00_alpha_pixels": int(b00_alpha.sum()),
            "mhr_silhouette_pixels": int(mhr_silhouette.sum()),
            "registered_for_direct_b00_pixel_extraction": False,
        },
        "missing_for_full_contract": [
            "A garment-bearing geometry file with named outerwear/innerwear/skirt/sleeve objects and matching skin weights.",
            "Separate left/right shoe meshes or shoe object-ID masks; anatomical foot IDs are insufficient.",
            "A reviewed transfer/registration map from candidate3 MHR projection to B00 art pixels.",
            "A resolver for ID 255 ambiguous joint faces before formal ownership masks.",
        ],
        "outputs": {name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()},
        "pixel_counts": {name: int(mask.sum()) for name, mask in masks.items()},
    }
    report_path = OUT / "yaw000-mhr-object-id-ownership-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "silhouette_iou": iou, "part_ids": present_ids, "report": str(report_path), "contact": str(contact_path)}, ensure_ascii=False))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
