import os
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app import (
    MEMORY_CATEGORIES,
    ArchivedMemoryDialog,
    MemoryEditorDialog,
    classify_memory_text,
)
from db import StudioDB


def run() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "memory.db"
        db = StudioDB(path)
        try:
            person_id = db.add_memory(
                "林小姐是主上的出版窗口。",
                "人物",
                "manual",
                4,
                "出版窗口",
            )
            preference_id = db.add_memory(
                "主上偏好使用台灣繁體中文。",
                "偏好",
                "conversation",
                5,
                "語言偏好",
            )
            assert [row["id"] for row in db.list_memories(category="人物")] == [
                person_id
            ]
            assert [
                row["id"] for row in db.list_memories(category="偏好")
            ] == [preference_id]
            assert db.update_memory(
                person_id,
                "主要出版窗口",
                "林小姐是主上的主要出版窗口，週一聯絡。",
                "工作流程",
                5,
            )
            updated = db.memory(person_id)
            assert updated["title"] == "主要出版視窗"
            assert updated["category"] == "工作流程"
            assert updated["content"] == (
                "林小姐是主上的主要出版視窗，週一聯絡。"
            )
            assert updated["importance"] == 5
            db.add_memory(
                "林小姐是主上的主要出版窗口，週一聯絡。",
                "工作流程",
                "conversation",
                4,
            )
            assert db.memory(person_id)["title"] == "主要出版視窗"
            assert db.delete_memories([preference_id]) == 1
            assert db.memory(preference_id) is None
            assert db.memory(person_id) is not None

            duplicate_id = db.add_memory(
                "不可重複的內容", "其他", "manual", 3, "第一則"
            )
            second_id = db.add_memory(
                "另一則內容", "其他", "manual", 3, "第二則"
            )
            before = dict(db.memory(second_id))
            assert not db.update_memory(
                second_id,
                "衝突測試",
                "不可重複的內容",
                "目標",
                5,
            )
            after = dict(db.memory(second_id))
            assert after == before
            assert db.memory(duplicate_id) is not None

            app = QApplication.instance() or QApplication([])
            editor = MemoryEditorDialog(db.memory(person_id))
            assert editor.category_input.currentText() == "工作流程"
            assert editor.importance_input.value() == 5
            assert editor.values() == (
                "主要出版視窗",
                "林小姐是主上的主要出版視窗，週一聯絡。",
                "工作流程",
                5,
            )
            editor.close()
            app.processEvents()
            assert db._archive_memory_ids([person_id], "test-archive") == 1
            archive_dialog = ArchivedMemoryDialog(db)
            assert archive_dialog.archive_list.count() == 1
            archive_dialog.archive_list.item(0).setCheckState(Qt.Checked)
            archive_dialog.restore_checked()
            assert archive_dialog.changed
            assert archive_dialog.archive_list.count() == 0
            assert db.memory_context(query="出版窗口")
            archive_dialog.close()
            app.processEvents()
        finally:
            db.close()

        legacy_path = Path(tmp) / "legacy-memory.db"
        legacy = sqlite3.connect(legacy_path)
        legacy.executescript(
            """
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL UNIQUE,
                importance INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            INSERT INTO memories(category,content,importance,created_at)
            VALUES(
                'preference',
                '舊資料不能遺失',
                5,
                '2026-07-30T09:00:00'
            );
            """
        )
        legacy.commit()
        legacy.close()
        migrated = StudioDB(legacy_path)
        try:
            row = migrated.list_memories()[0]
            assert row["category"] == "偏好"
            assert row["title"] == "舊資料不能遺失"
            assert row["content"] == "舊資料不能遺失"
            assert row["source"] == "manual"
            assert row["updated_at"] == "2026-07-30T09:00:00"
        finally:
            migrated.close()

    assert set(MEMORY_CATEGORIES) == {
        "人物",
        "偏好",
        "目標",
        "工作流程",
        "重要日期",
        "其他",
    }
    assert classify_memory_text("請記住林小姐是我的出版窗口") == "人物"
    assert classify_memory_text("我的目標是完成新書") == "目標"
    assert classify_memory_text("我的生日是十月十日") == "重要日期"
    assert classify_memory_text("我習慣先畫漫畫再處理行政") == "工作流程"
    assert classify_memory_text("我喜歡使用深色介面") == "偏好"
    print("MEMORY_MANAGEMENT_OK")


if __name__ == "__main__":
    run()
