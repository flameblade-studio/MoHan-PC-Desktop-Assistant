"""Replace an owner-approved local asset set with pinned rollback copies."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

PLAN_SCHEMA = "mohan.approved-asset-replacements.v1"
APPROVAL_SCHEMA = "mohan.four-look-owner-approved-installation.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(root: Path, relative: str, prefix: str) -> Path:
    if not isinstance(relative, str) or not relative.startswith(prefix + "/"):
        raise ValueError(f"Asset path must begin with {prefix}/")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or ".." in Path(relative).parts:
        raise ValueError("Asset path escapes the project.")
    return candidate


def _replace(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".approved-replacement.tmp")
    if temporary.exists():
        raise FileExistsError(temporary)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _preflight(root: Path, plan: dict) -> list[tuple[dict, Path, Path]]:
    """Verify approval, evidence and every old/new file before making changes."""
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "validated":
        raise ValueError("Only a validated replacement plan can be installed.")
    approval_pin = plan["approval"]
    approval_path = _path(root, approval_pin["path"], "scratchpad")
    if sha256(approval_path) != approval_pin["sha256"]:
        raise ValueError("Owner approval pin changed.")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if approval.get("schema") != APPROVAL_SCHEMA or approval.get("owner_appearance_approved") is not True:
        raise ValueError("The replacement set lacks owner appearance approval.")
    for evidence in plan.get("validation", []):
        path = _path(root, evidence["path"], "scratchpad")
        if sha256(path) != evidence["sha256"]:
            raise ValueError("Installation validation evidence changed.")
    records = plan.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Replacement plan has no files.")
    targets = set()
    resolved = []
    for record in records:
        target = _path(root, record["target"], "assets")
        source = _path(root, record["source"], "scratchpad")
        if target in targets:
            raise ValueError("Replacement plan repeats a target.")
        targets.add(target)
        before = sha256(target) if target.exists() else None
        if before != record["before_sha256"] or sha256(source) != record["sha256"]:
            raise ValueError(f"Replacement source or target changed: {record['target']}")
        resolved.append((record, source, target))
    return resolved


def install(root: Path, plan_path: Path, output: Path) -> dict:
    """Preflight the entire set, back up current bytes, then replace atomically.

    Each file replacement is atomic. Any later failure restores every replaced
    file from the preflight snapshot; the completed receipt is written last.
    """
    root = root.resolve()
    output = output.resolve()
    if not output.is_relative_to(root / "scratchpad"):
        raise ValueError("Installation evidence must stay under project scratchpad.")
    if output.exists():
        raise FileExistsError("Installation evidence already exists; inspect it before resuming.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    resolved = _preflight(root, plan)
    output.mkdir(parents=True)
    shutil.copy2(plan_path, output / "plan.json")
    for record, _, target in resolved:
        if record["before_sha256"] is not None:
            backup = output / "backup" / record["target"]
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            if sha256(backup) != record["before_sha256"]:
                raise ValueError("Rollback backup verification failed before replacement.")
    written = []
    try:
        for record, source, target in resolved:
            if (sha256(target) if target.exists() else None) != record["before_sha256"]:
                raise ValueError("A target changed after preflight.")
            _replace(source, target)
            written.append((record, target))
            if sha256(target) != record["sha256"]:
                raise ValueError("Installed asset differs from its staged source.")
    except Exception:
        for record, target in reversed(written):
            if record["before_sha256"] is None:
                target.unlink()
            else:
                _replace(output / "backup" / record["target"], target)
        (output / "rollback.json").write_text(json.dumps({"restored_files": len(written)}), encoding="utf-8")
        raise
    receipt = {"schema": "mohan.approved-asset-installation.v1", "status": "installed",
               "plan_sha256": sha256(plan_path), "approval": plan["approval"],
               "replaced_files": len(written), "files": plan["files"]}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt
