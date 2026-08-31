#!/usr/bin/env python3
"""Read-only audit of the exact 12 owner-approved LoRA candidates.

This script deliberately separates visual approval from pixel-rights admission
and training readiness.  It does not modify inputs, masks, captions, trainers,
or model weights.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ARTIFACT = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/owner12-exact-selected-diversity-rights-audit-main"
OWNER_MANIFEST = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/mohan-v3-owner-review-12-main/owner-review-12-approved-manifest.json"
RIGHTS_AUDIT = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/owner12-pixel-provenance-audit-main/OWNER12-PIXEL-PROVENANCE-AUDIT.json"
DATASET_PREFLIGHT = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/v2-r3-owner12-lora-dataset-preflight-main/v2-r3-owner12-lora-dataset-preflight.json"

REPORT_JSON = ARTIFACT / "owner12-exact-selected-identity-angle-expression-crop-rights-duplicate-matrix.json"
REPORT_MD = ARTIFACT / "OWNER12-EXACT-SELECTED-MATRIX.md"
CONTACT = ARTIFACT / "owner12-exact-selected-rights-duplicate-contact.png"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rgba_pixel_sha(image: Image.Image) -> str:
    rgba = image.convert("RGBA")
    digest = hashlib.sha256()
    digest.update(rgba.width.to_bytes(4, "big"))
    digest.update(rgba.height.to_bytes(4, "big"))
    digest.update(rgba.tobytes())
    return digest.hexdigest().upper()


def bits_to_hex(bits: np.ndarray) -> str:
    flat = np.asarray(bits, dtype=np.uint8).ravel()
    return np.packbits(flat).tobytes().hex().upper()


def subject_square(image: Image.Image, side: int = 256) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox() or (0, 0, rgba.width, rgba.height)
    crop = rgba.crop(bbox)
    extent = max(crop.size)
    square = Image.new("RGBA", (extent, extent), (0, 0, 0, 0))
    square.alpha_composite(crop, ((extent - crop.width) // 2, (extent - crop.height) // 2))
    square = square.resize((side, side), Image.Resampling.LANCZOS)
    background = Image.new("RGBA", square.size, (127, 127, 127, 255))
    background.alpha_composite(square)
    return background.convert("L")


def dhash64(image: Image.Image) -> str:
    gray = subject_square(image).resize((9, 8), Image.Resampling.LANCZOS)
    values = np.asarray(gray, dtype=np.int16)
    return bits_to_hex(values[:, 1:] > values[:, :-1])


def phash64(image: Image.Image) -> str:
    values = np.asarray(subject_square(image, 32), dtype=np.float64)
    n = values.shape[0]
    coordinates = np.arange(n, dtype=np.float64)
    frequencies = coordinates[:, None]
    dct = np.cos(np.pi * (2 * coordinates + 1) * frequencies / (2 * n))
    dct[0, :] *= np.sqrt(1.0 / n)
    dct[1:, :] *= np.sqrt(2.0 / n)
    coefficients = dct @ values @ dct.T
    low = coefficients[:8, :8]
    median = float(np.median(low.ravel()[1:]))
    return bits_to_hex(low >= median)


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def transparent_rgb_nonzero(image: Image.Image) -> int:
    array = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    transparent = array[:, :, 3] == 0
    return int(np.count_nonzero(np.any(array[:, :, :3] != 0, axis=2) & transparent))


def connected_components(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    visited: set[str] = set()
    components: list[list[str]] = []
    for node in adjacency:
        if node in visited:
            continue
        stack = [node]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - visited, reverse=True))
        if len(component) > 1:
            components.append(sorted(component))
    return sorted(components)


def json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT)).replace("/", "\\")
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class AuditInputs:
    owner: dict[str, Any]
    rights: dict[str, Any]
    preflight: dict[str, Any]


def audit(inputs: AuditInputs) -> dict[str, Any]:
    owner_by_seq = {record["sequence"]: record for record in inputs.owner["records"]}
    rights_by_seq = {record["sequence"]: record for record in inputs.rights["records"]}
    preflight_by_seq = {record["sequence"]: record for record in inputs.preflight["records"]}
    order = inputs.owner["exact_sequence_order"]

    records: list[dict[str, Any]] = []
    images: dict[str, Image.Image] = {}
    for sequence in order:
        owner = owner_by_seq[sequence]
        rights = rights_by_seq[sequence]
        preflight = preflight_by_seq[sequence]
        selected = Path(owner["selected_asset_review_copy"])
        with Image.open(selected) as opened:
            image = opened.convert("RGBA")
        images[sequence] = image
        file_sha = sha256_file(selected)
        pixel_sha = rgba_pixel_sha(image)
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()
        if bbox is None:
            bbox = (0, 0, 0, 0)
        x0, y0, x1, y1 = bbox
        width = max(0, x1 - x0)
        height = max(0, y1 - y0)
        margins = [x0, y0, image.width - x1, image.height - y1]
        corner_alpha = [
            alpha.getpixel((0, 0)),
            alpha.getpixel((image.width - 1, 0)),
            alpha.getpixel((0, image.height - 1)),
            alpha.getpixel((image.width - 1, image.height - 1)),
        ]
        train_ready = bool(
            rights["admission"] == "PASS"
            and preflight["decision"] == "PASS"
            and preflight["exact_selected_mask_binding"]
            and preflight["caption_exact_selected_sha_binding"]
        )
        records.append(
            {
                "sequence": sequence,
                "selected_asset": str(selected),
                "selected_asset_project_relative": relative_or_absolute(selected),
                "identity": {
                    "owner_status": owner["owner_status"],
                    "scope": "OWNER_VISUAL_APPROVAL_ONLY",
                    "numeric_identity_score": None,
                    "claim_limit": "No numeric identity distance was recomputed by this audit.",
                },
                "angle": {
                    "label": preflight["pose_label"],
                    "status": "LABEL_ONLY_FROM_V2_R3_PREFLIGHT_NOT_EXACT_YAW_MEASUREMENT",
                },
                "expression": {
                    "label": preflight["expression_label"],
                    "status": preflight["expression_pixel_distinctness_status"],
                },
                "crop": {
                    "mode": image.mode,
                    "size": list(image.size),
                    "alpha_bbox": list(bbox),
                    "alpha_bbox_width": width,
                    "alpha_bbox_height": height,
                    "alpha_bbox_area_ratio": round((width * height) / (image.width * image.height), 8),
                    "margins_left_top_right_bottom": margins,
                    "touches_canvas_edge": any(margin == 0 for margin in margins),
                    "corner_alpha": corner_alpha,
                    "transparent_rgb_nonzero_pixels": transparent_rgb_nonzero(image),
                    "mouth_chin_landmark_measurement": "NOT_PERFORMED_IN_THIS_READ_ONLY_AUDIT",
                },
                "source_rights": {
                    "admission": rights["admission"],
                    "existing_rights_status": rights["existing_rights_status"],
                    "existing_commercial_pixel_admission": rights["existing_commercial_pixel_admission"],
                    "upstream_source": rights["upstream_source"],
                    "gaps": rights["gaps"],
                    "owner_visual_approval_is_pixel_rights": False,
                },
                "pixel_repeat": {
                    "expected_file_sha256": owner["selected_asset_sha256"].upper(),
                    "actual_file_sha256": file_sha,
                    "file_sha_matches_manifest": file_sha == owner["selected_asset_sha256"].upper(),
                    "normalized_rgba_pixel_sha256": pixel_sha,
                    "dhash64_subject_normalized": dhash64(image),
                    "phash64_subject_normalized": phash64(image),
                },
                "bindings": {
                    "exact_selected_mask_binding": preflight["exact_selected_mask_binding"],
                    "caption_exact_selected_sha_binding": preflight["caption_exact_selected_sha_binding"],
                    "dataset_preflight_decision": preflight["decision"],
                },
                "currently_train_ready": train_ready,
            }
        )

    file_groups: dict[str, list[str]] = defaultdict(list)
    pixel_groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        file_groups[record["pixel_repeat"]["actual_file_sha256"]].append(record["sequence"])
        pixel_groups[record["pixel_repeat"]["normalized_rgba_pixel_sha256"]].append(record["sequence"])
    exact_file_groups = sorted(sorted(group) for group in file_groups.values() if len(group) > 1)
    exact_pixel_groups = sorted(sorted(group) for group in pixel_groups.values() if len(group) > 1)

    pairs: list[dict[str, Any]] = []
    strict_edges: list[tuple[str, str]] = []
    review_pairs: list[dict[str, Any]] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            d_distance = hamming(
                left["pixel_repeat"]["dhash64_subject_normalized"],
                right["pixel_repeat"]["dhash64_subject_normalized"],
            )
            p_distance = hamming(
                left["pixel_repeat"]["phash64_subject_normalized"],
                right["pixel_repeat"]["phash64_subject_normalized"],
            )
            strict = d_distance <= 4 and p_distance <= 6
            review = d_distance <= 10 or p_distance <= 12
            pair = {
                "left": left["sequence"],
                "right": right["sequence"],
                "dhash_hamming": d_distance,
                "phash_hamming": p_distance,
                "strict_perceptual_near_duplicate": strict,
                "review_similarity": review,
            }
            pairs.append(pair)
            if strict:
                strict_edges.append((left["sequence"], right["sequence"]))
            if review:
                review_pairs.append(pair)

    strict_groups = connected_components(order, strict_edges)
    pose_distribution = Counter(record["angle"]["label"] for record in records)
    expression_distribution = Counter(record["expression"]["label"] for record in records)
    owner_approved = sum(record["identity"]["owner_status"] == "APPROVED" for record in records)
    rights_pass = sum(record["source_rights"]["admission"] == "PASS" for record in records)
    train_ready = sum(record["currently_train_ready"] for record in records)

    return {
        "schema": "mohan.owner12.exact-selected-diversity-rights-audit.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "READ_ONLY_EXACT_OWNER_SELECTED_RGBA_NO_TRAINING_NO_PROMOTION",
        "decision": "BLOCKED_DO_NOT_TRAIN",
        "training_started": False,
        "training_resume_allowed": False,
        "counts": {
            "selected_records": len(records),
            "owner_visual_approved": owner_approved,
            "pixel_rights_admitted": rights_pass,
            "pixel_rights_blocked": len(records) - rights_pass,
            "currently_train_ready_all_gates": train_ready,
            "exact_file_duplicate_groups": len(exact_file_groups),
            "exact_normalized_rgba_pixel_duplicate_groups": len(exact_pixel_groups),
            "strict_perceptual_near_duplicate_groups": len(strict_groups),
            "review_similarity_pairs": len(review_pairs),
        },
        "actual_usable_count": {
            "owner_visual_approved_candidates": owner_approved,
            "rights_admitted_for_dataset_preparation_only": rights_pass,
            "train_ready_under_all_current_gates": train_ready,
            "statement": "12/12 visual approval is not pixel-rights admission. Only seq01/seq02 are rights-admitted, and neither is train-ready because exact-selected mask/caption bindings remain false.",
        },
        "label_distributions": {
            "pose_label_only": dict(sorted(pose_distribution.items())),
            "expression_label_only": dict(sorted(expression_distribution.items())),
            "claim_limit": "Pose/expression labels are inherited metadata; exact yaw and pixel-distinct expression were not measured here.",
        },
        "duplicate_policy": {
            "exact_file": "Identical selected PNG file SHA-256.",
            "exact_pixels": "Identical decoded RGBA dimensions and pixel bytes.",
            "strict_perceptual_near_duplicate": "subject-normalized dHash Hamming <= 4 AND pHash Hamming <= 6",
            "review_similarity": "subject-normalized dHash Hamming <= 10 OR pHash Hamming <= 12",
            "claim_limit": "Perceptual hashes are screening evidence, not proof of legal independence or identity equivalence.",
        },
        "exact_file_duplicate_groups": exact_file_groups,
        "exact_normalized_rgba_pixel_duplicate_groups": exact_pixel_groups,
        "strict_perceptual_near_duplicate_groups": strict_groups,
        "review_similarity_pairs": sorted(
            review_pairs,
            key=lambda item: (item["dhash_hamming"] + item["phash_hamming"], item["left"], item["right"]),
        ),
        "all_pair_distances": pairs,
        "records": records,
        "source_evidence": {
            "owner_manifest": str(OWNER_MANIFEST),
            "owner_manifest_sha256": sha256_file(OWNER_MANIFEST),
            "rights_audit": str(RIGHTS_AUDIT),
            "rights_audit_sha256": sha256_file(RIGHTS_AUDIT),
            "dataset_preflight": str(DATASET_PREFLIGHT),
            "dataset_preflight_sha256": sha256_file(DATASET_PREFLIGHT),
        },
    }


def render_contact(report: dict[str, Any]) -> None:
    width, height = 1600, 1430
    canvas = Image.new("RGB", (width, height), (28, 31, 35))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=22)
    small = ImageFont.load_default(size=17)
    draw.text((25, 18), "MOHAN OWNER12 — EXACT SELECTED / RIGHTS / DUPLICATE AUDIT", fill=(245, 245, 245), font=font)
    counts = report["counts"]
    draw.text(
        (25, 52),
        f"visual approved {counts['owner_visual_approved']}/12 | pixel-rights PASS {counts['pixel_rights_admitted']}/12 | train-ready {counts['currently_train_ready_all_gates']}/12",
        fill=(245, 204, 95),
        font=small,
    )
    cell_w, cell_h = 390, 405
    image_side = 300
    for index, record in enumerate(report["records"]):
        row, col = divmod(index, 4)
        left = 20 + col * cell_w
        top = 90 + row * cell_h
        admitted = record["source_rights"]["admission"] == "PASS"
        color = (52, 199, 89) if admitted else (225, 74, 74)
        draw.rectangle((left, top, left + 365, top + 380), outline=color, width=4)
        selected = Path(record["selected_asset"])
        with Image.open(selected) as opened:
            rgba = opened.convert("RGBA")
        checker = Image.new("RGB", (image_side, image_side), (180, 180, 180))
        checker_draw = ImageDraw.Draw(checker)
        tile = 20
        for y in range(0, image_side, tile):
            for x in range(0, image_side, tile):
                if (x // tile + y // tile) % 2:
                    checker_draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(220, 220, 220))
        preview = rgba.resize((image_side, image_side), Image.Resampling.LANCZOS)
        checker.paste(preview.convert("RGB"), (0, 0), preview.getchannel("A"))
        canvas.paste(checker, (left + 32, top + 32))
        draw.text((left + 12, top + 8), f"{record['sequence']} | RIGHTS {record['source_rights']['admission']}", fill=color, font=small)
        draw.text(
            (left + 12, top + 338),
            f"{record['angle']['label']} / {record['expression']['label']} | SHA {record['pixel_repeat']['actual_file_sha256'][:10]}",
            fill=(240, 240, 240),
            font=small,
        )
        draw.text(
            (left + 12, top + 359),
            f"bbox {record['crop']['alpha_bbox']} | train-ready {record['currently_train_ready']}",
            fill=(220, 220, 220),
            font=small,
        )
    canvas.save(CONTACT)


def render_markdown(report: dict[str, Any]) -> None:
    counts = report["counts"]
    lines = [
        "# Owner12 exact-selected audit",
        "",
        "## Result",
        "",
        "- Decision: `BLOCKED_DO_NOT_TRAIN`.",
        f"- Owner visual approval: `{counts['owner_visual_approved']}/12`.",
        f"- Pixel-rights admission: `{counts['pixel_rights_admitted']}/12` (`seq01`, `seq02` only).",
        f"- Train-ready under every current gate: `{counts['currently_train_ready_all_gates']}/12`.",
        f"- Exact file duplicate groups: `{counts['exact_file_duplicate_groups']}`.",
        f"- Exact decoded RGBA duplicate groups: `{counts['exact_normalized_rgba_pixel_duplicate_groups']}`.",
        f"- Strict perceptual near-duplicate groups: `{counts['strict_perceptual_near_duplicate_groups']}`.",
        "",
        "美術核准不等於像素權利准入。其餘 10 張保留 `BLOCKED`；seq01/02 仍缺 exact-selected mask 與 caption SHA 綁定，因此不能啟動訓練。",
        "",
        "## Matrix",
        "",
        "| seq | identity | angle* | expression* | crop alpha bbox | rights | file SHA | exact pixel duplicate | train-ready |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    pixel_members: dict[str, int] = Counter(
        record["pixel_repeat"]["normalized_rgba_pixel_sha256"] for record in report["records"]
    )
    for record in report["records"]:
        pixel_sha = record["pixel_repeat"]["normalized_rgba_pixel_sha256"]
        lines.append(
            "| {sequence} | {identity} | {angle} | {expression} | `{bbox}` | {rights} | `{sha}` | {duplicate} | {ready} |".format(
                sequence=record["sequence"],
                identity=record["identity"]["owner_status"] + " (visual only)",
                angle=record["angle"]["label"],
                expression=record["expression"]["label"],
                bbox=record["crop"]["alpha_bbox"],
                rights=record["source_rights"]["admission"],
                sha=record["pixel_repeat"]["actual_file_sha256"][:12],
                duplicate="YES" if pixel_members[pixel_sha] > 1 else "NO",
                ready=str(record["currently_train_ready"]),
            )
        )
    lines.extend(
        [
            "",
            "`*` angle/expression are inherited labels only; exact yaw and pixel-distinct expression were not re-measured.",
            "",
            "## Perceptual screening",
            "",
            f"Strict near-duplicate groups: `{json.dumps(report['strict_perceptual_near_duplicate_groups'])}`.",
            "",
            "Review-similarity pairs (screening only):",
            "",
        ]
    )
    if report["review_similarity_pairs"]:
        for pair in report["review_similarity_pairs"]:
            lines.append(
                f"- `{pair['left']}–{pair['right']}`: dHash `{pair['dhash_hamming']}`, pHash `{pair['phash_hamming']}`."
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "Perceptual hashes cannot establish legal independence, identity equality, or expression diversity by themselves.",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    inputs = AuditInputs(
        owner=json_load(OWNER_MANIFEST),
        rights=json_load(RIGHTS_AUDIT),
        preflight=json_load(DATASET_PREFLIGHT),
    )
    report = audit(inputs)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_contact(report)
    render_markdown(report)
    print(json.dumps({"report": str(REPORT_JSON), "contact": str(CONTACT), "counts": report["counts"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
