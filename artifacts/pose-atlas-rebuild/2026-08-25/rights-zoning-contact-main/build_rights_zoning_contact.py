from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
OUT = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/rights-zoning-contact-main"
PROVENANCE = (
    PROJECT
    / "artifacts/pose-atlas-rebuild/2026-08-25/image-input-production-admission"
    / "candidate-image-provenance-manifest-v3.json"
)
OWNER_AUDIT = (
    PROJECT
    / "artifacts/pose-atlas-rebuild/2026-08-25/owner12-pixel-provenance-audit-main"
    / "OWNER12-PIXEL-PROVENANCE-AUDIT.json"
)

GREEN = (53, 209, 111)
CYAN = (46, 177, 231)
RED = (236, 74, 74)
BG = (22, 25, 29)
CARD = (34, 39, 45)
WHITE = (245, 247, 250)
MUTED = (184, 193, 203)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msjhbd.ttc" if bold else r"C:\Windows\Fonts\msjh.ttc"),
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def provenance_record(index: dict[str, Any], path: str) -> dict[str, Any]:
    result = next((record for record in index["records"] if record["path"] == path), None)
    if result is None:
        raise RuntimeError(f"PROVENANCE_RECORD_MISSING:{path}")
    return result


def make_record(
    *,
    source: dict[str, Any],
    source_id: str,
    display_class: str,
    color: tuple[int, int, int],
    identity_reference_allowed: bool,
    training_pixels_allowed: bool,
    training_status: str,
    scope_note: str,
) -> dict[str, Any]:
    path = Path(source["path"])
    actual = sha256(path)
    if actual != source["sha256"]:
        raise RuntimeError(f"SOURCE_HASH_MISMATCH:{source_id}")
    return {
        "source_id": source_id,
        "path": str(path),
        "sha256": actual,
        "display_class": display_class,
        "display_color_rgb": list(color),
        "identity_reference_allowed": identity_reference_allowed,
        "training_pixels_allowed": training_pixels_allowed,
        "training_status": training_status,
        "scope_note": scope_note,
        "authority_class": source.get("authority_class"),
        "license_status": source.get("license_status"),
        "source_license": source.get("source_license"),
        "commercial_formal_png_admission": source.get("commercial_formal_png_admission"),
        "allowed_uses": source.get("allowed_uses", []),
        "prohibited_uses": source.get("prohibited_uses", []),
        "decision_reason": source.get("decision_reason"),
        "owner_visual_approval_used_as_pixel_rights": False,
    }


def ellipsize(value: str, length: int) -> str:
    return value if len(value) <= length else value[: length - 1] + "…"


