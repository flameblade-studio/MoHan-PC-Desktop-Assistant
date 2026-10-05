"""Replace an owner-approved local asset set with pinned rollback copies."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy from dataclasses import dataclass
lazy from pathlib import Path


@dataclass(frozen=True, slots=True)
class AssetInstallCharacterSettings:
    """Character-owned schemas and roots for an approved asset installation."""

    character_id: str
    plan_schema: str
    approval_schema: str
    generic_approval_schema: str
    receipt_schema: str
    target_root: str
    staging_root: str
    evidence_root: str
    owner_approval_field: str = "owner_appearance_approved"
    approved_targets_field: str = "approved_targets"

    def __post_init__(self) -> None:
        values = (
            self.character_id,
            self.plan_schema,
            self.approval_schema,
            self.generic_approval_schema,
            self.receipt_schema,
            self.target_root,
            self.staging_root,
            self.evidence_root,
            self.owner_approval_field,
            self.approved_targets_field,
        )
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("角色安裝設定的 schema、路徑與欄位名稱必須是非空字串。")
        for value in (self.target_root, self.staging_root, self.evidence_root):
            path = Path(value)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"角色安裝根目錄必須是安全的相對路徑：{value}")


DEFAULT_CHARACTER_SETTINGS = AssetInstallCharacterSettings(
    character_id="flameblade.mohan",
    plan_schema="mohan.approved-asset-replacements.v1",
    approval_schema="mohan.four-look-owner-approved-installation.v1",
    generic_approval_schema="mohan.owner-approved-asset-installation.v1",
    receipt_schema="mohan.approved-asset-installation.v1",
    target_root="assets",
    staging_root="scratchpad",
    evidence_root="scratchpad",
)

# Public compatibility aliases keep existing plans and callers unchanged.
PLAN_SCHEMA = DEFAULT_CHARACTER_SETTINGS.plan_schema
APPROVAL_SCHEMA = DEFAULT_CHARACTER_SETTINGS.approval_schema
GENERIC_APPROVAL_SCHEMA = DEFAULT_CHARACTER_SETTINGS.generic_approval_schema


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


def _preflight(
    root: Path,
    plan: dict,
    settings: AssetInstallCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> list[tuple[dict, Path, Path]]:
    """Verify approval, evidence and every old/new file before making changes."""
    if plan.get("schema") != settings.plan_schema or plan.get("status") != "validated":
        raise ValueError("Only a validated replacement plan can be installed.")
    approval_pin = plan["approval"]
    approval_path = _path(root, approval_pin["path"], settings.staging_root)
    if sha256(approval_path) != approval_pin["sha256"]:
        raise ValueError("Owner approval pin changed.")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if approval.get(settings.owner_approval_field) is not True:
        raise ValueError("The replacement set lacks owner appearance approval.")
    approval_schema = approval.get("schema")
    approved_targets: set[str] | None = None
    if approval_schema == settings.generic_approval_schema:
        targets = approval.get(settings.approved_targets_field)
        if not isinstance(targets, list) or not targets or not all(
            isinstance(target, str) and target.startswith(settings.target_root + "/")
            for target in targets
        ):
            raise ValueError("Generic owner approval must list approved asset targets.")
        approved_targets = set(targets)
        if len(approved_targets) != len(targets):
            raise ValueError("Generic owner approval repeats an approved target.")
    elif approval_schema != settings.approval_schema:
        raise ValueError("The replacement set uses an unsupported approval schema.")
    for evidence in plan.get("validation", []):
        path = _path(root, evidence["path"], settings.staging_root)
        if sha256(path) != evidence["sha256"]:
            raise ValueError("Installation validation evidence changed.")
    records = plan.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Replacement plan has no files.")
    targets = set()
    resolved = []
    for record in records:
        if approved_targets is not None and record["target"] not in approved_targets:
            raise ValueError(f"Target is outside owner approval: {record['target']}")
        target = _path(root, record["target"], settings.target_root)
        source = _path(root, record["source"], settings.staging_root)
        if target in targets:
            raise ValueError("Replacement plan repeats a target.")
        targets.add(target)
        before = sha256(target) if target.exists() else None
        if before != record["before_sha256"] or sha256(source) != record["sha256"]:
            raise ValueError(f"Replacement source or target changed: {record['target']}")
        resolved.append((record, source, target))
    return resolved


def install(
    root: Path,
    plan_path: Path,
    output: Path,
    *,
    settings: AssetInstallCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict:
    """Preflight the entire set, back up current bytes, then replace atomically.

    Each file replacement is atomic. Any later failure restores every replaced
    file from the preflight snapshot; the completed receipt is written last.
    """
    root = root.resolve()
    output = output.resolve()
    evidence_root = (root / settings.evidence_root).resolve()
    if not output.is_relative_to(evidence_root):
        raise ValueError("Installation evidence must stay under project scratchpad.")
    if output.exists():
        raise FileExistsError("Installation evidence already exists; inspect it before resuming.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    resolved = _preflight(root, plan, settings)
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
    receipt = {"schema": settings.receipt_schema, "status": "installed",
               "plan_sha256": sha256(plan_path), "approval": plan["approval"],
               "replaced_files": len(written), "files": plan["files"]}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt
