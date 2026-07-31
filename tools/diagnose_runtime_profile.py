from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def main(path_text: str) -> None:
    path = Path(path_text).resolve()
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        print("SETTINGS")
        for row in connection.execute(
            """
            SELECT key, value
            FROM settings
            WHERE key IN ('ai_model', 'realtime_model', 'transcription_model')
            ORDER BY key
            """
        ):
            print(json.dumps(dict(row), ensure_ascii=False))
        print("CONNECTOR")
        for row in connection.execute(
            """
            SELECT connector_id, enabled, last_health, configuration
            FROM connector_profiles
            WHERE connector_id = 'google'
            """
        ):
            print(json.dumps(dict(row), ensure_ascii=False))
        print("RECENT_AUDIT")
        for row in connection.execute(
            """
            SELECT event_type, payload, created_at
            FROM action_audit
            ORDER BY id DESC
            LIMIT 12
            """
        ):
            print(json.dumps(dict(row), ensure_ascii=False))
    finally:
        connection.close()


if __name__ == "__main__":
    main(sys.argv[1])
