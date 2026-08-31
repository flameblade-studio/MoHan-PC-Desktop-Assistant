from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[4]
SOURCE = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-24/mother-views/yaw+000-pitch+00.approved-rgba.png"
OUT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rectangle(shape: tuple[int, int], xyxy: tuple[int, int, int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    x0, y0, x1, y1 = xyxy
    mask[y0:y1, x0:x1] = True
    return mask


def rgba_layer(source: np.ndarray, mask: np.ndarray) -> np.ndarray:
    result = np.zeros_like(source)
    result[mask] = source[mask]
    return result


def save_rgba(name: str, array: np.ndarray) -> Path:
    path = OUT / name
    Image.fromarray(array, "RGBA").save(path, optimize=True)
    return path


def save_mask(name: str, mask: np.ndarray) -> Path:
    path = OUT / name
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path, optimize=True)
    return path


def thumb(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    bg = Image.new("RGBA", image.size, (35, 39, 44, 255))
    bg.alpha_composite(image)
    bg.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (26, 29, 33))
    canvas.paste(bg.convert("RGB"), ((size[0] - bg.width) // 2, (size[1] - bg.height) // 2))
    return canvas


def build_contact(entries: list[tuple[str, Path]], path: Path) -> None:
    cell_w, cell_h, label_h, columns = 180, 270, 42, 4
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (22, 25, 29))
    draw, font = ImageDraw.Draw(sheet), ImageFont.load_default()
    for index, (label, source) in enumerate(entries):
        col, row = index % columns, index // columns
        x, y = col * cell_w, row * (cell_h + label_h)
        sheet.paste(thumb(Image.open(source), (cell_w - 8, cell_h)), (x + 4, y))
        draw.text((x + 5, y + cell_h + 5), label, fill=(245, 245, 245), font=font)
        if "HEURISTIC" in label or "UNRESOLVED" in label:
            draw.text((x + 5, y + cell_h + 21), "NOT PRODUCTION", fill=(255, 92, 92), font=font)
    sheet.save(path, optimize=True)


def main() -> int:
    raw = np.asarray(Image.open(SOURCE).convert("RGBA")).copy()
    clean = raw.copy()
    alpha = clean[:, :, 3]
    transparent = alpha == 0
    transparent_rgb_nonzero = int(np.any(clean[:, :, :3] != 0, axis=2)[transparent].sum())
    clean[transparent, :3] = 0
    visible = alpha > 0
    rgb = clean[:, :, :3].astype(np.int16)
    height, width = alpha.shape

    # Weak candidate heuristics only. They are never accepted as semantic truth.
    skin_chroma = (rgb[:, :, 0] >= 90) & (rgb[:, :, 0] >= rgb[:, :, 1] + 4) & (rgb[:, :, 1] >= rgb[:, :, 2] - 8)
    rois = {
        "core_skin_visible": (430, 125, 595, 390),
        "hand_left": (225, 735, 305, 860),
        "hand_right": (720, 735, 805, 860),
        "shoe_left": (395, 1365, 490, 1495),
        "shoe_right": (525, 1365, 625, 1495),
    }
    masks: dict[str, np.ndarray] = {}
    masks["core_skin_visible"] = visible & skin_chroma & rectangle((height, width), rois["core_skin_visible"])
    occupied = masks["core_skin_visible"].copy()
    for name in ("hand_left", "hand_right"):
        masks[name] = visible & skin_chroma & rectangle((height, width), rois[name]) & ~occupied
        occupied |= masks[name]
    for name in ("shoe_left", "shoe_right"):
        masks[name] = visible & rectangle((height, width), rois[name]) & ~occupied
        occupied |= masks[name]
    blue = (rgb[:, :, 2] >= rgb[:, :, 0] + 10) & (rgb[:, :, 2] >= rgb[:, :, 1] + 3)
    neutral_light = (rgb.min(axis=2) >= 135) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 60)
    garment_region = rectangle((height, width), (205, 310, 820, 1415))
    masks["garment_ownership"] = visible & garment_region & (blue | neutral_light) & ~occupied
    occupied |= masks["garment_ownership"]
    masks["unresolved_residual"] = visible & ~occupied

    membership = sum(mask.astype(np.uint8) for mask in masks.values())
    overlap_pixels = int((membership > 1).sum())
    unassigned_visible_pixels = int((visible & (membership == 0)).sum())
    paths: dict[str, Path] = {}
    paths["sanitized_source"] = save_rgba("yaw+000-pitch+00.b00-transparent-rgb-clean.staging.png", clean)
    for name, mask in masks.items():
        paths[name] = save_rgba(f"yaw+000-pitch+00.{name}.heuristic-candidate-rgba.png", rgba_layer(clean, mask))
        paths[f"{name}_mask"] = save_mask(f"yaw+000-pitch+00.{name}.heuristic-candidate-mask.png", mask)

    recomposed = np.zeros_like(clean)
    for mask in masks.values():
        recomposed[mask] = clean[mask]
    paths["recomposed"] = save_rgba("yaw+000-pitch+00.heuristic-partition-recomposed.png", recomposed)
    diff_clean = np.abs(clean.astype(np.int16) - recomposed.astype(np.int16)).astype(np.uint8)
    paths["diff_vs_sanitized"] = save_rgba("yaw+000-pitch+00.diff-vs-sanitized.png", diff_clean)
    diff_raw = np.abs(raw.astype(np.int16) - recomposed.astype(np.int16)).astype(np.uint8)
    paths["diff_vs_original"] = save_rgba("yaw+000-pitch+00.diff-vs-original-rgba.png", diff_raw)
    diff_clean_pixels = int(np.any(diff_clean != 0, axis=2).sum())
    diff_raw_pixels = int(np.any(diff_raw != 0, axis=2).sum())

    hands_path = save_rgba("yaw+000-pitch+00.hands-combined.preview.png", rgba_layer(clean, masks["hand_left"] | masks["hand_right"]))
    shoes_path = save_rgba("yaw+000-pitch+00.shoes-combined.preview.png", rgba_layer(clean, masks["shoe_left"] | masks["shoe_right"]))
    contact_path = OUT / "yaw+000-pitch+00.ownership-extraction-contact.png"
    build_contact([
        ("B00 CLEAN STAGING", paths["sanitized_source"]),
        ("CORE SKIN VISIBLE HEURISTIC", paths["core_skin_visible"]),
        ("HANDS HEURISTIC", hands_path),
        ("SHOES ROI HEURISTIC", shoes_path),
        ("GARMENT HEURISTIC", paths["garment_ownership"]),
        ("UNRESOLVED RESIDUAL", paths["unresolved_residual"]),
        ("RECOMPOSED", paths["recomposed"]),
        ("DIFF VS SANITIZED", paths["diff_vs_sanitized"]),
    ], contact_path)
    paths["contact"] = contact_path

    report = {
        "schema": "mohan.yaw000.b00.ownership_extraction_prototype",
        "version": 1,
        "status": "FAIL_SEMANTIC_OWNERSHIP_NOT_AUTHORITATIVE",
        "promotion_allowed": False,
        "formal_assets_modified": False,
        "source": {"path": str(SOURCE), "sha256": sha256(SOURCE), "mode": "RGBA", "dimensions": [width, height], "transparent_rgb_nonzero_pixels": transparent_rgb_nonzero},
        "pixel_conservation_gate": {
            "sanitized_rgba_recomposition_exact": diff_clean_pixels == 0,
            "diff_pixels_vs_sanitized_rgba": diff_clean_pixels,
            "diff_pixels_vs_original_rgba": diff_raw_pixels,
            "mask_overlap_pixels": overlap_pixels,
            "unassigned_visible_pixels": unassigned_visible_pixels,
            "explanation": "Original B00 stores non-zero checkerboard RGB under alpha=0; exact alpha composition is tested against a staging-only transparent-RGB-clean copy.",
        },
        "semantic_gate": {
            "passed": False,
            "reasons": [
                "Visible skin and garment candidates use ROI/chroma heuristics, not authoritative semantic segmentation.",
                "A clothed B00 cannot reveal occluded adult body geometry or skin beneath garments.",
                "Embroidery, hair crossings, translucent cloth, hands, and shoes require reviewed ownership masks.",
                "Existing candidate3 controls provide silhouette/depth/normal but no per-part object-ID ownership mask.",
            ],
            "required_existing_or_first_party_inputs": [
                "Manually reviewed first-party B00 ownership mask: core_skin, hair, fixed ornament, hands, shoes, outerwear, innerwear, skirt, sleeves.",
                "Admitted MHR/body render with verified per-part object IDs for occluded core_skin/body_geometry; silhouette/depth/normal alone is insufficient.",
                "BiRefNet is limited to foreground alpha refinement and cannot establish garment/body ownership.",
            ],
        },
        "candidate_pixel_counts": {name: int(mask.sum()) for name, mask in masks.items()},
        "outputs": {name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()},
    }
    report_path = OUT / "ownership-extraction-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "recomposition_exact_vs_sanitized": diff_clean_pixels == 0, "diff_pixels_vs_sanitized": diff_clean_pixels, "diff_pixels_vs_original": diff_raw_pixels, "transparent_rgb_nonzero_pixels_source": transparent_rgb_nonzero, "overlap_pixels": overlap_pixels, "unassigned_visible_pixels": unassigned_visible_pixels, "report": str(report_path), "contact": str(contact_path)}, ensure_ascii=False))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
