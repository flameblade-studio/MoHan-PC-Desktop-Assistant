from __future__ import annotations

lazy import hashlib
lazy import sys
lazy import time
lazy from datetime import timedelta
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB
lazy from infrastructure.memory_index import MemoryVectorIndex
lazy from time_utils import local_wall_time

TARGET_ACTIVE_COUNT = 400
EXPECTED_PRUNED_COUNT = 107
EXPECTED_ARCHIVED_COUNT = 107
EXPECTED_ARCHIVED_AFTER_RESTORE = 106
RANK_RESULT_COUNT = 24
# Coarse anti-regression gate, not a performance benchmark (relaxed 500 ->
# 2000 on 2026-08-27): warmed ranking over 1000 rows normally takes a few
# milliseconds, so this only catches order-of-magnitude regressions without
# exploding on slow or heavily loaded CI runners.
MAX_RANK_ELAPSED_MS = 2000


def _insert_old_low_importance_memories(
    db: StudioDB,
    count: int,
) -> None:
    old = (local_wall_time() - timedelta(days=180)).isoformat(timespec="seconds")
    rows = []
    for index in range(count):
        unique = hashlib.sha256(f"memory-{index}".encode()).hexdigest()
        rows.append(
            (
                "其他",
                f"舊對話 {index}",
                unique,
                "conversation",
                1,
                old,
                old,
            )
        )
    with db.conn:
        db.conn.executemany(
            "INSERT INTO memories(category,title,content,source,importance,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            rows,
        )


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        db = StudioDB(Path(temp_dir) / "semantic-memory.db")
        try:
            travel_id = db.add_memory(
                "主上計畫九月帶兩個女兒去大阪環球影城。",
                "目標",
                "manual",
                5,
                "大阪親子旅行",
            )
            db.add_memory(
                "墨寒專案使用 Python 3.14 建置 Windows 安裝程式。",
                "工作流程",
                "manual",
                5,
                "Python 版本",
            )
            context = db.memory_context(limit=1, query="大阪旅行要帶誰去？")
            assert "兩個女兒" in context
            assert db.memory(travel_id)["last_used_at"] is not None
        finally:
            db.close()

    with TemporaryDirectory() as temp_dir:
        db = StudioDB(Path(temp_dir) / "pruning.db")
        try:
            protected_manual = db.add_memory(
                "這是使用者親自保存、永遠不得自動刪除的重要記憶。",
                "人物",
                "manual",
                5,
            )
            protected_conversation = db.add_memory(
                "這是高重要度對話記憶，也不得自動刪除。",
                "人物",
                "conversation",
                5,
            )
            _insert_old_low_importance_memories(db, 505)
            result = db.optimize_memories(max_active=500, target_active=400)
            assert result["active"] == TARGET_ACTIVE_COUNT
            assert result["pruned"] == EXPECTED_PRUNED_COUNT
            assert db.memory(protected_manual) is not None
            assert db.memory(protected_conversation) is not None
            archived = db.list_archived_memories(200)
            assert len(archived) == EXPECTED_ARCHIVED_COUNT
            restored_id = db.restore_archived_memory(int(archived[0]["id"]))
            assert restored_id > 0
            assert db.memory(restored_id) is not None
            assert len(db.list_archived_memories(200)) == EXPECTED_ARCHIVED_AFTER_RESTORE
        finally:
            db.close()

    # Retrieval stays comfortably within an interactive millisecond-scale
    # budget after the lazy index has been warmed.
    rows = [
        {
            "id": index,
            "category": "工作流程",
            "title": f"專案項目 {index}",
            "content": f"墨寒記憶檢索測試資料 {index} token-{index * 7919}",
            "importance": (index % 5) + 1,
            "updated_at": local_wall_time().isoformat(timespec="seconds"),
        }
        for index in range(1, 1001)
    ]
    index = MemoryVectorIndex()
    index.rank("墨寒測試", rows, 24)
    started = time.perf_counter()
    ranked = index.rank("記憶檢索專案 777", rows, 24)
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert len(ranked) == RANK_RESULT_COUNT
    assert elapsed_ms < MAX_RANK_ELAPSED_MS, elapsed_ms

    print(f"MEMORY_VECTOR_AND_PRUNING_OK elapsed_ms={elapsed_ms:.2f}")


if __name__ == "__main__":
    run()
