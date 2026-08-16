from __future__ import annotations

lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from framing_preferences import (
    SETTING_KEYS,
    FramingPreferences,
    PreferredFraming,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.framing_preferences_store import (
    STORE_SCHEMA_KEY,
    FramingPreferencesStore,
)
lazy from infrastructure.profile_transfer import PortableProfileManager


def assert_db_staging_and_profile_round_trip(root: Path) -> None:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    source = FramingPreferencesStore(StudioDBSettingsPort(source_db))
    target = FramingPreferencesStore(StudioDBSettingsPort(target_db))
    expected = FramingPreferences(
        adaptive_enabled=False,
        allow_close=False,
        allow_full_body=True,
        focus_protection_enabled=False,
        preferred_framing=PreferredFraming.FULL_BODY,
    )
    try:
        before = source_db.conn.total_changes
        source.begin_edit().update(
            preferred_framing=PreferredFraming.CLOSE
        ).cancel()
        assert source_db.conn.total_changes == before
        source.save(expected)
        target.save(FramingPreferences(preferred_framing=PreferredFraming.HALF))
        source_db.set_setting("api_key", "fixture-secret")
        source_db.set_setting("face_identity_templates", "fixture-embedding")
        source_db.set_setting("camera_frame_cache", "fixture-frame")
        source_db.set_setting(
            "multisensory_phrasebook_v1",
            {"version": 1, "welcomes": {"custom": ["fixture-phrasebook"]}},
        )
        bundle, _manifest = PortableProfileManager(
            source_db, root / "source" / "backups"
        ).export_profile(root / "framing-profile")
        with zipfile.ZipFile(bundle, "r") as archive:
            exported_path = root / "exported.db"
            exported_path.write_bytes(archive.read("profile.db"))
        exported = sqlite3.connect(exported_path)
        try:
            rows = dict(exported.execute("SELECT key,value FROM settings"))
        finally:
            exported.close()
        assert set(SETTING_KEYS) <= set(rows)
        assert STORE_SCHEMA_KEY in rows
        for forbidden in (
            "api_key",
            "face_identity_templates",
            "camera_frame_cache",
        ):
            assert forbidden not in rows
        assert "multisensory_phrasebook_v1" in rows
        PortableProfileManager(
            target_db, root / "target" / "backups"
        ).import_profile(bundle)
        assert target.load() == expected
    finally:
        source_db.close()
        target_db.close()


def assert_old_profile_preserves_local_framing(root: Path) -> None:
    source_db = StudioDB(root / "old-source" / "mohan.db")
    target_db = StudioDB(root / "old-target" / "mohan.db")
    target = FramingPreferencesStore(StudioDBSettingsPort(target_db))
    local = FramingPreferences(preferred_framing=PreferredFraming.CLOSE)
    try:
        target.save(local)
        bundle, _manifest = PortableProfileManager(
            source_db, root / "old-source" / "backups"
        ).export_profile(root / "old-profile")
        PortableProfileManager(
            target_db, root / "old-target" / "backups"
        ).import_profile(bundle)
        assert target.load() == local
    finally:
        source_db.close()
        target_db.close()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_db_staging_and_profile_round_trip(root)
        assert_old_profile_preserves_local_framing(root)
    print("FRAMING_PREFERENCES_WIRING_OK")


if __name__ == "__main__":
    run()
