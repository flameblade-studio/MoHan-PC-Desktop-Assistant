#!/usr/bin/env python3
"""Read-only pixel provenance audit for the 12 owner-approved LoRA images.

The only writes are this audit's JSON/Markdown evidence files.  The audit does
not train, download, delete, promote, or mutate any source/selected image.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
BASE = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25"
OUTPUT = BASE / "owner12-pixel-provenance-audit-main"
OWNER_MANIFEST = BASE / "mohan-v3-owner-review-12-main/owner-review-12-approved-manifest.json"
RIGHTS_GATE = BASE / "pure-face-v3-r12-independent-qa-agent-c/lora-owner12-controls-provenance-admission.json"
SOURCE_CHAIN = BASE / "pure-face-v3-r12-independent-qa-agent-c/owner10-source-chain-and-trainer-unlock.json"
CANDIDATE_PROVENANCE = BASE / "image-input-production-admission/candidate-image-provenance-manifest-v3.json"
OPENAI_RIGHTS = BASE / "image-input-production-admission/official-openai-output-rights-evidence.json"
ASSETS_LICENSE = PROJECT / "ASSETS-LICENSE.md"
REPO_LICENSE = PROJECT / "LICENSE"
GENERATED_POOL = Path.home() / r".codex\generated_images"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def pixel_sha256(path: Path) -> str:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        digest = hashlib.sha256()
        digest.update(f"RGBA:{rgba.width}x{rgba.height}:".encode("ascii"))
        digest.update(rgba.tobytes())
        return digest.hexdigest().upper()


def evidence(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
    }


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    owner = json.loads(OWNER_MANIFEST.read_text(encoding="utf-8"))
    rights = json.loads(RIGHTS_GATE.read_text(encoding="utf-8"))
    source_chain = json.loads(SOURCE_CHAIN.read_text(encoding="utf-8"))
    provenance = json.loads(CANDIDATE_PROVENANCE.read_text(encoding="utf-8"))

    rights_by_sequence = {
        item["sequence"]: item for item in rights["owner_review_12"]["records"]
    }
    chain_by_sequence = {item["sequence"]: item for item in source_chain["records"]}
    provenance_by_hash = {item.get("sha256"): item for item in provenance["records"]}

    generated_exact: dict[str, list[str]] = {}
    generated_pixel: dict[str, list[str]] = {}
    generated_files = [path for path in GENERATED_POOL.rglob("*") if path.is_file()]
    for path in generated_files:
        file_hash = sha256(path)
        generated_exact.setdefault(file_hash, []).append(str(path))
        try:
            pixels = pixel_sha256(path)
        except Exception:
            continue
        generated_pixel.setdefault(pixels, []).append(str(path))

    fallback_by_sequence = {
        "seq03": "idle_lean.png",
        "seq04": "idle_lean.png",
        "seq05": "idle_lean.png",
        "seq06": "idle_front.png",
        "seq09": "idle_front.png",
        "seq13": "idle_front.png",
        "seq14": "idle_front.png",
        "seq15": "idle_front.png",
        "seq16": "idle_front.png",
        "seq17": "idle_front.png",
    }
    admitted_sources = {
        "idle_front.png": PROJECT / "assets/expressions/idle_front.png",
        "idle_lean.png": PROJECT / "assets/expressions/idle_lean.png",
    }

    records: list[dict[str, Any]] = []
    for owner_record in owner["records"]:
        sequence = owner_record["sequence"]
        rights_record = rights_by_sequence[sequence]
        upstream = Path(rights_record["upstream_source_path"])
        selected = Path(owner_record["selected_asset_review_copy"])
        crop = Path(owner_record["source"])
        upstream_actual_hash = sha256(upstream) if upstream.is_file() else None
        upstream_pixels = pixel_sha256(upstream) if upstream.is_file() else None
        selected_actual_hash = sha256(selected) if selected.is_file() else None
        crop_actual_hash = sha256(crop) if crop.is_file() else None

        local_provenance = provenance_by_hash.get(upstream_actual_hash)
        source_chain_record = chain_by_sequence.get(sequence)
        pass_rights = rights_record["license_provenance_admission"] == "PASS"
        gaps: list[str] = []
        if not pass_rights:
            gaps.extend(
                [
                    "No per-file original generation receipt links this upstream pixel/file hash to a generating account and output event.",
                    "No complete per-generation prompt/input list and input-rights chain was found.",
                    "The owner approved visual selection and local training action, but the saved wording does not explicitly declare copyright/third-party clearance for this upstream file.",
                    "OpenAI's general output-rights terms are present locally but are not a per-file generation receipt and do not clear unknown third-party inputs.",
                ]
            )

        exact_matches = generated_exact.get(upstream_actual_hash or "", [])
        pixel_matches = generated_pixel.get(upstream_pixels or "", [])
        fallback = admitted_sources.get(fallback_by_sequence.get(sequence, ""))
        alternatives: list[dict[str, Any]] = []
        if not pass_rights and fallback is not None:
            alternatives.extend(
                [
                    {
                        "kind": "DETERMINISTIC_DERIVATIVE_OF_ADMITTED_AUTHORITY",
                        "path": str(fallback),
                        "sha256": sha256(fallback),
                        "rights_basis": "Committed expression authority covered by repository ASSETS-LICENSE.md and MIT LICENSE.",
                        "tradeoff": "Rights-clean but lower pose/expression diversity; must not mirror the fixed-side ornament.",
                    },
                    {
                        "kind": "NEW_FIRST_PARTY_SOURCE_REQUIRED",
                        "path": None,
                        "sha256": None,
                        "rights_basis": "Create a new owner-authored/commissioned source with an explicit per-file commercial-training and derivative-rights declaration.",
                        "tradeoff": "Best path to restore unique pose/expression diversity; no replacement exists until evidence is recorded.",
                    },
                    {
                        "kind": "NEW_GENERATION_WITH_COMPLETE_RECEIPT_REQUIRED",
                        "path": None,
                        "sha256": None,
                        "rights_basis": "Generate anew from admitted idle_front/idle_lean inputs only, preserving the output event, prompt, all inputs and their hashes, tool/terms version, and input-rights chain.",
                        "tradeoff": "OpenAI output assignment alone is insufficient if the generation input chain is missing or blocked.",
                    },
                ]
            )

        records.append(
            {
                "sequence": sequence,
                "admission": "PASS" if pass_rights else "BLOCKED",
                "owner_visual_status": owner_record["owner_status"],
                "selected_asset": str(selected),
                "selected_expected_sha256": owner_record["selected_asset_sha256"],
                "selected_actual_sha256": selected_actual_hash,
                "selected_hash_matches": selected_actual_hash == owner_record["selected_asset_sha256"],
                "intermediate_crop": str(crop),
                "intermediate_crop_expected_sha256": owner_record["source_sha256"],
                "intermediate_crop_actual_sha256": crop_actual_hash,
                "intermediate_crop_hash_matches": crop_actual_hash == owner_record["source_sha256"],
                "upstream_source": str(upstream),
                "upstream_expected_sha256": rights_record["upstream_source_sha256"],
                "upstream_actual_sha256": upstream_actual_hash,
                "upstream_hash_matches": upstream_actual_hash == rights_record["upstream_source_sha256"],
                "upstream_pixel_sha256": upstream_pixels,
                "existing_rights_status": rights_record["upstream_license_status"],
                "existing_commercial_pixel_admission": rights_record["upstream_commercial_pixel_admission"],
                "candidate_provenance_record": local_provenance,
                "generated_images_pool_scan": {
                    "pool": str(GENERATED_POOL),
                    "scanned_file_count": len(generated_files),
                    "exact_file_hash_matches": exact_matches,
                    "normalized_rgba_pixel_matches": pixel_matches,
                    "original_generation_record_found": bool(exact_matches or pixel_matches),
                },
                "session_attachment_record_found": (
                    source_chain_record.get("attachment_record_found")
                    if source_chain_record is not None
                    else None
                ),
                "prior_source_chain_original_generation_record_found": (
                    source_chain_record.get("original_generation_record_found")
                    if source_chain_record is not None
                    else None
                ),
                "gaps": gaps,
                "lawful_replacement_options": alternatives,
            }
        )

    pass_count = sum(record["admission"] == "PASS" for record in records)
    blocked_count = sum(record["admission"] == "BLOCKED" for record in records)
    report = {
        "schema": "mohan.owner12_pixel_provenance_audit.v1",
        "scope": "READ_ONLY_NO_DOWNLOAD_NO_TRAINING_NO_DELETE_NO_PROMOTION",
        "decision": "PASS" if blocked_count == 0 else "FAIL_CLOSED",
        "exit_code": 0 if blocked_count == 0 else 4,
        "counts": {
            "records": len(records),
            "pass": pass_count,
            "blocked": blocked_count,
            "generated_images_scanned": len(generated_files),
        },
        "claim_limits": [
            "Owner visual approval is not a copyright or third-party-input clearance declaration.",
            "A matching local attachment would not itself be a generation receipt; no exact or normalized-pixel match was found in the current generated_images pool for the ten blocked upstream files.",
            "OpenAI output assignment is contractual output-rights evidence, not MIT/open-source licensing and not blanket input-rights clearance.",
            "Only seq01/seq02 are admitted by current repository asset-license evidence.",
        ],
        "evidence": [
            evidence(OWNER_MANIFEST),
            evidence(RIGHTS_GATE),
            evidence(SOURCE_CHAIN),
            evidence(CANDIDATE_PROVENANCE),
            evidence(OPENAI_RIGHTS),
            evidence(ASSETS_LICENSE),
            evidence(REPO_LICENSE),
        ],
        "records": records,
    }

    report_path = OUTPUT / "OWNER12-PIXEL-PROVENANCE-AUDIT.json"
    table_path = OUTPUT / "OWNER12-PIXEL-PROVENANCE-TABLE.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Owner-approved 12/12 LoRA pixel provenance audit",
        "",
        f"Decision: **{report['decision']}**; PASS {pass_count}/12, BLOCKED {blocked_count}/12.",
        "",
        "| Seq | Rights | Upstream SHA256 | Generation record | Gap / lawful replacement |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        found = record["generated_images_pool_scan"]["original_generation_record_found"]
        if record["admission"] == "PASS":
            summary = "Repository ASSETS-LICENSE.md + MIT LICENSE."
        else:
            fallback = record["lawful_replacement_options"][0]
            summary = f"Per-file generation/input-rights evidence missing; fallback: {fallback['path']}."
        lines.append(
            f"| {record['sequence']} | {record['admission']} | `{record['upstream_actual_sha256']}` | "
            f"{'FOUND' if found else 'NOT FOUND'} | {summary} |"
        )
    lines.extend(
        [
            "",
            "## Fail-closed boundary",
            "",
            "The ten blocked files remain usable only as visual/context references under the current evidence. "
            "Their pixels are not admitted to LoRA training, commercial derivatives, or redistribution.",
        ]
    )
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "decision": report["decision"],
        "counts": report["counts"],
        "report": str(report_path),
        "table": str(table_path),
    }, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