def build_contact(records: list[dict[str, Any]], output: Path) -> None:
    columns = 4
    card_w, card_h = 390, 520
    gap = 22
    header_h = 190
    rows = (len(records) + columns - 1) // columns
    width = gap + columns * (card_w + gap)
    height = header_h + rows * (card_h + gap) + gap
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((gap, 18), "墨寒 LoRA 像素權利分區（現有來源）", font=font(34, True), fill=WHITE)
    draw.text(
        (gap, 66),
        "綠：像素權利可訓練（仍須獨立來源/資料集閘門）  藍：僅參考，禁止訓練像素  紅：禁止訓練",
        font=font(21),
        fill=MUTED,
    )
    draw.text(
        (gap, 104),
        "Owner visual approval ≠ pixel rights.  Reference-only cards always show TRAINING: NO.",
        font=font(21, True),
        fill=(255, 204, 89),
    )
    draw.text(
        (gap, 142),
        "本圖只分權利用途；不代表 LoRA 已准入、不代表 12 個獨立來源已齊備。",
        font=font(20),
        fill=MUTED,
    )

    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x = gap + column * (card_w + gap)
        y = header_h + row * (card_h + gap)
        color = tuple(record["display_color_rgb"])
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=14, fill=CARD, outline=color, width=6)
        source = Image.open(record["path"]).convert("RGBA")
        checker = Image.new("RGB", (card_w - 28, 330), (91, 96, 102))
        tile = 18
        check_draw = ImageDraw.Draw(checker)
        for yy in range(0, checker.height, tile):
            for xx in range(0, checker.width, tile):
                if (xx // tile + yy // tile) % 2:
                    check_draw.rectangle((xx, yy, xx + tile - 1, yy + tile - 1), fill=(121, 126, 132))
        preview = ImageOps.contain(source, checker.size, Image.Resampling.LANCZOS)
        checker.paste(preview, ((checker.width - preview.width) // 2, (checker.height - preview.height) // 2), preview)
        canvas.paste(checker, (x + 14, y + 14))
        draw.rectangle((x + 14, y + 344, x + card_w - 14, y + 387), fill=color)
        draw.text((x + 26, y + 351), record["display_class"], font=font(21, True), fill=(8, 12, 16))
        draw.text(
            (x + 22, y + 399),
            f"TRAINING: {'YES' if record['training_pixels_allowed'] else 'NO'}",
            font=font(22, True),
            fill=GREEN if record["training_pixels_allowed"] else RED,
        )
        draw.text((x + 22, y + 432), ellipsize(Path(record["path"]).name, 41), font=font(17), fill=WHITE)
        draw.text((x + 22, y + 459), f"SHA {record['sha256'][:16]}…", font=font(15), fill=MUTED)
        draw.text((x + 22, y + 484), ellipsize(record["scope_note"], 46), font=font(15), fill=MUTED)

    canvas.save(output, format="PNG", optimize=True)


def main() -> int:
    provenance = load(PROVENANCE)
    owner_audit = load(OWNER_AUDIT)
    owner_upstreams = {record["sequence"]: record["upstream_source"] for record in owner_audit["records"]}

    records: list[dict[str, Any]] = []
    for name in ["idle_front.png", "idle_lean.png", "idle.png"]:
        path = str(PROJECT / "assets/expressions" / name)
        source = provenance_record(provenance, path)
        records.append(
            make_record(
                source=source,
                source_id=f"repository-{Path(name).stem}",
                display_class="TRAINABLE PIXELS",
                color=GREEN,
                identity_reference_allowed=True,
                training_pixels_allowed=True,
                training_status="RIGHTS_PASS_DATASET_ADMISSION_SEPARATE",
                scope_note="MIT pixel rights; distinct-source admission is separate.",
            )
        )

    b00_path = str(
        PROJECT
        / "artifacts/pose-atlas-rebuild/2026-08-24/mother-views"
        / "yaw+000-pitch+00.approved-rgba.png"
    )
    records.append(
        make_record(
            source=provenance_record(provenance, b00_path),
            source_id="B00-front-full-body",
            display_class="IDENTITY REFERENCE ONLY",
            color=CYAN,
            identity_reference_allowed=True,
            training_pixels_allowed=False,
            training_status="BLOCK_INPUT_RIGHTS_LINEAGE_UNVERIFIED",
            scope_note="Reference only; per-generation input-rights chain incomplete.",
        )
    )

    support_sequences = ["seq03", "seq04", "seq05", "seq06", "seq09", "seq13", "seq14", "seq15", "seq16", "seq17"]
    for sequence in support_sequences:
        path = owner_upstreams[sequence]
        source = provenance_record(provenance, path)
        records.append(
            make_record(
                source=source,
                source_id=f"ithome-{sequence}",
                display_class="IDENTITY REFERENCE ONLY",
                color=CYAN,
                identity_reference_allowed=True,
                training_pixels_allowed=False,
                training_status="BLOCK_RIGHTS_AND_PER_FILE_RECEIPT_MISSING",
                scope_note="Owner visual PASS is not pixel-rights evidence.",
            )
        )

    profile_path = str(Path.home() / r"OneDrive\桌面\墨寒桌面語音互動虛擬女友2026.07.28開始開發\062.png")
    records.append(
        make_record(
            source=provenance_record(provenance, profile_path),
            source_id="062-profile-contour",
            display_class="TRAINING PROHIBITED",
            color=RED,
            identity_reference_allowed=False,
            training_pixels_allowed=False,
            training_status="BLOCK_REFERENCE_CONTOUR_ONLY",
            scope_note="Profile contour review only; no direct pixel derivative.",
        )
    )

    counts = {
        "trainable_pixels_rights_pass": sum(record["training_pixels_allowed"] for record in records),
        "identity_reference_only": sum(record["display_class"] == "IDENTITY REFERENCE ONLY" for record in records),
        "training_prohibited": sum(record["display_class"] == "TRAINING PROHIBITED" for record in records),
        "total": len(records),
    }
    manifest = {
        "schema": "mohan.lora.pixel_rights_zoning.v1",
        "status": "PASS_RIGHTS_ZONING_ONLY",
        "training_resume_allowed": False,
        "owner_visual_approval_is_pixel_rights": False,
        "classification_contract": {
            "TRAINABLE_PIXELS": "Pixel rights permit training use; independent-source, identity, QA, and dataset admission remain separate gates.",
            "IDENTITY_REFERENCE_ONLY": "May guide identity/proportion review, but source pixels must not enter training or derivative training assets.",
            "TRAINING_PROHIBITED": "May only be used within the narrower recorded reference scope; no training pixels.",
        },
        "counts": counts,
        "records": records,
        "evidence": {
            "candidate_provenance_manifest": str(PROVENANCE),
            "candidate_provenance_manifest_sha256": sha256(PROVENANCE),
            "owner12_pixel_provenance_audit": str(OWNER_AUDIT),
            "owner12_pixel_provenance_audit_sha256": sha256(OWNER_AUDIT),
        },
        "claim_limit": "Rights zoning only. This does not admit LoRA training and does not prove twelve independent sources.",
    }
    manifest_path = OUT / "pixel-rights-zoning-manifest.json"
    contact_path = OUT / "pixel-rights-zoning-contact.png"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_contact(records, contact_path)
    print(json.dumps({"manifest": str(manifest_path), "contact": str(contact_path), "counts": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
