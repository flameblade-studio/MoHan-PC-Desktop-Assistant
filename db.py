from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from text_normalizer import to_taiwan_traditional


DEFAULT_REMINDERS = {
    "work": ("開始工作", "09:30", 1),
    "lunch": ("吃飯", "12:30", 1),
    "dinner": ("晚餐", "18:30", 1),
    "offwork": ("下班", "21:00", 1),
}

class StudioDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.existing_install = path.exists() and path.stat().st_size > 0
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
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
        idea_columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(ideas)")
        }
        legacy_idea_source = (
            "text"
            if "text" in idea_columns
            else "body"
            if "body" in idea_columns
            else None
        )
        if "text" not in idea_columns:
            self.conn.execute(
                "ALTER TABLE ideas ADD COLUMN text TEXT NOT NULL DEFAULT ''"
            )
        if "title" not in idea_columns:
            self.conn.execute(
                "ALTER TABLE ideas ADD COLUMN title TEXT NOT NULL DEFAULT ''"
            )
        if "content" not in idea_columns:
            self.conn.execute(
                "ALTER TABLE ideas ADD COLUMN content TEXT NOT NULL DEFAULT ''"
            )
        if "updated_at" not in idea_columns:
            self.conn.execute("ALTER TABLE ideas ADD COLUMN updated_at TEXT")
        if legacy_idea_source:
            self.conn.execute(
                f"UPDATE ideas SET text={legacy_idea_source} "
                "WHERE COALESCE(text,'')=''"
            )
        self.conn.execute(
            "UPDATE ideas SET title=text WHERE COALESCE(title,'')=''"
        )
        self.conn.execute(
            "UPDATE ideas SET updated_at=created_at "
            "WHERE COALESCE(updated_at,'')=''"
        )
        memory_columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(memories)")
        }
        if "category" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN "
                "category TEXT NOT NULL DEFAULT '其他'"
            )
        if "title" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN title TEXT NOT NULL DEFAULT ''"
            )
        if "source" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN "
                "source TEXT NOT NULL DEFAULT 'manual'"
            )
        if "importance" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN "
                "importance INTEGER NOT NULL DEFAULT 3"
            )
        if "updated_at" not in memory_columns:
            self.conn.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT")
        if "scope" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN "
                "scope TEXT NOT NULL DEFAULT 'personal'"
            )
        if "expires_at" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN expires_at TEXT"
            )
        if "last_used_at" not in memory_columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN last_used_at TEXT"
            )
        self.conn.execute(
            "UPDATE memories SET updated_at=created_at "
            "WHERE COALESCE(updated_at,'')=''"
        )
        for row in self.conn.execute(
            "SELECT id,content FROM memories WHERE COALESCE(title,'')=''"
        ).fetchall():
            title = " ".join(str(row["content"]).split())
            if len(title) > 36:
                title = title[:36].rstrip() + "…"
            self.conn.execute(
                "UPDATE memories SET title=? WHERE id=?",
                (title or "未命名記憶", int(row["id"])),
            )
        legacy_memory_categories = {
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
        }
        for old_category, new_category in legacy_memory_categories.items():
            self.conn.execute(
                "UPDATE memories SET category=? "
                "WHERE LOWER(TRIM(category))=?",
                (new_category, old_category),
            )
        platform_columns = {
            row["name"]
            for row in self.conn.execute(
                "PRAGMA table_info(platform_progress)"
            )
        }
        for column in ("item_name", "next_action", "notes", "url"):
            if column not in platform_columns:
                self.conn.execute(
                    f"ALTER TABLE platform_progress ADD COLUMN "
                    f"{column} TEXT NOT NULL DEFAULT ''"
                )
        if "sort_order" not in platform_columns:
            self.conn.execute(
                "ALTER TABLE platform_progress "
                "ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
            )
        for kind, (label, at, enabled) in DEFAULT_REMINDERS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO reminders(kind,label,time_of_day,enabled) VALUES(?,?,?,?)",
                (kind, label, at, enabled),
            )
        now = datetime.now().isoformat(timespec="seconds")
        platform_seed_marker = self.conn.execute(
            "SELECT value FROM settings "
            "WHERE key='custom_platforms_v1207_seeded'"
        ).fetchone()
        if platform_seed_marker is None:
            # Existing installations already contain their original platform
            # rows. New installations intentionally start empty so the tracker
            # suits any profession instead of assuming a publishing workflow.
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('custom_platforms_v1207_seeded','true')"
            )
        self.conn.execute(
            "UPDATE chat_log SET content=REPLACE(content,'劍主','主上') "
            "WHERE content LIKE '%劍主%'"
        )
        traditional_chat_marker = self.conn.execute(
            "SELECT value FROM settings "
            "WHERE key='traditional_chat_v1215_migrated'"
        ).fetchone()
        if traditional_chat_marker is None:
            # Upgrade history created by older versions as well as newly
            # displayed text, so future AI context cannot reintroduce
            # Simplified Chinese from a stored conversation.
            for row in self.conn.execute(
                "SELECT id,content FROM chat_log"
            ).fetchall():
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
        migration_marker = self.conn.execute(
            "SELECT value FROM settings WHERE key='luna_default_v12_migrated'"
        ).fetchone()
        if migration_marker is None:
            current_model = self.conn.execute(
                "SELECT value FROM settings WHERE key='ai_model'"
            ).fetchone()
            current_value = None
            if current_model is not None:
                try:
                    current_value = json.loads(current_model["value"])
                except json.JSONDecodeError:
                    current_value = None
            if current_value in (None, "gpt-5.6-terra"):
                self.conn.execute(
                    "INSERT INTO settings(key,value) VALUES('ai_model',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (json.dumps("gpt-5.6-luna"),),
                )
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('luna_default_v12_migrated','true')"
            )
        mini_marker = self.conn.execute(
            "SELECT value FROM settings WHERE key='mini_default_v118_migrated'"
        ).fetchone()
        if mini_marker is None:
            current_model = self.conn.execute(
                "SELECT value FROM settings WHERE key='ai_model'"
            ).fetchone()
            current_value = None
            if current_model is not None:
                try:
                    current_value = json.loads(current_model["value"])
                except json.JSONDecodeError:
                    current_value = None
            if current_value in (None, "gpt-5.6-luna"):
                self.conn.execute(
                    "INSERT INTO settings(key,value) VALUES('ai_model',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (json.dumps("gpt-5.4-mini"),),
                )
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('mini_default_v118_migrated','true')"
            )
        mini_restore_marker = self.conn.execute(
            "SELECT value FROM settings "
            "WHERE key='mini_default_v1213_restored'"
        ).fetchone()
        if mini_restore_marker is None:
            current_model = self.conn.execute(
                "SELECT value FROM settings WHERE key='ai_model'"
            ).fetchone()
            current_value = None
            if current_model is not None:
                try:
                    current_value = json.loads(current_model["value"])
                except json.JSONDecodeError:
                    current_value = None
            if current_value in (None, "gpt-5.6-luna"):
                self.conn.execute(
                    "INSERT INTO settings(key,value) VALUES('ai_model',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (json.dumps("gpt-5.4-mini"),),
                )
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('mini_default_v1213_restored','true')"
            )
        if self.existing_install:
            # Public-release profile migration is deliberately non-destructive.
            # Existing users keep the identity and workflow they already had;
            # only previously unavailable fields are supplied.
            legacy_profile = {
                "assistant_name": "墨寒",
                "user_title": "主上",
                "organization_name": "炎劍文化工作室",
                "window_title": "",
                "work_type": "創作／內容工作",
                "ui_language": "zh-TW",
                "wake_word": "墨寒",
                "onboarding_complete": True,
                "transcription_language": "zh",
                "transcription_prompt": (
                    "請使用台灣繁體中文轉錄。常用詞：墨寒、寒、"
                    "主上、妾、炎劍文化工作室、赤焰劍、"
                    "斬空劍主、Pubu、Google Play Books、DistroKid、"
                    "LINE 貼圖。請保留原意，不要改寫。"
                ),
            }
            for key, value in legacy_profile.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                    (key, json.dumps(value, ensure_ascii=False)),
                )
        self.conn.commit()

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
                datetime.now().isoformat(timespec="seconds"),
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
                datetime.now().isoformat(timespec="seconds") if done else None,
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
        now = datetime.now().isoformat(timespec="seconds")
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
                datetime.now().isoformat(timespec="seconds"),
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
            (datetime.now().isoformat(timespec="seconds"),),
        )
        self.conn.commit()
        return True

    def stop_work(self) -> bool:
        row = self.active_session()
        if not row:
            return False
        self.conn.execute(
            "UPDATE work_sessions SET ended_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), row["id"]),
        )
        self.conn.commit()
        return True

    def today_work_seconds(self) -> int:
        day_start = datetime.combine(date.today(), datetime.min.time())
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
        now = datetime.now()
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
            int((datetime.now() - datetime.fromisoformat(row["started_at"])).total_seconds()),
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
                    datetime.now().isoformat(timespec="seconds"),
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
        platform: str,
        status: str,
        missing: str,
        item_name: str = "",
        next_action: str = "",
        notes: str = "",
        url: str = "",
    ) -> None:
        self.update_platforms(
            [
                {
                    "platform": platform,
                    "status": status,
                    "missing": missing,
                    "item_name": item_name,
                    "next_action": next_action,
                    "notes": notes,
                    "url": url,
                }
            ]
        )

    def update_platforms(self, entries: list[dict[str, str]]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        normalized = []
        for entry in entries:
            normalized.append(
                (
                    entry["platform"],
                    to_taiwan_traditional(
                        entry.get("status", "尚未開始").strip()
                    )
                    or "尚未開始",
                    to_taiwan_traditional(
                        entry.get("missing", "").strip()
                    ),
                    to_taiwan_traditional(
                        entry.get("item_name", "").strip()
                    ),
                    to_taiwan_traditional(
                        entry.get("next_action", "").strip()
                    ),
                    to_taiwan_traditional(
                        entry.get("notes", "").strip()
                    ),
                    entry.get("url", "").strip(),
                    now,
                )
            )
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
                datetime.now().isoformat(timespec="seconds"),
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
        now = datetime.now().isoformat(timespec="seconds")
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
        return int(row["id"])

    def list_memories(
        self,
        limit: int = 100,
        category: str | None = None,
    ) -> list[sqlite3.Row]:
        now = datetime.now().isoformat(timespec="seconds")
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
                    datetime.now().isoformat(timespec="seconds"),
                    memory_id,
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False
        return cursor.rowcount > 0

    def delete_memory(self, memory_id: int) -> None:
        self.conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self.conn.commit()

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
        return max(0, int(cursor.rowcount))

    def clear_memories(self) -> None:
        self.conn.execute("DELETE FROM memories")
        self.conn.commit()

    def memory_context(self, limit: int = 24) -> str:
        rows = self.list_memories(limit)
        if rows:
            now = datetime.now().isoformat(timespec="seconds")
            with self.conn:
                self.conn.executemany(
                    "UPDATE memories SET last_used_at=? WHERE id=?",
                    [(now, int(row["id"])) for row in rows],
                )
        return "\n".join(f"- [{row['category']}] {row['content']}" for row in rows)

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
                    datetime.now().isoformat(timespec="seconds"),
                    int(memory_id),
                ),
            )

    def purge_expired_memories(self) -> int:
        now = datetime.now().isoformat(timespec="seconds")
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
                datetime.now().isoformat(timespec="seconds"),
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
        now = datetime.now().isoformat(timespec="seconds")
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
                    datetime.now().isoformat(timespec="seconds"),
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
        now = datetime.now().isoformat(timespec="seconds")
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
        now = datetime.now().isoformat(timespec="seconds")
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
                    datetime.now().isoformat(timespec="seconds"),
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
