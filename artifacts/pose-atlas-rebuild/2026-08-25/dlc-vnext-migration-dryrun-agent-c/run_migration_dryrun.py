from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[4]
SOURCE_DIR = PROJECT / "assets" / "pose-atlas" / "v4-layered"
SOURCE_MANIFEST = SOURCE_DIR / "layer_manifest.json"
OUT_DIR = Path(__file__).resolve().parent
VNEXT_DIR = OUT_DIR.parent / "dlc-manifest-vnext-spec-agent-c"
VNEXT_SPEC = VNEXT_DIR / "ownership-mask-spec.json"

FACE_LAYERS = [
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right",
]
HAIR_LAYERS = ["hair_back", "hair_left", "hair_right"]
RETAINABLE_LAYERS = FACE_LAYERS + HAIR_LAYERS
MIGRATION_LAYERS = ["body", "sleeve_left", "sleeve_right", "ornament"]
EXPECTED_LAYERS = FACE_LAYERS + ["body"] + HAIR_LAYERS + [
    "sleeve_left", "sleeve_right", "ornament"
]
MISSING_VNEXT = [
    "core_skin", "body_geometry", "hand_left", "hand_right", "shoe_left",
    "shoe_right", "outfit_outer", "outfit_inner", "outfit_skirt",
    "outfit_sleeve_left", "outfit_sleeve_right", "ownership_masks",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def inspect_rgba(path: Path) -> tuple[dict[str, object], Image.Image]:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    array = np.asarray(image)
    alpha = array[:, :, 3]
    visible = alpha > 0
    rgb = array[:, :, :3].astype(np.int16)
    blue = visible & (rgb[:, :, 2] >= rgb[:, :, 0] + 12) & (
        rgb[:, :, 2] >= rgb[:, :, 1] + 4
    )
    skin = visible & (rgb[:, :, 0] >= 95) & (rgb[:, :, 0] >= rgb[:, :, 1] + 6) & (
        rgb[:, :, 1] >= rgb[:, :, 2] - 5
    )
    rows = np.indices(alpha.shape)[0]
    lower = visible & (rows >= 900)
    metrics = {
        "file": path.name,
        "sha256": sha256(path),
        "mode": "RGBA",
        "dimensions": [image.width, image.height],
        "visible_alpha_pixels": int(visible.sum()),
        "blue_pixel_proxy": int(blue.sum()),
        "skin_pixel_proxy": int(skin.sum()),
        "visible_pixels_y_gte_900": int(lower.sum()),
    }
    return metrics, image


def add_decision(metrics: dict[str, object], status: str, reason: str) -> dict[str, object]:
    return {**metrics, "migration_status": status, "reason": reason}


def make_thumb(image: Image.Image, width: int = 180, height: int = 270) -> Image.Image:
    background = Image.new("RGBA", image.size, (35, 39, 44, 255))
    background.alpha_composite(image)
    background.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), (27, 30, 34))
    x = (width - background.width) // 2
    y = (height - background.height) // 2
    canvas.paste(background.convert("RGB"), (x, y))
    return canvas


