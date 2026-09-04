from __future__ import annotations

lazy import json

lazy from domain.time_utils import local_wall_time
lazy from infrastructure.corrupt_data import (
    CORRUPT_DATA_MESSAGE,
    CorruptStoredJSON,
)

__all__ = ("StudioDBCorruptDataMethods",)

CORRUPT_DATA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS corrupt_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    item_key TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    reason TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    notified_at TEXT,
    UNIQUE(source,item_key,raw_value,reason)
)
"""


class StudioDBCorruptDataMethods:
    def _ensure_corrupt_data_table(self) -> None:
        self.conn.execute(CORRUPT_DATA_TABLE_SQL)

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
