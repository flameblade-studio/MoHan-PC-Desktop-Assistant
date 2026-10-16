"""A stale asset cannot be overwritten and a failed set restores existing work."""
lazy import json
lazy from dataclasses import replace
lazy from pathlib import Path

lazy import pytest

lazy from tools.art_pipeline import approved_asset_install as installer


def prepare(root: Path, *, generic: bool = False):
    (root / "assets").mkdir()
    (root / "scratchpad").mkdir()
    old = root / "assets/old.png"
    old.write_bytes(b"existing uncommitted artwork")
    source = root / "scratchpad/new.png"
    source.write_bytes(b"approved replacement")
    approval = root / "scratchpad/approval.json"
    approval_payload = {
        "schema": (
            installer.GENERIC_APPROVAL_SCHEMA if generic else installer.APPROVAL_SCHEMA
        ),
        "owner_appearance_approved": True,
    }
    if generic:
        approval_payload["approved_targets"] = ["assets/old.png"]
    approval.write_text(json.dumps(approval_payload), encoding="utf-8")
    record = {"target": "assets/old.png", "source": "scratchpad/new.png",
              "before_sha256": installer.sha256(old), "sha256": installer.sha256(source)}
    plan = {"schema": installer.PLAN_SCHEMA, "status": "validated",
            "approval": {"path": "scratchpad/approval.json", "sha256": installer.sha256(approval)},
            "files": [record]}
    return old, source, plan


def save_plan(root, plan):
    path = root / "scratchpad/plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
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
    expected = {
        "schema": "mohan.approved-asset-installation.v1", "status": "installed",
        "plan_sha256": installer.sha256(save_plan(tmp_path, plan)),
        "approval": plan["approval"], "replaced_files": 1, "files": plan["files"],
    }
    assert (output / "receipt.json").read_text(encoding="utf-8") == (
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    )


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


def test_generic_approval_accepts_only_explicit_targets(tmp_path):
    old, source, plan = prepare(tmp_path, generic=True)
    output = tmp_path / "scratchpad/install"
    installer.install(tmp_path, save_plan(tmp_path, plan), output)
    assert old.read_bytes() == source.read_bytes()


def test_generic_approval_rejects_target_outside_approved_list(tmp_path):
    old, _, plan = prepare(tmp_path, generic=True)
    plan["files"][0]["target"] = "assets/not-approved.png"
    plan["files"][0]["before_sha256"] = None
    with pytest.raises(ValueError, match="outside owner approval"):
        installer.install(
            tmp_path,
            save_plan(tmp_path, plan),
            tmp_path / "scratchpad/install",
        )
    assert old.read_bytes() == b"existing uncommitted artwork"


def test_default_character_settings_preserve_existing_contract():
    settings = installer.DEFAULT_CHARACTER_SETTINGS
    assert settings.character_id == "flameblade.mohan"
    assert settings.plan_schema == installer.PLAN_SCHEMA
    assert settings.approval_schema == installer.APPROVAL_SCHEMA
    assert settings.generic_approval_schema == installer.GENERIC_APPROVAL_SCHEMA
    assert settings.receipt_schema == "mohan.approved-asset-installation.v1"
    assert (settings.target_root, settings.staging_root, settings.evidence_root) == (
        "assets", "scratchpad", "scratchpad",
    )


def test_fake_character_settings_drive_schemas_and_paths(tmp_path):
    settings = replace(
        installer.DEFAULT_CHARACTER_SETTINGS,
        character_id="example.test-character",
        plan_schema="example.asset-replacements.v1",
        approval_schema="example.owner-approved-installation.v1",
        generic_approval_schema="example.generic-owner-approval.v1",
        receipt_schema="example.asset-installation.v1",
        target_root="characters/example/assets",
        staging_root="work/example",
        evidence_root="receipts/example",
        owner_approval_field="approved_by_creator",
        approved_targets_field="targets",
    )
    target = tmp_path / "characters/example/assets/body.png"
    source = tmp_path / "work/example/replacement.png"
    approval = tmp_path / "work/example/approval.json"
    target.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    target.write_bytes(b"old example character")
    source.write_bytes(b"new example character")
    approval.write_text(json.dumps({
        "schema": settings.generic_approval_schema,
        "approved_by_creator": True,
        "targets": ["characters/example/assets/body.png"],
    }), encoding="utf-8")
    plan = {
        "schema": settings.plan_schema,
        "status": "validated",
        "approval": {
            "path": "work/example/approval.json",
            "sha256": installer.sha256(approval),
        },
        "files": [{
            "target": "characters/example/assets/body.png",
            "source": "work/example/replacement.png",
            "before_sha256": installer.sha256(target),
            "sha256": installer.sha256(source),
        }],
    }
    plan_path = tmp_path / "work/example/plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    output = tmp_path / "receipts/example/install"

    receipt = installer.install(
        tmp_path,
        plan_path,
        output,
        settings=settings,
    )

    assert target.read_bytes() == b"new example character"
    assert (output / "backup/characters/example/assets/body.png").read_bytes() == (
        b"old example character"
    )
    assert receipt["schema"] == "example.asset-installation.v1"


@pytest.mark.parametrize("relative", ["../escape", "C:relative", "C:/absolute", "assets\\other"])
def test_character_install_settings_reject_unsafe_roots(relative):
    with pytest.raises(ValueError):
        replace(installer.DEFAULT_CHARACTER_SETTINGS, evidence_root=relative)


def test_resolved_evidence_root_cannot_escape_project(tmp_path, monkeypatch):
    old, _, plan = prepare(tmp_path)
    output = tmp_path / "scratchpad/install"
    path = save_plan(tmp_path, plan)
    original = Path.resolve
    outside = tmp_path.parent / "outside-receipts"

    def resolve(self, *args, **kwargs):
        if self == tmp_path / "scratchpad":
            return outside
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError, match="root escapes"):
        installer.install(tmp_path, path, output)
    assert old.read_bytes() == b"existing uncommitted artwork"
    assert not output.exists()
