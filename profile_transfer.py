from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backup_manager import BackupManager
from contracts import ProfileDatabasePort


PROFILE_EXTENSION = ".mohan-profile"
PROFILE_FORMAT_VERSION = 1
MAX_PROFILE_BYTES = 128 * 1024 * 1024

# These tables describe the user's continuing relationship and work progress.
# Machine permissions, OAuth state, audit logs and paired devices intentionally
# remain local to each computer.
PORTABLE_TABLES = (
    "todos",
    "ideas",
    "work_sessions",
    "reminders",
    "platform_progress",
    "chat_log",
    "memories",
    "workflows",
)

PORTABLE_SETTING_KEYS = frozenset(
    {
        "ai_model",
        "assistant_name",
        "auto_memory",
        "break_minutes",
        "cloud_voice",
        "mode",
        "onboarding_complete",
        "organization_name",
        "persona_prompt",
        "proactive_mode",
        "realtime_echo_guard",
        "realtime_model",
        "realtime_voice",
        "transcription_language",
        "transcription_prompt",
        "tts_enabled",
        "tts_voice",
        "ui_language",
        "user_title",
        "voice_engine",
        "voice_instructions",
        "voice_muted",
        "voice_rate",
        "voice_volume_percent",
        "wake_word",
        "window_title",
        "work_type",
    }
)
PORTABLE_SETTING_PREFIXES = (
    "physics_",
    "reminder_message_",
)


class ProfileTransferError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProfileManifest:
    created_at: str
    snapshot_id: str
    source_installation_id: str
    assistant_name: str
    organization_name: str
    record_counts: dict[str, int]


@dataclass(frozen=True)
class ProfileImportResult:
    manifest: ProfileManifest
    backup_path: Path
    imported_counts: dict[str, int]


def is_portable_setting(key: str) -> bool:
    return key in PORTABLE_SETTING_KEYS or key.startswith(
        PORTABLE_SETTING_PREFIXES
    )


def normalized_profile_path(path: Path) -> Path:
    if path.name.lower().endswith(PROFILE_EXTENSION):
        return path
    return path.with_name(path.name + PROFILE_EXTENSION)


