from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
SOURCE = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
SOURCE_MASKS = SOURCE / "masks"
OUT = HERE / "masks"
CONTACTS = HERE / "per-view-contact-sheets"
YAWS = tuple(range(-180, 180, 15))
RIGID_IDS = frozenset(range(1, 15))
SOFT_IDS = frozenset({255})
ALLOWED_IDS = frozenset({0, *RIGID_IDS, *SOFT_IDS})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def colorize(values: tuple[int, ...], size: tuple[int, int]) -> Image.Image:
    palette = {0: (0, 0, 0), **{part: (50 + part * 13 % 190, 70 + part * 31 % 180, 90 + part * 47 % 160) for part in RIGID_IDS}, 255: (255, 0, 255)}
    image = Image.new("RGB", size)
    image.putdata([palette[value] for value in values])
    return image


def panel(title: str, image: Image.Image) -> Image.Image:
    thumb = image.resize((256, 384), Image.Resampling.NEAREST)
    result = Image.new("RGB", (256, 408), (245, 245, 245))
    result.paste(thumb, (0, 24))
    ImageDraw.Draw(result).text((5, 5), title, fill=(0, 0, 0))
    return result


def main() -> int:
    OUT.mkdir(exist_ok=True)
    CONTACTS.mkdir(exist_ok=True)
    source_manifest = json.loads((SOURCE / "skin-weight-part-manifest.json").read_text(encoding="utf-8"))
    if source_manifest["status"] != "PASS_FOR_CONTROL_MASKS":
        raise ValueError("source part-ID gate is not PASS_FOR_CONTROL_MASKS")
    views = []
    master_panels = []
    for yaw in YAWS:
        view_id = f"yaw{yaw:+04d}-pitch+00"
        source_path = SOURCE_MASKS / f"{view_id}_part-id.png"
        source = Image.open(source_path)
        source.load()
        if source.mode != "L" or source.size != (1024, 1536):
            raise ValueError(f"invalid source mask: {view_id}")
        values = tuple(source.get_flattened_data())
        unexpected = set(values) - ALLOWED_IDS
        if unexpected:
            raise ValueError(f"unsupported part IDs {unexpected}: {view_id}")
        rigid_values = tuple(255 if value in RIGID_IDS else 0 for value in values)
        soft_values = tuple(255 if value in SOFT_IDS else 0 for value in values)
        intersection = sum(1 for rigid, soft in zip(rigid_values, soft_values, strict=True) if rigid and soft)
        union_mismatch = sum(1 for value, rigid, soft in zip(values, rigid_values, soft_values, strict=True) if (value != 0) != bool(rigid or soft))
        rigid_pixels = sum(1 for value in rigid_values if value)
        soft_pixels = sum(1 for value in soft_values if value)
        foreground_pixels = sum(1 for value in values if value)
        if intersection != 0 or union_mismatch != 0 or rigid_pixels + soft_pixels != foreground_pixels:
            raise ValueError(f"mask partition invariant failed: {view_id}")
        rigid = Image.new("L", source.size); rigid.putdata(rigid_values)
        soft = Image.new("L", source.size); soft.putdata(soft_values)
        rigid_path = OUT / f"{view_id}_rigid.png"
        soft_path = OUT / f"{view_id}_soft.png"
        rigid.save(rigid_path, optimize=False)
        soft.save(soft_path, optimize=False)
        triptych = Image.new("RGB", (768, 408), (255, 255, 255))
        triptych.paste(panel(f"{view_id} part-ID", colorize(values, source.size)), (0, 0))
        triptych.paste(panel("rigid IDs 1-14", rigid.convert("RGB")), (256, 0))
        soft_rgb = Image.new("RGB", source.size); soft_rgb.putdata([(255, 0, 255) if value else (0, 0, 0) for value in soft_values])
        triptych.paste(panel("soft ID 255", soft_rgb), (512, 0))
        contact_path = CONTACTS / f"{view_id}_contact-sheet.png"
        triptych.save(contact_path)
        master_panels.append(panel(view_id, colorize(values, source.size)))
        views.append({
            "view_id": view_id,
            "source": {"path": str(source_path.relative_to(PROJECT)).replace("\\", "/"), "sha256": digest(source_path), "mode": "L", "size": [1024, 1536]},
            "rigid": {"path": str(rigid_path.relative_to(HERE)).replace("\\", "/"), "sha256": digest(rigid_path), "mode": "L", "size": [1024, 1536], "foreground_pixels": rigid_pixels},
            "soft": {"path": str(soft_path.relative_to(HERE)).replace("\\", "/"), "sha256": digest(soft_path), "mode": "L", "size": [1024, 1536], "foreground_pixels": soft_pixels},
            "contact_sheet": {"path": str(contact_path.relative_to(HERE)).replace("\\", "/"), "sha256": digest(contact_path)},
            "qa": {"intersection_pixels": intersection, "union_mismatch_pixels": union_mismatch, "source_foreground_pixels": foreground_pixels, "partition_sum_pixels": rigid_pixels + soft_pixels}
        })
    master = Image.new("RGB", (6 * 256, 4 * 408), (255, 255, 255))
    for index, image in enumerate(master_panels):
        master.paste(image, ((index % 6) * 256, (index // 6) * 408))
    master_path = HERE / "24-view-geometry-part-contact-sheet.png"
    master.save(master_path)
    manifest = {
        "schema": "mohan.pose-atlas.geometry-rigid-soft-mask-pack.v1",
        "status": "GEOMETRY_CONTROL_ONLY_NOT_SEMANTIC_ART_SEGMENTATION",
        "canvas": {"width": 1024, "height": 1536, "mode": "L", "offset": [0, 0]},
        "source_contract": {"manifest": str((SOURCE / "skin-weight-part-manifest.json").relative_to(PROJECT)).replace("\\", "/"), "sha256": digest(SOURCE / "skin-weight-part-manifest.json")},
        "rules": {"background": {"part_ids": [0], "mask_value": 0}, "rigid": {"part_ids": sorted(RIGID_IDS), "mask_value": 255, "meaning": "interior triangles whose three vertices share one skin-weight-derived body part"}, "soft": {"part_ids": [255], "mask_value": 255, "meaning": "joint/part boundary triangles or low-confidence vertex assignment"}},
        "compose_usage": {"allowed": "geometry-only deformation control reference for the 25-layer pipeline", "forbidden_claims": ["clothing segmentation", "hair segmentation", "facial-feature segmentation", "final-art layer ownership", "pixel-perfect anatomical ground truth"]},
        "views": views,
        "summary": {"view_count": len(views), "mask_file_count": len(views) * 2, "per_view_contact_sheet_count": len(views), "all_intersections_zero": all(view["qa"]["intersection_pixels"] == 0 for view in views), "all_unions_exact": all(view["qa"]["union_mismatch_pixels"] == 0 for view in views), "master_contact_sheet_sha256": digest(master_path)}
    }
    (HERE / "geometry-rigid-soft-mask-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", **manifest["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
