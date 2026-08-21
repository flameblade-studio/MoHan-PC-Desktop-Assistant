from __future__ import annotations

lazy import json
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.performance_preferences_store import (
    STORE_SCHEMA_KEY,
    PerformancePreferencesStore,
)
lazy from infrastructure.profile_transfer import PortableProfileManager
lazy from performance_preferences import (
    INTENSITY_KEY,
    PREFERENCES_FORMAT,
    PREFERENCES_VERSION,
    PROACTIVE_BODY_KEY,
    SETTING_KEYS,
    PerformancePreferences,
)

DEFAULT_INTENSITY_PERCENT = 60
COMMITTED_INTENSITY_PERCENT = 72
IMPORTED_INTENSITY_PERCENT = 77

PRIVATE_SETTINGS = {
    "api_key": "fixture-secret",
    "azure_speech_key": "fixture-azure-secret",
    "face_identity_templates": "fixture-embedding",
    "camera_frame_cache": "fixture-camera-frame",
}
PORTABLE_PRIVATE_PHRASEBOOK = {
    "version": 1,
    "welcomes": {"custom": ["fixture-private-phrasebook"]},
}


def assert_db_port_is_atomic_and_cancel_does_not_write(root: Path) -> None:
    database = StudioDB(root / "db-port" / "mohan.db")
    try:
        database.set_setting(PROACTIVE_BODY_KEY, True)
        database.set_setting(INTENSITY_KEY, 60)
        store = PerformancePreferencesStore(StudioDBSettingsPort(database))
        before_changes = database.conn.total_changes
        draft = store.begin_edit().update(
            proactive_body_enabled=False,
            intensity_percent=95,
            camera_context_enabled=True,
        )
        draft.cancel()
        assert database.conn.total_changes == before_changes
        assert database.setting(PROACTIVE_BODY_KEY) is True
        assert database.setting(INTENSITY_KEY) == DEFAULT_INTENSITY_PERCENT

        committed = store.begin_edit().update(intensity_percent=72).commit()
        assert committed.intensity_percent == COMMITTED_INTENSITY_PERCENT
        assert database.setting(INTENSITY_KEY) == COMMITTED_INTENSITY_PERCENT
        assert database.setting(STORE_SCHEMA_KEY) == 1
    finally:
        database.close()


def assert_profile_round_trip_uses_existing_settings_schema(root: Path) -> None:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    source = PerformancePreferencesStore(StudioDBSettingsPort(source_db))
    target = PerformancePreferencesStore(StudioDBSettingsPort(target_db))
    source_preferences = PerformancePreferences(
        proactive_body_enabled=False,
        intensity_percent=88,
        view_360_enabled=True,
        full_back_view_enabled=True,
        emotional_back_view_enabled=True,
        left_gestures_enabled=False,
        right_gestures_enabled=True,
        camera_context_enabled=True,
    )
    try:
        source.save(source_preferences)
        target.save(PerformancePreferences(intensity_percent=12))
        for key, value in PRIVATE_SETTINGS.items():
            source_db.set_setting(key, value)
            target_db.set_setting(key, f"target-{key}")
        source_db.set_setting(
            "multisensory_phrasebook_v1", PORTABLE_PRIVATE_PHRASEBOOK
        )
        target_db.set_setting(
            "multisensory_phrasebook_v1", {"version": 1, "welcomes": {}}
        )
        manager = PortableProfileManager(source_db, root / "source" / "backups")
        bundle, _manifest = manager.export_profile(root / "performance-profile")
        with zipfile.ZipFile(bundle, "r") as archive:
            exported_path = root / "exported.db"
            exported_path.write_bytes(archive.read("profile.db"))
        exported = sqlite3.connect(exported_path)
        try:
            settings = dict(exported.execute("SELECT key,value FROM settings"))
        finally:
            exported.close()
        assert set(SETTING_KEYS) <= set(settings)
        assert STORE_SCHEMA_KEY in settings
        for key in PRIVATE_SETTINGS:
            assert key not in settings
        assert json.loads(settings["multisensory_phrasebook_v1"]) == (
            PORTABLE_PRIVATE_PHRASEBOOK
        )

        PortableProfileManager(
            target_db, root / "target" / "backups"
        ).import_profile(bundle)
        assert target.load() == source_preferences
        for key in PRIVATE_SETTINGS:
            assert target_db.setting(key) == f"target-{key}"
        assert target_db.setting("multisensory_phrasebook_v1") == (
            PORTABLE_PRIVATE_PHRASEBOOK
        )
    finally:
        source_db.close()
        target_db.close()


def assert_old_profile_preserves_new_local_preferences(root: Path) -> None:
    source_db = StudioDB(root / "legacy-source" / "mohan.db")
    target_db = StudioDB(root / "legacy-target" / "mohan.db")
    target_store = PerformancePreferencesStore(StudioDBSettingsPort(target_db))
    local = PerformancePreferences(intensity_percent=31, camera_context_enabled=False)
    try:
        target_store.save(local)
        manager = PortableProfileManager(source_db, root / "legacy-source" / "backups")
        bundle, _manifest = manager.export_profile(root / "legacy-profile")
        PortableProfileManager(
            target_db, root / "legacy-target" / "backups"
        ).import_profile(bundle)
        assert target_store.load() == local
    finally:
        source_db.close()
        target_db.close()


def assert_unknown_portable_fields_never_reach_database(root: Path) -> None:
    database = StudioDB(root / "unknown" / "mohan.db")
    store = PerformancePreferencesStore(StudioDBSettingsPort(database))
    try:
        imported = store.import_portable(
            {
                "format": PREFERENCES_FORMAT,
                "version": PREFERENCES_VERSION,
                "future": "ignored",
                "preferences": {
                    "intensity_percent": 77,
                    "future_motion": True,
                    "api_key": "must-not-persist",
                    "face_embedding": [0.1, 0.2],
                    "camera_frame": "must-not-persist",
                    "private_phrasebook": "must-not-persist",
                },
            }
        )
        assert imported.intensity_percent == IMPORTED_INTENSITY_PERCENT
        raw = dict(database.conn.execute("SELECT key,value FROM settings"))
        forbidden = {
            "future_motion",
            "api_key",
            "face_embedding",
            "camera_frame",
            "private_phrasebook",
        }
        assert forbidden.isdisjoint(raw)
        serialized = json.dumps(
            {
                key: raw[key]
                for key in (*SETTING_KEYS, STORE_SCHEMA_KEY)
                if key in raw
            }
        )
        assert "must-not-persist" not in serialized
        assert "embedding" not in serialized
        assert "phrasebook" not in serialized
    finally:
        database.close()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_db_port_is_atomic_and_cancel_does_not_write(root)
        assert_profile_round_trip_uses_existing_settings_schema(root)
        assert_old_profile_preserves_new_local_preferences(root)
        assert_unknown_portable_fields_never_reach_database(root)
    print("PERFORMANCE_PREFERENCES_WIRING_OK")


if __name__ == "__main__":
    run()