def build_contact(rows: list[tuple[str, dict[str, Image.Image]]], path: Path) -> None:
    cell_w, image_h, label_h = 190, 270, 54
    columns = ["body", "sleeve_left", "sleeve_right", "ornament"]
    header_h = 48
    sheet = Image.new(
        "RGB", (cell_w * (len(columns) + 1), header_h + len(rows) * (image_h + label_h)),
        (25, 28, 32),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((8, 15), "VIEW / READ-ONLY MIGRATION DRY-RUN", fill=(245, 245, 245), font=font)
    for index, name in enumerate(columns, 1):
        draw.text((index * cell_w + 8, 15), name, fill=(245, 245, 245), font=font)
    decisions = {
        "body": "REDO: garment+shoe welded",
        "sleeve_left": "SPLIT: hand+fabric welded",
        "sleeve_right": "SPLIT: hand+fabric welded",
        "ornament": "VERIFY/SPLIT physical ownership",
    }
    for row_index, (view_id, images) in enumerate(rows):
        top = header_h + row_index * (image_h + label_h)
        draw.text((8, top + 10), view_id, fill=(255, 214, 102), font=font)
        draw.text((8, top + 31), "NOT PROMOTABLE", fill=(255, 104, 104), font=font)
        for col_index, name in enumerate(columns, 1):
            thumb = make_thumb(images[name], cell_w - 10, image_h)
            sheet.paste(thumb, (col_index * cell_w + 5, top))
            draw.text(
                (col_index * cell_w + 7, top + image_h + 6),
                decisions[name], fill=(255, 152, 152), font=font,
            )
    sheet.save(path, format="PNG", optimize=True)


def main() -> int:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    views = manifest.get("views", [])
    errors: list[str] = []
    if len(views) != 24:
        errors.append(f"expected 24 views, found {len(views)}")
    results: list[dict[str, object]] = []
    contact_ids = {
        "yaw-180-pitch+00", "yaw-090-pitch+00", "yaw+000-pitch+00",
        "yaw+045-pitch+00", "yaw+090-pitch+00", "yaw+165-pitch+00",
    }
    contact_rows: list[tuple[str, dict[str, Image.Image]]] = []
    all_source_files: list[Path] = []
    for view in views:
        view_id = view["view_id"]
        layer_map = {entry["layer"]: entry for entry in view.get("layers", [])}
        if set(layer_map) != set(EXPECTED_LAYERS):
            errors.append(f"{view_id}: layer set mismatch")
            continue
        decisions: dict[str, object] = {}
        contact_images: dict[str, Image.Image] = {}
        retainable_visible = 0
        for layer_name in EXPECTED_LAYERS:
            source_path = SOURCE_DIR / layer_map[layer_name]["file"]
            if not source_path.is_file():
                errors.append(f"{view_id}: missing {source_path.name}")
                continue
            all_source_files.append(source_path)
            metrics, image = inspect_rgba(source_path)
            if metrics["dimensions"] != [1024, 1536]:
                errors.append(f"{view_id}/{layer_name}: wrong dimensions")
            if layer_name in RETAINABLE_LAYERS:
                retainable_visible += int(metrics["visible_alpha_pixels"])
                decisions[layer_name] = add_decision(
                    metrics,
                    "STRUCTURALLY_RETAINABLE_PENDING_ART_AND_OWNERSHIP_QA",
                    "Layer ownership can be mapped without claiming identity or art acceptance.",
                )
            elif layer_name == "body":
                decisions[layer_name] = add_decision(
                    metrics,
                    "REDO_REQUIRED_GARMENT_AND_SHOE_WELDED",
                    "Legacy body contains blue/white garment and lower skirt/shoe pixels; it cannot become core_skin.",
                )
            elif layer_name.startswith("sleeve_"):
                decisions[layer_name] = add_decision(
                    metrics,
                    "SPLIT_REQUIRED_HAND_AND_FABRIC_WELDED",
                    "Legacy sleeve layer mixes hand pixels with garment fabric; vNext hand alias must contain no fabric.",
                )
            else:
                decisions[layer_name] = add_decision(
                    metrics,
                    "VERIFY_OR_SPLIT_REQUIRED_FIXED_VS_REPLACEABLE_ORNAMENT",
                    "No typed ownership mask proves that only the fixed physical-side hairpin is present.",
                )
            if layer_name in MIGRATION_LAYERS and view_id in contact_ids:
                contact_images[layer_name] = image
        results.append({
            "view_id": view_id,
            "migration_ready": False,
            "promotion_allowed": False,
            "structurally_retainable_layer_count": len(RETAINABLE_LAYERS),
            "structurally_retainable_visible_alpha_pixel_sum_non_union": retainable_visible,
            "redo_or_split_current_layer_count": len(MIGRATION_LAYERS),
            "missing_vnext_assets": MISSING_VNEXT,
            "decisions": decisions,
        })
        if view_id in contact_ids:
            contact_rows.append((view_id, contact_images))
    if len(all_source_files) != 600:
        errors.append(f"expected 600 source PNG references, found {len(all_source_files)}")
    output = {
        "schema": "mohan.pose_atlas.dlc_vnext_migration_dryrun",
        "version": 1,
        "generated_by": "artifact-only read-only migration audit",
        "status": "BLOCKED_MIGRATION",
        "promotion_allowed": False,
        "formal_assets_modified": False,
        "meaning_of_retainable": "Ownership structure can be mapped; this is not an identity, art, alpha, or formal acceptance PASS.",
        "source": {
            "manifest": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(SOURCE_MANIFEST),
            "referenced_png_count": len(all_source_files),
        },
        "vnext_contract": {
            "ownership_mask_spec": str(VNEXT_SPEC),
            "ownership_mask_spec_sha256": sha256(VNEXT_SPEC),
            "fixture_is_non_production": True,
        },
        "summary": {
            "view_count": len(results),
            "views_migration_ready": 0,
            "views_blocked": len(results),
            "per_view_structurally_retainable_layers": len(RETAINABLE_LAYERS),
            "per_view_redo_or_split_current_layers": len(MIGRATION_LAYERS),
            "global_blockers": [
                "body is not skin-only and includes garments/shoes",
                "sleeve layers mix hands and garment fabric",
                "independent core_skin/body_geometry/hands/shoes are absent",
                "typed ownership masks and DLC garment slots are absent",
                "ornament lacks fixed-vs-replaceable ownership proof",
            ],
        },
        "validation_errors": errors,
        "views": results,
    }
    json_path = OUT_DIR / "migration-dryrun.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_contact(contact_rows, OUT_DIR / "migration-contact.png")
    print(json.dumps({
        "status": output["status"],
        "views": len(results),
        "source_pngs": len(all_source_files),
        "validation_errors": errors,
        "json": str(json_path),
        "contact": str(OUT_DIR / "migration-contact.png"),
    }, ensure_ascii=False))
    return 4 if output["status"] == "BLOCKED_MIGRATION" or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
