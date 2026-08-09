from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from db import StudioDB
lazy from profile_transfer import (
    PORTABLE_TABLES,
    PortableProfileManager,
    ProfileManifest,
    ProfileTransferError,
)


def seed_profile(db: StudioDB, prefix: str) -> None:
    now = "2026-07-31T12:00:00"
    db.set_setting("assistant_name", f"{prefix}墨寒")
    db.set_setting("organization_name", f"{prefix}工作室")
    db.set_setting("persona_prompt", f"{prefix}人格")
    db.set_setting("physics_hair", True)
    db.set_setting("work_folder", f"C:/{prefix}/work")
    db.set_setting("windows_voice", f"{prefix}-voice")
    db.set_setting("tool_permissions", f"{prefix}-permissions")
    db.conn.execute(
        "INSERT INTO todos(title,category,status,created_at) VALUES(?,?,?,?)",
        (f"{prefix}待辦", "文章", "待處理", now),
    )
    db.conn.execute(
        "INSERT INTO ideas(text,title,content,created_at,updated_at) "
        "VALUES(?,?,?,?,?)",
        (f"{prefix}靈感", f"{prefix}標題", f"{prefix}內容", now, now),
    )
    db.conn.execute(
        "INSERT INTO chat_log(role,content,created_at) VALUES(?,?,?)",
        ("user", f"{prefix}對話", now),
    )
    db.conn.execute(
        "INSERT INTO memories(category,title,content,source,importance,"
        "created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        ("偏好", f"{prefix}記憶", f"{prefix}內容", "manual", 5, now, now),
    )
    db.conn.execute(
        "INSERT INTO workflows(name,definition,enabled,created_at,updated_at) "
        "VALUES(?,?,?,?,?)",
        (f"{prefix}流程", "{}", 1, now, now),
    )
    db.add_allowed_target(
        "folder",
        f"{prefix}資料夾",
        f"C:/{prefix}/allowed",
        "read",
    )
    db.audit_event("profile-test", {"prefix": prefix})
    db.conn.commit()


def rewrite_manifest(
    source: Path,
    target: Path,
    *,
    database_bytes: bytes | None = None,
    add_extra: bool = False,
) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        profile = (
            database_bytes
            if database_bytes is not None
            else archive.read("profile.db")
        )
    manifest["database_sha256"] = hashlib.sha256(profile).hexdigest()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False),
        )
        archive.writestr("profile.db", profile)
        if add_extra:
            archive.writestr("../unexpected.txt", "blocked")


@dataclass(frozen=True, slots=True)
class TransferFixture:
    root: Path
    source_db: StudioDB
    target_db: StudioDB
    source_manager: PortableProfileManager
    target_manager: PortableProfileManager
    bundle: Path
    manifest: ProfileManifest


def _create_fixture(root: Path) -> TransferFixture:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    seed_profile(source_db, "筆電")
    seed_profile(target_db, "桌機")
    source_manager = PortableProfileManager(source_db, root / "source" / "backups")
    bundle, manifest = source_manager.export_profile(root / "墨寒外出進度")
    target_manager = PortableProfileManager(target_db, root / "target" / "backups")
    return TransferFixture(
        root,
        source_db,
        target_db,
        source_manager,
        target_manager,
        bundle,
        manifest,
    )


def _assert_export_manifest(fixture: TransferFixture) -> None:
    assert fixture.bundle.name.endswith(".mohan-profile")
    assert fixture.manifest.assistant_name == "筆電墨寒"
    assert len(fixture.manifest.snapshot_id) == 32
    assert len(fixture.manifest.source_installation_id) == 32
    assert set(PORTABLE_TABLES) <= set(fixture.manifest.record_counts)


def _assert_sanitized_export(fixture: TransferFixture) -> None:
    exported_db = fixture.root / "exported.db"
    with zipfile.ZipFile(fixture.bundle, "r") as archive:
        assert set(archive.namelist()) == {"manifest.json", "profile.db"}
        exported_db.write_bytes(archive.read("profile.db"))
    sanitized = sqlite3.connect(exported_db)
    try:
        settings = dict(sanitized.execute("SELECT key,value FROM settings"))
        assert json.loads(settings["assistant_name"]) == "筆電墨寒"
        assert json.loads(settings["physics_hair"]) is True
        assert "work_folder" not in settings
        assert "windows_voice" not in settings
        assert "tool_permissions" not in settings
        assert sanitized.execute(
            "SELECT COUNT(*) FROM allowed_targets"
        ).fetchone()[0] == 0
        assert sanitized.execute(
            "SELECT COUNT(*) FROM action_audit"
        ).fetchone()[0] == 0
    finally:
        sanitized.close()


