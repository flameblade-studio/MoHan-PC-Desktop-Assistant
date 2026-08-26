from __future__ import annotations

lazy from datetime import UTC, datetime
lazy from pathlib import Path

lazy from infrastructure.db import StudioDB

TARGET_ACTIVE = 400
EXPECTED_ARCHIVED = 101


def test_recent_important_memories_archive_recoverably_instead_of_filling(
    tmp_path: Path,
) -> None:
    db = StudioDB(tmp_path / "capacity.db")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        with db.conn:
            db.conn.executemany(
                "INSERT INTO memories(category,title,content,source,importance,"
                "created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (
                    ("人物", f"重要 {index}", f"recent-{index}", "manual", 5, now, now)
                    for index in range(501)
                ),
            )

        result = db.optimize_memories(max_active=500, target_active=TARGET_ACTIVE)

        assert result["active"] == TARGET_ACTIVE
        assert result["capacity_fallback"] == EXPECTED_ARCHIVED
        archived = db.list_archived_memories(200)
        assert len(archived) == EXPECTED_ARCHIVED
        assert {item["reason"] for item in archived} == {"capacity-overflow"}
        assert db.restore_archived_memory(int(archived[0]["id"])) > 0
    finally:
        db.close()
