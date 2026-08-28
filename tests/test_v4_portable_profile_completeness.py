from __future__ import annotations

lazy import json
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.appearance_session import ACTIVE_OUTFIT_SETTING_KEY
lazy from domain.framing_preferences import SETTING_KEYS as FRAMING_SETTING_KEYS
lazy from domain.gesture_configuration import LANDMARKS_PER_HAND
lazy from infrastructure.companion_proactivity_preferences_store import (
    PORTABLE_SETTING_KEYS as PROACTIVITY_SETTING_KEYS,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.framing_preferences_store import (
    STORE_SCHEMA_KEY as FRAMING_SCHEMA_KEY,
)
lazy from infrastructure.gesture_configuration_store import (
    PORTABLE_GESTURE_SETTING_KEYS,
)
lazy from infrastructure.openai_vision_preferences_store import (
    STORE_SCHEMA_KEY as VISION_SCHEMA_KEY,
)
lazy from infrastructure.performance_preferences_store import (
    STORE_SCHEMA_KEY as PERFORMANCE_SCHEMA_KEY,
)
lazy from infrastructure.portable_secret_binding import bind_portable_secret_stores
lazy from infrastructure.portable_secrets import SECRET_IDS
lazy from infrastructure.profile_transfer import (
    PORTABLE_SETTING_KEYS,
    PortableProfileManager,
)
lazy from domain.openai_vision_preferences import SETTING_KEYS as VISION_SETTING_KEYS
lazy from domain.performance_preferences import SETTING_KEYS as PERFORMANCE_SETTING_KEYS
lazy from domain.theme_session import ACTIVE_THEME_SETTING_KEY

VOICE_SETTING_KEYS = frozenset(
    {
        "voice_engine",
        "windows_voice",
        "azure_speech_region",
        "azure_speech_voice",
        "azure_hd_speech_region",
        "azure_hd_speech_voice",
        "tts_voice",
        "cloud_voice",
        "voice_rate",
        "voice_volume_percent",
        "voice_muted",
        "voice_instructions",
        "speech_recognition",
        "transcription_model",
        "transcription_language",
        "transcription_prompt",
        "windows_transcription_fallback",
        "realtime_model",
        "realtime_voice",
        "realtime_output_mode",
        "realtime_transcription_model",
        "realtime_noise_reduction",
        "realtime_turn_detection",
        "realtime_echo_guard",
        "realtime_hybrid_transcription",
    }
)
V4_APPEARANCE_SETTING_KEYS = frozenset(
    {
        "flagship_high_contrast",
        "flagship_ui_scale",
        ACTIVE_THEME_SETTING_KEY,
        ACTIVE_OUTFIT_SETTING_KEY,
    }
)
V4_INTERACTION_SETTING_KEYS = frozenset(
    {
        "multisensory_phrasebook_v1",
        *PROACTIVITY_SETTING_KEYS,
        *PORTABLE_GESTURE_SETTING_KEYS,
        *VISION_SETTING_KEYS,
        VISION_SCHEMA_KEY,
    }
)
V4_POSE_SETTING_KEYS = frozenset(
    {
        *FRAMING_SETTING_KEYS,
        FRAMING_SCHEMA_KEY,
        *PERFORMANCE_SETTING_KEYS,
        PERFORMANCE_SCHEMA_KEY,
    }
)
REQUIRED_SECRET_IDS = frozenset(
    {
        "openai",
        "azure_speech",
        "azure_dragon_hd",
        "home_assistant",
        "oauth_google",
        "oauth_microsoft",
        "oauth_github",
        "face_identities",
        "gesture_templates",
    }
)
FORBIDDEN_ORDINARY_SETTING_KEYS = frozenset(
    {
        "api_key",
        "openai_api_key",
        "realtime_api_key",
        "azure_speech_key",
        "azure_hd_speech_key",
        "face_identity_templates",
        "gesture_templates",
        "camera_frame_cache",
    }
)
MACHINE_OR_PERMISSION_SETTING_KEYS = frozenset(
    {
        "camera_presence_enabled",
        "face_identity_enabled",
        "adaptive_character_v4_enabled",
        "autostart",
        "work_folder",
        "remote_port",
        "tool_permissions",
        "flagship_permissions",
    }
)


class MemorySecretStore:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


def _gesture_template_payload() -> str:
    points = [[index / 100, index / 200, 0.0] for index in range(LANDMARKS_PER_HAND)]
    return json.dumps(
        {
            "format": "mohan-protected-gesture-templates",
            "version": 1,
            "templates": {"custom:portable-audit": [points]},
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _face_template_payload() -> str:
    return json.dumps(
        {
            "version": 1,
            "profiles": [
                {
                    "profile_id": "portable-audit-profile",
                    "display_name": "Portable audit",
                    "embeddings": [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4]],
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _profile_setting_keys(bundle: Path, temporary_root: Path) -> frozenset[str]:
    with zipfile.ZipFile(bundle, "r") as archive:
        database_path = temporary_root / "profile.db"
        database_path.write_bytes(archive.read("profile.db"))
    connection = sqlite3.connect(database_path)
    try:
        return frozenset(
            str(row[0]) for row in connection.execute("SELECT key FROM settings")
        )
    finally:
        connection.close()


def _seed_portable_settings(database: StudioDB) -> None:
    for key in _required_portable_setting_keys():
        database.set_setting(key, f"portable-value:{key}")
    database.conn.commit()


def _required_portable_setting_keys() -> frozenset[str]:
    return frozenset(
        {
        *VOICE_SETTING_KEYS,
        *V4_INTERACTION_SETTING_KEYS,
        *V4_APPEARANCE_SETTING_KEYS,
        *V4_POSE_SETTING_KEYS,
        }
    )


def _assert_sensitive_archive_is_opaque(
    bundle: Path,
    secret_values: dict[str, str],
    unique_prefix: str,
) -> None:
    archive_bytes = bundle.read_bytes()
    assert unique_prefix.encode("utf-8") not in archive_bytes
    assert _face_template_payload().encode("utf-8") not in archive_bytes
    assert _gesture_template_payload().encode("utf-8") not in archive_bytes
    with zipfile.ZipFile(bundle, "r") as archive:
        assert "sensitive.enc" in archive.namelist()
        archive_manifest = json.loads(archive.read("manifest.json"))
        assert archive_manifest["secrets_included"] is True
        assert archive_manifest["sensitive"]["encrypted"] is True
        ordinary_database = archive.read("profile.db")
        assert not any(
            value.encode("utf-8") in ordinary_database
            for value in secret_values.values()
        )


def test_v4_portable_ordinary_setting_contract_is_complete() -> None:
    required = _required_portable_setting_keys()
    missing = sorted(required - PORTABLE_SETTING_KEYS)
    assert not missing, "V4_PORTABLE_ORDINARY_SETTINGS_MISSING: " + ", ".join(missing)


def test_sensitive_and_machine_bound_values_never_use_ordinary_profile() -> None:
    assert not (FORBIDDEN_ORDINARY_SETTING_KEYS & PORTABLE_SETTING_KEYS)
    assert not (MACHINE_OR_PERMISSION_SETTING_KEYS & PORTABLE_SETTING_KEYS)


def test_v4_secret_contract_is_complete_and_uses_distinct_stores() -> None:
    assert SECRET_IDS == REQUIRED_SECRET_IDS
    stores = {secret_id: MemorySecretStore() for secret_id in SECRET_IDS}
    binding = bind_portable_secret_stores(stores)
    assert binding.store_ids() == REQUIRED_SECRET_IDS
    assert len({id(store) for store in stores.values()}) == len(REQUIRED_SECRET_IDS)


def test_v4_sensitive_round_trip_is_encrypted_and_complete() -> None:
    unique_prefix = "V4-PORTABLE-SENSITIVE-PLAINTEXT-MUST-NOT-LEAK-"
    secret_values = {
        secret_id: unique_prefix + secret_id for secret_id in sorted(SECRET_IDS)
    }
    secret_values["face_identities"] = _face_template_payload()
    secret_values["gesture_templates"] = _gesture_template_payload()
    stores = {
        secret_id: MemorySecretStore(value)
        for secret_id, value in secret_values.items()
    }
    password = bytearray(b"v4 portable profile audit password")
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        source_db = StudioDB(root / "source" / "mohan.db")
        target_db = StudioDB(root / "target" / "mohan.db")
        try:
            _seed_portable_settings(source_db)
            source = PortableProfileManager(source_db, root / "source-backups")
            bundle, _manifest = source.export_profile(
                root / "complete-v4",
                sensitive_stores=stores,
                password=password,
            )
            assert all(value == 0 for value in password)
            _assert_sensitive_archive_is_opaque(
                bundle,
                secret_values,
                unique_prefix,
            )
            exported_keys = _profile_setting_keys(bundle, root)
            assert _required_portable_setting_keys() <= exported_keys
            assert not (FORBIDDEN_ORDINARY_SETTING_KEYS & exported_keys)
            target = PortableProfileManager(target_db, root / "target-backups")
            result = target.import_profile(
                bundle,
                password=bytearray(b"v4 portable profile audit password"),
            )
            for key in _required_portable_setting_keys():
                assert target_db.setting(key) == f"portable-value:{key}"
            assert result.sensitive_payload is not None
            assert result.sensitive_payload["secrets"] == secret_values
            restored = {
                secret_id: MemorySecretStore() for secret_id in SECRET_IDS
            }
            target.apply_imported_sensitive_payload(result, restored)
            assert {
                secret_id: store.value for secret_id, store in restored.items()
            } == secret_values
        finally:
            source_db.close()
            target_db.close()


def test_realtime_reuses_openai_secret_without_plaintext_duplicate() -> None:
    assert "openai" in SECRET_IDS
    assert "openai_realtime" not in SECRET_IDS
    assert "realtime_api_key" not in PORTABLE_SETTING_KEYS
    assert {
        "realtime_model",
        "realtime_voice",
        "realtime_output_mode",
    } <= PORTABLE_SETTING_KEYS


if __name__ == "__main__":
    test_sensitive_and_machine_bound_values_never_use_ordinary_profile()
    test_v4_secret_contract_is_complete_and_uses_distinct_stores()
    test_v4_sensitive_round_trip_is_encrypted_and_complete()
    test_realtime_reuses_openai_secret_without_plaintext_duplicate()
    test_v4_portable_ordinary_setting_contract_is_complete()
