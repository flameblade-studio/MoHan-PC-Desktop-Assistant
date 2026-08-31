"""Audit the local FLUX LoRA trainer provenance without mutating it.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Flameblade Studio
"""

from __future__ import annotations

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
UPSTREAM_FILES = (
    SOURCE / "examples/dreambooth/train_dreambooth_lora_flux.py",
    SOURCE / "examples/dreambooth/train_dreambooth_flux.py",
)
EXPECTED_COMMIT = "a949d3dd906528363d2b61f7f0b38abaed4169ca"
UPSTREAM_URL = "https://github.com/huggingface/diffusers.git"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def run_git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def normalized_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        normalized = " ".join(raw.strip().split())
        if normalized and not normalized.startswith("#"):
            lines.append(normalized)
    return lines


def similarity(trainer: Path, upstream: Path) -> dict[str, Any]:
    trainer_lines = normalized_lines(trainer)
    upstream_lines = normalized_lines(upstream)
    matcher = difflib.SequenceMatcher(a=trainer_lines, b=upstream_lines, autojunk=False)
    blocks = sorted(matcher.get_matching_blocks(), key=lambda block: block.size, reverse=True)
    shared_unique = sorted(set(trainer_lines) & set(upstream_lines))
    material_shared = [line for line in shared_unique if len(line) >= 24]
    return {
        "upstream_path": str(upstream),
        "upstream_sha256": sha256(upstream),
        "trainer_normalized_line_count": len(trainer_lines),
        "upstream_normalized_line_count": len(upstream_lines),
        "sequence_matcher_ratio": matcher.ratio(),
        "longest_contiguous_matching_block_lines": blocks[0].size if blocks else 0,
        "shared_unique_normalized_lines": len(shared_unique),
        "material_shared_lines_24plus_chars": material_shared,
        "interpretation": (
            "Similarity and shared API idioms can support a derivation review, "
            "but cannot prove which upstream file was actually consulted."
        ),
    }


def line_locations(path: Path, needles: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        needle: [
            {"line": number, "text": text.strip()}
            for number, text in enumerate(lines, start=1)
            if needle in text
        ]
        for needle in needles
    }


