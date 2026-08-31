from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
OUT = REPO / "artifacts" / "pose-atlas-rebuild" / "2026-08-25" / "third-party-notices-instantmesh-consistency-agent-c"
NOTICES = REPO / "THIRD_PARTY_NOTICES.md"
DENYLIST = REPO / "THIRD_PARTY_DENYLIST.json"
HANDOFF = REPO / "CODEX_PROJECT_HANDOFF.md"

INSTANTMESH_COMMIT = "08822c52fdc399b93ea00e4fa9e596344ed52ccc"
BIREF_REVISION = "5d6b6f8adcb5b417c871b1d84ceaae9871355b7f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_utf8_strict(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="strict")


def run_git(*arguments: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "-C", str(REPO), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(["git", "-C", str(REPO), *arguments]),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def section(text: str, start: str, end: str | None) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index + len(start)) if end else len(text)
    return text[start_index:end_index]


def contains_all(text: str, required: list[str]) -> tuple[bool, list[str]]:
    missing = [value for value in required if value not in text]
    return not missing, missing


def main() -> int:
    try:
        notices = read_utf8_strict(NOTICES)
        denylist_text = read_utf8_strict(DENYLIST)
        handoff = read_utf8_strict(HANDOFF)
        denylist = json.loads(denylist_text)
    except (UnicodeDecodeError, FileNotFoundError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, ensure_ascii=False))
        return 4

    sections = {
        "zh-TW": section(notices, "## 繁體中文", "## 简体中文"),
        "zh-CN": section(notices, "## 简体中文", "## English"),
        "en": section(notices, "## English", "## 日本語"),
        "ja": section(notices, "## 日本語", None),
    }
    required_by_language = {
        "zh-TW": [
            "原始碼僅保留作授權與來源證據",
            "完整推論管線已停用",
            "nvdiffrast",
            "Zero123++",
            "正式 24／600 產線",
        ],
        "zh-CN": [
            "源代码仅保留为许可与来源证据",
            "完整推理管线已停用",
            "nvdiffrast",
            "Zero123++",
            "正式 24／600 产线",
        ],
        "en": [
            "Source retained only as license and provenance evidence",
            "complete inference pipeline is disabled",
            "nvdiffrast",
            "Zero123++",
            "formal 24/600 pipeline",
        ],
        "ja": [
            "ソースはライセンスと来歴の証拠としてのみ保持します",
            "完全な推論パイプラインは無効",
            "nvdiffrast",
            "Zero123++",
            "正式な 24／600 パイプライン",
        ],
    }
    language_checks: dict[str, Any] = {}
    for language, text in sections.items():
        phrase_pass, missing = contains_all(text, required_by_language[language])
        language_checks[language] = {
            "pass": phrase_pass,
            "missing": missing,
            "instantmesh_count": text.count("InstantMesh"),
            "nvdiffrast_count": text.count("nvdiffrast"),
            "zero123plus_count": text.count("Zero123++"),
            "instantmesh_commit_count": text.count(INSTANTMESH_COMMIT),
            "biref_revision_count": text.count(BIREF_REVISION),
            "biref_mit_record_present": "BiRefNet" in text and "MIT" in text,
        }

    permanent_by_id = {item["id"]: item for item in denylist["permanent_denials"]}
    policy_checks = {
        "denylist_schema": denylist.get("schema") == "mohan.third-party-denylist.v1",
        "nvdiffrast_permanent_no_exceptions": permanent_by_id["nvdiffrast"].get("exceptions") == [],
        "zero123plus_permanent_no_exceptions": permanent_by_id["zero123plus-weights"].get("exceptions") == [],
        "instantmesh_source_evidence_only": denylist["pipeline_effect"]["instantmesh_source_code"] == "retained_apache_2_0_for_license_evidence_only_but_not_approved_as_a_complete_pipeline",
        "instantmesh_pipeline_disabled": denylist["pipeline_effect"]["instantmesh_end_to_end_pipeline"] == "disabled_because_it_requires_permanently_denied_components",
        "geometry_route_mhr_ufbx": denylist["pipeline_effect"]["approved_24_600_geometry_path"] == "MHR Apache-2.0 plus ufbx MIT Alternative A",
        "handoff_points_to_machine_denylist": "`THIRD_PARTY_DENYLIST.json` 是本專案機器可讀的永久禁用清單" in handoff,
        "handoff_nvdiffrast_absolute": "`nvdiffrast` 禁止再次下載、安裝、編譯、匯入、使用、封裝或發行；無例外" in handoff,
        "handoff_zero123plus_absolute": "`Zero123++`／`sudo-ai/zero123plus-v1.2` 模型權重禁止再次下載、快取、載入、使用、封裝或發行；無例外" in handoff,
        "handoff_instantmesh_evidence_only_pipeline_disabled": "InstantMesh 的 Apache-2.0 原始碼可保留作歷史來源證據，但依賴上述禁用元件的完整推論管線不得再進入正式 24／600 產線" in handoff,
        "handoff_geometry_route_mhr_ufbx": "正式幾何路線固定為 MHR（Apache-2.0）＋ufbx（MIT Alternative A）" in handoff,
    }

    protected_record_checks = {
        "biref_exact_revision_all_four_languages": all(
            item["biref_revision_count"] == 1 for item in language_checks.values()
        ),
        "biref_mit_all_four_languages": all(
            item["biref_mit_record_present"] for item in language_checks.values()
        ),
        "instantmesh_exact_commit_all_four_languages": all(
            item["instantmesh_commit_count"] == 1 for item in language_checks.values()
        ),
        "mhr_route_preserved_in_denylist_and_handoff": policy_checks["geometry_route_mhr_ufbx"] and policy_checks["handoff_geometry_route_mhr_ufbx"],
        "ufbx_alternative_a_preserved": "ufbx MIT Alternative A" in denylist_text and "ufbx（MIT Alternative A）" in handoff,
        "pypng_not_touched_by_targeted_notice_diff": True,
    }

    diff = run_git("diff", "--numstat", "--", str(NOTICES), str(DENYLIST), str(HANDOFF))
    status = run_git("status", "--short", "--", str(NOTICES), str(DENYLIST), str(HANDOFF))
    notices_diff = run_git("diff", "--unified=0", "--", str(NOTICES))
    changed_lines = [
        line for line in notices_diff["stdout"].splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    pypng_changed_lines = [line for line in changed_lines if "PyPNG" in line]
    mhr_changed_lines = [line for line in changed_lines if "MHR" in line]
    ufbx_changed_lines = [line for line in changed_lines if "ufbx" in line]
    protected_record_checks["pypng_not_touched_by_targeted_notice_diff"] = not pypng_changed_lines
    protected_record_checks["mhr_not_touched_by_targeted_notice_diff"] = not mhr_changed_lines
    protected_record_checks["ufbx_not_touched_by_targeted_notice_diff"] = not ufbx_changed_lines

    utf8_checks = {
        "notices_utf8_strict": True,
        "denylist_utf8_strict": True,
        "handoff_utf8_strict": True,
        "no_unicode_replacement_character": all("�" not in text for text in (notices, denylist_text, handoff)),
    }
    passed = (
        all(utf8_checks.values())
        and all(item["pass"] for item in language_checks.values())
        and all(policy_checks.values())
        and all(protected_record_checks.values())
        and diff["exit_code"] == 0
        and status["exit_code"] == 0
        and notices_diff["exit_code"] == 0
    )
    result = {
        "schema": "mohan.third-party-notices-instantmesh-consistency-audit/v1",
        "status": "PASS" if passed else "BLOCKED",
        "exit_code": 0 if passed else 4,
        "files": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (NOTICES, DENYLIST, HANDOFF)
        ],
        "utf8_checks": utf8_checks,
        "four_language_checks": language_checks,
        "policy_checks": policy_checks,
        "protected_record_checks": protected_record_checks,
        "diff_scope": {
            "targeted_numstat": diff,
            "targeted_status": status,
            "notice_changed_line_count": len(changed_lines),
            "notice_changed_terms": {
                "BiRefNet": sum("BiRefNet" in line for line in changed_lines),
                "InstantMesh": sum("InstantMesh" in line for line in changed_lines),
                "MHR": len(mhr_changed_lines),
                "ufbx": len(ufbx_changed_lines),
                "PyPNG": len(pypng_changed_lines),
            },
        },
        "documents_modified_by_audit": False,
    }
    output = OUT / "notices-instantmesh-consistency-audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = OUT / "REPORT.md"
    report.write_text(
        "# InstantMesh 四語第三方聲明一致性稽核\n\n"
        f"- 狀態：`{result['status']}`\n"
        f"- 退出碼：`{result['exit_code']}`\n"
        f"- 四語段落：`{', '.join(language_checks)}`\n"
        f"- UTF-8：`{'PASS' if all(utf8_checks.values()) else 'FAIL'}`\n"
        f"- 政策一致性：`{'PASS' if all(policy_checks.values()) else 'FAIL'}`\n"
        f"- 保護記錄：`{'PASS' if all(protected_record_checks.values()) else 'FAIL'}`\n"
        "- 本稽核未修改 THIRD_PARTY_NOTICES.md、THIRD_PARTY_DENYLIST.json 或 CODEX_PROJECT_HANDOFF.md。\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "exit_code": result["exit_code"], "output": str(output)}, ensure_ascii=False))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
