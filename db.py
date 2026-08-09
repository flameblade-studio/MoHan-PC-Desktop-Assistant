from __future__ import annotations

lazy import json
lazy import re
lazy import sqlite3
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from datetime import datetime, timedelta
lazy from pathlib import Path

lazy from language_support import (
    LEGACY_AUTHOR_ORGANIZATION,
    LEGACY_TRANSCRIPTION_PROMPT,
    localized_transcription_prompt,
)
lazy from memory_index import (
    MemoryVectorIndex,
    cosine_similarity,
    hashed_text_vector,
)
lazy from text_normalizer import to_taiwan_traditional
lazy from time_utils import local_wall_time

DEFAULT_REMINDERS = frozendict({
    "work": ("開始工作", "09:30", 1),
    "lunch": ("吃飯", "12:30", 1),
    "dinner": ("晚餐", "18:30", 1),
    "offwork": ("下班", "21:00", 1),
})

IDEA_COLUMN_DEFINITIONS = frozendict({
    "text": "TEXT NOT NULL DEFAULT ''",
    "title": "TEXT NOT NULL DEFAULT ''",
    "content": "TEXT NOT NULL DEFAULT ''",
    "updated_at": "TEXT",
})
MEMORY_COLUMN_DEFINITIONS = frozendict({
    "category": "TEXT NOT NULL DEFAULT '其他'",
    "title": "TEXT NOT NULL DEFAULT ''",
    "source": "TEXT NOT NULL DEFAULT 'manual'",
    "importance": "INTEGER NOT NULL DEFAULT 3",
    "updated_at": "TEXT",
    "scope": "TEXT NOT NULL DEFAULT 'personal'",
    "expires_at": "TEXT",
    "last_used_at": "TEXT",
})
PLATFORM_COLUMN_DEFINITIONS = frozendict({
    "item_name": "TEXT NOT NULL DEFAULT ''",
    "next_action": "TEXT NOT NULL DEFAULT ''",
    "notes": "TEXT NOT NULL DEFAULT ''",
    "url": "TEXT NOT NULL DEFAULT ''",
    "sort_order": "INTEGER NOT NULL DEFAULT 0",
})
LEGACY_MEMORY_CATEGORIES = frozendict({
    "person": "人物",
    "people": "人物",
    "preference": "偏好",
    "preferences": "偏好",
    "goal": "目標",
    "goals": "目標",
    "workflow": "工作流程",
    "date": "重要日期",
    "important_date": "重要日期",
    "other": "其他",
})
MODEL_DEFAULT_MIGRATIONS = (
    (
        "luna_default_v12_migrated",
        frozenset({None, "gpt-5.6-terra"}),
        "gpt-5.6-luna",
    ),
    (
        "mini_default_v118_migrated",
        frozenset({None, "gpt-5.6-luna"}),
        "gpt-5.4-mini",
    ),
    (
        "mini_default_v1213_restored",
        frozenset({None, "gpt-5.6-luna"}),
        "gpt-5.4-mini",
    ),
    (
        "luna_default_v210rc1_migrated",
        frozenset({None, "gpt-5.4-mini"}),
        "gpt-5.6-luna",
    ),
)
LEGACY_PROFILE_DEFAULTS = frozendict({
    "assistant_name": "墨寒",
    "user_title": "主上",
    "organization_name": "炎劍文化工作室",
    "window_title": "",
    "work_type": "創作／內容工作",
    "ui_language": "zh-TW",
    "wake_word": "墨寒",
    "onboarding_complete": True,
    "transcription_language": "zh",
    "transcription_prompt": LEGACY_TRANSCRIPTION_PROMPT,
})
TRANSCRIPTION_PROFILE_KEYS = (
    "ui_language",
    "assistant_name",
    "user_title",
    "organization_name",
    "wake_word",
)


@dataclass(frozen=True, slots=True)
class PlatformProgressUpdate:
    platform: str
    status: str
    missing: str
    item_name: str = ""
    next_action: str = ""
    notes: str = ""
    url: str = ""

    def database_row(self, updated_at: str) -> tuple[str, ...]:
        return (
            self.platform,
            to_taiwan_traditional(self.status.strip()) or "尚未開始",
            to_taiwan_traditional(self.missing.strip()),
            to_taiwan_traditional(self.item_name.strip()),
            to_taiwan_traditional(self.next_action.strip()),
            to_taiwan_traditional(self.notes.strip()),
            self.url.strip(),
            updated_at,
        )

class StudioDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.existing_install = path.exists() and path.stat().st_size > 0
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._memory_index = MemoryVectorIndex()
        try:
            self._migrate()
        except Exception:
            # A failed migration must never leave the profile database locked.
            self.conn.close()
            raise

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '其他',
                status TEXT NOT NULL DEFAULT '待辦',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reminders (
                kind TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                time_of_day TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_fired_date TEXT
            );
            CREATE TABLE IF NOT EXISTS platform_progress (
                platform TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT '尚未開始',
                missing TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT '偏好',
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL DEFAULT 'manual',
                importance INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER NOT NULL,
                snapshot TEXT NOT NULL,
                reason TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                restored_at TEXT
            );
            CREATE TABLE IF NOT EXISTS action_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                definition TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS connector_profiles (
                connector_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                configuration TEXT NOT NULL DEFAULT '{}',
                last_health TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS allowed_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                display_name TEXT NOT NULL,
                target_value TEXT NOT NULL,
                access_mode TEXT NOT NULL DEFAULT 'read',
                enabled INTEGER NOT NULL DEFAULT 1,
                UNIQUE(target_type,target_value)
            );
            CREATE TABLE IF NOT EXISTS paired_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                permissions TEXT NOT NULL DEFAULT '[]',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_seen_at TEXT
            );
            """
        )
        self._migrate_ideas()
        self._migrate_memories()
        self._migrate_platform_progress()
        self._migrate_chat_history()
        self._migrate_model_defaults()
        self._migrate_existing_profile()
        self.conn.commit()

    def _table_columns(self, table: str) -> set[str]:
        return {
            str(row["name"])
            for row in self.conn.execute(f"PRAGMA table_info({table})")
        }

    def _ensure_columns(
        self,
        table: str,
        definitions: Mapping[str, str],
        existing: set[str],
    ) -> None:
        for column, definition in definitions.items():
            if column not in existing:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )

    def _migrate_ideas(self) -> None:
        columns = self._table_columns("ideas")
        legacy_source = (
            "text"
            if "text" in columns
            else "body"
            if "body" in columns
            else None
        )
        self._ensure_columns("ideas", IDEA_COLUMN_DEFINITIONS, columns)
        if legacy_source is not None:
            self.conn.execute(
                f"UPDATE ideas SET text={legacy_source} "
                "WHERE COALESCE(text,'')=''"
            )
        self.conn.execute(
            "UPDATE ideas SET title=text WHERE COALESCE(title,'')=''"
        )
        self.conn.execute(
            "UPDATE ideas SET updated_at=created_at "
            "WHERE COALESCE(updated_at,'')=''"
        )

    def _migrate_memories(self) -> None:
        columns = self._table_columns("memories")
        self._ensure_columns("memories", MEMORY_COLUMN_DEFINITIONS, columns)
        self.conn.execute(
            "UPDATE memories SET updated_at=created_at "
            "WHERE COALESCE(updated_at,'')=''"
        )
        rows = self.conn.execute(
            "SELECT id,content FROM memories WHERE COALESCE(title,'')=''"
        ).fetchall()
        for row in rows:
            title = " ".join(str(row["content"]).split())
            if len(title) > 36:
                title = title[:36].rstrip() + "…"
            self.conn.execute(
                "UPDATE memories SET title=? WHERE id=?",
                (title or "未命名記憶", int(row["id"])),
            )
        for old_category, new_category in LEGACY_MEMORY_CATEGORIES.items():
            self.conn.execute(
                "UPDATE memories SET category=? "
                "WHERE LOWER(TRIM(category))=?",
                (new_category, old_category),
            )

    def _migrate_platform_progress(self) -> None:
        columns = self._table_columns("platform_progress")
        self._ensure_columns(
            "platform_progress",
            PLATFORM_COLUMN_DEFINITIONS,
            columns,
        )
        for kind, (label, at, enabled) in DEFAULT_REMINDERS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO reminders("
                "kind,label,time_of_day,enabled"
                ") VALUES(?,?,?,?)",
                (kind, label, at, enabled),
            )
        marker = self.conn.execute(
            "SELECT value FROM settings "
            "WHERE key='custom_platforms_v1207_seeded'"
        ).fetchone()
        if marker is None:
            # Existing profiles retain their rows; new profiles intentionally
            # start empty instead of assuming a publishing workflow.
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('custom_platforms_v1207_seeded','true')"
            )

    def _migrate_chat_history(self) -> None:
        self.conn.execute(
            "UPDATE chat_log SET content=REPLACE(content,'劍主','主上') "
            "WHERE content LIKE '%劍主%'"
        )
        marker = self.conn.execute(
            "SELECT value FROM settings "
            "WHERE key='traditional_chat_v1215_migrated'"
        ).fetchone()
        if marker is not None:
            return
        rows = self.conn.execute("SELECT id,content FROM chat_log").fetchall()
        for row in rows:
            normalized = to_taiwan_traditional(row["content"])
            if normalized != row["content"]:
                self.conn.execute(
                    "UPDATE chat_log SET content=? WHERE id=?",
                    (normalized, row["id"]),
                )
        self.conn.execute(
            "INSERT INTO settings(key,value) "
            "VALUES('traditional_chat_v1215_migrated','true')"
        )

    def _decoded_setting(self, key: str) -> object | None:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return None

    def _migrate_model_default(
        self,
        marker: str,
        prior_values: frozenset[str | None],
        target: str,
    ) -> None:
        marker_row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (marker,),
        ).fetchone()
        if marker_row is not None:
            return
        if self._decoded_setting("ai_model") in prior_values:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES('ai_model',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(target),),
            )
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?)",
            (marker, "true"),
        )

    def _migrate_model_defaults(self) -> None:
        for marker, prior_values, target in MODEL_DEFAULT_MIGRATIONS:
            self._migrate_model_default(marker, prior_values, target)

    def _migrate_existing_profile(self) -> None:
        if not self.existing_install:
            return
        # Existing users retain identity and workflow choices; only fields
        # unavailable in older releases are supplied.
        for key, value in LEGACY_PROFILE_DEFAULTS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )
        current_prompt = self._decoded_setting("transcription_prompt")
        if current_prompt != LEGACY_TRANSCRIPTION_PROMPT:
            return
        profile = {
            key: self._decoded_setting(key) or ""
            for key in TRANSCRIPTION_PROFILE_KEYS
        }
        organization_name = str(profile["organization_name"])
        migrated_prompt = localized_transcription_prompt(
            str(profile["ui_language"] or "zh-TW"),
            assistant_name=str(profile["assistant_name"]),
            user_title=str(profile["user_title"]),
            organization_name=(
                ""
                if organization_name.strip() == LEGACY_AUTHOR_ORGANIZATION
                else organization_name
            ),
            wake_word=str(profile["wake_word"]),
        )
        self.conn.execute(
            "UPDATE settings SET value=? WHERE key='transcription_prompt'",
            (json.dumps(migrated_prompt, ensure_ascii=False),),
        )

    def close(self) -> None:
        self.conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: object) -> None:
        encoded = json.dumps(value, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, encoded),
        )
        self.conn.commit()

    def setting(self, key: str, default: object = None) -> object:
        raw = self.get_setting(key)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    def add_todo(self, title: str, category: str = "其他") -> int:
        normalized_title = to_taiwan_traditional(title.strip())
        cur = self.conn.execute(
            "INSERT INTO todos(title,category,created_at) VALUES(?,?,?)",
            (
                normalized_title,
                category,
                local_wall_time().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_todos(self, include_done: bool = False) -> list[sqlite3.Row]:
        where = "" if include_done else "WHERE status != '完成'"
        return list(
            self.conn.execute(
                f"SELECT * FROM todos {where} ORDER BY status='完成', id DESC"
            )
        )

    def set_todo_done(self, todo_id: int, done: bool) -> None:
        self.conn.execute(
            "UPDATE todos SET status=?,completed_at=? WHERE id=?",
            (
                "完成" if done else "待辦",
                local_wall_time().isoformat(timespec="seconds") if done else None,
                todo_id,
            ),
        )
        self.conn.commit()

    def delete_todo(self, todo_id: int) -> None:
        self.conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        self.conn.commit()

    def add_idea(self, text: str, content: str = "") -> int:
        normalized_text = to_taiwan_traditional(text.strip())
        normalized_content = to_taiwan_traditional(content.strip())
        now = local_wall_time().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO ideas(text,title,content,created_at,updated_at) "
            "VALUES(?,?,?,?,?)",
            (
                normalized_text,
                normalized_text,
                normalized_content,
                now,
                now,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_ideas(self, limit: int = 30) -> list[sqlite3.Row]:
        return list(
            self.conn.execute("SELECT * FROM ideas ORDER BY id DESC LIMIT ?", (limit,))
        )

    def idea(self, idea_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM ideas WHERE id=?", (idea_id,)
        ).fetchone()

    def update_idea(self, idea_id: int, title: str, content: str) -> None:
        normalized_title = to_taiwan_traditional(title.strip())
        normalized_content = to_taiwan_traditional(content.strip())
        self.conn.execute(
            "UPDATE ideas SET text=?,title=?,content=?,updated_at=? WHERE id=?",
            (
                normalized_title,
                normalized_title,
                normalized_content,
                local_wall_time().isoformat(timespec="seconds"),
                idea_id,
            ),
        )
        self.conn.commit()

    def delete_ideas(self, idea_ids: list[int]) -> int:
        ids = sorted({int(idea_id) for idea_id in idea_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"DELETE FROM ideas WHERE id IN ({placeholders})",
            ids,
        )
        self.conn.commit()
        return max(0, int(cursor.rowcount))

    def active_session(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM work_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def start_work(self) -> bool:
        if self.active_session():
            return False
        self.conn.execute(
            "INSERT INTO work_sessions(started_at) VALUES(?)",
            (local_wall_time().isoformat(timespec="seconds"),),
        )
        self.conn.commit()
        return True

    def stop_work(self) -> bool:
        row = self.active_session()
        if not row:
            return False
        self.conn.execute(
            "UPDATE work_sessions SET ended_at=? WHERE id=?",
            (local_wall_time().isoformat(timespec="seconds"), row["id"]),
        )
        self.conn.commit()
        return True

    def today_work_seconds(self) -> int:
        day_start = datetime.combine(local_wall_time().date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)
        rows = self.conn.execute(
            "SELECT * FROM work_sessions "
            "WHERE started_at < ? AND (ended_at IS NULL OR ended_at >= ?)",
            (
                day_end.isoformat(timespec="seconds"),
                day_start.isoformat(timespec="seconds"),
            ),
        )
        total = 0
        now = local_wall_time()
        for row in rows:
            start = max(
                datetime.fromisoformat(row["started_at"]),
                day_start,
            )
            end = min(
                datetime.fromisoformat(row["ended_at"])
                if row["ended_at"]
                else now,
                day_end,
            )
            total += max(0, int((end - start).total_seconds()))
        return total

    def active_session_seconds(self) -> int:
        row = self.active_session()
        if not row:
            return 0
        return max(
            0,
            int((local_wall_time() - datetime.fromisoformat(row["started_at"])).total_seconds()),
        )

    def reminders(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM reminders ORDER BY time_of_day"))

    def update_reminder(self, kind: str, at: str, enabled: bool) -> None:
        self.conn.execute(
            "UPDATE reminders SET time_of_day=?,enabled=? WHERE kind=?",
            (at, int(enabled), kind),
        )
        self.conn.commit()

    def due_reminders(self, now: datetime) -> list[sqlite3.Row]:
        today = now.date().isoformat()
        current = now.strftime("%H:%M")
        return list(
            self.conn.execute(
                "SELECT * FROM reminders WHERE enabled=1 AND time_of_day=? "
                "AND COALESCE(last_fired_date,'') != ?",
                (current, today),
            )
        )

    def mark_reminder_fired(self, kind: str, fired_date: str) -> None:
        self.conn.execute(
            "UPDATE reminders SET last_fired_date=? WHERE kind=?", (fired_date, kind)
        )
        self.conn.commit()

    def platform_rows(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM platform_progress "
                "ORDER BY sort_order, platform COLLATE NOCASE"
            )
        )

    def add_platform(self, platform: str, url: str = "") -> bool:
        name = to_taiwan_traditional(platform.strip())
        if not name:
            return False
        row = self.conn.execute(
            "SELECT 1 FROM platform_progress "
            "WHERE platform=? COLLATE NOCASE",
            (name,),
        ).fetchone()
        if row is not None:
            return False
        next_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order),-1)+1 FROM platform_progress"
        ).fetchone()[0]
        with self.conn:
            self.conn.execute(
                "INSERT INTO platform_progress("
                "platform,url,updated_at,sort_order"
                ") VALUES(?,?,?,?)",
                (
                    name,
                    url.strip(),
                    local_wall_time().isoformat(timespec="seconds"),
                    int(next_order),
                ),
            )
        return True

    def delete_platform(self, platform: str) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM platform_progress WHERE platform=?",
                (platform,),
            )
        return cursor.rowcount > 0

    def update_platform(
        self,
        entry: PlatformProgressUpdate,
    ) -> None:
        self.update_platforms([entry])

    def update_platforms(
        self,
        entries: list[PlatformProgressUpdate],
    ) -> None:
        now = local_wall_time().isoformat(timespec="seconds")
        normalized = [entry.database_row(now) for entry in entries]
        with self.conn:
            self.conn.executemany(
                """
                INSERT INTO platform_progress(
                    platform,status,missing,item_name,next_action,notes,url,updated_at
                ) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(platform) DO UPDATE SET
                    status=excluded.status,
                    missing=excluded.missing,
                    item_name=excluded.item_name,
                    next_action=excluded.next_action,
                    notes=excluded.notes,
                    url=excluded.url,
                    updated_at=excluded.updated_at
                """,
                normalized,
            )

    def log_chat(self, role: str, content: str) -> None:
        self.conn.execute(
            "INSERT INTO chat_log(role,content,created_at) VALUES(?,?,?)",
            (
                role,
                to_taiwan_traditional(content),
                local_wall_time().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()

    def recent_chat(self, limit: int = 12) -> list[sqlite3.Row]:
        rows = list(
            self.conn.execute("SELECT * FROM chat_log ORDER BY id DESC LIMIT ?", (limit,))
        )
        rows.reverse()
        return rows

    def chat_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS total FROM chat_log").fetchone()
        return int(row["total"]) if row else 0

    def chat_history(self, limit: int = 500) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM chat_log ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        )

    def delete_chat_entries(self, chat_ids: list[int]) -> int:
        ids = sorted({int(chat_id) for chat_id in chat_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"DELETE FROM chat_log WHERE id IN ({placeholders})",
            ids,
        )
        self.conn.commit()
        return max(0, int(cursor.rowcount))

    def add_memory(
        self,
        content: str,
        category: str = "偏好",
        source: str = "manual",
        importance: int = 3,
        title: str = "",
    ) -> int:
        text = to_taiwan_traditional(content.strip())
        if not text:
            return 0
        title_was_supplied = bool(title.strip())
        normalized_title = to_taiwan_traditional(title.strip())
        if not normalized_title:
            normalized_title = " ".join(text.split())
            if len(normalized_title) > 36:
                normalized_title = normalized_title[:36].rstrip() + "…"
        now = local_wall_time().isoformat(timespec="seconds")
        conflict_title = (
            "title=excluded.title,"
            if title_was_supplied
            else "title=memories.title,"
        )
        statement = (
            "INSERT INTO memories(category,title,content,source,importance,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(content) DO UPDATE SET "
            f"category=excluded.category,{conflict_title}"
            "source=excluded.source,"
            "importance=MAX(memories.importance,excluded.importance),"
            "updated_at=excluded.updated_at"
        )
        self.conn.execute(
            statement,
            (
                to_taiwan_traditional(category.strip()) or "其他",
                normalized_title or "未命名記憶",
                text,
                source,
                max(1, min(5, importance)),
                now,
                now,
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM memories WHERE content=?", (text,)
        ).fetchone()
        memory_id = int(row["id"])
        self._memory_index.clear()
        total = self.conn.execute(
            "SELECT COUNT(*) AS total FROM memories"
        ).fetchone()["total"]
        if int(total) > 500:
            self.optimize_memories()
        return memory_id

    def list_memories(
        self,
        limit: int = 100,
        category: str | None = None,
    ) -> list[sqlite3.Row]:
        now = local_wall_time().isoformat(timespec="seconds")
        where = "WHERE (expires_at IS NULL OR expires_at > ?)"
        parameters: list[object] = [now]
        if category:
            where += " AND category=?"
            parameters.append(category)
        parameters.append(limit)
        return list(
            self.conn.execute(
                f"SELECT * FROM memories {where} "
                "ORDER BY importance DESC,updated_at DESC LIMIT ?",
                parameters,
            )
        )

    def memory(self, memory_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        ).fetchone()

    def update_memory(
        self,
        memory_id: int,
        title: str,
        content: str,
        category: str,
        importance: int,
    ) -> bool:
        normalized_title = to_taiwan_traditional(title.strip())
        normalized_content = to_taiwan_traditional(content.strip())
        normalized_category = (
            to_taiwan_traditional(category.strip()) or "其他"
        )
        if not normalized_title or not normalized_content:
            return False
        try:
            cursor = self.conn.execute(
                "UPDATE memories SET title=?,content=?,category=?,"
                "importance=?,updated_at=? WHERE id=?",
                (
                    normalized_title,
                    normalized_content,
                    normalized_category,
                    max(1, min(5, int(importance))),
                    local_wall_time().isoformat(timespec="seconds"),
                    memory_id,
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False
        self._memory_index.clear()
        return cursor.rowcount > 0

    def delete_memory(self, memory_id: int) -> None:
        self.conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self.conn.commit()
        self._memory_index.clear()

    def delete_memories(self, memory_ids: list[int]) -> int:
        ids = sorted({int(memory_id) for memory_id in memory_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})",
            ids,
        )
        self.conn.commit()
        self._memory_index.clear()
        return max(0, int(cursor.rowcount))

    def clear_memories(self) -> None:
        self.conn.execute("DELETE FROM memories")
        self.conn.commit()
        self._memory_index.clear()

    def memory_context(self, limit: int = 24, query: str = "") -> str:
        pool = self.list_memories(5000)
        if query.strip():
            row_by_id = {int(row["id"]): row for row in pool}
            rows = [
                row_by_id[item.memory_id]
                for item in self._memory_index.rank(
                    query,
                    [dict(row) for row in pool],
                    limit,
                )
            ]
        else:
            rows = pool[:limit]
        if rows:
            now = local_wall_time().isoformat(timespec="seconds")
            with self.conn:
                self.conn.executemany(
                    "UPDATE memories SET last_used_at=? WHERE id=?",
                    [(now, int(row["id"])) for row in rows],
                )
        return "\n".join(f"- [{row['category']}] {row['content']}" for row in rows)

    def _archive_memory_ids(self, memory_ids: list[int], reason: str) -> int:
        ids = sorted({int(memory_id) for memory_id in memory_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        archived_at = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            self.conn.executemany(
                "INSERT INTO memory_archive(original_id,snapshot,reason,archived_at) "
                "VALUES(?,?,?,?)",
                [
                    (
                        int(row["id"]),
                        json.dumps(dict(row), ensure_ascii=False),
                        reason,
                        archived_at,
                    )
                    for row in rows
                ],
            )
            self.conn.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})",
                ids,
            )
        self._memory_index.clear()
        return len(rows)

    def list_archived_memories(self, limit: int = 200) -> list[dict]:
        rows = list(
            self.conn.execute(
                "SELECT * FROM memory_archive WHERE restored_at IS NULL "
                "ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            )
        )
        archived: list[dict] = []
        for row in rows:
            try:
                snapshot = json.loads(str(row["snapshot"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                snapshot = {}
            archived.append(
                {
                    "id": int(row["id"]),
                    "original_id": int(row["original_id"]),
                    "reason": str(row["reason"]),
                    "archived_at": str(row["archived_at"]),
                    "category": str(snapshot.get("category") or "其他"),
                    "title": str(snapshot.get("title") or "未命名記憶"),
                    "content": str(snapshot.get("content") or ""),
                    "source": str(snapshot.get("source") or "conversation"),
                    "importance": int(snapshot.get("importance") or 1),
                }
            )
        return archived

    def restore_archived_memory(self, archive_id: int) -> int:
        row = self.conn.execute(
            "SELECT * FROM memory_archive WHERE id=? AND restored_at IS NULL",
            (int(archive_id),),
        ).fetchone()
        if row is None:
            return 0
        snapshot = json.loads(str(row["snapshot"]))
        restored_at = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                "INSERT INTO memories(category,title,content,source,importance,"
                "created_at,updated_at,scope,expires_at,last_used_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(content) DO UPDATE SET "
                "importance=MAX(memories.importance,excluded.importance),"
                "updated_at=excluded.updated_at",
                (
                    snapshot["category"],
                    snapshot["title"],
                    snapshot["content"],
                    snapshot["source"],
                    snapshot["importance"],
                    snapshot["created_at"],
                    snapshot["updated_at"],
                    snapshot.get("scope", "personal"),
                    snapshot.get("expires_at"),
                    snapshot.get("last_used_at"),
                ),
            )
            self.conn.execute(
                "UPDATE memory_archive SET restored_at=? WHERE id=?",
                (restored_at, int(archive_id)),
            )
        restored = self.conn.execute(
            "SELECT id FROM memories WHERE content=?",
            (snapshot["content"],),
        ).fetchone()
        self._memory_index.clear()
        return int(restored["id"]) if restored else 0

    @staticmethod
    def _memory_age_days(row: sqlite3.Row, now: datetime) -> float:
        raw = str(row["last_used_at"] or row["updated_at"] or row["created_at"])
        try:
            return max(0.0, (now - datetime.fromisoformat(raw)).total_seconds() / 86400)
        except ValueError:
            return 3650.0

    def _consolidate_auto_duplicates(
        self,
        rows: list[sqlite3.Row],
        threshold: float = 0.90,
    ) -> int:
        candidates = [
            row
            for row in rows
            if str(row["source"]) == "conversation"
            and int(row["importance"]) <= 2
        ]
        vectors = {
            int(row["id"]): hashed_text_vector(str(row["content"]))
            for row in candidates
        }
        archived = 0
        consumed: set[int] = set()
        for index, keeper in enumerate(candidates):
            keeper_id = int(keeper["id"])
            if keeper_id in consumed:
                continue
            duplicate_ids: list[int] = []
            contents = [str(keeper["content"])]
            for other in candidates[index + 1 :]:
                other_id = int(other["id"])
                if other_id in consumed or other["category"] != keeper["category"]:
                    continue
                if cosine_similarity(vectors[keeper_id], vectors[other_id]) >= threshold:
                    duplicate_ids.append(other_id)
                    contents.append(str(other["content"]))
                    consumed.add(other_id)
            if not duplicate_ids:
                continue
            summary = self._merge_memory_contents(contents)
            archived += self._archive_memory_ids(
                duplicate_ids,
                "semantic-deduplication",
            )
            with self.conn:
                self.conn.execute(
                    "UPDATE memories SET content=?,updated_at=? WHERE id=?",
                    (summary, local_wall_time().isoformat(timespec="seconds"), keeper_id),
                )
        return archived

    @staticmethod
    def _merge_memory_contents(contents: list[str], limit: int = 500) -> str:
        """Merge near-duplicate facts without inventing or discarding details."""
        fragments: list[str] = []
        seen: set[str] = set()
        for content in contents:
            for fragment in re.split(r"(?<=[。！？.!?])\s*|[；;]\s*", content):
                cleaned = " ".join(fragment.split()).strip()
                key = re.sub(r"\W+", "", cleaned).casefold()
                if not cleaned or not key or key in seen:
                    continue
                seen.add(key)
                fragments.append(cleaned)
        merged = " ".join(fragments) or max(contents, key=len, default="")
        if len(merged) > limit:
            merged = merged[: max(1, limit - 1)].rstrip() + "…"
        return merged

    def optimize_memories(
        self,
        max_active: int = 500,
        target_active: int = 400,
        now: datetime | None = None,
    ) -> dict[str, int]:
        if target_active <= 0 or max_active < target_active:
            raise ValueError("memory limits are invalid")
        reference = now or local_wall_time()
        rows = self.list_memories(10000)
        deduplicated = self._consolidate_auto_duplicates(rows)
        rows = self.list_memories(10000)
        excess = max(0, len(rows) - target_active) if len(rows) > max_active else 0
        eligible = sorted(
            (
                row for row in rows
                if str(row["source"]) == "conversation"
                and int(row["importance"]) <= 2
                and self._memory_age_days(row, reference) >= 90
            ),
            key=lambda row: (
                int(row["importance"]),
                str(row["last_used_at"] or row["updated_at"] or row["created_at"]),
                int(row["id"]),
            ),
        )
        pruned = self._archive_memory_ids(
            [int(row["id"]) for row in eligible[:excess]],
            "capacity-pruning",
        )
        return {
            "deduplicated": deduplicated,
            "pruned": pruned,
            "active": len(self.list_memories(10000)),
            "archived": len(self.list_archived_memories(10000)),
        }

    def update_memory_policy(
        self,
        memory_id: int,
        *,
        scope: str = "personal",
        expires_at: str | None = None,
    ) -> None:
        if scope not in {"session", "personal", "work", "shared"}:
            raise ValueError("不支援的記憶範圍")
        if expires_at:
            datetime.fromisoformat(expires_at)
        with self.conn:
            self.conn.execute(
                "UPDATE memories SET scope=?,expires_at=?,updated_at=? "
                "WHERE id=?",
                (
                    scope,
                    expires_at,
                    local_wall_time().isoformat(timespec="seconds"),
                    int(memory_id),
                ),
            )

    def purge_expired_memories(self) -> int:
        now = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM memories "
                "WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
        return max(0, int(cursor.rowcount))

    def export_memories(self) -> list[dict]:
        return [
            {
                key: row[key]
                for key in (
                    "id",
                    "category",
                    "content",
                    "source",
                    "importance",
                    "scope",
                    "expires_at",
                    "created_at",
                    "updated_at",
                )
            }
            for row in self.list_memories(10000)
        ]

    def audit_event(self, event_type: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT INTO action_audit(event_type,payload,created_at) "
            "VALUES(?,?,?)",
            (
                event_type,
                json.dumps(payload, ensure_ascii=False, default=str),
                local_wall_time().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()

    def audit_rows(self, limit: int = 200) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM action_audit ORDER BY id DESC LIMIT ?",
                (max(1, min(5000, int(limit))),),
            )
        )

    def clear_audit_before(self, before_iso: str) -> int:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM action_audit WHERE created_at < ?",
                (before_iso,),
            )
        return max(0, int(cursor.rowcount))

    def save_workflow(
        self,
        name: str,
        definition: str,
        *,
        enabled: bool = True,
        workflow_id: int | None = None,
    ) -> int:
        normalized = to_taiwan_traditional(name.strip())
        if not normalized:
            raise ValueError("工作流程名稱不可留空")
        json.loads(definition)
        now = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            if workflow_id is None:
                cursor = self.conn.execute(
                    "INSERT INTO workflows("
                    "name,definition,enabled,created_at,updated_at"
                    ") VALUES(?,?,?,?,?)",
                    (normalized, definition, int(enabled), now, now),
                )
                return int(cursor.lastrowid)
            self.conn.execute(
                "UPDATE workflows SET name=?,definition=?,enabled=?,"
                "updated_at=? WHERE id=?",
                (normalized, definition, int(enabled), now, int(workflow_id)),
            )
        return int(workflow_id)

    def workflows(self, enabled_only: bool = False) -> list[sqlite3.Row]:
        where = "WHERE enabled=1" if enabled_only else ""
        return list(
            self.conn.execute(
                f"SELECT * FROM workflows {where} "
                "ORDER BY enabled DESC,name COLLATE NOCASE"
            )
        )

    def workflow(self, workflow_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM workflows WHERE id=?",
            (int(workflow_id),),
        ).fetchone()

    def delete_workflow(self, workflow_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM workflows WHERE id=?",
                (int(workflow_id),),
            )
        return cursor.rowcount > 0

    def mark_workflow_run(self, workflow_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE workflows SET last_run_at=? WHERE id=?",
                (
                    local_wall_time().isoformat(timespec="seconds"),
                    int(workflow_id),
                ),
            )

    def save_connector(
        self,
        connector_id: str,
        display_name: str,
        enabled: bool,
        configuration: dict,
        last_health: str | None = None,
    ) -> None:
        now = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO connector_profiles(
                    connector_id,display_name,enabled,configuration,
                    last_health,updated_at
                ) VALUES(?,?,?,?,?,?)
                ON CONFLICT(connector_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    enabled=excluded.enabled,
                    configuration=excluded.configuration,
                    last_health=COALESCE(excluded.last_health,last_health),
                    updated_at=excluded.updated_at
                """,
                (
                    connector_id,
                    to_taiwan_traditional(display_name.strip()),
                    int(enabled),
                    json.dumps(configuration, ensure_ascii=False),
                    last_health,
                    now,
                ),
            )

    def connector(self, connector_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM connector_profiles WHERE connector_id=?",
            (connector_id,),
        ).fetchone()

    def connectors(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM connector_profiles "
                "ORDER BY display_name COLLATE NOCASE"
            )
        )

    def add_allowed_target(
        self,
        target_type: str,
        display_name: str,
        target_value: str,
        access_mode: str = "read",
    ) -> int:
        if access_mode not in {"read", "write", "control", "confirm"}:
            raise ValueError("不支援的存取模式")
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO allowed_targets(
                    target_type,display_name,target_value,access_mode
                ) VALUES(?,?,?,?)
                ON CONFLICT(target_type,target_value) DO UPDATE SET
                    display_name=excluded.display_name,
                    access_mode=excluded.access_mode,
                    enabled=1
                """,
                (
                    target_type.strip(),
                    to_taiwan_traditional(display_name.strip()),
                    target_value.strip(),
                    access_mode,
                ),
            )
        row = self.conn.execute(
            "SELECT id FROM allowed_targets "
            "WHERE target_type=? AND target_value=?",
            (target_type.strip(), target_value.strip()),
        ).fetchone()
        return int(row["id"])

    def allowed_targets(
        self,
        target_type: str | None = None,
    ) -> list[sqlite3.Row]:
        if target_type:
            return list(
                self.conn.execute(
                    "SELECT * FROM allowed_targets "
                    "WHERE enabled=1 AND target_type=? ORDER BY display_name",
                    (target_type,),
                )
            )
        return list(
            self.conn.execute(
                "SELECT * FROM allowed_targets WHERE enabled=1 "
                "ORDER BY target_type,display_name"
            )
        )

    def remove_allowed_target(self, target_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM allowed_targets WHERE id=?",
                (int(target_id),),
            )
        return cursor.rowcount > 0

    def add_paired_device(
        self,
        device_name: str,
        token_hash: str,
        permissions: list[str],
    ) -> int:
        now = local_wall_time().isoformat(timespec="seconds")
        cursor = self.conn.execute(
            "INSERT INTO paired_devices("
            "device_name,token_hash,permissions,created_at"
            ") VALUES(?,?,?,?)",
            (
                to_taiwan_traditional(device_name.strip()),
                token_hash,
                json.dumps(sorted(set(permissions)), ensure_ascii=False),
                now,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def paired_devices(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT id,device_name,permissions,enabled,created_at,"
                "last_seen_at FROM paired_devices ORDER BY id DESC"
            )
        )

    def paired_device_by_hash(
        self,
        token_hash: str,
    ) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM paired_devices WHERE token_hash=?",
            (token_hash,),
        ).fetchone()

    def touch_paired_device(self, device_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE paired_devices SET last_seen_at=? WHERE id=?",
                (
                    local_wall_time().isoformat(timespec="seconds"),
                    int(device_id),
                ),
            )

    def revoke_paired_device(self, device_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE paired_devices SET enabled=0 WHERE id=?",
                (int(device_id),),
            )
        return cursor.rowcount > 0


def format_duration(seconds: int) -> str:
    hours, rest = divmod(max(0, seconds), 3600)
    minutes = rest // 60
    if hours:
        return f"{hours} 小時 {minutes} 分"
    return f"{minutes} 分鐘"
