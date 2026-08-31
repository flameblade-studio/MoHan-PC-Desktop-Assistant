#!/usr/bin/env python3
"""Trace exact owner12 pixels and create an unsigned declaration template.

Reads existing evidence only. It does not download, train, alter source images,
or sign any declaration for the owner.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT = REPO / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
OUT = ROOT / "owner12-provenance-gap-and-declaration-main"
RIGHTS_AUDIT = ROOT / "owner12-pixel-provenance-audit-main" / "OWNER12-PIXEL-PROVENANCE-AUDIT.json"
OWNER_MANIFEST = ROOT / "mohan-v3-owner-review-12-main" / "owner-review-12-approved-manifest.json"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def evidence(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path),
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row_from_record(record: dict[str, Any]) -> dict[str, Any]:
    selected = Path(record["selected_asset"])
    intermediate = Path(record["intermediate_crop"])
    upstream = Path(record["upstream_source"])
    candidate = record.get("candidate_provenance_record", {})
    admission = record.get("admission")
    provenance_evidence: list[dict[str, Any]] = []
    for item in candidate.get("provenance_evidence", []):
        if isinstance(item, dict) and item.get("path"):
            provenance_evidence.append(evidence(Path(item["path"])))
        else:
            provenance_evidence.append(item)
    return {
        "sequence": record["sequence"],
        "owner_visual_status": record.get("owner_visual_status"),
        "current_pixel_rights_admission": admission,
        "selected_asset": {
            **evidence(selected),
            "expected_sha256": record.get("selected_expected_sha256"),
            "hash_matches_prior_evidence": (
                sha256(selected) == str(record.get("selected_expected_sha256", "")).upper()
            ),
        },
        "intermediate_crop": {
            **evidence(intermediate),
            "expected_sha256": record.get("intermediate_crop_expected_sha256"),
            "hash_matches_prior_evidence": (
                sha256(intermediate) == str(record.get("intermediate_crop_expected_sha256", "")).upper()
            ),
        },
        "upstream_source": {
            **evidence(upstream),
            "expected_sha256": record.get("upstream_expected_sha256"),
            "normalized_pixel_sha256": record.get("upstream_pixel_sha256"),
            "hash_matches_prior_evidence": (
                sha256(upstream) == str(record.get("upstream_expected_sha256", "")).upper()
            ),
            "category": candidate.get("category"),
            "authority_class": candidate.get("authority_class"),
        },
        "rights_evidence": {
            "existing_rights_status": record.get("existing_rights_status"),
            "commercial_pixel_admission": record.get("existing_commercial_pixel_admission"),
            "source_license": candidate.get("source_license"),
            "decision_reason": candidate.get("decision_reason"),
            "provenance_evidence": provenance_evidence,
            "git_last_commit": candidate.get("git_last_commit"),
            "session_attachment_record_found": record.get("session_attachment_record_found"),
            "original_generation_record_found": (
                record.get("generated_images_pool_scan", {}).get("original_generation_record_found")
            ),
            "prior_source_chain_original_generation_record_found": record.get(
                "prior_source_chain_original_generation_record_found"
            ),
        },
        "gaps": record.get("gaps", []),
        "lawful_replacement_options": record.get("lawful_replacement_options", []),
        "why_pass_or_hold": (
            "PASS because the upstream is a committed canonical expression asset bound to the repository ASSETS-LICENSE.md and MIT LICENSE. Art/input QA remains separate."
            if admission == "PASS"
            else "HOLD because the iThome support image is documented only as reference evidence; its per-file generation receipt, complete prompt/input rights chain, and explicit owner/rightsholder declaration were not found."
        ),
    }


def declaration_row(row: dict[str, Any]) -> dict[str, Any]:
    upstream = row["upstream_source"]
    selected = row["selected_asset"]
    return {
        "sequence": row["sequence"],
        "selected_asset_path": selected["path"],
        "selected_asset_sha256": selected["sha256"],
        "upstream_source_path": upstream["path"],
        "upstream_source_sha256": upstream["sha256"],
        "declaration_required_for_current_rights_gap": row["current_pixel_rights_admission"] != "PASS",
        "owner_declaration": {
            "declarant_legal_name": "",
            "declarant_role": "",
            "rights_basis": "",
            "rights_basis_allowed_values": [
                "SOLE_COPYRIGHT_OWNER",
                "AUTHORIZED_BY_RIGHTSHOLDER",
                "WORK_MADE_FOR_HIRE_OR_COMMISSION_WITH_TRANSFER",
                "OTHER_WITH_ATTACHED_EVIDENCE",
            ],
            "generation_or_creation_method": "",
            "generation_service_or_tool": "",
            "generation_account_owned_or_controlled_by_declarant": None,
            "generation_event_or_receipt_id": "",
            "generation_receipt_path": "",
            "generation_receipt_sha256": "",
            "prompt_and_settings_record_path": "",
            "prompt_and_settings_record_sha256": "",
            "all_input_assets_disclosed": None,
            "input_assets": [],
            "no_nc_or_noncommercial_restriction": None,
            "no_copyleft_or_share_alike_obligation_incompatible_with_mohan": None,
            "commercial_machine_learning_training_authorized": None,
            "commercial_derivatives_authorized": None,
            "redistribution_of_resulting_lora_or_generated_outputs_authorized": None,
            "third_party_personality_or_privacy_clearance_confirmed_if_applicable": None,
            "declaration_text": "",
            "required_declaration_text": (
                "I declare that the exact upstream file identified by path and SHA256 above is owned or duly licensed by me for commercial machine-learning training and commercial derivative use; all generation inputs and third-party restrictions have been fully disclosed, and no undisclosed NC or incompatible reciprocal restriction applies."
            ),
            "signature_name": "",
            "signed_at_iso8601_with_timezone": "",
            "supporting_evidence_paths": [],
        },
        "validator_boundary": (
            "A structurally complete declaration can only establish exact-SHA owner evidence for later review. Validator exit 0 must not be treated as legal advice, pixel-rights admission, training permission, or LoRA art PASS."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# owner12 像素來源與權利缺口表",
        "",
        f"- 決策：`{report['decision']}`",
        f"- 現有像素權利准入：`{report['counts']['pixel_rights_pass']}/12`",
        "- owner 美術核准只證明畫面選擇，不自動證明每張來源像素權利。",
        "",
        "| seq | owner美術 | selected SHA | 原始來源 | upstream SHA | 權利 | 原因/缺口 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        upstream_name = Path(row["upstream_source"]["path"]).name
        gaps = "；".join(row["gaps"]) if row["gaps"] else row["why_pass_or_hold"]
        lines.append(
            f"| {row['sequence']} | {row['owner_visual_status']} | `{row['selected_asset']['sha256'][:12]}…` | "
            f"{upstream_name} | `{row['upstream_source']['sha256'][:12]}…` | "
            f"{row['current_pixel_rights_admission']} | {gaps} |"
        )
    lines.extend(
        [
            "",
            "## 為何只有 2/12",
            "",
            "- `seq01`、`seq02` 的上游是 Git 已提交的 `idle_front.png`、`idle_lean.png`，有 exact SHA、Git commit、`ASSETS-LICENSE.md` 與 MIT `LICENSE` 綁定。",
            "- 其餘 10 張上游是 iThome 支援圖。檔案存在且 SHA 可驗，但目前只准作身份參考；沒有逐檔生成 receipt、完整 prompt/輸入權利鏈，以及針對 exact SHA 的 owner/rightsholder 商用訓練聲明。",
            "- 本機找到一般服務條款或對話附件，不等於逐檔生成證明，也不能清除未揭露的第三方輸入權利。",
            "",
            "## 表單邊界",
            "",
            "`owner-exact-sha-declaration.blank.json` 是空白表單，未代簽。即使未來結構 validator 退出碼 0，仍只代表欄位和 SHA 綁定完整，必須再經權利審查；不能直接宣稱可訓練。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rights = load(RIGHTS_AUDIT)
    rows = [row_from_record(record) for record in rights.get("records", [])]
    rows.sort(key=lambda item: item["sequence"])
    pass_count = sum(row["current_pixel_rights_admission"] == "PASS" for row in rows)
    all_hashes_match = all(
        row[part]["exists"] and row[part]["hash_matches_prior_evidence"]
        for row in rows
        for part in ["selected_asset", "intermediate_crop", "upstream_source"]
    )
    report = {
        "schema": "mohan.owner12.provenance_gap_table.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "READ_ONLY_NO_DOWNLOAD_NO_TRAINING_NO_OWNER_SIGNATURE",
        "decision": "HOLD_10_OF_12_PIXEL_RIGHTS_UNDOCUMENTED",
        "counts": {
            "rows": len(rows),
            "owner_visual_approved": sum(row["owner_visual_status"] == "APPROVED" for row in rows),
            "pixel_rights_pass": pass_count,
            "pixel_rights_hold": len(rows) - pass_count,
            "all_selected_intermediate_upstream_hashes_match": all_hashes_match,
        },
        "source_evidence": {
            "prior_rights_audit": evidence(RIGHTS_AUDIT),
            "owner_visual_manifest": evidence(OWNER_MANIFEST),
        },
        "rows": rows,
        "training_started": False,
        "download_performed": False,
        "owner_signature_created": False,
    }
    template = {
        "schema": "mohan.owner12.exact_sha_owner_declaration.v1",
        "status": "BLANK_UNSIGNED_TEMPLATE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "owner_signature_created_by_audit": False,
        "rows": [declaration_row(row) for row in rows],
        "review_boundary": (
            "Do not change status to ADMITTED automatically. A completed declaration requires separate factual and rights review, and training remains governed by the existing fail-closed dataset and trainer gates."
        ),
    }
    report_path = OUT / "owner12-provenance-gap-table.json"
    md_path = OUT / "OWNER12-PROVENANCE-GAP-TABLE.md"
    template_path = OUT / "owner-exact-sha-declaration.blank.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    template_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "rows": len(rows),
                "pixel_rights_pass": pass_count,
                "pixel_rights_hold": len(rows) - pass_count,
                "all_hashes_match": all_hashes_match,
                "report": str(report_path),
                "blank_declaration": str(template_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
