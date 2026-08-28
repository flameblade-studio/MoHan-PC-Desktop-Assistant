from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB
lazy from infrastructure.openai_vision_preferences_store import STORE_SCHEMA_KEY
lazy from infrastructure.profile_transfer import (
    PORTABLE_SETTING_KEYS,
    PortableProfileManager,
)
lazy from domain.openai_vision_preferences import SETTING_KEYS


def assert_real_profile_round_trip_excludes_key(root: Path) -> None:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    try:
        for index, key in enumerate(SETTING_KEYS):
            source_db.set_setting(key, False if "enabled" in key else index + 1)
        source_db.set_setting(STORE_SCHEMA_KEY, 1)
        source_db.set_setting("api_key", "PRIVATE-OPENAI-KEY")
        source = PortableProfileManager(source_db, root / "source" / "backups")
        target = PortableProfileManager(target_db, root / "target" / "backups")
        bundle, _manifest = source.export_profile(root / "vision-profile")
        target.import_profile(bundle)
        for key in SETTING_KEYS:
            assert target_db.setting(key) == source_db.setting(key)
        assert target_db.setting(STORE_SCHEMA_KEY) == 1
        assert target_db.setting("api_key", None) is None
    finally:
        source_db.close()
        target_db.close()


def run() -> None:
    assert set(SETTING_KEYS) <= PORTABLE_SETTING_KEYS
    assert STORE_SCHEMA_KEY in PORTABLE_SETTING_KEYS
    lowered = {key.lower() for key in PORTABLE_SETTING_KEYS}
    assert not any("api_key" in key or "secret" in key for key in lowered)
    assert "openai_key" not in lowered
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        assert_real_profile_round_trip_excludes_key(Path(temp))
    print("OPENAI_VISION_PROFILE_WIRING_OK")


if __name__ == "__main__":
    run()