def main() -> int:
    required = [TRAINER, SOURCE, LICENSE, *UPSTREAM_FILES]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        report = {
            "schema": "mohan.trainer_derivation_audit.v1",
            "decision": "FAIL_CLOSED_MISSING_LOCAL_EVIDENCE",
            "exit_code": 4,
            "missing": missing,
            "training_authorized": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 4

    trainer_text = TRAINER.read_text(encoding="utf-8", errors="replace")
    license_text = LICENSE.read_text(encoding="utf-8", errors="strict")
    head = run_git("rev-parse", "HEAD", cwd=SOURCE)
    remote = run_git("remote", "get-url", "origin", cwd=SOURCE)
    status = run_git("status", "--porcelain=v1", "--untracked-files=all", cwd=SOURCE)
    describe = run_git("describe", "--tags", "--always", "--dirty", cwd=SOURCE)
    commit_details = run_git(
        "show", "-s", "--format=%H%n%aI%n%an%n%ae%n%s", "HEAD", cwd=SOURCE
    ).splitlines()
    trainer_relative = TRAINER.relative_to(PROJECT).as_posix()
    trainer_status = run_git("status", "--short", "--", trainer_relative, cwd=PROJECT)
    trainer_tracked = bool(run_git("ls-files", "--", trainer_relative, cwd=PROJECT))
    trainer_history = run_git(
        "log", "--follow", "--format=%H %aI %an %s", "--", trainer_relative, cwd=PROJECT
    )

    binding = {
        "spdx_header_present": "SPDX-License-Identifier: Apache-2.0" in trainer_text,
        "upstream_commit_present": EXPECTED_COMMIT in trainer_text,
        "upstream_url_present": UPSTREAM_URL in trainer_text,
        "local_modifier_present": "Flameblade Studio" in trainer_text,
        "exact_upstream_files_declared": all(path.name in trainer_text for path in UPSTREAM_FILES),
        "local_changes_declared": "Local modifications" in trainer_text,
    }
    checkout_verified = (
        head == EXPECTED_COMMIT
        and remote == UPSTREAM_URL
        and status == ""
        and "Apache License" in license_text
        and "Version 2.0" in license_text
    )
    derivation_binding_verified = all(binding.values())
    trainer_lineage_verified = trainer_tracked and bool(trainer_history)
    unlock = checkout_verified and derivation_binding_verified and trainer_lineage_verified
    gaps = []
    if not derivation_binding_verified:
        gaps.append(
            "The executable trainer does not bind an SPDX expression, upstream URL/commit, exact consulted files, modifier, and local-change declaration."
        )
    if not trainer_tracked:
        gaps.append("The executable trainer is untracked in the project Git worktree.")
    if not trainer_history:
        gaps.append("No Git history proves the trainer's authorship or derivation lineage.")
    gaps.append(
        "Text similarity is not authorship evidence; an accountable maintainer must attest whether code was copied, adapted, or independently implemented."
    )

    functional_needles = (
        "LoraConfig(",
        'init_lora_weights="gaussian"',
        ".add_adapter(",
        "get_peft_model_state_dict",
        "FluxPipeline._prepare_latent_image_ids",
        "FluxPipeline._pack_latents",
        "noise - clean",
        "noise - model_input",
    )
    report = {
        "schema": "mohan.trainer_derivation_audit.v1",
        "decision": "PASS_TRAINER_PROVENANCE_UNLOCK" if unlock else "FAIL_CLOSED_INSUFFICIENT_DERIVATION_BINDING",
        "exit_code": 0 if unlock else 4,
        "scope": "Read-only trainer provenance audit; no model load, training, download, deletion, or trainer mutation.",
        "training_authorized": False,
        "trainer": {
            "path": str(TRAINER),
            "sha256": sha256(TRAINER),
            "git_status": trainer_status,
            "git_tracked": trainer_tracked,
            "git_history": trainer_history.splitlines() if trainer_history else [],
            "binding": binding,
        },
        "upstream": {
            "name": "Hugging Face Diffusers",
            "url": remote,
            "expected_url": UPSTREAM_URL,
            "head_commit": head,
            "expected_commit": EXPECTED_COMMIT,
            "nearest_tag_description": describe,
            "checkout_porcelain_status": status,
            "checkout_clean": status == "",
            "commit": {
                "sha": commit_details[0],
                "author_date": commit_details[1],
                "author_name": commit_details[2],
                "author_email": commit_details[3],
                "subject": commit_details[4],
            },
            "spdx_concluded": "Apache-2.0",
            "spdx_basis": [
                "Root LICENSE is the complete Apache License Version 2.0 text.",
                "setup.py declares license='Apache 2.0 License' and the Apache Software License classifier.",
                "README.md states the repository is licensed under Apache License Version 2.0.",
            ],
            "license_path": str(LICENSE),
            "license_sha256": sha256(LICENSE),
            "license_full_text": license_text,
            "relevant_files": [
                {"path": str(path), "sha256": sha256(path)} for path in UPSTREAM_FILES
            ],
        },
        "similarity_evidence": [similarity(TRAINER, path) for path in UPSTREAM_FILES],
        "functional_correspondence": {
            "purpose": "Line-located API/algorithm correspondence; not proof of authorship.",
            "trainer": line_locations(TRAINER, functional_needles),
            "upstream": {
                str(path): line_locations(path, functional_needles) for path in UPSTREAM_FILES
            },
        },
        "checks": {
            "upstream_checkout_verified": checkout_verified,
            "derivation_binding_verified": derivation_binding_verified,
            "trainer_lineage_verified": trainer_lineage_verified,
        },
        "blocking_gaps": gaps if not unlock else [],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    license_copy = OUTPUT / "DIFFUSERS-LICENSE-Apache-2.0.txt"
    license_copy.write_bytes(LICENSE.read_bytes())
    report["upstream"]["license_evidence_copy"] = {
        "path": str(license_copy),
        "sha256": sha256(license_copy),
    }
    output = OUTPUT / "trainer-derivation-audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
