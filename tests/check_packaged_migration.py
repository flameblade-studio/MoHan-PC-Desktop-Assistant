from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import StudioDB
from app import VOICE_GENERATION_PROMPT


def database_path() -> Path:
    return (
        Path(os.environ["LOCALAPPDATA"])
        / "YanJianStudio"
        / "MoHan"
        / "mohan.db"
    )


def prepare() -> None:
    db = StudioDB(database_path())
    db.set_setting("legacy_marker", "保留")
    db.set_setting("windows_voice", "OneCore::Microsoft Zhiwei")
    db.set_setting("voice_instructions", "舊語音提示")
    db.set_setting("tts_voice", "marin")
    db.set_setting("cloud_voice", "marin")
    db.set_setting("realtime_voice", "shimmer")
    db.set_setting("ai_model", "gpt-5.6-luna")
    db.conn.execute(
        "DELETE FROM settings WHERE key='mini_default_v1213_restored'"
    )
    db.conn.execute(
        "DELETE FROM settings "
        "WHERE key='traditional_chat_v1215_migrated'"
    )
    db.conn.execute(
        "INSERT INTO chat_log(role,content,created_at) VALUES(?,?,?)",
        (
            "assistant",
            "会保持专注，打开软件和鼠标。",
            "2026-01-01T00:00:00",
        ),
    )
    db.conn.commit()
    db.add_todo("既有資料不可遺失", "漫畫")
    db.close()


def verify() -> None:
    connection = sqlite3.connect(database_path())
    marker = connection.execute(
        "SELECT value FROM settings WHERE key='legacy_marker'"
    ).fetchone()
    todo = connection.execute(
        "SELECT COUNT(*) FROM todos WHERE title='既有資料不可遺失'"
    ).fetchone()
    voice = connection.execute(
        "SELECT value FROM settings WHERE key='windows_voice'"
    ).fetchone()
    voice_prompt = connection.execute(
        "SELECT value FROM settings WHERE key='voice_instructions'"
    ).fetchone()
    tts_voice = connection.execute(
        "SELECT value FROM settings WHERE key='tts_voice'"
    ).fetchone()
    realtime_voice = connection.execute(
        "SELECT value FROM settings WHERE key='realtime_voice'"
    ).fetchone()
    text_model = connection.execute(
        "SELECT value FROM settings WHERE key='ai_model'"
    ).fetchone()
    traditional_chat = connection.execute(
        "SELECT content FROM chat_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    connection.close()
    assert marker is not None and "保留" in marker[0]
    assert todo is not None and todo[0] == 1
    assert voice is not None and "zhiwei" not in voice[0].lower()
    assert voice_prompt is not None and VOICE_GENERATION_PROMPT in voice_prompt[0]
    assert tts_voice is not None and "coral" in tts_voice[0]
    assert realtime_voice is not None and "coral" in realtime_voice[0]
    assert text_model is not None and "gpt-5.4-mini" in text_model[0]
    assert traditional_chat is not None and traditional_chat[0] == (
        "會保持專注，開啟軟體和滑鼠。"
    )
    print("PACKAGED_MIGRATION_DATA_OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["verify"]:
        verify()
    else:
        raise SystemExit("usage: check_packaged_migration.py prepare|verify")
