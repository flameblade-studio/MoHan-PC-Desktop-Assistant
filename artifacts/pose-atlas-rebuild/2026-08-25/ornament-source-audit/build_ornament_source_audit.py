from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
REFS = Path(r"C:\Users\hitos\OneDrive\桌面\墨寒桌面語音互動虛擬女友2026.07.28開始開發\2026iThome鐵人賽參賽插圖")
OUT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def image_record(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        return {
            "path": str(path), "sha256": sha256(path), "dimensions": list(image.size),
            "mode": image.mode, "has_alpha": alpha is not None,
            "alpha_extrema": list(alpha.getextrema()) if alpha else None,
            "alpha_bbox": list(alpha.getbbox()) if alpha and alpha.getbbox() else None,
        }


def preview(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
    checker = Image.new("RGB", rgba.size, (38, 43, 48))
    draw = ImageDraw.Draw(checker)
    cell = 32
    for y in range(0, rgba.height, cell):
        for x in range(0, rgba.width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(72, 78, 84))
    checker.paste(rgba, mask=rgba.getchannel("A"))
    checker.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (28, 32, 36))
    canvas.paste(checker, ((size[0] - checker.width) // 2, (size[1] - checker.height) // 2))
    return canvas


def main() -> int:
    committed_clean = [
        REPO / "assets/expressions/layered/front_ornament.png",
        REPO / "assets/expressions/layered/cheek_ornament.png",
        REPO / "assets/expressions/layered/lean_ornament.png",
    ]
    old_fullbody = REPO / "assets/pose-atlas/v4-layered/yaw+030-pitch+00_ornament.png"
    extracted = REPO / "artifacts/pose-atlas-rebuild/2026-08-25/mhr-neutral-body-smoke-agent-b/yaw030-ornament-layer-isolation-attempt2-agent-b/yaw+030-pitch+00_ornament.candidate.png"
    extracted_mask = REPO / "artifacts/pose-atlas-rebuild/2026-08-25/mhr-neutral-body-smoke-agent-b/yaw030-candidate-v2-checker-hybrid-refine-v3-attempt2-agent-b/candidate-ornament-mask.png"
    evidence = REPO / "docs/release-evidence/layered-full-body-semantic-audit/layered-full-body-semantic-audit.json"
    assets_license = REPO / "ASSETS-LICENSE.md"
    for required in [*committed_clean, old_fullbody, extracted, extracted_mask, evidence, assets_license]:
        if not required.is_file():
            raise FileNotFoundError(required)

    ref_images = sorted(path for path in REFS.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    ref_records = [image_record(path) for path in ref_images]
    candidates = []
    for path in committed_clean:
        record = image_record(path)
        record.update({
            "classification": "CLEAN_INDEPENDENT_HALF_BODY_ORNAMENT",
            "content": "blue flower and double dangle only; no face or garment pixels observed",
            "yaw030_safe_use": "REFERENCE_OR_REPROJECT_ONLY",
            "reason": "clean source, but 1254x1254 half-body pose projection is not a calibrated +030 full-body layer",
            "source_status": "committed repository animation layer", "license_status": "MIT", "license_evidence": str(assets_license),
        })
        candidates.append(record)

    record = image_record(extracted)
    record.update({
        "classification": "YAW030_EXACT_RGB_MASK_EXTRACTION_CANDIDATE",
        "content": "silver crown/hairpins plus blue flower and double dangle extracted from current +030 raw",
        "yaw030_safe_use": "TECHNICALLY_ALIGNED_BUT_FORMAL_USE_BLOCKED",
        "reason": "full-canvas alignment and exact raw RGB are useful, but manual art gate and artifact-level provenance remain pending",
        "source_status": "derived artifact; not a committed source asset", "license_status": "UNRECORDED_FOR_THIS_ARTIFACT", "license_evidence": None,
    })
    candidates.append(record)
    record = image_record(extracted_mask)
    record.update({
        "classification": "YAW030_BINARY_MASK_CANDIDATE", "content": "candidate ornament mask only",
        "yaw030_safe_use": "MASK_QA_ONLY_PENDING_ART_REVIEW",
        "reason": "mask is aligned but is not an independent visual source or object-ID ground truth",
        "source_status": "derived artifact", "license_status": "NOT_APPLICABLE_TO_MASK_LOGIC; SOURCE_IMAGE_PROVENANCE_PENDING", "license_evidence": None,
    })
    candidates.append(record)
    record = image_record(old_fullbody)
    record.update({
        "classification": "REJECT_FACE_CONTAMINATION", "content": "ornament layer contains most of a face", "yaw030_safe_use": "NO",
        "reason": "existing semantic audit reports ornament_contains_face; current file is also modified in dirty worktree",
        "source_status": "committed path but current bytes modified", "license_status": "MIT path scope, unusable on semantic grounds",
        "license_evidence": str(assets_license), "semantic_evidence": str(evidence),
    })
    candidates.append(record)

    report = {
        "schema": "mohan.ornament-source-audit.v1", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_NO_FORMALLY_READY_YAW030_COMPLETE_ORNAMENT_SOURCE", "source_files_modified": False,
        "downloads_performed": False, "banned_components_used": [],
        "findings": {
            "clean_committed_halfbody_source_found": True,
            "complete_crown_hairpin_blue_flower_double_dangle_yaw030_source_found": False,
            "aligned_yaw030_extraction_candidate_found": True, "aligned_yaw030_candidate_formally_approved": False,
            "old_v4_yaw030_layer_safe": False,
        },
        "candidates": candidates,
        "ironman_reference_scan": {
            "root": str(REFS), "image_count": len(ref_records),
            "rgba_count": sum(bool(item["has_alpha"]) for item in ref_records),
            "classification": "SCENE_AND_IDENTITY_REFERENCE_ONLY", "standalone_ornament_or_object_id_found_by_file_structure": False,
            "reason": "no filename-level ornament/mask/object-ID assets; the only RGBA file spans almost the whole frame and is not a standalone ornament",
            "files": ref_records,
        },
        "required_next_gate": [
            "manual visual approval of the aligned +030 extraction on four backgrounds",
            "record explicit source/provenance for the +030 generated raw and derivative",
            "verify crown, hairpins, blue flower and both dangles without hair/skin contamination",
        ],
    }
    report_path = OUT / "ornament-source-audit.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    panels = [*committed_clean, extracted, extracted_mask, old_fullbody]
    labels = ["MIT clean: front blue flower + double dangle", "MIT clean: cheek pose", "MIT clean: lean pose", "+030 extraction: aligned, provenance/art pending", "+030 mask: not object-ID ground truth", "REJECT: old v4 ornament contains face"]
    sheet = Image.new("RGB", (1800, 1320), (24, 28, 32)); draw = ImageDraw.Draw(sheet); font = ImageFont.load_default()
    draw.text((24, 18), "MoHan ornament source audit - existing files only", fill=(245, 245, 245), font=font)
    draw.text((24, 38), "No mirror, download, generation, debackgrounding or source modification", fill=(255, 190, 80), font=font)
    for index, (path, label) in enumerate(zip(panels, labels)):
        col, row = index % 3, index // 3; x, y = 24 + col * 592, 72 + row * 610
        sheet.paste(preview(path, (560, 540)), (x, y + 28)); draw.text((x, y), label, fill=(235, 235, 235), font=font)
    contact_path = OUT / "ornament-source-contact-sheet.jpg"; sheet.save(contact_path, quality=94)
    report["outputs"] = {"contact_sheet": {"path": str(contact_path), "sha256": sha256(contact_path)}}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path), "contact_sheet": str(contact_path)}, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
