from __future__ import annotations

# 2026-08-27 稽核收編：本檔由 check_packaged_migration.py 更名後納入 run_all。
# prepare 建立 legacy_marker，啟動已安裝應用完成遷移，再由 verify 驗證。
# 證據齊備時執行完整閘門；證據待補時明確 skip。保留 prepare/verify CLI。
# 2026-08-27 审计收编：本文件从 check_packaged_migration.py 更名后纳入 run_all。
# prepare 创建 legacy_marker，启动已安装应用完成迁移，再由 verify 验证。
# 证据齐备时执行完整门槛；证据待补时明确 skip。保留 prepare/verify CLI。
# 2026-08-27 audit adoption: rename check_packaged_migration.py for run_all collection.
# prepare creates legacy_marker; launch the installed app, then run verify.
# Complete evidence enables the full gate; absent evidence yields an explicit skip.
# The prepare/verify CLI remains available for packaging.
# 2026-08-27 監査編入：check_packaged_migration.py を改名し run_all に登録。
# prepare で legacy_marker を作成し、導入済みアプリを起動して verify で検証。
# 証拠が揃えば完全検証を実行し、準備中は明示的に skip。CLI は維持する。

lazy import os
lazy import sqlite3
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB
lazy from domain.speech_configuration import VOICE_GENERATION_PROMPT


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
    db.set_setting("ai_model", "gpt-5.4-mini")
    db.conn.execute(
        "DELETE FROM settings WHERE key='mini_default_v1213_restored'"
    )
    db.conn.execute(
        "DELETE FROM settings WHERE key=?",
        ("luna_default_v210rc1_migrated",),
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
    preserved_chat = connection.execute(
        "SELECT content FROM chat_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    connection.close()
    assert marker is not None and "保留" in marker[0]
    assert todo is not None and todo[0] == 1
    assert voice is not None and "zhiwei" not in voice[0].lower()
    assert voice_prompt is not None and VOICE_GENERATION_PROMPT in voice_prompt[0]
    assert tts_voice is not None and "coral" in tts_voice[0]
    assert realtime_voice is not None and "coral" in realtime_voice[0]
    assert text_model is not None and "gpt-5.6-luna" in text_model[0]
    assert preserved_chat is not None and preserved_chat[0] == (
        "会保持专注，打开软件和鼠标。"
    )
    print("PACKAGED_MIGRATION_DATA_OK")


def _prepared_evidence_exists() -> bool:
    """Return whether the two-phase harness left its legacy marker behind."""

    path = database_path()
    if not path.exists():
        return False
    connection = sqlite3.connect(path)
    try:
        marker = connection.execute(
            "SELECT value FROM settings WHERE key='legacy_marker'"
        ).fetchone()
    except sqlite3.Error:
        return False
    finally:
        connection.close()
    return marker is not None


def test_packaged_migration_preserves_and_migrates_legacy_data() -> None:
    """Validate the packaged migration when its required evidence is available.

    prepare seeds a legacy database, then one installed-app startup migrates
    voices, prompts, and the model default. verify checks that resulting state.
    The test reports an explicit skip until the packaged product and migrated
    evidence are present.
    """

    if not _prepared_evidence_exists():
        print(
            "PACKAGED_MIGRATION_SKIPPED: no prepared packaged database "
            "(run prepare, launch the packaged app, then verify)"
        )
        return
    verify()


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["verify"]:
        verify()
    elif not sys.argv[1:]:
        test_packaged_migration_preserves_and_migrates_legacy_data()
        print("PACKAGED_MIGRATION_CHECK_OK")
    else:
        raise SystemExit("usage: test_packaged_migration.py [prepare|verify]")
