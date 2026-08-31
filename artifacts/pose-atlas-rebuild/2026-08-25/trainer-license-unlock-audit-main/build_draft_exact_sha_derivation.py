"""Build a draft-only, exact-SHA trainer derivation evidence package.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Flameblade Studio
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
WORKSPACE = Path(r"D:\FlamebladeStudio\CodexProjects")
ARTIFACTS = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25"
OUTPUT = ARTIFACTS / "trainer-license-unlock-audit-main"
TRAINER = ARTIFACTS / "flux-nf4-cached-single-step-agent-a/cached_single_step.py"
SOURCE = WORKSPACE / ".third-party-cache/diffusers-source-a949d3dd"
LICENSE = SOURCE / "LICENSE"
UPSTREAM = (
    SOURCE / "examples/dreambooth/train_dreambooth_lora_flux.py",
    SOURCE / "examples/dreambooth/train_dreambooth_flux.py",
)
PINNED_COMMIT = "a949d3dd906528363d2b61f7f0b38abaed4169ca"
PINNED_TRAINER_SHA256 = "41337722967D3566ED98BFB4CF421154E129AFF1A185C349230676BF432CBBE7"
PINNED_LICENSE_SHA256 = "E28423074EF718E6580A2C15459CDBF08D01EABAF0218754AD1B65DB0C1F4CB6"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def normalized(lines: list[str]) -> list[str]:
    return [
        value
        for raw in lines
        if (value := " ".join(raw.strip().split())) and not value.startswith("#")
    ]


def calls(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            target = item.func
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Attribute):
                parts = [target.attr]
                value = target.value
                while isinstance(value, ast.Attribute):
                    parts.append(value.attr)
                    value = value.value
                if isinstance(value, ast.Name):
                    parts.append(value.id)
                names.add(".".join(reversed(parts)))
    return names


def local_sections() -> list[dict[str, Any]]:
    text = TRAINER.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    upstream_text = [path.read_text(encoding="utf-8", errors="replace") for path in UPSTREAM]
    upstream_lines = [normalized(value.splitlines()) for value in upstream_text]
    upstream_trees = [ast.parse(value) for value in upstream_text]
    upstream_calls = [calls(tree) for tree in upstream_trees]
    sections = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        section_lines = normalized(lines[node.lineno - 1 : node.end_lineno])
        section_calls = calls(node)
        comparisons = []
        for path, candidate_lines, candidate_calls in zip(UPSTREAM, upstream_lines, upstream_calls):
            matcher = difflib.SequenceMatcher(a=section_lines, b=candidate_lines, autojunk=False)
            largest = max((block.size for block in matcher.get_matching_blocks()), default=0)
            nontrivial_shared_calls = sorted(
                name
                for name in section_calls & candidate_calls
                if "." in name or len(name) >= 12
            )
            comparisons.append(
                {
                    "upstream_path": str(path),
                    "upstream_sha256": sha256(path),
                    "exact_sequence_ratio": matcher.ratio(),
                    "longest_exact_contiguous_normalized_lines": largest,
                    "nontrivial_shared_calls": nontrivial_shared_calls,
                }
            )
        max_block = max(item["longest_exact_contiguous_normalized_lines"] for item in comparisons)
        copied_proven = max_block >= 5
        sections.append(
            {
                "name": node.name,
                "local_lines": [node.lineno, node.end_lineno],
                "classification": "COPIED" if copied_proven else "UNDETERMINED",
                "classification_basis": (
                    "At least five exact contiguous normalized lines match the pinned upstream."
                    if copied_proven
                    else (
                        "No nontrivial copied block was proven. API/algorithm correspondence cannot, "
                        "without authorship or change history, distinguish ADAPTED from INDEPENDENT."
                    )
                ),
                "adapted_proven": False,
                "independent_proven": False,
                "comparisons": comparisons,
            }
        )
    return sections


def main() -> int:
    actual = {
        "trainer_sha256": sha256(TRAINER),
        "license_sha256": sha256(LICENSE),
        "upstream_head": git("rev-parse", "HEAD", cwd=SOURCE),
        "upstream_status": git("status", "--porcelain=v1", cwd=SOURCE),
        "upstream_url": git("remote", "get-url", "origin", cwd=SOURCE),
        "trainer_git_status": git(
            "status", "--short", "--", TRAINER.relative_to(PROJECT).as_posix(), cwd=PROJECT
        ),
        "trainer_git_history": git(
            "log",
            "--follow",
            "--format=%H %aI %an %s",
            "--",
            TRAINER.relative_to(PROJECT).as_posix(),
            cwd=PROJECT,
        ),
    }
    if (
        actual["trainer_sha256"] != PINNED_TRAINER_SHA256
        or actual["license_sha256"] != PINNED_LICENSE_SHA256
        or actual["upstream_head"] != PINNED_COMMIT
        or actual["upstream_status"]
    ):
        raise RuntimeError(f"FAIL_CLOSED: pinned evidence drifted: {actual}")

    sections = local_sections()
    unresolved = [item["name"] for item in sections if item["classification"] == "UNDETERMINED"]
    copied = [item["name"] for item in sections if item["classification"] == "COPIED"]
    classification = {
        "whole_file": "UNDETERMINED" if unresolved else "COPIED" if copied else "INDEPENDENT",
        "copied_sections_proven": copied,
        "adapted_sections_proven": [],
        "independent_sections_proven": [],
        "undetermined_sections": unresolved,
        "rule": (
            "COPIED requires >=5 exact contiguous normalized lines. ADAPTED or INDEPENDENT requires "
            "accountable authorship/change-history evidence; structural similarity alone is insufficient."
        ),
    }
    report = {
        "schema": "mohan.trainer_section_derivation_classification.v1",
        "status": "BLOCK_UNDETERMINED_DERIVATION" if unresolved else "READY_FOR_OWNER_REVIEW",
        "exit_code": 4 if unresolved else 0,
        "scope": "Static local comparison only; no model load, training, network, deletion, or trainer mutation.",
        "actual": actual,
        "classification": classification,
        "sections": sections,
        "precise_gap": (
            "The trainer is untracked and has no Git history or signed maintainer attestation. "
            "Therefore ADAPTED versus INDEPENDENT cannot be proven for the unresolved sections."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT / "trainer-section-classification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sidecar = {
        "schema": "mohan.trainer_derivation_sidecar.v1",
        "status": "DRAFT_NOT_ADOPTED",
        "formal_admission": "BLOCK",
        "training_authorized": False,
        "trainer": {"path": str(TRAINER), "sha256": PINNED_TRAINER_SHA256},
        "upstream": {
            "name": "Hugging Face Diffusers",
            "url": actual["upstream_url"],
            "commit": PINNED_COMMIT,
            "license_spdx": "Apache-2.0",
            "license_path": str(LICENSE),
            "license_sha256": PINNED_LICENSE_SHA256,
            "candidate_files_not_author_attested": [
                {"path": str(path), "sha256": sha256(path)} for path in UPSTREAM
            ],
        },
        "local_modification_state": {
            "git_status": actual["trainer_git_status"],
            "git_history": actual["trainer_git_history"].splitlines()
            if actual["trainer_git_history"]
            else [],
            "modified_by": "UNVERIFIED",
            "modification_summary": "UNVERIFIED",
        },
        "classification": classification,
        "classification_report": {
            "path": str(report_path),
            "sha256": sha256(report_path),
        },
        "adoption_requirements": [
            "An accountable maintainer must attest copied/adapted/independent status per unresolved section.",
            "Exact upstream files actually consulted must be named; candidates are not proof.",
            "Local modification author and a truthful modification summary must be adopted.",
            "After adoption, recompute the sidecar SHA and pin it in the formal validator.",
        ],
    }
    sidecar_path = OUTPUT / "CACHED-TRAINER-DERIVATION-SIDECAR-DRAFT.json"
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    suggestion = f'''# DRAFT ONLY — DO NOT APPLY UNTIL OWNER/MAINTAINER ATTESTATION
# Suggested formal validator changes for review, not an adopted patch.
# Current exact trainer SHA: {PINNED_TRAINER_SHA256}
# Current draft sidecar SHA: {sha256(sidecar_path)}
# The placeholder below must be replaced only after status becomes ADOPTED.

@@ trainer provenance inputs @@
+    trainer_sidecar = ARTIFACTS / "trainer-license-unlock-audit-main/CACHED-TRAINER-DERIVATION-SIDECAR-DRAFT.json"
+    trainer_sidecar_file = check(
+        trainer_sidecar,
+        "<ADOPTED_SIDECAR_SHA256_AFTER_REVIEW>",
+    )
+    trainer_sidecar_data = json.loads(trainer_sidecar.read_text(encoding="utf-8")) if trainer_sidecar_file["exists"] else {{}}
     trainer_files = [
-        check(trainer, "437EE06299627BECA0E58486F584918164FD26566501EF387CABFBD0D9B603FF"),
+        check(trainer, "{PINNED_TRAINER_SHA256}"),
         check(trainer_license, "{PINNED_LICENSE_SHA256}", ("Apache License", "Version 2.0")),
+        trainer_sidecar_file,
     ]
-    trainer_pass = files_pass(trainer_files) and derivation_bound
+    trainer_pass = (
+        files_pass(trainer_files)
+        and trainer_sidecar_data.get("status") == "ADOPTED"
+        and trainer_sidecar_data.get("formal_admission") == "PASS"
+        and trainer_sidecar_data.get("trainer", {{}}).get("sha256") == sha256(trainer)
+        and trainer_sidecar_data.get("upstream", {{}}).get("commit") == "{PINNED_COMMIT}"
+        and trainer_sidecar_data.get("upstream", {{}}).get("license_spdx") == "Apache-2.0"
+        and trainer_sidecar_data.get("classification", {{}}).get("whole_file") != "UNDETERMINED"
+    )
'''
    (OUTPUT / "FORMAL-VALIDATOR-UPDATE-SUGGESTION.diff").write_text(suggestion, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
