from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sqlite3
lazy import uuid
lazy import zipfile
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from typing import Any

lazy from backup_manager import BackupManager
lazy from contracts import ProfileDatabasePort

PROFILE_EXTENSION = ".mohan-profile"
PROFILE_FORMAT_VERSION = 1
MAX_PROFILE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MANIFEST_FILENAME = "manifest.json"
DATABASE_FILENAME = "profile.db"
PROFILE_ARCHIVE_MEMBERS = frozenset(
    {MANIFEST_FILENAME, DATABASE_FILENAME}
)

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
MACHINE_BOUND_TABLES = (
    "action_audit",
    "connector_profiles",
    "allowed_targets",
    "paired_devices",
)


class ProfileTransferError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProfileManifest:
    created_at: str
    snapshot_id: str
    source_installation_id: str
    assistant_name: str
    organization_name: str
    record_counts: frozendict[str, int]


@dataclass(frozen=True, slots=True)
class ProfileImportResult:
    manifest: ProfileManifest
    backup_path: Path
    imported_counts: frozendict[str, int]


@dataclass(frozen=True, slots=True)
class PortableTablePayload:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True, slots=True)
class PortableProfilePayload:
    settings: tuple[tuple[str, str], ...]
    tables: frozendict[str, PortableTablePayload]


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
        if not isinstance(counts, Mapping):
            raise ProfileTransferError("攜帶檔缺少資料筆數資訊。")
        try:
            normalized_counts = frozendict(
                (str(key), max(0, int(value)))
                for key, value in counts.items()
            )
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

    @staticmethod
    def _assert_integrity(
        connection: sqlite3.Connection,
        error_message: str,
    ) -> None:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ProfileTransferError(error_message)

    @staticmethod
    def _quoted_columns(columns: tuple[str, ...]) -> str:
        return ",".join(
            '"' + column.replace('"', '""') + '"' for column in columns
        )

    def _record_counts(
        self,
        connection: sqlite3.Connection,
    ) -> frozendict[str, int]:
        counts = {
            table: int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            )
            for table in PORTABLE_TABLES
        }
        counts["settings"] = int(
            connection.execute(
                "SELECT COUNT(*) FROM settings"
            ).fetchone()[0]
        )
        return frozendict(counts)

    def _source_installation_id(self) -> str:
        installation_id = str(
            self.db.setting("portable_installation_id", "")
        ).strip()
        if not installation_id:
            installation_id = uuid.uuid4().hex
            self.db.set_setting(
                "portable_installation_id",
                installation_id,
            )
        self.db.conn.commit()
        return installation_id

    def _copy_live_database(self, snapshot_path: Path) -> None:
        destination = sqlite3.connect(snapshot_path)
        try:
            self.db.conn.backup(destination)
        finally:
            destination.close()

    @staticmethod
    def _delete_nonportable_settings(
        snapshot: sqlite3.Connection,
    ) -> None:
        nonportable = tuple(
            (str(row["key"]),)
            for row in snapshot.execute("SELECT key FROM settings")
            if not is_portable_setting(str(row["key"]))
        )
        if nonportable:
            snapshot.executemany(
                "DELETE FROM settings WHERE key=?",
                nonportable,
            )

    def _clear_machine_bound_tables(
        self,
        snapshot: sqlite3.Connection,
    ) -> None:
        available_tables = self._table_names(snapshot)
        for table in MACHINE_BOUND_TABLES:
            if table in available_tables:
                snapshot.execute(f'DELETE FROM "{table}"')

    @staticmethod
    def _profile_identity(
        snapshot: sqlite3.Connection,
    ) -> frozendict[str, str]:
        profile: dict[str, str] = {}
        rows = snapshot.execute(
            "SELECT key,value FROM settings "
            "WHERE key IN ('assistant_name','organization_name')"
        )
        for row in rows:
            try:
                decoded = json.loads(str(row["value"]))
            except json.JSONDecodeError:
                decoded = ""
            profile[str(row["key"])] = str(decoded or "")
        return frozendict(profile)

    def _sanitize_snapshot(
        self,
        snapshot_path: Path,
    ) -> tuple[frozendict[str, int], frozendict[str, str]]:
        snapshot = sqlite3.connect(snapshot_path)
        snapshot.row_factory = sqlite3.Row
        try:
            snapshot.execute("PRAGMA trusted_schema=OFF")
            self._delete_nonportable_settings(snapshot)
            self._clear_machine_bound_tables(snapshot)
            snapshot.commit()
            snapshot.execute("PRAGMA journal_mode=DELETE")
            self._assert_integrity(
                snapshot,
                "匯出資料庫完整性檢查失敗。",
            )
            return (
                self._record_counts(snapshot),
                self._profile_identity(snapshot),
            )
        finally:
            snapshot.close()

    def _create_snapshot(
        self,
        snapshot_path: Path,
    ) -> tuple[frozendict[str, int], frozendict[str, str]]:
        self._copy_live_database(snapshot_path)
        return self._sanitize_snapshot(snapshot_path)

    @staticmethod
    def _manifest_payload(
        snapshot_path: Path,
        installation_id: str,
        record_counts: frozendict[str, int],
        profile: frozendict[str, str],
    ) -> dict[str, Any]:
        return {
            "format": "mohan-portable-profile",
            "format_version": PROFILE_FORMAT_VERSION,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "snapshot_id": uuid.uuid4().hex,
            "source_installation_id": installation_id,
            "assistant_name": profile.get("assistant_name", ""),
            "organization_name": profile.get("organization_name", ""),
            "record_counts": record_counts,
            "database_sha256": hashlib.sha256(
                snapshot_path.read_bytes()
            ).hexdigest(),
            "secrets_included": False,
            "machine_permissions_included": False,
        }

    @staticmethod
    def _write_archive(
        target: Path,
        snapshot_path: Path,
        manifest_payload: dict[str, Any],
    ) -> None:
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
                    MANIFEST_FILENAME,
                    json.dumps(
                        manifest_payload,
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )
                archive.write(snapshot_path, DATABASE_FILENAME)
            temporary_target.replace(target)
        finally:
            temporary_target.unlink(missing_ok=True)

    def export_profile(self, target: Path) -> tuple[Path, ProfileManifest]:
        destination = normalized_profile_path(Path(target))
        destination.parent.mkdir(parents=True, exist_ok=True)
        installation_id = self._source_installation_id()
        with TemporaryDirectory(prefix="mohan-profile-export-") as temp:
            snapshot_path = Path(temp) / DATABASE_FILENAME
            record_counts, profile = self._create_snapshot(snapshot_path)
            manifest_payload = self._manifest_payload(
                snapshot_path,
                installation_id,
                record_counts,
                profile,
            )
            manifest = self._manifest_from_payload(manifest_payload)
            self._write_archive(
                destination,
                snapshot_path,
                manifest_payload,
            )
        return destination, manifest

    @staticmethod
    def _validated_source(source: Path) -> Path:
        profile_path = Path(source)
        if not profile_path.is_file():
            raise ProfileTransferError("找不到指定的墨寒攜帶檔。")
        if profile_path.stat().st_size > MAX_PROFILE_BYTES:
            raise ProfileTransferError("攜帶檔超過安全大小限制。")
        return profile_path

    @staticmethod
    def _validate_archive_entries(
        entries: list[zipfile.ZipInfo],
    ) -> None:
        names = {entry.filename for entry in entries}
        if (
            len(entries) != len(PROFILE_ARCHIVE_MEMBERS)
            or names != PROFILE_ARCHIVE_MEMBERS
        ):
            raise ProfileTransferError(
                "攜帶檔內容不完整，或含有非預期檔案。"
            )
        if any(
            entry.is_dir()
            or bool(entry.flag_bits & 0x1)
            or entry.filename.startswith(("/", "\\"))
            or ".." in Path(entry.filename).parts
            for entry in entries
        ):
            raise ProfileTransferError("攜帶檔包含不安全的路徑或加密內容。")
        sizes = {entry.filename: entry.file_size for entry in entries}
        if (
            sizes[MANIFEST_FILENAME] > MAX_MANIFEST_BYTES
            or sizes[DATABASE_FILENAME] > MAX_PROFILE_BYTES
        ):
            raise ProfileTransferError("攜帶檔包含超過安全限制的內容。")

    def _read_archive(
        self,
        source: Path,
    ) -> tuple[Any, bytes]:
        with zipfile.ZipFile(source, "r") as archive:
            self._validate_archive_entries(archive.infolist())
            manifest_payload = json.loads(
                archive.read(MANIFEST_FILENAME).decode("utf-8")
            )
            database_bytes = archive.read(DATABASE_FILENAME)
        return manifest_payload, database_bytes

    def _verified_manifest(
        self,
        payload: Any,
        database_bytes: bytes,
    ) -> ProfileManifest:
        if not isinstance(payload, dict):
            raise ProfileTransferError("攜帶檔描述格式錯誤。")
        if payload.get("format") != "mohan-portable-profile":
            raise ProfileTransferError("攜帶檔格式識別錯誤。")
        if (
            payload.get("secrets_included") is True
            or payload.get("machine_permissions_included") is True
        ):
            raise ProfileTransferError("攜帶檔不得包含密鑰或機器權限。")
        manifest = self._manifest_from_payload(payload)
        expected_hash = str(payload.get("database_sha256", ""))
        actual_hash = hashlib.sha256(database_bytes).hexdigest()
        if not expected_hash or actual_hash != expected_hash:
            raise ProfileTransferError(
                "攜帶檔雜湊驗證失敗，檔案可能已損毀。"
            )
        return manifest

    @staticmethod
    def _open_readonly_database(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA trusted_schema=OFF")
        return connection

    def _validate_incoming_database(
        self,
        database_path: Path,
        manifest: ProfileManifest,
    ) -> None:
        incoming = self._open_readonly_database(database_path)
        try:
            self._assert_integrity(
                incoming,
                "攜帶檔資料庫完整性檢查失敗。",
            )
            required_tables = set(PORTABLE_TABLES) | {"settings"}
            missing = required_tables - self._table_names(incoming)
            if missing:
                raise ProfileTransferError(
                    "攜帶檔缺少必要資料表："
                    + "、".join(sorted(missing))
                )
            actual_counts = self._record_counts(incoming)
            if any(
                manifest.record_counts.get(table) != count
                for table, count in actual_counts.items()
            ):
                raise ProfileTransferError(
                    "攜帶檔描述與實際資料筆數不一致。"
                )
        finally:
            incoming.close()

    def _materialize_database(
        self,
        temporary: TemporaryDirectory,
        database_bytes: bytes,
    ) -> Path:
        database_path = Path(temporary.name) / DATABASE_FILENAME
        database_path.write_bytes(database_bytes)
        return database_path

    def inspect_profile(
        self,
        source: Path,
    ) -> tuple[ProfileManifest, Path, TemporaryDirectory]:
        profile_path = self._validated_source(source)
        temporary = TemporaryDirectory(prefix="mohan-profile-import-")
        try:
            payload, database_bytes = self._read_archive(profile_path)
            manifest = self._verified_manifest(payload, database_bytes)
            database_path = self._materialize_database(
                temporary,
                database_bytes,
            )
            self._validate_incoming_database(database_path, manifest)
            return manifest, database_path, temporary
        except (
            zipfile.BadZipFile,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:
            temporary.cleanup()
            raise ProfileTransferError(
                "攜帶檔不是有效的墨寒進度檔。"
            ) from exc
        except Exception:
            temporary.cleanup()
            raise

    def _assert_snapshot_not_imported(
        self,
        manifest: ProfileManifest,
    ) -> None:
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

    @staticmethod
    def _missing_required_columns(
        target_info: list[sqlite3.Row],
        source_names: set[str],
    ) -> tuple[str, ...]:
        return tuple(
            str(row["name"])
            for row in target_info
            if bool(row["notnull"])
            and row["dflt_value"] is None
            and not bool(row["pk"])
            and str(row["name"]) not in source_names
        )

    def _read_table_payload(
        self,
        incoming: sqlite3.Connection,
        table: str,
    ) -> PortableTablePayload:
        target_info = self._table_columns(self.db.conn, table)
        source_names = {
            str(row["name"])
            for row in self._table_columns(incoming, table)
        }
        columns = tuple(
            str(row["name"])
            for row in target_info
            if str(row["name"]) in source_names
        )
        required_missing = self._missing_required_columns(
            target_info,
            source_names,
        )
        if required_missing:
            raise ProfileTransferError(
                f"{table} 缺少必要欄位："
                + "、".join(required_missing)
            )
        if not columns:
            raise ProfileTransferError(f"{table} 沒有可安全匯入的欄位。")
        quoted = self._quoted_columns(columns)
        rows = tuple(
            tuple(row[column] for column in columns)
            for row in incoming.execute(
                f'SELECT {quoted} FROM "{table}"'
            )
        )
        return PortableTablePayload(columns=columns, rows=rows)

    @staticmethod
    def _read_portable_settings(
        incoming: sqlite3.Connection,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            (str(row["key"]), str(row["value"]))
            for row in incoming.execute(
                "SELECT key,value FROM settings"
            )
            if is_portable_setting(str(row["key"]))
        )

    def _load_profile_payload(
        self,
        database_path: Path,
    ) -> PortableProfilePayload:
        incoming = self._open_readonly_database(database_path)
        try:
            tables = frozendict(
                (
                    table,
                    self._read_table_payload(incoming, table),
                )
                for table in PORTABLE_TABLES
            )
            return PortableProfilePayload(
                settings=self._read_portable_settings(incoming),
                tables=tables,
            )
        finally:
            incoming.close()

    def _delete_current_portable_settings(self) -> None:
        portable_keys = tuple(
            (str(row[0]),)
            for row in self.db.conn.execute(
                "SELECT key FROM settings"
            )
            if is_portable_setting(str(row[0]))
        )
        if portable_keys:
            self.db.conn.executemany(
                "DELETE FROM settings WHERE key=?",
                portable_keys,
            )

    def _upsert_settings(
        self,
        rows: tuple[tuple[str, str], ...],
    ) -> None:
        self.db.conn.executemany(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            rows,
        )

    def _write_import_markers(self, manifest: ProfileManifest) -> None:
        markers = tuple(
            (key, json.dumps(value))
            for key, value in (
                (
                    "portable_last_import_snapshot_id",
                    manifest.snapshot_id,
                ),
                (
                    "portable_last_import_created_at",
                    manifest.created_at,
                ),
            )
            if value
        )
        self._upsert_settings(markers)

    def _replace_table(
        self,
        table: str,
        payload: PortableTablePayload,
    ) -> int:
        self.db.conn.execute(f'DELETE FROM "{table}"')
        if payload.rows:
            quoted = self._quoted_columns(payload.columns)
            placeholders = ",".join("?" for _ in payload.columns)
            self.db.conn.executemany(
                f'INSERT INTO "{table}"({quoted}) '
                f"VALUES({placeholders})",
                payload.rows,
            )
        return len(payload.rows)

    def _apply_profile_payload(
        self,
        payload: PortableProfilePayload,
        manifest: ProfileManifest,
    ) -> frozendict[str, int]:
        imported_counts = {"settings": len(payload.settings)}
        with self.db.conn:
            self._delete_current_portable_settings()
            self._upsert_settings(payload.settings)
            self._write_import_markers(manifest)
            for table, table_payload in payload.tables.items():
                imported_counts[table] = self._replace_table(
                    table,
                    table_payload,
                )
            self._assert_integrity(
                self.db.conn,
                "匯入後資料庫完整性檢查失敗。",
            )
        return frozendict(imported_counts)

    def import_profile(self, source: Path) -> ProfileImportResult:
        manifest, database_path, temporary = self.inspect_profile(source)
        try:
            self._assert_snapshot_not_imported(manifest)
            payload = self._load_profile_payload(database_path)
            backup = BackupManager(self.db, self.backup_dir).create(
                "before-portable-import"
            )
            imported_counts = self._apply_profile_payload(
                payload,
                manifest,
            )
            return ProfileImportResult(
                manifest=manifest,
                backup_path=backup,
                imported_counts=imported_counts,
            )
        except sqlite3.Error as exc:
            raise ProfileTransferError(f"匯入資料庫失敗：{exc}") from exc
        finally:
            temporary.cleanup()
