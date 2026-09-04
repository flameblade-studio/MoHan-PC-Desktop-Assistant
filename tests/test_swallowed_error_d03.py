from __future__ import annotations

lazy import sys
lazy from datetime import datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.corrupt_data import (
    CORRUPT_DATA_MESSAGE,
    CorruptStoredJSON,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.memory_index import MemoryVectorIndex

BROKEN_JSON = "{broken-json"


def assert_settings_bad_json_is_retained_and_reported() -> None:
    with TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "settings.db")
        try:
            db.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?)",
                ("broken_setting", BROKEN_JSON),
            )
            db.conn.commit()
            result = StudioDBSettingsPort(db).read(("broken_setting",))["broken_setting"]
            assert isinstance(result, CorruptStoredJSON)
            assert result.status == "corrupt"
            assert result.raw == BROKEN_JSON
            assert db.consume_corrupt_data_notifications() == (CORRUPT_DATA_MESSAGE,)
            assert db.consume_corrupt_data_notifications() == ()
        finally:
            db.close()


def assert_migration_bad_json_is_not_overwritten() -> None:
    with TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "migration.db")
        try:
            db.conn.execute(
                "INSERT INTO settings(key,value) VALUES('ai_model',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (BROKEN_JSON,),
            )
            db._migrate_model_default(
                "d03_test_marker",
                frozenset({None}),
                "replacement-model",
            )
            assert db.get_setting("ai_model") == BROKEN_JSON
        finally:
            db.close()


def assert_archive_bad_json_is_retained_and_reported() -> None:
    with TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "archive.db")
        try:
            db.conn.execute(
                "INSERT INTO memory_archive(original_id,snapshot,reason,archived_at) "
                "VALUES(1,?,?,?)",
                (BROKEN_JSON, "test", "2026-09-04T00:00:00"),
            )
            db.conn.commit()
            row = db.list_archived_memories()[0]
            assert row["status"] == "corrupt"
            assert row["raw_snapshot"] == BROKEN_JSON
            assert db.consume_corrupt_data_notifications() == (CORRUPT_DATA_MESSAGE,)
        finally:
            db.close()


def assert_archive_restore_bad_json_returns_status() -> None:
    with TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "archive-restore.db")
        try:
            db.conn.execute(
                "INSERT INTO memory_archive(original_id,snapshot,reason,archived_at) "
                "VALUES(1,?,?,?)",
                (BROKEN_JSON, "test", "2026-09-04T00:00:00"),
            )
            db.conn.commit()
            result = db.restore_archived_memory(1)
            assert isinstance(result, CorruptStoredJSON)
            assert result.status == "corrupt"
            assert result.raw == BROKEN_JSON
        finally:
            db.close()


def assert_invalid_memory_date_is_not_treated_as_ten_years_old() -> None:
    with TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "date.db")
        try:
            memory_id = db.add_memory("日期壞值不可偽裝成十年前", source="conversation")
            db.conn.execute(
                "UPDATE memories SET updated_at=? WHERE id=?",
                ("not-a-date", memory_id),
            )
            db.conn.commit()
            row = db.memory(memory_id)
            assert row is not None
            assert db._memory_age_days(row, datetime(2026, 9, 4)) is None
        finally:
            db.close()


def assert_memory_index_marks_invalid_timestamp() -> None:
    index = MemoryVectorIndex()
    ranked = index.rank(
        "保留",
        [
            {
                "id": 1,
                "category": "偏好",
                "title": "保留",
                "content": "保留這項記憶",
                "importance": 3,
                "updated_at": "not-a-date",
            }
        ],
        1,
        now=datetime(2026, 9, 4),
    )
    assert ranked[0].status == "corrupt-timestamp"


def run() -> None:
    checks = (
        assert_settings_bad_json_is_retained_and_reported,
        assert_migration_bad_json_is_not_overwritten,
        assert_archive_bad_json_is_retained_and_reported,
        assert_archive_restore_bad_json_returns_status,
        assert_invalid_memory_date_is_not_treated_as_ten_years_old,
        assert_memory_index_marks_invalid_timestamp,
    )
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except Exception as error:
            failures.append(f"{check.__name__}: {type(error).__name__}: {error}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("D03_CORRUPT_DATA_OK")


if __name__ == "__main__":
    run()
