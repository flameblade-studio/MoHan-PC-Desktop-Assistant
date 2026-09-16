"""A stale asset cannot be overwritten and a failed set restores existing work."""
import json
from pathlib import Path

import pytest

from tools.art_pipeline import approved_asset_install as installer


def prepare(root: Path):
    (root / "assets").mkdir()
    (root / "scratchpad").mkdir()
    old = root / "assets/old.png"
    old.write_bytes(b"existing uncommitted artwork")
    source = root / "scratchpad/new.png"
    source.write_bytes(b"approved replacement")
    approval = root / "scratchpad/approval.json"
    approval.write_text(json.dumps({"schema": installer.APPROVAL_SCHEMA,
                                    "owner_appearance_approved": True}))
    record = {"target": "assets/old.png", "source": "scratchpad/new.png",
              "before_sha256": installer.sha256(old), "sha256": installer.sha256(source)}
    plan = {"schema": installer.PLAN_SCHEMA, "status": "validated",
            "approval": {"path": "scratchpad/approval.json", "sha256": installer.sha256(approval)},
            "files": [record]}
    return old, source, plan


def save_plan(root, plan):
    path = root / "scratchpad/plan.json"
    path.write_text(json.dumps(plan))
    return path


def test_stale_source_rejects_entire_plan_without_touching_existing_asset(tmp_path):
    old, source, plan = prepare(tmp_path)
    source.write_bytes(b"unreviewed change")
    with pytest.raises(ValueError, match="changed"):
        installer.install(tmp_path, save_plan(tmp_path, plan), tmp_path / "scratchpad/install")
    assert old.read_bytes() == b"existing uncommitted artwork"
    assert not (tmp_path / "scratchpad/install").exists()


def test_success_keeps_verified_backup_of_dirty_asset_and_writes_receipt(tmp_path):
    old, source, plan = prepare(tmp_path)
    output = tmp_path / "scratchpad/install"
    result = installer.install(tmp_path, save_plan(tmp_path, plan), output)
    assert result["status"] == "installed"
    assert old.read_bytes() == source.read_bytes()
    assert (output / "backup/assets/old.png").read_bytes() == b"existing uncommitted artwork"
    assert (output / "receipt.json").is_file()


def test_later_write_failure_rolls_back_previous_replacement(tmp_path, monkeypatch):
    old, _, plan = prepare(tmp_path)
    second = dict(plan["files"][0], target="assets/new.png", before_sha256=None)
    plan["files"].append(second)
    original_replace = installer._replace

    def fail_second(source, target):
        if target.name == "new.png":
            raise OSError("disk write failed")
        original_replace(source, target)

    monkeypatch.setattr(installer, "_replace", fail_second)
    output = tmp_path / "scratchpad/install"
    with pytest.raises(OSError, match="disk write failed"):
        installer.install(tmp_path, save_plan(tmp_path, plan), output)
    assert old.read_bytes() == b"existing uncommitted artwork"
    assert not (tmp_path / "assets/new.png").exists()
    assert (output / "rollback.json").is_file()
    assert not (output / "receipt.json").exists()
