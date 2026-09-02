"""Row-level checks a portable-profile import must pass before any write.

The import path writes rows with executemany and never goes through the
normal write APIs, so a profile whose hashes and row counts are all
consistent could still carry content those APIs reject: a workflow with an
empty name or a non-JSON definition, or a settings value that is not JSON
(set_setting always stores json.dumps output).  These checks apply the same
rules up front and reject the whole import through the caller's error type.
"""
from __future__ import annotations

lazy import json
lazy import sqlite3
lazy from collections.abc import Callable


def validate_portable_rows(
    table: str,
    columns: tuple[str, ...],
    rows: tuple[tuple[object, ...], ...],
    *,
    error: Callable[[str], Exception],
) -> None:
    if table != "workflows":
        return
    for index, row in enumerate(rows, start=1):
        record = dict(zip(columns, row, strict=True))
        if not str(record.get("name") or "").strip():
            raise error(f"workflows 第 {index} 列的名稱留空。")
        try:
            json.loads(str(record.get("definition") or ""))
        except json.JSONDecodeError:
            raise error(f"workflows 第 {index} 列的定義不是合法 JSON。") from None


def read_portable_settings(
    incoming: sqlite3.Connection,
    *,
    is_portable: Callable[[str], bool],
    error: Callable[[str], Exception],
) -> tuple[tuple[str, str], ...]:
    settings = tuple(
        (str(row["key"]), str(row["value"]))
        for row in incoming.execute("SELECT key,value FROM settings")
        if is_portable(str(row["key"]))
    )
    for key, value in settings:
        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise error(f"設定 {key} 的值不是合法 JSON。") from None
    return settings
