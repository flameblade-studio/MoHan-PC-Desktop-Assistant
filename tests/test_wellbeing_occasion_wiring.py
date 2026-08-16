from __future__ import annotations

lazy import json
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.profile_transfer import PortableProfileManager
lazy from infrastructure.special_occasion_store import (
    SPECIAL_OCCASION_STATE_KEY,
    OccasionState,
    SpecialOccasionState,
    SpecialOccasionStore,
)
lazy from infrastructure.wellbeing_reminder_store import (
    WELLBEING_STATE_KEY,
    WellbeingReminderStore,
    default_wellbeing_state,
)
lazy from special_occasion import OccasionKind, OccasionResponse
lazy from wellbeing_reminder import ReminderResponse, WellbeingKind

NOW = datetime(2027, 1, 8, 12, tzinfo=UTC)
FORBIDDEN_SETTINGS = {
    "api_key": "fixture-api-secret",
    "oauth_access_token": "fixture-oauth-secret",
    "face_identity_templates": "fixture-face-embedding",
    "camera_frame_cache": "fixture-camera-frame",
}
PHRASEBOOK = {
    "version": 1,
    "welcomes": {"private": ["fixture-user-authored-phrase"]},
}


def wellbeing_state(store: WellbeingReminderStore):
    state = default_wellbeing_state(NOW.date())
    return store.update_kind(
        state,
        WellbeingKind.HYDRATION,
        enabled=False,
        snooze_until=NOW + timedelta(minutes=30),
        response=ReminderResponse.SNOOZED,
        initial_delivered_at=NOW - timedelta(minutes=20),
        reinforcement_delivered_at=NOW - timedelta(minutes=5),
        daily_reinforcement_count=2,
        maximum_daily_reinforcements=6,
        same_kind_cooldown_seconds=5400,
        last_same_kind_reinforcement_at=NOW - timedelta(minutes=5),
    )


def occasion_state() -> SpecialOccasionState:
    return SpecialOccasionState(
        NOW.date(),
        {
            kind: OccasionState(
                enabled=kind is not OccasionKind.CHRISTMAS_DAY,
                hint_delivered_at=NOW - timedelta(hours=3),
                grumble_delivered_at=NOW - timedelta(hours=1),
                response=(
                    OccasionResponse.CELEBRATED
                    if kind is OccasionKind.MOHAN_BIRTHDAY
                    else OccasionResponse.DISMISSED
                ),
            )
            for kind in OccasionKind
        },
    )


def assert_profile_round_trip_and_private_boundaries(root: Path) -> None:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    source_wellbeing = WellbeingReminderStore(StudioDBSettingsPort(source_db))
    target_wellbeing = WellbeingReminderStore(StudioDBSettingsPort(target_db))
    source_occasion = SpecialOccasionStore(StudioDBSettingsPort(source_db))
    target_occasion = SpecialOccasionStore(StudioDBSettingsPort(target_db))
    expected_wellbeing = wellbeing_state(source_wellbeing)
    expected_occasion = occasion_state()
    try:
        source_wellbeing.save(expected_wellbeing)
        source_occasion.save(expected_occasion)
        source_db.set_setting("multisensory_phrasebook_v1", PHRASEBOOK)
        for key, value in FORBIDDEN_SETTINGS.items():
            source_db.set_setting(key, value)
            target_db.set_setting(key, f"target-{key}")

        bundle, _manifest = PortableProfileManager(
            source_db, root / "source" / "backups"
        ).export_profile(root / "wellbeing-occasion-profile")
        with zipfile.ZipFile(bundle, "r") as archive:
            exported_path = root / "exported.db"
            exported_path.write_bytes(archive.read("profile.db"))
        exported = sqlite3.connect(exported_path)
        try:
            settings = dict(exported.execute("SELECT key,value FROM settings"))
        finally:
            exported.close()
        assert WELLBEING_STATE_KEY in settings
        assert SPECIAL_OCCASION_STATE_KEY in settings
        assert json.loads(settings["multisensory_phrasebook_v1"]) == PHRASEBOOK
        assert FORBIDDEN_SETTINGS.keys().isdisjoint(settings)

        PortableProfileManager(
            target_db, root / "target" / "backups"
        ).import_profile(bundle)
        assert target_wellbeing.load(NOW) == expected_wellbeing
        assert target_occasion.load(NOW) == expected_occasion
        assert target_db.setting("multisensory_phrasebook_v1") == PHRASEBOOK
        for key in FORBIDDEN_SETTINGS:
            assert target_db.setting(key) == f"target-{key}"
    finally:
        source_db.close()
        target_db.close()


def assert_old_profile_preserves_new_local_state(root: Path) -> None:
    source_db = StudioDB(root / "legacy-source" / "mohan.db")
    target_db = StudioDB(root / "legacy-target" / "mohan.db")
    target_wellbeing = WellbeingReminderStore(StudioDBSettingsPort(target_db))
    target_occasion = SpecialOccasionStore(StudioDBSettingsPort(target_db))
    local_wellbeing = wellbeing_state(target_wellbeing)
    local_occasion = occasion_state()
    try:
        target_wellbeing.save(local_wellbeing)
        target_occasion.save(local_occasion)
        bundle, _manifest = PortableProfileManager(
            source_db, root / "legacy-source" / "backups"
        ).export_profile(root / "legacy-profile")
        PortableProfileManager(
            target_db, root / "legacy-target" / "backups"
        ).import_profile(bundle)
        assert target_wellbeing.load(NOW) == local_wellbeing
        assert target_occasion.load(NOW) == local_occasion
    finally:
        source_db.close()
        target_db.close()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_profile_round_trip_and_private_boundaries(root)
        assert_old_profile_preserves_new_local_state(root)
    print("WELLBEING_OCCASION_WIRING_OK")


if __name__ == "__main__":
    run()
