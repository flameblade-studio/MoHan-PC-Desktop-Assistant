from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sqlite3
lazy import uuid
lazy import zipfile
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from typing import Any

lazy from application.appearance_session import ACTIVE_OUTFIT_SETTING_KEY
lazy from application.presentation_ports import ProfileTransferError
lazy from domain.contracts import ProfileDatabasePort, SecretStorePort
lazy from domain.framing_preferences import SETTING_KEYS as FRAMING_SETTING_KEYS
lazy from domain.openai_vision_preferences import (
    SETTING_KEYS as OPENAI_VISION_SETTING_KEYS,
)
lazy from domain.performance_preferences import (
    SETTING_KEYS as PERFORMANCE_SETTING_KEYS,
)
lazy from domain.safe_error import (
    SafeDiagnostic,
    SafeError,
    SafeErrorType,
    sanitize_error,
)
lazy from domain.theme_session import ACTIVE_THEME_SETTING_KEY
lazy from infrastructure.backup_manager import BackupManager
lazy from infrastructure.companion_proactivity_preferences_store import (
    PORTABLE_SETTING_KEYS as COMPANION_PROACTIVITY_SETTING_KEYS,
)
lazy from infrastructure.framing_preferences_store import (
    STORE_SCHEMA_KEY as FRAMING_STORE_SCHEMA_KEY,
)
lazy from infrastructure.gesture_configuration_store import (
    PORTABLE_GESTURE_SETTING_KEYS,
)
lazy from infrastructure.openai_vision_preferences_store import (
    STORE_SCHEMA_KEY as OPENAI_VISION_STORE_SCHEMA_KEY,
)
lazy from infrastructure.performance_preferences_store import STORE_SCHEMA_KEY
lazy from infrastructure.portable_secrets import (
    PortableSecretsError,
    PortableSecretsPayload,
    apply_sensitive_payload,
    collect_sensitive_payload,
    validate_sensitive_payload,
)
lazy from infrastructure.portable_sensitive import (
    SensitiveProfileError,
    build_sensitive_envelope,
    open_sensitive_envelope,
)
lazy from infrastructure.special_occasion_store import (
    PORTABLE_SETTING_KEYS as SPECIAL_OCCASION_PORTABLE_SETTING_KEYS,
)
lazy from infrastructure.wellbeing_reminder_store import (
    PORTABLE_SETTING_KEYS as WELLBEING_PORTABLE_SETTING_KEYS,
)

