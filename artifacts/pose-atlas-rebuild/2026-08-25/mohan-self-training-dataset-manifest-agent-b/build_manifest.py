from __future__ import annotations

import hashlib
import json
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
ITHOME = Path(r"C:\Users\hitos\OneDrive\桌面\墨寒桌面語音互動虛擬女友2026.07.28開始開發\2026iThome鐵人賽參賽插圖")
PROFILE_062 = Path(r"C:\Users\hitos\OneDrive\桌面\墨寒桌面語音互動虛擬女友2026.07.28開始開發\062.png")
AUTHORITIES = (
    ("idle_front", PROJECT / "assets/expressions/idle_front.png"),
    ("idle_lean", PROJECT / "assets/expressions/idle_lean.png"),
    ("idle", PROJECT / "assets/expressions/idle.png"),
    ("B00", PROJECT / "artifacts/pose-atlas-rebuild/2026-08-24/mother-views/yaw+000-pitch+00.approved-rgba.png"),
    ("062", PROFILE_062),
)
FONT = ImageFont.load_default()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dhash(image: Image.Image) -> str:
    gray = ImageOps.grayscale(image).resize((9, 8), Image.Resampling.LANCZOS)
    values = list(gray.get_flattened_data())
    bits = 0
    for row in range(8):
        for column in range(8):
            bits = (bits << 1) | (values[row * 9 + column] > values[row * 9 + column + 1])
    return f"{bits:016X}"


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def record(index: int, source_group: str, name: str, path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
        fingerprint = dhash(image)
    base = {
        "index": index, "source_group": source_group, "name": name,
        "path": str(path), "width": width, "height": height, "mode": mode,
        "sha256": file_hash(path), "dhash64": fingerprint,
    }
    if source_group == "identity_authority":
        return {
            **base,
            "character_label": "mohan_identity_authority",
            "garment_label": "blue-white-default-visible-but-masked-from-identity",
            "angle_label": {"idle_front": "front", "idle_lean": "near-front-lean", "idle": "near-front-lean"}[name],
            "identity_lora": "ADMIT_FACE_HAIR_ORNAMENT_CROP_ONLY",
            "garment_conditioning": "EXCLUDE_THIS_CROP",
            "reason": "Only face, hairstyle and physical ornament identity may enter identity LoRA; garment pixels must be masked/cropped out.",
        }
    if name == "B00":
        return {
            **base, "character_label": "mohan_fullbody_proportion_authority",
            "garment_label": "default-blue-outer-white-inner-authority",
            "angle_label": "front-yaw+000", "identity_lora": "EXCLUDE",
            "garment_conditioning": "ADMIT",
            "reason": "B00 controls full-body proportion and the default outfit, not the face identity standard.",
        }
    if name == "062":
        return {
            **base, "character_label": "not-mohan-profile-geometry-reference",
            "garment_label": "irrelevant", "angle_label": "strict-side-profile",
            "identity_lora": "EXCLUDE", "garment_conditioning": "EXCLUDE",
            "reason": "062 is side-profile bone geometry only and must never train MoHan identity.",
        }
    contextual_angles = {
        76: "mixed-contact", 77: "mixed-contact", 78: "near-front",
        79: "front", 80: "near-front-three-quarter", 81: "mixed-contact",
        82: "near-front", 83: "near-front", 84: "front", 85: "front",
        86: "front", 87: "mixed-contact", 88: "mixed-contact",
        89: "mixed-contact", 90: "mixed-contact", 91: "mixed-contact",
        92: "front", 93: "front", 94: "front", 95: "front",
        96: "near-front", 97: "front", 98: "front", 99: "front",
        100: "front", 101: "near-front", 102: "front", 103: "front",
        104: "front", 105: "near-front", 106: "front", 107: "front",
        108: "front", 109: "near-front", 110: "front",
        111: "near-front", 112: "near-front",
    }
    if 76 <= index <= 112:
        return {
            **base, "character_label": "mohan-contextual-auxiliary-unapproved",
            "garment_label": "blue-white-robe-contextual-scene",
            "angle_label": contextual_angles[index],
            "identity_lora": "HOLD_FACE_HAIR_ORNAMENT_CROP_ONLY",
            "garment_conditioning": "HOLD_DLC_CONDITIONING_REVIEW",
            "reason": "Visually recognizable contextual MoHan reference, but not an identity authority. Admit only after per-image identity/provenance review and a crop/mask that excludes clothing, hands, props and scene.",
        }
    if index in {52, 53}:
        return {
            **base, "character_label": "detail-reference-not-identity",
            "garment_label": "default-blue-white-detail",
            "angle_label": "detail-crop",
            "identity_lora": "EXCLUDE",
            "garment_conditioning": "HOLD_DLC_DETAIL_REVIEW",
            "reason": "Detail crop is useful only for garment/hand/shoe review; it cannot train face identity.",
        }
    if index in {33, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 48, 49, 50, 51, 54, 57, 58, 59, 61, 62, 63, 64, 68, 75, 113}:
        return {
            **base, "character_label": "mohan-pipeline-candidate-unapproved",
            "garment_label": "default-blue-white-candidate",
            "angle_label": "front-to-three-quarter-unverified",
            "identity_lora": "EXCLUDE_UNTIL_FORMAL_ART_APPROVAL",
            "garment_conditioning": "HOLD_DLC_CANDIDATE_REVIEW",
            "reason": "Single candidate or crop from the production pipeline; filename and visual plausibility are not authority approval.",
        }
    if index in {114, 115}:
        return {
            **base, "character_label": "no-character-background-only",
            "garment_label": "none", "angle_label": "not-applicable",
            "identity_lora": "EXCLUDE", "garment_conditioning": "EXCLUDE",
            "reason": "Background-only landscape contains no MoHan identity or garment evidence.",
        }
    return {
        **base, "character_label": "nontraining-diagnostic-or-control",
        "garment_label": "mixed-or-not-applicable",
        "angle_label": "mixed-grid-control-or-unverified",
        "identity_lora": "EXCLUDE",
        "garment_conditioning": "EXCLUDE_RAW",
        "reason": "Contact sheet, overlay, geometry render, mask, annotated diagnostic, unrelated body/reference, or multi-image grid; raw use would duplicate or contaminate training.",
    }


def group(records: list[dict[str, object]]) -> tuple[list[list[int]], list[list[int]]]:
    exact = defaultdict(list)
    for item in records:
        exact[str(item["sha256"])].append(int(item["index"]))
    exact_groups = [members for members in exact.values() if len(members) > 1]

    parents = list(range(len(records)))
    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value
    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parents[b] = a
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            if records[left]["sha256"] == records[right]["sha256"]:
                continue
            if records[left]["width"] != records[right]["width"] or records[left]["height"] != records[right]["height"]:
                continue
            if hamming(str(records[left]["dhash64"]), str(records[right]["dhash64"])) <= 4:
                union(left, right)
    candidates = defaultdict(list)
    for offset, item in enumerate(records):
        candidates[find(offset)].append(int(item["index"]))
    near = [members for members in candidates.values() if len(members) > 1]
    return exact_groups, near


def contact(records: list[dict[str, object]]) -> None:
    card_w, card_h, label_h, columns = 180, 180, 34, 8
    rows = (len(records) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * card_w, rows * (card_h + label_h)), (32, 35, 42))
    draw = ImageDraw.Draw(sheet)
    for position, item in enumerate(records):
        with Image.open(Path(str(item["path"]))) as image:
            rgba = image.convert("RGBA")
            white = Image.new("RGBA", rgba.size, "white")
            thumb = Image.alpha_composite(white, rgba).convert("RGB")
            thumb.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
        x = (position % columns) * card_w
        y = (position // columns) * (card_h + label_h)
        sheet.paste(thumb, (x + (card_w - thumb.width) // 2, y + (card_h - thumb.height) // 2))
        draw.rectangle((x, y + card_h, x + card_w, y + card_h + label_h), fill=(20, 23, 29))
        draw.text((x + 5, y + card_h + 4), f"{item['index']:03d} {item['source_group']}", fill="white", font=FONT)
        draw.text((x + 5, y + card_h + 18), str(item["name"])[:25], fill=(200, 205, 215), font=FONT)
    sheet.save(HERE / "indexed-source-contact.png")


def main() -> int:
    paths: list[tuple[str, str, Path]] = []
    for name, path in AUTHORITIES:
        group_name = "identity_authority" if name.startswith("idle") else ("garment_authority" if name == "B00" else "profile_geometry_only")
        paths.append((group_name, name, path))
    for path in sorted(ITHOME.iterdir(), key=lambda value: value.name):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            paths.append(("ithome_context", path.name, path))
    missing = [str(path) for _, _, path in paths if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, ensure_ascii=False))
        return 4
    records = [record(index, group_name, name, path) for index, (group_name, name, path) in enumerate(paths, 1)]
    exact, near = group(records)
    for item in records:
        item["exact_duplicate_group"] = next((f"exact-{i:03d}" for i, members in enumerate(exact, 1) if item["index"] in members), None)
        item["near_duplicate_candidate_group"] = next((f"near-{i:03d}" for i, members in enumerate(near, 1) if item["index"] in members), None)
    contact(records)
    identity_status_counts = defaultdict(int)
    garment_status_counts = defaultdict(int)
    character_label_counts = defaultdict(int)
    for item in records:
        identity_status_counts[str(item["identity_lora"])] += 1
        garment_status_counts[str(item["garment_conditioning"])] += 1
        character_label_counts[str(item["character_label"])] += 1
    manifest = {
        "schema": "mohan.self-training-source-manifest.v1",
        "read_only_sources": True,
        "source_files_copied": False,
        "training_executed": False,
        "policy": {
            "identity_lora": "Only verified MoHan face, hairstyle and physical ornament identity; exclude garments and scene style.",
            "garment_conditioning": "DLC/garment dataset is separate from identity and may use B00/default outfit or reviewed iThome clothing references.",
            "profile_062": "Profile geometry only; excluded from identity and garment training.",
            "dedup": "Exact SHA duplicates collapse to one canonical source. Same-dimension dHash Hamming <=4 is only a near-duplicate candidate and requires visual confirmation; never auto-delete.",
            "split": "All exact/confirmed near duplicates stay in the same train/validation group to prevent leakage.",
        },
        "counts": {"total": len(records), "identity_authority_crop_only": 3, "garment_authority": 1, "profile_geometry_only": 1, "ithome_sources": len(records) - 5, "exact_duplicate_groups": len(exact), "near_duplicate_candidate_groups": len(near), "identity_status": dict(sorted(identity_status_counts.items())), "garment_status": dict(sorted(garment_status_counts.items())), "character_labels": dict(sorted(character_label_counts.items()))},
        "exact_duplicate_groups": [{"id": f"exact-{i:03d}", "indices": members, "canonical_index": min(members)} for i, members in enumerate(exact, 1)],
        "near_duplicate_candidate_groups": [{"id": f"near-{i:03d}", "indices": members, "action": "HOLD_VISUAL_CONFIRMATION"} for i, members in enumerate(near, 1)],
        "records": records,
    }
    (HERE / "dataset-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = (
        "index", "source_group", "name", "path", "width", "height", "mode",
        "sha256", "dhash64", "exact_duplicate_group",
        "near_duplicate_candidate_group", "character_label", "garment_label",
        "angle_label", "identity_lora", "garment_conditioning", "reason",
    )
    with (HERE / "dataset-manifest.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({"status": "PASS_MANIFEST_BUILT", **manifest["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
