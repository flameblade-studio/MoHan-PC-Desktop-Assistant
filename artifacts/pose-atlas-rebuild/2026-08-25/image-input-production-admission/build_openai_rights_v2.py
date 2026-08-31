from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


OUT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\image-input-production-admission")
V1 = OUT / "image-input-production-admission.json"
CAPTURED_AT = "2026-08-25T04:38:57.3852740+08:00"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def write_json(path: Path, value: Any) -> str:
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(content)
    return sha256_bytes(content)


def main() -> int:
    if not V1.is_file():
        print(json.dumps({"status": "BLOCK", "missing": str(V1)}, indent=2))
        return 3
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    official_evidence = {
        "schema": "mohan.openai_output_rights_evidence.v1",
        "captured_at": CAPTURED_AT,
        "capture_method": "Official OpenAI web pages opened through web retrieval; canonical clause summary archived here, not a full HTML mirror.",
        "scope": "built-in OpenAI image generation output rights only; not an MIT/open-source license and not third-party input clearance",
        "sources": [
            {
                "title": "OpenAI Terms of Use (rest of world)",
                "url": "https://openai.com/policies/row-terms-of-use/",
                "published": "2026-01-01",
                "effective": "2026-01-01",
                "retrieved_at": CAPTURED_AT,
                "relevant_lines": [38, 41, 44, 45, 47, 51, 56, 57, 58, 64, 65, 92, 94, 101, 103],
                "clause_summary": {
                    "input": "User retains existing Input ownership but must have all rights, licenses and permissions needed to provide Input.",
                    "output": "As between user and OpenAI, user owns Output; OpenAI assigns any OpenAI right, title and interest in Output to user, to the extent permitted by law.",
                    "similarity": "Output may be non-unique; assignment does not cover another user's output or Third Party Output.",
                    "commercial_use": "The terms do not impose a non-commercial restriction on ordinary image Output; access/use remains subject to law and policy. Business/organization use carries indemnity and responsibility boundaries.",
                    "responsibility": "User must review appropriateness, avoid infringement, disclose that output is AI-generated where required by the terms, and bears use risk/responsibility.",
                },
            },
            {
                "title": "OpenAI Services Agreement",
                "url": "https://openai.com/policies/services-agreement/",
                "updated": "2025-12-01",
                "effective": "2026-01-01",
                "retrieved_at": CAPTURED_AT,
                "relevant_lines": [24, 41, 47, 48, 50, 51, 52, 53, 79, 80],
                "clause_summary": {
                    "account_scope": "Applies to APIs, ChatGPT Enterprise/Business and business/developer customers, not ordinary individual consumer use.",
                    "input": "Customer retains Input rights and warrants all necessary Input rights, licenses and permissions.",
                    "output": "Customer owns Output as between Customer and OpenAI; OpenAI assigns any rights it has in Output.",
                    "similarity": "Output may be non-unique and other users' responses are not Customer Output.",
                    "responsibility": "Customer is responsible for use, accuracy and appropriateness and must not violate third-party rights.",
                },
            },
            {
                "title": "OpenAI Service Terms",
                "url": "https://openai.com/policies/service-terms/",
                "updated": "2026-06-12",
                "retrieved_at": CAPTURED_AT,
                "relevant_lines": [20, 22, 23, 33, 34, 60, 61, 62, 63, 68, 69],
                "clause_summary": {
                    "visual_inputs": "Visual capabilities may not reproduce a person's likeness without express consent and all necessary rights.",
                    "third_party_apps": "Content retrieved from third-party apps may not be owned by the user or OpenAI and may have separate terms.",
                    "indemnity_boundary": "Any applicable output indemnity has exclusions, including missing Input rights, modified/combined Output, ignored safeguards, trademark claims in commerce and Third Party Offerings.",
                },
            },
        ],
        "legal_characterization": {
            "is_open_source_license": False,
            "is_MIT": False,
            "establishes_as_between_openai_and_user_output_ownership": True,
            "establishes_blanket_non_infringement": False,
            "clears_unknown_third_party_input_rights": False,
            "guarantees_output_uniqueness": False,
            "commercial_output_prohibition_found": False,
        },
    }
    canonical = json.dumps(official_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    official_evidence["canonical_summary_sha256"] = sha256_bytes(canonical)
    evidence_path = OUT / "official-openai-output-rights-evidence.json"
    evidence_sha = write_json(evidence_path, official_evidence)

    v2 = json.loads(json.dumps(v1))
    v2["schema"] = "mohan.image_input_production_admission.v2"
    v2["generated_at"] = "2026-08-25"
    v2["status"] = "OPENAI_OUTPUT_RIGHTS_CLEARED_INPUT_CHAIN_STILL_FAIL_CLOSED"
    v2["supersedes_for_candidate_review_only"] = str(V1)
    v2["official_openai_output_rights_evidence"] = {"path": str(evidence_path), "sha256": evidence_sha}
    v2["policy"]["openai_output_terms_are_not_MIT"] = True
    v2["policy"]["openai_output_ownership_does_not_clear_input_rights"] = True

    updated = 0
    for record in v2["records"]:
        if record["category"] not in {"approved_B00_artifact", "builtin_imagegen_candidate"}:
            continue
        updated += 1
        record["openai_output_rights_status"] = "CLEARED_AS_BETWEEN_OPENAI_AND_USER"
        record["license_status"] = "OPENAI_OUTPUT_RIGHTS_CLEARED_INPUT_CHAIN_REVIEW_REQUIRED"
        record["source_license"] = "OpenAI contractual output assignment; NOT MIT/open-source"
        record["provenance_evidence"].append({"path": str(evidence_path), "sha256": evidence_sha})
        record["decision_reason"] = (
            "Official OpenAI terms establish that, as between OpenAI and the user and to the extent permitted by law, "
            "the user owns Output and OpenAI assigns any rights it has. They do not clear third-party Input rights, "
            "guarantee uniqueness/non-infringement, or turn Output into MIT-licensed material. This record lacks a complete "
            "per-generation Input-rights chain, so formal PNG promotion remains blocked on that narrower ground."
        )
        record["commercial_formal_png_admission"] = "BLOCK_INPUT_RIGHTS_LINEAGE_UNVERIFIED"

    v2["openai_output_records_updated"] = updated
    v2["blocked_direct_pixel_records"] = sum(
        str(record["commercial_formal_png_admission"]).startswith("BLOCK") for record in v2["records"]
    )
    v2_path = OUT / "image-input-production-admission-v2.json"
    v2_sha = write_json(v2_path, v2)

    manifest = {
        "schema": "mohan.candidate_image_provenance_manifest.v2",
        "status": "CANDIDATE_ONLY_NOT_FORMAL_ASSET_MANIFEST",
        "official_output_rights_evidence": {"path": str(evidence_path), "sha256": evidence_sha},
        "records": [
            {
                key: record.get(key)
                for key in (
                    "path", "sha256", "category", "authority_class", "license_status", "source_license",
                    "openai_output_rights_status", "allowed_uses", "prohibited_uses",
                    "commercial_formal_png_admission", "decision_reason", "provenance_evidence"
                )
            }
            for record in v2["records"]
        ],
    }
    manifest_path = OUT / "candidate-image-provenance-manifest-v2.json"
    manifest_sha = write_json(manifest_path, manifest)

    report = f"""# OpenAI ImageGen 輸出權利查核與候選 provenance v2

## 結論

官方條款足以解除 B00 與 built-in ImageGen 候選原本的「缺 OpenAI 輸出所有權證據」阻塞：在使用者與 OpenAI 之間，使用者保留 Input 的既有權利並擁有 Output，OpenAI 將其對 Output 可能具有的權利讓與使用者。一般影像 Output 沒有查到 NC 或僅限非商用條款。

但這不是 MIT、Apache 或其他開源授權，也不是不侵權保證。條款同時要求使用者具備所有 Input 權利；Output 可能與他人相似，第三方 Output 不在讓與範圍，而且使用者負責合法性、適用性與人工審查。因此目前只能解除「OpenAI output rights」這一層，不能解除 B00／候選的完整正式 PNG 閘門。其每次生成使用了哪些 B00、062、iThome 或其他參考圖，仍需逐筆證明權利／限制；缺少該鏈者已改標 `BLOCK_INPUT_RIGHTS_LINEAGE_UNVERIFIED`。

## 官方來源

- OpenAI Terms of Use（ROW）：https://openai.com/policies/row-terms-of-use/；發布及生效 2026-01-01。
- OpenAI Services Agreement：https://openai.com/policies/services-agreement/；更新 2025-12-01，生效 2026-01-01。
- OpenAI Service Terms：https://openai.com/policies/service-terms/；更新 2026-06-12。
- 擷取時間：{CAPTURED_AT}
- 官方條款摘要證據 SHA256：`{evidence_sha}`

## v2 變更

- 更新 B00 1 筆及 built-in ImageGen 16 筆，共 {updated} 筆。
- `OPENAI_OUTPUT_RIGHTS_CLEARED`：是。
- `FORMAL_COMMERCIAL_PNG_FULL_ADMISSION`：否；Input 權利鏈仍未逐生成完成。
- 未變更正式 manifest、正式 assets 或正式 third-party notices。

## 法律與工程邊界

這是官方條款的工程准入紀錄，不是法律意見。輸出所有權條款不能替 062、iThome、商標、真人肖像或第三方素材補授權，也不能保證特定司法管轄區承認純 AI 輸出的著作權保護。
"""
    report_path = OUT / "OPENAI-OUTPUT-RIGHTS-REPORT-v2.md"
    report_path.write_text(report, encoding="utf-8")
    report_sha = sha256_bytes(report_path.read_bytes())

    print(json.dumps({
        "status": v2["status"],
        "openai_output_records_updated": updated,
        "openai_output_rights_cleared": True,
        "formal_png_full_admission": False,
        "remaining_reason": "per-generation input rights lineage unverified",
        "outputs": {
            str(evidence_path): evidence_sha,
            str(v2_path): v2_sha,
            str(manifest_path): manifest_sha,
            str(report_path): report_sha,
        },
    }, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    sys.exit(main())
