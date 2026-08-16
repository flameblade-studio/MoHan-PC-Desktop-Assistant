lazy import sqlite3
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB


def run() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy.db"
        legacy = sqlite3.connect(path)
        legacy.executescript(
            """
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE platform_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                item TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            INSERT INTO settings(key, value) VALUES
                ('studio_name', '炎劍文化工作室'),
                ('user_title', '主上'),
                ('chat_model', 'gpt-5.4-mini');
            INSERT INTO ideas(body, created_at)
                VALUES ('舊版靈感必須保留', '2026-07-29T12:00:00');
            INSERT INTO memories(category, content, importance, created_at)
                VALUES ('preference', '偏好繁體中文', 5, '2026-07-29T12:00:00');
            """
        )
        legacy.commit()
        legacy.close()

        db = StudioDB(path)
        try:
            assert db.get_setting("studio_name") == "炎劍文化工作室"
            assert db.get_setting("user_title") == "主上"
            assert db.get_setting("chat_model") == "gpt-5.4-mini"
            idea = db.conn.execute(
                "SELECT body, title, content FROM ideas"
            ).fetchone()
            assert idea[0] == "舊版靈感必須保留"
            memory = db.conn.execute(
                "SELECT content, scope FROM memories"
            ).fetchone()
            assert memory[0] == "偏好繁體中文"
            assert memory[1] == "personal"
            expected_tables = {
                "action_audit",
                "workflows",
                "connector_profiles",
                "allowed_targets",
                "paired_devices",
            }
            actual_tables = {
                row[0]
                for row in db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert expected_tables <= actual_tables
            assert db.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            db.close()
    print("V1219_MIGRATION_OK")


if __name__ == "__main__":
    run()
