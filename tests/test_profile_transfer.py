from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from framing_preferences import (
    ADAPTIVE_FRAMING_KEY,
    ALLOW_CLOSE_KEY,
    ALLOW_FULL_BODY_KEY,
    FOCUS_PROTECTION_KEY,
    PREFERRED_FRAMING_KEY,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.framing_preferences_store import (
    STORE_SCHEMA_KEY as FRAMING_STORE_SCHEMA_KEY,
)

UUID_HEX_LENGTH = 32
lazy from infrastructure.performance_preferences_store import STORE_SCHEMA_KEY
lazy from infrastructure.portable_secrets import (
    PORTABLE_SECRETS_FORMAT,
    PORTABLE_SECRETS_VERSION,
)
lazy from infrastructure.profile_transfer import (
    PORTABLE_TABLES,
    PortableProfileManager,
    ProfileManifest,
    ProfileTransferError,
)
lazy from performance_preferences import (
    CAMERA_CONTEXT_KEY,
    EMOTIONAL_BACK_KEY,
    FULL_BACK_KEY,
    INTENSITY_KEY,
    LEFT_GESTURES_KEY,
    PROACTIVE_BODY_KEY,
    RIGHT_GESTURES_KEY,
    VIEW_360_KEY,
)
lazy from profile_transfer_ui import localized_profile_failure
lazy from safe_error_localization import safe_error_message

_BAIT_PATH = r"Z:\private-fixture\owner\mohan-private.db"
_BAIT_TOKEN = "fixture-profile-private-token"
_BAIT_DETAIL = f"{_BAIT_PATH}; token={_BAIT_TOKEN}"
_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
_SENSITIVE_BAIT = "fixture-sensitive-value-must-not-leak"


class MemorySecretStore:
    def __init__(
        self,
        value: str = "",
        *,
        fail_on: frozenset[str] = frozenset(),
        mutate_before_failure: bool = False,
    ) -> None:
        self.value = value
        self.fail_on = fail_on
        self.mutate_before_failure = mutate_before_failure

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        if value in self.fail_on:
            if self.mutate_before_failure:
                self.value = value
            raise RuntimeError("PRIVATE-STORE-FAILURE")
        self.value = value

    def clear(self) -> None:
        self.value = ""

_PORTABLE_EXAMPLE_SETTINGS = frozendict(
    {
        "voice_engine": "azure-speech",
        "windows_voice": "OneCore::Microsoft Yating",
        "azure_speech_region": "eastasia",
        "azure_speech_voice": "zh-TW-HsiaoChenNeural",
        "azure_hd_speech_region": "westus2",
        "azure_hd_speech_voice": "zh-CN-Xiaoxiao:DragonHDLatestNeural",
        "tts_voice": "coral",
        "cloud_voice": "coral",
        "voice_rate": -1,
        "voice_volume_percent": 125,
        "voice_muted": False,
        "voice_instructions": "溫柔、自然、沉穩並帶有笑意",
        "speech_recognition": "OpenAI 高準確辨識（推薦）",
        "transcription_model": "gpt-4o-mini-transcribe",
        "transcription_language": "zh",
        "transcription_prompt": "辨識墨寒、炎劍工作室與常用專有名詞",
        "windows_transcription_fallback": True,
        "realtime_model": "gpt-realtime-2.1-mini",
        "realtime_voice": "coral",
        "realtime_output_mode": "azure-speech",
        "realtime_transcription_model": "gpt-4o-mini-transcribe",
        "realtime_noise_reduction": "near_field",
        "realtime_turn_detection": "server_vad",
        "realtime_echo_guard": True,
        "realtime_hybrid_transcription": True,
        "topmost_mode": "智慧置頂（推薦）",
        "character_scale_percent": 105,
        "chat_zoom_percent": 120,
        "automatic_update_check": True,
        "update_channel": "stable",
        "proactive_mode": "平衡（推薦）",
        "background_assistant_enabled": True,
        "background_watch_apps": "Visual Studio Code,GitHub Desktop",
        "proactive_interaction_enabled": True,
        "proactive_interaction_mode": "balanced",
        "multisensory_welcome_minimum_seconds": 30,
        "multisensory_welcome_brief_max_seconds": 300,
        "multisensory_welcome_long_seconds": 1800,
        "multisensory_conversation_mode": "balanced",
        "multisensory_conversation_silence_seconds": 900,
        PROACTIVE_BODY_KEY: False,
        INTENSITY_KEY: 82,
        VIEW_360_KEY: True,
        FULL_BACK_KEY: True,
        EMOTIONAL_BACK_KEY: True,
        LEFT_GESTURES_KEY: False,
        RIGHT_GESTURES_KEY: True,
        CAMERA_CONTEXT_KEY: True,
        STORE_SCHEMA_KEY: 1,
        ADAPTIVE_FRAMING_KEY: True,
        ALLOW_CLOSE_KEY: False,
        ALLOW_FULL_BODY_KEY: True,
        FOCUS_PROTECTION_KEY: True,
        PREFERRED_FRAMING_KEY: "three_quarter",
        FRAMING_STORE_SCHEMA_KEY: 1,
        "multisensory_phrasebook_v1": {
            "version": 1,
            "welcomes": {"private": ["fixture-private-phrase"]},
        },
    }
)

_NONPORTABLE_EXAMPLE_SETTINGS = frozendict(
    {
        "api_key": "fixture-openai-secret",
        "azure_speech_key": "fixture-azure-secret",
        "azure_hd_speech_key": "fixture-dragon-secret",
        "oauth_access_token": "fixture-oauth-token",
        "face_identity_enabled": True,
        "face_identity_templates": [0.1, 0.2, 0.3],
        "camera_presence_enabled": True,
        "camera_frame_cache": "fixture-camera-frame",
        "autostart": True,
        "background_diagnostic_report": "C:/private/diagnostics.json",
        "tool_permissions": {"delete_files": "允許"},
        "flagship_permissions": {"camera_view": "允許"},
        "remote_port": 8765,
    }
)


def seed_profile(db: StudioDB, prefix: str) -> None:
    now = "2026-07-31T12:00:00"
    db.set_setting("assistant_name", f"{prefix}墨寒")
    db.set_setting("organization_name", f"{prefix}工作室")
    db.set_setting("persona_prompt", f"{prefix}人格")
    db.set_setting("physics_hair", True)
    for key, value in _PORTABLE_EXAMPLE_SETTINGS.items():
        db.set_setting(key, value)
    for key, value in _NONPORTABLE_EXAMPLE_SETTINGS.items():
        db.set_setting(key, value)
    db.set_setting("work_folder", f"C:/{prefix}/work")
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


def remove_settings_from_bundle(
    source: Path,
    target: Path,
    keys: frozenset[str],
) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        profile = archive.read("profile.db")
    manifest.pop("sensitive", None)
    with TemporaryDirectory() as temp:
        database_path = Path(temp) / "legacy-profile.db"
        database_path.write_bytes(profile)
        database = sqlite3.connect(database_path)
        try:
            database.executemany(
                "DELETE FROM settings WHERE key=?",
                ((key,) for key in keys),
            )
            database.commit()
            manifest["record_counts"]["settings"] = database.execute(
                "SELECT COUNT(*) FROM settings"
            ).fetchone()[0]
        finally:
            database.close()
        database_bytes = database_path.read_bytes()
        manifest["database_sha256"] = hashlib.sha256(database_bytes).hexdigest()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False),
            )
            archive.writestr("profile.db", database_bytes)


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
    assert len(fixture.manifest.snapshot_id) == UUID_HEX_LENGTH
    assert len(fixture.manifest.source_installation_id) == UUID_HEX_LENGTH
    assert set(PORTABLE_TABLES) <= set(fixture.manifest.record_counts)
    with zipfile.ZipFile(fixture.bundle, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["secrets_included"] is False
    assert manifest["sensitive"] == {
        "included": False,
        "encrypted": False,
        "archive_member": None,
    }


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
        for key, value in _PORTABLE_EXAMPLE_SETTINGS.items():
            assert json.loads(settings[key]) == value
        for key in _NONPORTABLE_EXAMPLE_SETTINGS:
            assert key not in settings
        assert "work_folder" not in settings
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
    for key, value in _PORTABLE_EXAMPLE_SETTINGS.items():
        assert target_db.setting(key) == value
    assert target_db.setting("work_folder") == "C:/桌機/work"
    for key, value in _NONPORTABLE_EXAMPLE_SETTINGS.items():
        assert target_db.setting(key) == value
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


def _sensitive_stores(*, openai: str, azure: str) -> dict[str, MemorySecretStore]:
    return {
        "openai": MemorySecretStore(openai),
        "azure_speech": MemorySecretStore(azure),
        "oauth_github": MemorySecretStore(),
    }


def _assert_sensitive_round_trip_and_manifest(root: Path) -> None:
    source_db = StudioDB(root / "sensitive-source" / "mohan.db")
    target_db = StudioDB(root / "sensitive-target" / "mohan.db")
    seed_profile(source_db, "敏感來源")
    seed_profile(target_db, "敏感目標")
    source = PortableProfileManager(source_db, root / "sensitive-source" / "backups")
    target = PortableProfileManager(target_db, root / "sensitive-target" / "backups")
    password = bytearray(b"portable profile test password")
    try:
        bundle, _manifest = source.export_profile(
            root / "encrypted-profile",
            sensitive_stores=_sensitive_stores(
                openai=_SENSITIVE_BAIT,
                azure="fixture-azure-protected",
            ),
            password=password,
        )
        assert all(value == 0 for value in password)
        with zipfile.ZipFile(bundle, "r") as archive:
            assert set(archive.namelist()) == {
                "manifest.json",
                "profile.db",
                "sensitive.enc",
            }
            manifest = json.loads(archive.read("manifest.json"))
            envelope = archive.read("sensitive.enc")
        assert _SENSITIVE_BAIT.encode("utf-8") not in envelope
        assert manifest["secrets_included"] is True
        assert manifest["sensitive"] == {
            "included": True,
            "encrypted": True,
            "archive_member": "sensitive.enc",
            "sha256": hashlib.sha256(envelope).hexdigest(),
            "size": len(envelope),
        }
        result = target.import_profile(
            bundle,
            password=bytearray(b"portable profile test password"),
        )
        assert result.sensitive_payload == {
            "format": PORTABLE_SECRETS_FORMAT,
            "version": PORTABLE_SECRETS_VERSION,
            "secrets": {
                "azure_speech": "fixture-azure-protected",
                "openai": _SENSITIVE_BAIT,
            },
        }
        assert _SENSITIVE_BAIT not in repr(result)
        stores = _sensitive_stores(openai="old-openai", azure="old-azure")
        target.apply_imported_sensitive_payload(result, stores)
        assert stores["openai"].value == _SENSITIVE_BAIT
        assert stores["azure_speech"].value == "fixture-azure-protected"
    finally:
        source_db.close()
        target_db.close()


def _assert_sensitive_failure_restores_general_import(root: Path) -> None:
    source_db = StudioDB(root / "rollback-source" / "mohan.db")
    target_db = StudioDB(root / "rollback-target" / "mohan.db")
    seed_profile(source_db, "匯入來源")
    seed_profile(target_db, "匯入前")
    source = PortableProfileManager(source_db, root / "rollback-source" / "backups")
    target = PortableProfileManager(target_db, root / "rollback-target" / "backups")
    try:
        bundle, _manifest = source.export_profile(
            root / "rollback-profile",
            sensitive_stores=_sensitive_stores(
                openai="new-openai",
                azure="new-azure",
            ),
            password=bytearray(b"rollback profile password"),
        )
        result = target.import_profile(
            bundle,
            password=bytearray(b"rollback profile password"),
        )
        assert target_db.setting("assistant_name") == "匯入來源墨寒"
        stores = {
            "openai": MemorySecretStore("old-openai"),
            "azure_speech": MemorySecretStore(
                "old-azure",
                fail_on=frozenset({"new-azure"}),
                mutate_before_failure=True,
            ),
        }
        try:
            target.apply_imported_sensitive_payload(result, stores)
        except ProfileTransferError as exc:
            assert "PRIVATE" not in str(exc)
            assert "new-openai" not in str(exc)
            assert "new-azure" not in str(exc)
            assert "已自動回復" in str(exc)
        else:
            raise AssertionError("敏感 store 失敗時必須回復一般設定")
        assert stores["openai"].value == "old-openai"
        assert stores["azure_speech"].value == "old-azure"
        assert target_db.setting("assistant_name") == "匯入前墨寒"
        assert target_db.setting("portable_last_import_snapshot_id", "") == ""
        assert target_db.conn.execute(
            "SELECT content FROM chat_log"
        ).fetchone()[0] == "匯入前對話"
    finally:
        source_db.close()
        target_db.close()


def _assert_empty_sensitive_stores_remain_excluded(root: Path) -> None:
    database = StudioDB(root / "empty-sensitive" / "mohan.db")
    seed_profile(database, "空值")
    manager = PortableProfileManager(database, root / "empty-sensitive" / "backups")
    try:
        bundle, _manifest = manager.export_profile(
            root / "empty-sensitive-profile",
            sensitive_stores={"openai": MemorySecretStore()},
            password=None,
        )
        with zipfile.ZipFile(bundle, "r") as archive:
            assert "sensitive.enc" not in archive.namelist()
            manifest = json.loads(archive.read("manifest.json"))
        assert manifest["secrets_included"] is False
        assert manifest["sensitive"]["included"] is False
    finally:
        database.close()


def _assert_legacy_v1_profile_remains_compatible(root: Path) -> None:
    fixture = _create_fixture(root)
    legacy_bundle = root / "legacy-v1.mohan-profile"
    fixture.target_db.set_setting("azure_speech_region", "japaneast")
    fixture.target_db.set_setting(
        "multisensory_phrasebook_v1",
        {"version": 1, "welcomes": {"warm": ["主上回來啦"]}},
    )
    new_setting_keys = frozenset(
        set(_PORTABLE_EXAMPLE_SETTINGS)
        | {
            "multisensory_welcome_minimum_seconds",
            "multisensory_welcome_brief_max_seconds",
            "multisensory_welcome_long_seconds",
            "multisensory_conversation_mode",
            "multisensory_conversation_silence_seconds",
        }
    )
    try:
        remove_settings_from_bundle(
            fixture.bundle,
            legacy_bundle,
            new_setting_keys,
        )
        result = fixture.target_manager.import_profile(legacy_bundle)
        assert result.manifest.snapshot_id == fixture.manifest.snapshot_id
        assert fixture.target_db.setting("assistant_name") == "筆電墨寒"
        assert fixture.target_db.setting("azure_speech_region") == "japaneast"
        assert fixture.target_db.setting("multisensory_phrasebook_v1") == {
            "version": 1,
            "welcomes": {"warm": ["主上回來啦"]},
        }
    finally:
        fixture.source_db.close()
        fixture.target_db.close()


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
        assert "forced rollback" not in str(exc)
        assert exc.safe_error is not None
        assert exc.__cause__ is None
        assert exc.__context__ is None
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


def _assert_external_failure_is_safe(error: ProfileTransferError) -> None:
    assert error.safe_error is not None
    assert error.__cause__ is None
    assert error.__context__ is None
    surfaces = [str(error)]
    surfaces.extend(
        safe_error_message(language, error.safe_error)
        for language in _LANGUAGES
    )
    for surface in surfaces:
        assert _BAIT_PATH not in surface
        assert _BAIT_TOKEN not in surface
        assert _BAIT_DETAIL not in surface
    assert all(surface.strip() for surface in surfaces)


def _assert_four_language_ui_discards_private_detail() -> None:
    error = OSError(_BAIT_DETAIL)
    messages = tuple(
        localized_profile_failure(language, error)
        for language in _LANGUAGES
    )
    assert len(set(messages)) == len(_LANGUAGES)
    for message in messages:
        assert _BAIT_PATH not in message
        assert _BAIT_TOKEN not in message
        assert _BAIT_DETAIL not in message
        assert "diagnostic=local_io_failure" in message


def _assert_export_error_discards_private_detail(
    fixture: TransferFixture,
) -> None:
    with patch.object(
        fixture.source_manager,
        "_write_archive",
        side_effect=OSError(_BAIT_DETAIL),
    ):
        try:
            fixture.source_manager.export_profile(
                fixture.root / "private-export"
            )
        except ProfileTransferError as exc:
            _assert_external_failure_is_safe(exc)
        else:
            raise AssertionError("mocked export failure must be reported")


def _assert_inspection_error_discards_private_detail(
    fixture: TransferFixture,
) -> None:
    private_source = fixture.root / f"{_BAIT_TOKEN}.mohan-profile"
    private_source.write_text(_BAIT_DETAIL, encoding="utf-8")
    try:
        fixture.target_manager.inspect_profile(private_source)
    except ProfileTransferError as exc:
        _assert_external_failure_is_safe(exc)
    else:
        raise AssertionError("invalid profile must be rejected")


def _assert_sqlite_error_discards_private_detail(
    fixture: TransferFixture,
) -> None:
    fixture.source_db.set_setting("assistant_name", "安全邊界測試")
    bundle, _manifest = fixture.source_manager.export_profile(
        fixture.root / "安全邊界測試"
    )
    trigger = _BAIT_DETAIL.replace("'", "''")
    fixture.target_db.conn.execute(
        "CREATE TRIGGER reject_private_profile_delete "
        "BEFORE DELETE ON todos BEGIN "
        f"SELECT RAISE(ABORT,'{trigger}'); END"
    )
    fixture.target_db.conn.commit()
    try:
        fixture.target_manager.import_profile(bundle)
    except ProfileTransferError as exc:
        _assert_external_failure_is_safe(exc)
    else:
        raise AssertionError("mocked SQLite failure must be reported")
    fixture.target_db.conn.execute("DROP TRIGGER reject_private_profile_delete")
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
            _assert_export_error_discards_private_detail(fixture)
            _assert_inspection_error_discards_private_detail(fixture)
            _assert_sqlite_error_discards_private_detail(fixture)
            _assert_four_language_ui_discards_private_detail()
        finally:
            fixture.source_db.close()
            fixture.target_db.close()
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        _assert_legacy_v1_profile_remains_compatible(Path(temp))
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        _assert_sensitive_round_trip_and_manifest(root)
        _assert_sensitive_failure_restores_general_import(root)
        _assert_empty_sensitive_stores_remain_excluded(root)
    print("PROFILE_TRANSFER_OK")


if __name__ == "__main__":
    run()
