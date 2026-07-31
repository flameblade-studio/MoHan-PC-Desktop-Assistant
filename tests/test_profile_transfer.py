from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import StudioDB
from profile_transfer import (
    PORTABLE_TABLES,
    PortableProfileManager,
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


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        source_db = StudioDB(root / "source" / "mohan.db")
        target_db = StudioDB(root / "target" / "mohan.db")
        seed_profile(source_db, "筆電")
        seed_profile(target_db, "桌機")

        source_manager = PortableProfileManager(
            source_db,
            root / "source" / "backups",
        )
        bundle, manifest = source_manager.export_profile(
            root / "墨寒外出進度"
        )
        assert bundle.name.endswith(".mohan-profile")
        assert manifest.assistant_name == "筆電墨寒"
        assert len(manifest.snapshot_id) == 32
        assert len(manifest.source_installation_id) == 32
        assert set(PORTABLE_TABLES) <= set(manifest.record_counts)

        with zipfile.ZipFile(bundle, "r") as archive:
            assert set(archive.namelist()) == {
                "manifest.json",
                "profile.db",
            }
            exported_db = root / "exported.db"
            exported_db.write_bytes(archive.read("profile.db"))
        sanitized = sqlite3.connect(exported_db)
        try:
            settings = dict(
                sanitized.execute("SELECT key,value FROM settings")
            )
            assert json.loads(settings["assistant_name"]) == "筆電墨寒"
            assert json.loads(settings["physics_hair"]) is True
            assert "work_folder" not in settings
            assert "windows_voice" not in settings
            assert "tool_permissions" not in settings
            assert (
                sanitized.execute(
                    "SELECT COUNT(*) FROM allowed_targets"
                ).fetchone()[0]
                == 0
            )
            assert (
                sanitized.execute(
                    "SELECT COUNT(*) FROM action_audit"
                ).fetchone()[0]
                == 0
            )
        finally:
            sanitized.close()

        target_manager = PortableProfileManager(
            target_db,
            root / "target" / "backups",
        )
        result = target_manager.import_profile(bundle)
        assert result.backup_path.is_file()
        assert result.backup_path.with_suffix(".json").is_file()
        assert target_db.setting("assistant_name") == "筆電墨寒"
        assert target_db.setting("persona_prompt") == "筆電人格"
        assert target_db.setting("work_folder") == "C:/桌機/work"
        assert target_db.setting("windows_voice") == "桌機-voice"
        assert target_db.setting("tool_permissions") == "桌機-permissions"
        assert target_db.conn.execute(
            "SELECT title FROM todos"
        ).fetchone()[0] == "筆電待辦"
        assert target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0] == "筆電對話"
        assert target_db.conn.execute(
            "SELECT title FROM memories"
        ).fetchone()[0] == "筆電記憶"
        assert target_db.allowed_targets("folder")[0][
            "display_name"
        ] == "桌機資料夾"
        assert target_db.audit_rows()[0]["event_type"] == "profile-test"
        assert (
            target_db.setting("portable_last_import_snapshot_id")
            == manifest.snapshot_id
        )

        before = target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0]
        corrupt = root / "corrupt.mohan-profile"
        with zipfile.ZipFile(bundle, "r") as archive:
            manifest_payload = json.loads(archive.read("manifest.json"))
            profile_bytes = archive.read("profile.db") + b"tampered"
        with zipfile.ZipFile(corrupt, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest_payload),
            )
            archive.writestr("profile.db", profile_bytes)
        try:
            target_manager.import_profile(corrupt)
        except ProfileTransferError:
            pass
        else:
            raise AssertionError("corrupt profile must be rejected")
        assert target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0] == before

        try:
            target_manager.import_profile(bundle)
        except ProfileTransferError as exc:
            assert "已匯入過" in str(exc)
        else:
            raise AssertionError("duplicate snapshots must be rejected")

        # A failure after settings replacement begins must roll back every
        # portable table and the new snapshot marker as one atomic operation.
        source_db.set_setting("assistant_name", "第二份墨寒")
        second_bundle, second_manifest = source_manager.export_profile(
            root / "第二份外出進度"
        )
        previous_snapshot = target_db.setting(
            "portable_last_import_snapshot_id"
        )
        previous_name = target_db.setting("assistant_name")
        previous_chat = target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0]
        target_db.conn.execute(
            "CREATE TRIGGER reject_portable_todo_delete "
            "BEFORE DELETE ON todos BEGIN "
            "SELECT RAISE(ABORT,'forced rollback'); END"
        )
        target_db.conn.commit()
        try:
            target_manager.import_profile(second_bundle)
        except ProfileTransferError as exc:
            assert "forced rollback" in str(exc)
        else:
            raise AssertionError("forced import failure must be reported")
        assert second_manifest.snapshot_id != previous_snapshot
        assert target_db.setting("assistant_name") == previous_name
        assert (
            target_db.setting("portable_last_import_snapshot_id")
            == previous_snapshot
        )
        assert target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0] == previous_chat
        target_db.conn.execute("DROP TRIGGER reject_portable_todo_delete")
        target_db.conn.commit()

        unsafe = root / "unsafe.mohan-profile"
        rewrite_manifest(bundle, unsafe, add_extra=True)
        try:
            target_manager.inspect_profile(unsafe)
        except ProfileTransferError:
            pass
        else:
            raise AssertionError("unexpected archive entries must be rejected")

        source_db.close()
        target_db.close()
    print("PROFILE_TRANSFER_OK")


if __name__ == "__main__":
    run()