def _assert_imported_profile(fixture: TransferFixture) -> None:
    result = fixture.target_manager.import_profile(fixture.bundle)
    target_db = fixture.target_db
    assert result.backup_path.is_file()
    assert result.backup_path.with_suffix(".json").is_file()
    assert target_db.setting("assistant_name") == "筆電墨寒"
    assert target_db.setting("persona_prompt") == "筆電人格"
    assert target_db.setting("work_folder") == "C:/桌機/work"
    assert target_db.setting("windows_voice") == "桌機-voice"
    assert target_db.setting("tool_permissions") == "桌機-permissions"
    assert target_db.conn.execute("SELECT title FROM todos").fetchone()[0] == (
        "筆電待辦"
    )
    assert target_db.conn.execute(
        "SELECT content FROM chat_log"
    ).fetchone()[0] == "筆電對話"
    assert target_db.conn.execute("SELECT title FROM memories").fetchone()[0] == (
        "筆電記憶"
    )
    assert target_db.allowed_targets("folder")[0]["display_name"] == "桌機資料夾"
    assert target_db.audit_rows()[0]["event_type"] == "profile-test"
    assert target_db.setting("portable_last_import_snapshot_id") == (
        fixture.manifest.snapshot_id
    )


def _create_corrupt_bundle(fixture: TransferFixture) -> Path:
    corrupt = fixture.root / "corrupt.mohan-profile"
    with zipfile.ZipFile(fixture.bundle, "r") as archive:
        manifest_payload = json.loads(archive.read("manifest.json"))
        profile_bytes = archive.read("profile.db") + b"tampered"
    with zipfile.ZipFile(corrupt, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest_payload))
        archive.writestr("profile.db", profile_bytes)
    return corrupt


def _assert_corrupt_bundle_rejected(fixture: TransferFixture) -> None:
    before = fixture.target_db.conn.execute(
        "SELECT content FROM chat_log"
    ).fetchone()[0]
    try:
        fixture.target_manager.import_profile(_create_corrupt_bundle(fixture))
    except ProfileTransferError:
        pass
    else:
        raise AssertionError("corrupt profile must be rejected")
    assert fixture.target_db.conn.execute(
        "SELECT content FROM chat_log"
    ).fetchone()[0] == before


def _assert_duplicate_snapshot_rejected(fixture: TransferFixture) -> None:
    try:
        fixture.target_manager.import_profile(fixture.bundle)
    except ProfileTransferError as exc:
        assert "已匯入過" in str(exc)
        return
    raise AssertionError("duplicate snapshots must be rejected")


def _install_rollback_trigger(db: StudioDB) -> None:
    db.conn.execute(
        "CREATE TRIGGER reject_portable_todo_delete "
        "BEFORE DELETE ON todos BEGIN "
        "SELECT RAISE(ABORT,'forced rollback'); END"
    )
    db.conn.commit()


def _assert_atomic_rollback(fixture: TransferFixture) -> None:
    fixture.source_db.set_setting("assistant_name", "第二份墨寒")
    second_bundle, second_manifest = fixture.source_manager.export_profile(
        fixture.root / "第二份外出進度"
    )
    previous_snapshot = fixture.target_db.setting(
        "portable_last_import_snapshot_id"
    )
    previous_name = fixture.target_db.setting("assistant_name")
    previous_chat = fixture.target_db.conn.execute(
        "SELECT content FROM chat_log"
    ).fetchone()[0]
    _install_rollback_trigger(fixture.target_db)
    try:
        fixture.target_manager.import_profile(second_bundle)
    except ProfileTransferError as exc:
        assert "forced rollback" in str(exc)
    else:
        raise AssertionError("forced import failure must be reported")
    assert second_manifest.snapshot_id != previous_snapshot
    assert fixture.target_db.setting("assistant_name") == previous_name
    assert fixture.target_db.setting("portable_last_import_snapshot_id") == (
        previous_snapshot
    )
    assert fixture.target_db.conn.execute(
        "SELECT content FROM chat_log"
    ).fetchone()[0] == previous_chat
    fixture.target_db.conn.execute("DROP TRIGGER reject_portable_todo_delete")
    fixture.target_db.conn.commit()


def _assert_unsafe_archive_rejected(fixture: TransferFixture) -> None:
    unsafe = fixture.root / "unsafe.mohan-profile"
    rewrite_manifest(fixture.bundle, unsafe, add_extra=True)
    try:
        fixture.target_manager.inspect_profile(unsafe)
    except ProfileTransferError:
        return
    raise AssertionError("unexpected archive entries must be rejected")


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        fixture = _create_fixture(Path(temp))
        try:
            _assert_export_manifest(fixture)
            _assert_sanitized_export(fixture)
            _assert_imported_profile(fixture)
            _assert_corrupt_bundle_rejected(fixture)
            _assert_duplicate_snapshot_rejected(fixture)
            _assert_atomic_rollback(fixture)
            _assert_unsafe_archive_rejected(fixture)
        finally:
            fixture.source_db.close()
            fixture.target_db.close()
    print("PROFILE_TRANSFER_OK")


if __name__ == "__main__":
    run()