PROFILE_EXTENSION = ".mohan-profile"
PROFILE_FORMAT_VERSION = 1
MAX_PROFILE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MANIFEST_FILENAME = "manifest.json"
DATABASE_FILENAME = "profile.db"
SENSITIVE_FILENAME = "sensitive.enc"
SENSITIVE_MANIFEST_KEY = "sensitive"
PROFILE_ARCHIVE_MEMBERS = frozenset(
    {MANIFEST_FILENAME, DATABASE_FILENAME}
)
PROFILE_ARCHIVE_MEMBERS_WITH_SENSITIVE = frozenset(
    {*PROFILE_ARCHIVE_MEMBERS, SENSITIVE_FILENAME}
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
        ACTIVE_OUTFIT_SETTING_KEY,
        ACTIVE_THEME_SETTING_KEY,
        "affinity_value",
        "affinity_interaction_count",
        "jealousy_value",
        "favor_value",
        "satiety_value",
        "weather_temperature_c",
        "weather_condition",
        "wardrobe_current_weight",
        "assistant_name",
        "automatic_update_check",
        "auto_memory",
        "background_assistant_enabled",
        "background_watch_apps",
        "break_minutes",
        "cloud_voice",
        "character_scale_percent",
        "chat_zoom_percent",
        "flagship_high_contrast",
        "flagship_ui_scale",
        "mode",
        "multisensory_phrasebook_v1",
        "onboarding_complete",
        "organization_name",
        "persona_prompt",
        "proactive_mode",
        "proactive_interaction_enabled",
        "proactive_interaction_mode",
        "multisensory_welcome_minimum_seconds",
        "multisensory_welcome_brief_max_seconds",
        "multisensory_welcome_long_seconds",
        "multisensory_conversation_mode",
        "multisensory_conversation_silence_seconds",
        "azure_hd_speech_region",
        "azure_hd_speech_voice",
        "azure_speech_region",
        "azure_speech_voice",
        "realtime_echo_guard",
        "realtime_hybrid_transcription",
        "realtime_model",
        "realtime_noise_reduction",
        "realtime_output_mode",
        "realtime_transcription_model",
        "realtime_turn_detection",
        "realtime_voice",
        "speech_recognition",
        "topmost_mode",
        "transcription_language",
        "transcription_model",
        "transcription_prompt",
        "tts_enabled",
        "tts_voice",
        "ui_language",
        "update_channel",
        "user_title",
        "voice_engine",
        "voice_instructions",
        "voice_muted",
        "voice_rate",
        "voice_volume_percent",
        "wake_word",
        "windows_transcription_fallback",
        "windows_voice",
        "window_title",
        "work_type",
    }
    | set(COMPANION_PROACTIVITY_SETTING_KEYS)
    | set(FRAMING_SETTING_KEYS)
    | set(PORTABLE_GESTURE_SETTING_KEYS)
    | set(OPENAI_VISION_SETTING_KEYS)
    | set(PERFORMANCE_SETTING_KEYS)
    | set(SPECIAL_OCCASION_PORTABLE_SETTING_KEYS)
    | set(WELLBEING_PORTABLE_SETTING_KEYS)
    | {
        FRAMING_STORE_SCHEMA_KEY,
        OPENAI_VISION_STORE_SCHEMA_KEY,
        STORE_SCHEMA_KEY,
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


def _external_profile_error(error: BaseException) -> ProfileTransferError:
    """Discard external detail before it can reach UI or persistent state."""

    safe = sanitize_error(error)
    if isinstance(error, sqlite3.Error):
        safe = SafeError(
            SafeErrorType.OPERATING_SYSTEM_ERROR,
            SafeDiagnostic.LOCAL_IO_FAILURE,
        )
    return ProfileTransferError("", safe_error=safe)


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
    sensitive_payload: PortableSecretsPayload | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    target_database_path: Path | None = field(
        default=None,
        repr=False,
        compare=False,
    )


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
        failure: ProfileTransferError | None = None
        try:
            normalized_counts = frozendict(
                (str(key), max(0, int(value)))
                for key, value in counts.items()
            )
        except (TypeError, ValueError) as exc:
            failure = _external_profile_error(exc)
        if failure is not None:
            raise failure
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
            # SQLite 的 DELETE 只把頁面標記為可重用，內容仍留在檔案裡。
            # 這個功能存在的唯一目的就是把 action_audit（含剪貼簿與檔案內容）、
            # connector_profiles、allowed_targets、paired_devices 與非可攜設定
            # 排除在匯出檔之外——但先前只做 DELETE 就直接打包原始 SQLite 檔，
            # 那些位元組原封不動地跟著走。使用者以為分享的是乾淨的設定檔。
            #
            # secure_delete=ON 讓刪除當下就把頁面內容歸零；VACUUM 再把整個
            # 資料庫重寫一次，丟掉所有空閒頁面。兩者都要：secure_delete 管
            # 這一次刪除，VACUUM 管快照複製過來時就已經存在的舊空閒頁。
            snapshot.execute("PRAGMA secure_delete=ON")
            self._delete_nonportable_settings(snapshot)
            self._clear_machine_bound_tables(snapshot)
            snapshot.commit()
            snapshot.execute("VACUUM")
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
        sensitive_envelope: bytes | None = None,
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
                if sensitive_envelope is not None:
                    archive.writestr(SENSITIVE_FILENAME, sensitive_envelope)
            temporary_target.replace(target)
        finally:
            temporary_target.unlink(missing_ok=True)

    def export_profile(
        self,
        target: Path,
        *,
        sensitive_payload: Mapping[str, object] | None = None,
        sensitive_stores: Mapping[str, SecretStorePort] | None = None,
        password: str | bytes | bytearray | None = None,
    ) -> tuple[Path, ProfileManifest]:
        failure: ProfileTransferError | None = None
        result: tuple[Path, ProfileManifest] | None = None
        try:
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
                if (
                    sensitive_payload is not None
                    and sensitive_stores is not None
                ):
                    raise ProfileTransferError(
                        "敏感資料來源只能指定一種。"
                    )
                selected_sensitive_payload = (
                    collect_sensitive_payload(sensitive_stores)
                    if sensitive_stores is not None
                    else (
                        validate_sensitive_payload(sensitive_payload)
                        if sensitive_payload is not None
                        else None
                    )
                )
                include_sensitive = bool(
                    selected_sensitive_payload
                    and selected_sensitive_payload["secrets"]
                )
                sensitive_envelope = build_sensitive_envelope(
                    selected_sensitive_payload or {},
                    password=password,
                    include_sensitive=include_sensitive,
                )
                manifest_payload["secrets_included"] = (
                    sensitive_envelope is not None
                )
                manifest_payload[SENSITIVE_MANIFEST_KEY] = {
                    "included": sensitive_envelope is not None,
                    "encrypted": sensitive_envelope is not None,
                    "archive_member": (
                        SENSITIVE_FILENAME
                        if sensitive_envelope is not None
                        else None
                    ),
                }
                if sensitive_envelope is not None:
                    sensitive_hash = hashlib.sha256(
                        sensitive_envelope
                    ).hexdigest()
                    manifest_payload["sensitive_sha256"] = sensitive_hash
                    manifest_payload[SENSITIVE_MANIFEST_KEY].update(
                        {
                            "sha256": sensitive_hash,
                            "size": len(sensitive_envelope),
                        }
                    )
                manifest = self._manifest_from_payload(manifest_payload)
                self._write_archive(
                    destination,
                    snapshot_path,
                    manifest_payload,
                    sensitive_envelope,
                )
            result = destination, manifest
        except ProfileTransferError:
            raise
        except (
            OSError,
            PortableSecretsError,
            SensitiveProfileError,
            sqlite3.Error,
            ValueError,
            zipfile.LargeZipFile,
        ) as exc:
            failure = _external_profile_error(exc)
        if failure is not None:
            raise failure
        if result is None:
            raise AssertionError("profile export finished without a result")
        return result

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
        if names not in {
            PROFILE_ARCHIVE_MEMBERS,
            PROFILE_ARCHIVE_MEMBERS_WITH_SENSITIVE,
        } or len(entries) != len(names):
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
            or sizes.get(SENSITIVE_FILENAME, 0) > 8 * 1024 * 1024
        ):
            raise ProfileTransferError("攜帶檔包含超過安全限制的內容。")

    def _read_archive(
        self,
        source: Path,
    ) -> tuple[Any, bytes, bytes | None]:
        with zipfile.ZipFile(source, "r") as archive:
            self._validate_archive_entries(archive.infolist())
            manifest_payload = json.loads(
                archive.read(MANIFEST_FILENAME).decode("utf-8")
            )
            database_bytes = archive.read(DATABASE_FILENAME)
            sensitive_bytes = (
                archive.read(SENSITIVE_FILENAME)
                if SENSITIVE_FILENAME in archive.namelist()
                else None
            )
        return manifest_payload, database_bytes, sensitive_bytes

    def _verified_manifest(
        self,
        payload: Any,
        database_bytes: bytes,
        sensitive_bytes: bytes | None,
    ) -> ProfileManifest:
        if not isinstance(payload, dict):
            raise ProfileTransferError("攜帶檔描述格式錯誤。")
        if payload.get("format") != "mohan-portable-profile":
            raise ProfileTransferError("攜帶檔格式識別錯誤。")
        if payload.get("machine_permissions_included") is True:
            raise ProfileTransferError("攜帶檔不得包含機器權限。")
        has_sensitive = sensitive_bytes is not None
        if bool(payload.get("secrets_included")) != has_sensitive:
            raise ProfileTransferError("攜帶檔敏感資料描述不一致。")
        self._verify_sensitive_manifest(
            payload,
            sensitive_bytes,
        )
        if has_sensitive and hashlib.sha256(sensitive_bytes).hexdigest() != str(
            payload.get("sensitive_sha256", "")
        ):
            raise ProfileTransferError("攜帶檔敏感資料雜湊驗證失敗。")
        manifest = self._manifest_from_payload(payload)
        expected_hash = str(payload.get("database_sha256", ""))
        actual_hash = hashlib.sha256(database_bytes).hexdigest()
        if not expected_hash or actual_hash != expected_hash:
            raise ProfileTransferError(
                "攜帶檔雜湊驗證失敗，檔案可能已損毀。"
            )
        return manifest

    @staticmethod
    def _verify_sensitive_manifest(
        payload: Mapping[str, object],
        sensitive_bytes: bytes | None,
    ) -> None:
        has_sensitive = sensitive_bytes is not None
        sensitive_manifest = payload.get(SENSITIVE_MANIFEST_KEY)
        if sensitive_manifest is not None:
            if not isinstance(sensitive_manifest, Mapping):
                raise ProfileTransferError("攜帶檔敏感資料描述格式錯誤。")
            expected_keys = (
                {"included", "encrypted", "archive_member", "sha256", "size"}
                if has_sensitive
                else {"included", "encrypted", "archive_member"}
            )
            if set(sensitive_manifest) != expected_keys:
                raise ProfileTransferError("攜帶檔敏感資料描述格式錯誤。")
            if (
                sensitive_manifest.get("included") is not has_sensitive
                or sensitive_manifest.get("encrypted") is not has_sensitive
                or sensitive_manifest.get("archive_member")
                != (SENSITIVE_FILENAME if has_sensitive else None)
            ):
                raise ProfileTransferError("攜帶檔敏感資料描述不一致。")
            if has_sensitive and (
                sensitive_manifest.get("sha256")
                != payload.get("sensitive_sha256")
                or sensitive_manifest.get("size") != len(sensitive_bytes)
            ):
                raise ProfileTransferError("攜帶檔敏感資料描述不一致。")

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
        temporary: TemporaryDirectory | None = None
        failure: ProfileTransferError | None = None
        result: tuple[ProfileManifest, Path, TemporaryDirectory] | None = None
        try:
            profile_path = self._validated_source(source)
            temporary = TemporaryDirectory(prefix="mohan-profile-import-")
            payload, database_bytes, sensitive_bytes = self._read_archive(
                profile_path
            )
            manifest = self._verified_manifest(
                payload, database_bytes, sensitive_bytes
            )
            database_path = self._materialize_database(
                temporary,
                database_bytes,
            )
            self._validate_incoming_database(database_path, manifest)
            result = manifest, database_path, temporary
        except (
            OSError,
            sqlite3.Error,
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
            json.JSONDecodeError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            failure = _external_profile_error(exc)
            if temporary is not None:
                temporary.cleanup()
        except Exception:
            if temporary is not None:
                temporary.cleanup()
            raise
        if failure is not None:
            raise failure
        if result is None:
            raise AssertionError("profile inspection finished without a result")
        return result

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

    def _delete_replaced_portable_settings(
        self,
        incoming: tuple[tuple[str, str], ...],
    ) -> None:
        replaced_keys = tuple(
            (key,)
            for key, _value in incoming
            if is_portable_setting(key)
        )
        if replaced_keys:
            self.db.conn.executemany(
                "DELETE FROM settings WHERE key=?",
                replaced_keys,
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
            self._delete_replaced_portable_settings(payload.settings)
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

    def import_profile(
        self,
        source: Path,
        *,
        password: str | bytes | bytearray | None = None,
    ) -> ProfileImportResult:
        manifest, database_path, temporary = self.inspect_profile(source)
        failure: ProfileTransferError | None = None
        result: ProfileImportResult | None = None
        try:
            _payload, _database_bytes, sensitive_bytes = self._read_archive(
                Path(source)
            )
            sensitive_payload = None
            if sensitive_bytes is not None:
                decrypted = open_sensitive_envelope(
                    sensitive_bytes, password=password
                )
                # The generic envelope reader disables device capabilities.
                # They are never part of the typed secret schema.
                decrypted.pop("camera_presence_enabled", None)
                decrypted.pop("face_identity_enabled", None)
                sensitive_payload = validate_sensitive_payload(decrypted)
            self._assert_snapshot_not_imported(manifest)
            payload = self._load_profile_payload(database_path)
            backup = BackupManager(self.db, self.backup_dir).create(
                "before-portable-import"
            )
            imported_counts = self._apply_profile_payload(
                payload,
                manifest,
            )
            result = ProfileImportResult(
                manifest=manifest,
                backup_path=backup,
                imported_counts=imported_counts,
                sensitive_payload=sensitive_payload,
                target_database_path=self.db.path.resolve(),
            )
        except ProfileTransferError:
            raise
        except sqlite3.Error as exc:
            failure = _external_profile_error(exc)
        except (
            OSError,
            PortableSecretsError,
            SensitiveProfileError,
        ) as exc:
            failure = _external_profile_error(exc)
        finally:
            temporary.cleanup()
        if failure is not None:
            raise failure
        if result is None:
            raise AssertionError("profile import finished without a result")
        return result

    def restore_import(self, result: ProfileImportResult) -> None:
        """Restore the verified database backup created by this import."""

        backup = result.backup_path
        try:
            if (
                result.target_database_path is None
                or result.target_database_path != self.db.path.resolve()
            ):
                raise ProfileTransferError("匯入回復點不屬於目前資料庫。")
            current_snapshot_id = str(
                self.db.setting("portable_last_import_snapshot_id", "")
            )
            if current_snapshot_id != result.manifest.snapshot_id:
                raise ProfileTransferError("匯入回復點已過期。")
            expected_parent = self.backup_dir.resolve()
            if backup.resolve().parent != expected_parent:
                raise ProfileTransferError("匯入回復點不屬於目前資料庫。")
            manager = BackupManager(self.db, self.backup_dir)
            if not manager.verify(backup):
                raise ProfileTransferError("匯入回復點驗證失敗。")
            source = self._open_readonly_database(backup)
            try:
                source.backup(self.db.conn)
                self._assert_integrity(
                    self.db.conn,
                    "匯入回復後資料庫完整性檢查失敗。",
                )
            finally:
                source.close()
        except ProfileTransferError:
            raise
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise _external_profile_error(exc) from None

    def apply_imported_sensitive_payload(
        self,
        result: ProfileImportResult,
        stores: Mapping[str, SecretStorePort],
    ) -> None:
        """Apply imported secrets or restore the just-imported database."""

        if result.sensitive_payload is None:
            return
        try:
            apply_sensitive_payload(result.sensitive_payload, stores)
        except PortableSecretsError:
            try:
                self.restore_import(result)
            except ProfileTransferError:
                raise ProfileTransferError(
                    "敏感資料匯入失敗，且一般設定自動回復失敗。"
                ) from None
            raise ProfileTransferError(
                "敏感資料匯入失敗；一般設定已自動回復。"
            ) from None
