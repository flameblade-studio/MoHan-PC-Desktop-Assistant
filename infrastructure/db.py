from __future__ import annotations

lazy import json
lazy import sqlite3
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from datetime import datetime, timedelta
lazy from pathlib import Path

lazy from domain.language_support import (
    LEGACY_AUTHOR_ORGANIZATION, LEGACY_TRANSCRIPTION_PROMPT, canonical_ui_language, localized_transcription_prompt,
)
lazy from domain.time_utils import local_wall_time
lazy from infrastructure.db_affection import StudioDBAffectionMethods
lazy from infrastructure.db_memory import StudioDBMemoryMethods
lazy from infrastructure.corrupt_data import (
    CORRUPT_DATA_MESSAGE,
    CorruptStoredJSON,
)
lazy from infrastructure.memory_index import MemoryVectorIndex
lazy from infrastructure.sqlite_safety import classify_db_file, table_column_names

MAX_MEMORY_TITLE_LENGTH = 36

# 裁決 2026-08-28：這些鍵是執行期狀態（好感、天氣、自主衣櫥、新裝披露），
# 而非使用者可編輯的設定；restore_settings_snapshot 於快照回復時保留當前值。
RUNTIME_PRESERVED_KEYS = frozenset({
    "affinity_value", "jealousy_value", "affinity_interaction_count",
    "favor_value", "satiety_value", "camera_presence_state",
    "wardrobe_generation_pending_job_id", "wardrobe_generation_last_attempt_at",
    "wardrobe_generation_last_error", "wardrobe_last_generated_at",
    "active_outfit_id", "wardrobe_last_changed_at", "wardrobe_manual_lock_until",
    "wardrobe_current_weight", "weather_temperature_c", "weather_condition",
    "wardrobe_reveal_pending_outfit_id",
})

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
class DurationFormat:
    with_hours: str
    minutes_only: str


DURATION_FORMATS: Mapping[str, DurationFormat] = frozendict({
    "zh-TW": DurationFormat(
        with_hours="{hours} 小時 {minutes} 分",
        minutes_only="{minutes} 分鐘",
    ),
    "zh-CN": DurationFormat(
        with_hours="{hours} 小时 {minutes} 分",
        minutes_only="{minutes} 分钟",
    ),
    "en": DurationFormat(
        with_hours="{hours} h {minutes} min",
        minutes_only="{minutes} min",
    ),
    "ja-JP": DurationFormat(
        with_hours="{hours}時間{minutes}分",
        minutes_only="{minutes}分",
    ),
})


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
            self.platform.strip(),
            self.status.strip() or "尚未開始",
            self.missing.strip(),
            self.item_name.strip(),
            self.next_action.strip(),
            self.notes.strip(),
            self.url.strip(),
            updated_at,
        )


@dataclass(frozen=True, slots=True)
class SettingsRowsSnapshot:
    keys: tuple[str, ...]
    rows: frozendict[str, str]


class StudioDBSettingsPort:
    """Narrow atomic settings adapter for typed preference services."""

    def __init__(self, db: StudioDB) -> None:
        self._db = db

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        if not keys:
            return frozendict()
        placeholders = ",".join("?" for _key in keys)
        rows = self._db.conn.execute(
            f"SELECT key,value FROM settings WHERE key IN ({placeholders})",
            keys,
        )
        decoded: dict[str, object] = {}
        for row in rows:
            key = str(row["key"])
            try:
                decoded[key] = json.loads(str(row["value"]))
            except json.JSONDecodeError, TypeError, ValueError:
                raw = str(row["value"])
                self._db._record_corrupt_value(
                    "settings",
                    key,
                    raw,
                    "invalid-json",
                )
                decoded[key] = CorruptStoredJSON("settings", key, raw)
        return frozendict(decoded)

    def snapshot(self, keys: tuple[str, ...]) -> SettingsRowsSnapshot:
        if not keys:
            return SettingsRowsSnapshot((), frozendict())
        placeholders = ",".join("?" for _key in keys)
        return SettingsRowsSnapshot(
            keys=keys,
            rows=frozendict(
                (str(row["key"]), str(row["value"]))
                for row in self._db.conn.execute(
                    f"SELECT key,value FROM settings WHERE key IN ({placeholders})",
                    keys,
                )
            ),
        )

    def write(self, values: Mapping[str, object]) -> None:
        encoded = tuple(
            (str(key), json.dumps(value, ensure_ascii=False))
            for key, value in values.items()
        )
        with self._db.conn:
            self._db.conn.executemany(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                encoded,
            )

    def restore(self, snapshot: SettingsRowsSnapshot) -> None:
        if not isinstance(snapshot, SettingsRowsSnapshot):
            raise TypeError("settings snapshot type is invalid")
        keys = snapshot.keys
        with self._db.conn:
            if keys:
                placeholders = ",".join("?" for _key in keys)
                self._db.conn.execute(
                    f"DELETE FROM settings WHERE key IN ({placeholders})",
                    keys,
                )
            self._db.conn.executemany(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                tuple(snapshot.rows.items()),
            )


