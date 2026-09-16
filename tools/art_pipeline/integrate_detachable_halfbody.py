"""Guarded local installation of an authorized seven-pose detachable rig."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy import uuid
lazy from pathlib import Path

lazy from infrastructure.detachable_halfbody_assets import (
    PART_ORDER,
    POSES,
    SCHEMA,
    SHA256_HEX_LENGTH,
    load_detachable_halfbody_assets,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _inventory(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): _sha(path.read_bytes())
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def _remove_owned_directory(directory: Path, expected_parent: Path) -> None:
    if directory.is_symlink() or directory.resolve().parent != expected_parent.resolve():
        raise RuntimeError("Refusing to remove a directory outside the formal asset parent.")
    shutil.rmtree(directory)


def _verified_candidate(candidate: Path, expected_receipt_sha256: str) -> dict:
    receipt_path = candidate / "receipt.json"
    payload = receipt_path.read_bytes()
    if _sha(payload) != expected_receipt_sha256:
        raise ValueError("Final candidate receipt SHA-256 does not match authorization.")
    receipt = json.loads(payload)
    if (
        receipt.get("stage") != "detachable_candidates_repaired"
        or receipt.get("source_art_owner_approved") is not True
        or receipt.get("technical_seam_verified") is not True
        or receipt.get("formal_integration") is not False
    ):
        raise ValueError("Candidate lacks repaired seam evidence or is already integrated.")
    records = receipt.get("layers")
    if not isinstance(records, list) or len(records) != len(POSES) * len(PART_ORDER):
        raise ValueError("Final candidate requires exactly 49 pinned parts.")
    poses: dict[str, dict[str, dict[str, str]]] = {pose: {} for pose in POSES}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Final candidate part record must be an object.")
        pose, part = record.get("pose"), record.get("role")
        if pose not in POSES or part not in PART_ORDER or part in poses[pose]:
            raise ValueError("Duplicate or unknown final candidate part.")
        expected_path = f"{pose}/{part}.rgba.png"
        expected_hash = record.get("sha256")
        if record.get("output", "").replace("\\", "/") != expected_path:
            raise ValueError("Final candidate part path is outside its pose.")
        if not isinstance(expected_hash, str) or len(expected_hash) != SHA256_HEX_LENGTH:
            raise ValueError("Final candidate part lacks SHA-256.")
        if _sha((candidate / expected_path).read_bytes()) != expected_hash:
            raise ValueError(f"Final candidate part drifted: {expected_path}")
        poses[pose][part] = {"path": expected_path, "sha256": expected_hash}
    if any(set(parts) != set(PART_ORDER) for parts in poses.values()):
        raise ValueError("Final candidate has an incomplete pose.")
    return {"schema": SCHEMA, "source_receipt_sha256": expected_receipt_sha256, "poses": poses}


def _validate_paths(candidate: Path, destination: Path, backup_root: Path) -> tuple[Path, Path, Path]:
    candidate, destination, backup_root = map(Path, (candidate, destination, backup_root))
    candidate = candidate.resolve()
    destination = destination.resolve()
    backup_root = backup_root.resolve()
    if (
        candidate.is_relative_to(destination)
        or destination.is_relative_to(candidate)
        or backup_root.is_relative_to(destination)
        or destination.is_relative_to(backup_root)
    ):
        raise ValueError("Candidate and backup must be outside the formal rig directory.")
    if backup_root.is_relative_to(candidate):
        raise ValueError("Backup must be outside the candidate directory.")
    return candidate, destination, backup_root


def integrate_detachable_halfbody(
    candidate: Path,
    destination: Path,
    backup_root: Path,
    *,
    expected_receipt_sha256: str,
    owner_authorization_text: str,
) -> Path:
    """Install a SHA-bound rig; preserve old bytes and write receipt last."""
    candidate, destination, backup_root = _validate_paths(candidate, destination, backup_root)
    if not owner_authorization_text.strip():
        raise ValueError("Current owner authorization text is required.")
    if backup_root.exists():
        raise FileExistsError("Backup root must be new and empty.")
    manifest = _verified_candidate(candidate, expected_receipt_sha256)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.parent / f".{destination.name}.stage-{uuid.uuid4().hex}"
    old_inventory = _inventory(destination) if destination.exists() else None
    backup_root.mkdir(parents=True)
    backup = backup_root / "previous"
    moved_old = False
    installed = False
    try:
        stage.mkdir()
        for parts in manifest["poses"].values():
            for record in parts.values():
                relative = record["path"]
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate / relative, target)
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        load_detachable_halfbody_assets(stage)
        staged_inventory = _inventory(stage)
        if old_inventory is not None:
            if _inventory(destination) != old_inventory:
                raise RuntimeError("Formal rig changed concurrently before backup.")
            os.replace(destination, backup)
            moved_old = True
            if _inventory(backup) != old_inventory:
                raise RuntimeError("Backup readback differs from pre-install bytes.")
        elif destination.exists():
            raise RuntimeError("Formal rig appeared concurrently before installation.")
        os.replace(stage, destination)
        installed = True
        load_detachable_halfbody_assets(destination)
        if _inventory(destination) != staged_inventory:
            raise RuntimeError("Installed rig differs from staged bytes.")
        receipt = {
            "schema": "mohan.detachable-halfbody-integration.v1",
            "candidate_receipt_sha256": expected_receipt_sha256,
            "owner_authorization_text": owner_authorization_text,
            "technical_seam_verified": True,
            "human_repaired_appearance_approved": False,
            "previous": old_inventory,
            "installed": staged_inventory,
            "destination": str(destination.resolve()),
            "release": False,
        }
        output = backup_root / "integration-receipt.json"
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return output
    except Exception:
        if installed and _inventory(destination) == staged_inventory:
            _remove_owned_directory(destination, destination.parent)
        if moved_old and not destination.exists():
            os.replace(backup, destination)
        raise
    finally:
        if stage.exists():
            _remove_owned_directory(stage, destination.parent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("backup_root", type=Path)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--owner-authorization", required=True)
    args = parser.parse_args()
    receipt = integrate_detachable_halfbody(
        args.candidate,
        args.destination,
        args.backup_root,
        expected_receipt_sha256=args.receipt_sha256,
        owner_authorization_text=args.owner_authorization,
    )
    print(receipt)


if __name__ == "__main__":
    main()
