from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from infrastructure.db import RUNTIME_PRESERVED_KEYS, StudioDB

GROWN_AFFINITY = 0.62
LIVE_TEMPERATURE_C = 33.5
DRAFT_BREAK_MINUTES = 45
SNAPSHOT_BREAK_MINUTES = 25


@pytest.fixture
def db(tmp_path):
    database = StudioDB(tmp_path / "mohan.db")
    try:
        yield database
    finally:
        database.close()


def test_restore_keeps_runtime_state_written_after_the_snapshot(db) -> None:
    """Cancelling a settings draft must not roll back live runtime progress."""

    db.set_setting("break_minutes", SNAPSHOT_BREAK_MINUTES)
    db.set_setting("affinity_value", 0.30)
    db.set_setting("weather_temperature_c", 21.0)
    snapshot = db.settings_snapshot()

    # The settings dialog stays open while the companion keeps living.
    db.set_setting("break_minutes", DRAFT_BREAK_MINUTES)  # user draft noise
    db.set_setting("affinity_value", GROWN_AFFINITY)  # runtime growth
    db.set_setting("weather_temperature_c", LIVE_TEMPERATURE_C)
    db.set_setting("wardrobe_generation_pending_job_id", "job-1")  # new key
    db.set_setting("wardrobe_reveal_pending_outfit_id", "outfit-9")

    db.restore_settings_snapshot(snapshot)

    # Ordinary settings roll back to the snapshot.
    assert db.setting("break_minutes") == SNAPSHOT_BREAK_MINUTES
    # Runtime keys keep their live values, including keys that did not exist
    # when the snapshot was taken.
    assert db.setting("affinity_value") == GROWN_AFFINITY
    assert db.setting("weather_temperature_c") == LIVE_TEMPERATURE_C
    assert db.setting("wardrobe_generation_pending_job_id") == "job-1"
    assert db.setting("wardrobe_reveal_pending_outfit_id") == "outfit-9"


def test_restore_drops_non_runtime_keys_created_after_the_snapshot(db) -> None:
    snapshot = db.settings_snapshot()
    db.set_setting("break_minutes", DRAFT_BREAK_MINUTES)
    db.restore_settings_snapshot(snapshot)
    assert db.setting("break_minutes", None) is None


def test_preserved_key_absent_at_restore_time_stays_absent(db) -> None:
    """A runtime key deleted from the live table must not resurrect."""

    db.set_setting("affinity_value", 0.4)
    snapshot = db.settings_snapshot()
    db.conn.execute("DELETE FROM settings WHERE key='affinity_value'")
    db.conn.commit()
    db.restore_settings_snapshot(snapshot)
    assert db.setting("affinity_value", None) is None


def test_preserved_keys_cover_the_audited_runtime_families() -> None:
    expected = {
        "affinity_value",
        "jealousy_value",
        "affinity_interaction_count",
        "wardrobe_generation_pending_job_id",
        "wardrobe_last_generated_at",
        "active_outfit_id",
        "wardrobe_last_changed_at",
        "wardrobe_manual_lock_until",
        "weather_temperature_c",
        "weather_condition",
        "wardrobe_reveal_pending_outfit_id",
    }
    assert expected <= RUNTIME_PRESERVED_KEYS