class StudioDB:
    affection_row = StudioDBAffectionMethods.affection_row
    upsert_affection = StudioDBAffectionMethods.upsert_affection
    add_memory = StudioDBMemoryMethods.add_memory
    list_memories = StudioDBMemoryMethods.list_memories
    memory = StudioDBMemoryMethods.memory
    update_memory = StudioDBMemoryMethods.update_memory
    delete_memory = StudioDBMemoryMethods.delete_memory
    delete_memories = StudioDBMemoryMethods.delete_memories
    clear_memories = StudioDBMemoryMethods.clear_memories
    memory_context = StudioDBMemoryMethods.memory_context
    # #88 起 dashboard 呼叫此方法但委派漏掛——兩版「思考中」懸案第一因。
    recent_chat_context = StudioDBMemoryMethods.recent_chat_context
    _archive_memory_ids = StudioDBMemoryMethods._archive_memory_ids
    list_archived_memories = StudioDBMemoryMethods.list_archived_memories
    restore_archived_memory = StudioDBMemoryMethods.restore_archived_memory
    _decode_archived_snapshot = StudioDBMemoryMethods._decode_archived_snapshot
    _memory_age_days = staticmethod(StudioDBMemoryMethods._memory_age_days)
    _memory_timestamp_raw = staticmethod(StudioDBMemoryMethods._memory_timestamp_raw)
    _consolidate_auto_duplicates = StudioDBMemoryMethods._consolidate_auto_duplicates
    _merge_memory_contents = staticmethod(StudioDBMemoryMethods._merge_memory_contents)
    optimize_memories = StudioDBMemoryMethods.optimize_memories
    update_memory_policy = StudioDBMemoryMethods.update_memory_policy
    purge_expired_memories = StudioDBMemoryMethods.purge_expired_memories
    export_memories = StudioDBMemoryMethods.export_memories

    def _record_corrupt_value(
        self,
        source: str,
        key: str,
        raw: str,
        reason: str,
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO corrupt_data("
                "source,item_key,raw_value,reason,detected_at"
                ") VALUES(?,?,?,?,?)",
                (
                    str(source),
                    str(key),
                    str(raw),
                    str(reason),
                    local_wall_time().isoformat(timespec="seconds"),
                ),
            )

    def consume_corrupt_data_notifications(self) -> tuple[str, ...]:
        rows = self.conn.execute(
            "SELECT id FROM corrupt_data WHERE notified_at IS NULL"
        ).fetchall()
        if not rows:
            return ()
        with self.conn:
            self.conn.executemany(
                "UPDATE corrupt_data SET notified_at=? WHERE id=?",
                [
                    (local_wall_time().isoformat(timespec="seconds"), int(row["id"]))
                    for row in rows
                ],
            )
        return (CORRUPT_DATA_MESSAGE,)

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.corrupt_empty_database, self.existing_install = classify_db_file(path)
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
            CREATE TABLE IF NOT EXISTS corrupt_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                item_key TEXT NOT NULL,
                raw_value TEXT NOT NULL,
                reason TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                notified_at TEXT,
                UNIQUE(source,item_key,raw_value,reason)
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
            CREATE TABLE IF NOT EXISTS companion_affection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                favor_score REAL NOT NULL DEFAULT 0.0,
                trust_level REAL NOT NULL DEFAULT 0.0,
                jealousy_meter REAL NOT NULL DEFAULT 0.0,
                satiety_level REAL NOT NULL DEFAULT 1.0,
                devotion_bonus INTEGER NOT NULL DEFAULT 0,
                last_interaction_ts TEXT,
                updated_at TEXT NOT NULL
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
        columns = table_column_names(self.conn, "ideas")
        legacy_source = (
            "text" if "text" in columns else "body" if "body" in columns else None
        )
        self._ensure_columns("ideas", IDEA_COLUMN_DEFINITIONS, columns)
        if legacy_source is not None:
            self.conn.execute(
                f"UPDATE ideas SET text={legacy_source} WHERE COALESCE(text,'')=''"
            )
        self.conn.execute("UPDATE ideas SET title=text WHERE COALESCE(title,'')=''")
        self.conn.execute(
            "UPDATE ideas SET updated_at=created_at WHERE COALESCE(updated_at,'')=''"
        )

    def _migrate_memories(self) -> None:
        columns = table_column_names(self.conn, "memories")
        self._ensure_columns("memories", MEMORY_COLUMN_DEFINITIONS, columns)
        self.conn.execute(
            "UPDATE memories SET updated_at=created_at WHERE COALESCE(updated_at,'')=''"
        )
        rows = self.conn.execute(
            "SELECT id,content FROM memories WHERE COALESCE(title,'')=''"
        ).fetchall()
        for row in rows:
            title = " ".join(str(row["content"]).split())
            if len(title) > MAX_MEMORY_TITLE_LENGTH:
                title = title[:MAX_MEMORY_TITLE_LENGTH].rstrip() + "…"
            self.conn.execute(
                "UPDATE memories SET title=? WHERE id=?",
                (title or "未命名記憶", int(row["id"])),
            )
        for old_category, new_category in LEGACY_MEMORY_CATEGORIES.items():
            self.conn.execute(
                "UPDATE memories SET category=? WHERE LOWER(TRIM(category))=?",
                (new_category, old_category),
            )

    def _migrate_platform_progress(self) -> None:
        columns = table_column_names(self.conn, "platform_progress")
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
            "SELECT value FROM settings WHERE key='custom_platforms_v1207_seeded'"
        ).fetchone()
        if marker is None:
            # Existing profiles retain their rows; new profiles intentionally
            # start empty instead of assuming a publishing workflow.
            self.conn.execute(
                "INSERT INTO settings(key,value) "
                "VALUES('custom_platforms_v1207_seeded','true')"
            )

    def _migrate_chat_history(self) -> None:
        # Older single-language releases rewrote every chat row to Traditional
        # Chinese. A four-language profile must preserve user and model text
        # verbatim, so the legacy marker remains only for upgrade compatibility.
        self.conn.execute(
            "INSERT OR IGNORE INTO settings(key,value) "
            "VALUES('traditional_chat_v1215_migrated','true')"
        )

    def _decoded_setting(self, key: str) -> object:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        raw = str(row["value"])
        try:
            return json.loads(raw)
        except json.JSONDecodeError, TypeError, ValueError:
            self._record_corrupt_value("settings", key, raw, "invalid-json")
            return CorruptStoredJSON("settings", key, raw)

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
        decoded = self._decoded_setting("ai_model")
        if not isinstance(decoded, CorruptStoredJSON) and decoded in prior_values:
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
        profile: dict[str, object] = {}
        for key in TRANSCRIPTION_PROFILE_KEYS:
            value = self._decoded_setting(key)
            if isinstance(value, CorruptStoredJSON):
                return
            profile[key] = value or ""
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
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: object) -> None:
        encoded = json.dumps(value, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, encoded),
        )
        self.conn.commit()

    def settings_snapshot(self) -> frozendict[str, str]:
        """Capture exact encoded settings for reversible UI drafts."""

        return frozendict(
            (str(row["key"]), str(row["value"]))
            for row in self.conn.execute("SELECT key,value FROM settings")
        )

    def restore_settings_snapshot(self, snapshot: Mapping[str, str]) -> None:
        """Restore a trusted snapshot atomically, keeping live runtime state.

        裁決 2026-08-28（選擇性回滾）：:data:`RUNTIME_PRESERVED_KEYS` 內的鍵
        保留當前值（含快照後新出現的鍵），其餘鍵才回到快照內容。
        """

        with self.conn:
            keys = tuple(RUNTIME_PRESERVED_KEYS)
            preserved = {
                str(row["key"]): str(row["value"])
                for row in self.conn.execute(
                    "SELECT key,value FROM settings WHERE key IN "
                    f"({','.join('?' for _ in keys)})",
                    keys,
                )
            }
            kept = {
                key: value for key, value in snapshot.items()
                if key not in RUNTIME_PRESERVED_KEYS
            }
            restored = kept | preserved
            self.conn.execute("DELETE FROM settings")
            self.conn.executemany(
                "INSERT INTO settings(key,value) VALUES(?,?)",
                tuple(restored.items()),
            )

    def setting(self, key: str, default: object = None) -> object:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,),
        ).fetchone()
        if row is None:
            return default
        raw = str(row["value"])
        try:
            return json.loads(raw)
        except json.JSONDecodeError, TypeError, ValueError:
            self._record_corrupt_value("settings", key, raw, "invalid-json")
            return CorruptStoredJSON("settings", key, raw)

    def add_todo(self, title: str, category: str = "其他") -> int:
        title = title.strip()
        # An identical active todo is a duplicate, not a new task.  Return the
        # existing row so the UI can surface "already added" instead of piling
        # up near-identical entries.
        existing = self.conn.execute(
            "SELECT id FROM todos WHERE title=? AND status='待辦' ORDER BY id DESC LIMIT 1",
            (title,),
        ).fetchone()
        if existing is not None:
            return int(existing["id"])
        cur = self.conn.execute(
            "INSERT INTO todos(title,category,created_at) VALUES(?,?,?)",
            (
                title,
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
        text = text.strip()
        content = content.strip()
        # An identical idea is a duplicate; return the existing row instead of
        # creating a near-identical entry.
        existing = self.conn.execute(
            "SELECT id FROM ideas WHERE text=? ORDER BY id DESC LIMIT 1",
            (text,),
        ).fetchone()
        if existing is not None:
            return int(existing["id"])
        now = local_wall_time().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO ideas(text,title,content,created_at,updated_at) "
            "VALUES(?,?,?,?,?)",
            (
                text,
                text,
                content,
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
        title = title.strip()
        content = content.strip()
        self.conn.execute(
            "UPDATE ideas SET text=?,title=?,content=?,updated_at=? WHERE id=?",
            (
                title,
                title,
                content,
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
                datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else now,
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
            int(
                (
                    local_wall_time() - datetime.fromisoformat(row["started_at"])
                ).total_seconds()
            ),
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
        name = platform.strip()
        if not name:
            return False
        row = self.conn.execute(
            "SELECT 1 FROM platform_progress WHERE platform=? COLLATE NOCASE",
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
                content,
                local_wall_time().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()

    def recent_chat(self, limit: int = 12) -> list[sqlite3.Row]:
        rows = list(
            self.conn.execute(
                "SELECT * FROM chat_log ORDER BY id DESC LIMIT ?", (limit,)
            )
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

    def audit_event(self, event_type: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT INTO action_audit(event_type,payload,created_at) VALUES(?,?,?)",
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
        name = name.strip()
        if not name:
            raise ValueError("工作流程名稱不可留空")
        json.loads(definition)
        now = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            if workflow_id is None:
                cursor = self.conn.execute(
                    "INSERT INTO workflows("
                    "name,definition,enabled,created_at,updated_at"
                    ") VALUES(?,?,?,?,?)",
                    (name, definition, int(enabled), now, now),
                )
                return int(cursor.lastrowid)
            self.conn.execute(
                "UPDATE workflows SET name=?,definition=?,enabled=?,"
                "updated_at=? WHERE id=?",
                (name, definition, int(enabled), now, int(workflow_id)),
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
                    display_name.strip(),
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
                "SELECT * FROM connector_profiles ORDER BY display_name COLLATE NOCASE"
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
                    display_name.strip(),
                    target_value.strip(),
                    access_mode,
                ),
            )
        row = self.conn.execute(
            "SELECT id FROM allowed_targets WHERE target_type=? AND target_value=?",
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
                device_name.strip(),
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


def format_duration(seconds: int, language: str = "zh-TW") -> str:
    hours, rest = divmod(max(0, seconds), 3600)
    minutes = rest // 60
    duration_format = DURATION_FORMATS[canonical_ui_language(language)]
    template = duration_format.with_hours if hours else duration_format.minutes_only
    return template.format(hours=hours, minutes=minutes)