class PortableProfileManager:
    """Move user progress without moving machine-bound permissions or secrets."""

    def __init__(self, db: ProfileDatabasePort, backup_dir: Path):
        self.db = db
        self.backup_dir = backup_dir

    @staticmethod
    def _table_columns(
        connection: sqlite3.Connection,
        table: str,
    ) -> list[sqlite3.Row]:
        return list(connection.execute(f'PRAGMA table_info("{table}")'))

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    @staticmethod
    def _manifest_from_payload(payload: dict[str, Any]) -> ProfileManifest:
        if int(payload.get("format_version", 0)) != PROFILE_FORMAT_VERSION:
            raise ProfileTransferError("攜帶檔版本不受支援。")
        counts = payload.get("record_counts")
        if not isinstance(counts, dict):
            raise ProfileTransferError("攜帶檔缺少資料筆數資訊。")
        try:
            normalized_counts = {
                str(key): max(0, int(value))
                for key, value in counts.items()
            }
        except (TypeError, ValueError) as exc:
            raise ProfileTransferError("攜帶檔資料筆數格式錯誤。") from exc
        return ProfileManifest(
            created_at=str(payload.get("created_at", "")),
            snapshot_id=str(payload.get("snapshot_id", ""))[:64],
            source_installation_id=str(
                payload.get("source_installation_id", "")
            )[:64],
            assistant_name=str(payload.get("assistant_name", "")),
            organization_name=str(payload.get("organization_name", "")),
            record_counts=normalized_counts,
        )

    def export_profile(self, target: Path) -> tuple[Path, ProfileManifest]:
        target = normalized_profile_path(Path(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        source_installation_id = str(
            self.db.setting("portable_installation_id", "")
        ).strip()
        if not source_installation_id:
            source_installation_id = uuid.uuid4().hex
            self.db.set_setting(
                "portable_installation_id",
                source_installation_id,
            )
        self.db.conn.commit()

        with TemporaryDirectory(prefix="mohan-profile-export-") as temp:
            snapshot_path = Path(temp) / "profile.db"
            destination = sqlite3.connect(snapshot_path)
            try:
                self.db.conn.backup(destination)
            finally:
                destination.close()

            snapshot = sqlite3.connect(snapshot_path)
            snapshot.row_factory = sqlite3.Row
            try:
                snapshot.execute("PRAGMA trusted_schema=OFF")
                setting_rows = list(
                    snapshot.execute("SELECT key FROM settings")
                )
                nonportable = [
                    (str(row["key"]),)
                    for row in setting_rows
                    if not is_portable_setting(str(row["key"]))
                ]
                if nonportable:
                    snapshot.executemany(
                        "DELETE FROM settings WHERE key=?",
                        nonportable,
                    )
                for table in (
                    "action_audit",
                    "connector_profiles",
                    "allowed_targets",
                    "paired_devices",
                ):
                    if table in self._table_names(snapshot):
                        snapshot.execute(f'DELETE FROM "{table}"')
                snapshot.commit()
                snapshot.execute("PRAGMA journal_mode=DELETE")
                integrity = snapshot.execute(
                    "PRAGMA integrity_check"
                ).fetchone()
                if not integrity or integrity[0] != "ok":
                    raise ProfileTransferError("匯出資料庫完整性檢查失敗。")
                counts = {
                    table: int(
                        snapshot.execute(
                            f'SELECT COUNT(*) FROM "{table}"'
                        ).fetchone()[0]
                    )
                    for table in PORTABLE_TABLES
                }
                counts["settings"] = int(
                    snapshot.execute(
                        "SELECT COUNT(*) FROM settings"
                    ).fetchone()[0]
                )
                profile: dict[str, str] = {}
                for row in snapshot.execute(
                    "SELECT key,value FROM settings "
                    "WHERE key IN ('assistant_name','organization_name')"
                ):
                    try:
                        decoded = json.loads(str(row["value"]))
                    except json.JSONDecodeError:
                        decoded = ""
                    profile[str(row["key"])] = str(decoded or "")
            finally:
                snapshot.close()

            database_hash = hashlib.sha256(
                snapshot_path.read_bytes()
            ).hexdigest()
            created_at = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
            manifest_payload = {
                "format": "mohan-portable-profile",
                "format_version": PROFILE_FORMAT_VERSION,
                "created_at": created_at,
                "snapshot_id": uuid.uuid4().hex,
                "source_installation_id": source_installation_id,
                "assistant_name": profile.get("assistant_name", ""),
                "organization_name": profile.get("organization_name", ""),
                "record_counts": counts,
                "database_sha256": database_hash,
                "secrets_included": False,
                "machine_permissions_included": False,
            }
            manifest = self._manifest_from_payload(manifest_payload)
            temporary_target = target.with_name(target.name + ".tmp")
            temporary_target.unlink(missing_ok=True)
            try:
                with zipfile.ZipFile(
                    temporary_target,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                ) as archive:
                    archive.writestr(
                        "manifest.json",
                        json.dumps(
                            manifest_payload,
                            ensure_ascii=False,
                            indent=2,
                        ).encode("utf-8"),
                    )
                    archive.write(snapshot_path, "profile.db")
                temporary_target.replace(target)
            finally:
                temporary_target.unlink(missing_ok=True)
        return target, manifest

    def inspect_profile(
        self,
        source: Path,
    ) -> tuple[ProfileManifest, Path, TemporaryDirectory]:
        source = Path(source)
        if not source.is_file():
            raise ProfileTransferError("找不到指定的墨寒攜帶檔。")
        if source.stat().st_size > MAX_PROFILE_BYTES:
            raise ProfileTransferError("攜帶檔超過安全大小限制。")

        temporary = TemporaryDirectory(prefix="mohan-profile-import-")
        try:
            with zipfile.ZipFile(source, "r") as archive:
                entries = archive.infolist()
                names = {entry.filename for entry in entries}
                if names != {"manifest.json", "profile.db"}:
                    raise ProfileTransferError(
                        "攜帶檔內容不完整，或含有非預期檔案。"
                    )
                if any(
                    entry.file_size > MAX_PROFILE_BYTES
                    or entry.filename.startswith(("/", "\\"))
                    or ".." in Path(entry.filename).parts
                    for entry in entries
                ):
                    raise ProfileTransferError("攜帶檔包含不安全的路徑或大小。")
                manifest_payload = json.loads(
                    archive.read("manifest.json").decode("utf-8")
                )
                database_bytes = archive.read("profile.db")
            if not isinstance(manifest_payload, dict):
                raise ProfileTransferError("攜帶檔描述格式錯誤。")
            manifest = self._manifest_from_payload(manifest_payload)
            expected_hash = str(
                manifest_payload.get("database_sha256", "")
            )
            actual_hash = hashlib.sha256(database_bytes).hexdigest()
            if not expected_hash or actual_hash != expected_hash:
                raise ProfileTransferError("攜帶檔雜湊驗證失敗，檔案可能已損毀。")

            database_path = Path(temporary.name) / "profile.db"
            database_path.write_bytes(database_bytes)
            incoming = sqlite3.connect(
                f"file:{database_path}?mode=ro",
                uri=True,
            )
            try:
                incoming.execute("PRAGMA trusted_schema=OFF")
                integrity = incoming.execute(
                    "PRAGMA integrity_check"
                ).fetchone()
                if not integrity or integrity[0] != "ok":
                    raise ProfileTransferError("攜帶檔資料庫完整性檢查失敗。")
                required_tables = set(PORTABLE_TABLES) | {"settings"}
                missing = required_tables - self._table_names(incoming)
                if missing:
                    raise ProfileTransferError(
                        "攜帶檔缺少必要資料表："
                        + "、".join(sorted(missing))
                    )
                actual_counts = {
                    table: int(
                        incoming.execute(
                            f'SELECT COUNT(*) FROM "{table}"'
                        ).fetchone()[0]
                    )
                    for table in PORTABLE_TABLES
                }
                actual_counts["settings"] = int(
                    incoming.execute(
                        "SELECT COUNT(*) FROM settings"
                    ).fetchone()[0]
                )
                if any(
                    manifest.record_counts.get(table) != count
                    for table, count in actual_counts.items()
                ):
                    raise ProfileTransferError(
                        "攜帶檔描述與實際資料筆數不一致。"
                    )
            finally:
                incoming.close()
            return manifest, database_path, temporary
        except (
            zipfile.BadZipFile,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:
            temporary.cleanup()
            raise ProfileTransferError("攜帶檔不是有效的墨寒進度檔。") from exc
        except Exception:
            temporary.cleanup()
            raise

    def import_profile(self, source: Path) -> ProfileImportResult:
        manifest, database_path, temporary = self.inspect_profile(source)
        try:
            last_snapshot_id = str(
                self.db.setting("portable_last_import_snapshot_id", "")
            )
            if (
                manifest.snapshot_id
                and manifest.snapshot_id == last_snapshot_id
            ):
                raise ProfileTransferError(
                    "這份攜帶檔已匯入過；為避免覆蓋較新的進度，"
                    "本次未重複匯入。"
                )
            incoming = sqlite3.connect(
                f"file:{database_path}?mode=ro",
                uri=True,
            )
            incoming.row_factory = sqlite3.Row
            try:
                incoming.execute("PRAGMA trusted_schema=OFF")
                table_payloads: dict[
                    str,
                    tuple[list[str], list[tuple[Any, ...]]],
                ] = {}
                for table in PORTABLE_TABLES:
                    target_info = self._table_columns(self.db.conn, table)
                    source_names = {
                        str(row["name"])
                        for row in self._table_columns(incoming, table)
                    }
                    columns = [
                        str(row["name"])
                        for row in target_info
                        if str(row["name"]) in source_names
                    ]
                    required_missing = [
                        str(row["name"])
                        for row in target_info
                        if bool(row["notnull"])
                        and row["dflt_value"] is None
                        and not bool(row["pk"])
                        and str(row["name"]) not in source_names
                    ]
                    if required_missing:
                        raise ProfileTransferError(
                            f"{table} 缺少必要欄位："
                            + "、".join(required_missing)
                        )
                    quoted = ",".join(
                        f'"{column}"' for column in columns
                    )
                    rows = [
                        tuple(row[column] for column in columns)
                        for row in incoming.execute(
                            f'SELECT {quoted} FROM "{table}"'
                        )
                    ]
                    table_payloads[table] = (columns, rows)

                setting_rows = [
                    (str(row["key"]), str(row["value"]))
                    for row in incoming.execute(
                        "SELECT key,value FROM settings"
                    )
                    if is_portable_setting(str(row["key"]))
                ]
            finally:
                incoming.close()

            backup = BackupManager(self.db, self.backup_dir).create(
                "before-portable-import"
            )
            imported_counts: dict[str, int] = {}
            with self.db.conn:
                current_setting_keys = [
                    str(row[0])
                    for row in self.db.conn.execute(
                        "SELECT key FROM settings"
                    )
                ]
                portable_current = [
                    (key,)
                    for key in current_setting_keys
                    if is_portable_setting(key)
                ]
                if portable_current:
                    self.db.conn.executemany(
                        "DELETE FROM settings WHERE key=?",
                        portable_current,
                    )
                self.db.conn.executemany(
                    "INSERT INTO settings(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    setting_rows,
                )
                imported_counts["settings"] = len(setting_rows)
                if manifest.snapshot_id:
                    self.db.conn.execute(
                        "INSERT INTO settings(key,value) VALUES(?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (
                            "portable_last_import_snapshot_id",
                            json.dumps(manifest.snapshot_id),
                        ),
                    )
                if manifest.created_at:
                    self.db.conn.execute(
                        "INSERT INTO settings(key,value) VALUES(?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (
                            "portable_last_import_created_at",
                            json.dumps(manifest.created_at),
                        ),
                    )

                for table, (columns, rows) in table_payloads.items():
                    self.db.conn.execute(f'DELETE FROM "{table}"')
                    if rows:
                        quoted = ",".join(
                            f'"{column}"' for column in columns
                        )
                        placeholders = ",".join("?" for _ in columns)
                        self.db.conn.executemany(
                            f'INSERT INTO "{table}"({quoted}) '
                            f"VALUES({placeholders})",
                            rows,
                        )
                    imported_counts[table] = len(rows)
                integrity = self.db.conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()
                if not integrity or integrity[0] != "ok":
                    raise ProfileTransferError("匯入後資料庫完整性檢查失敗。")
            return ProfileImportResult(
                manifest=manifest,
                backup_path=backup,
                imported_counts=imported_counts,
            )
        except sqlite3.Error as exc:
            raise ProfileTransferError(f"匯入資料庫失敗：{exc}") from exc
        finally:
            temporary.cleanup()
