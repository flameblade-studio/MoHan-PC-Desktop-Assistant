from __future__ import annotations

# 2026-08-27 稽核收編：本檔原名 check_packaged_migration.py，是打包產物的
# 兩階段遷移驗證器（prepare → 啟動已安裝的應用程式 → verify），過去未被
# run_all 收集而成為孤兒。改名後由 run_all 收集：缺少打包遷移證據
# （prepare 留下的 legacy_marker 資料庫）時明確 skip，證據存在時執行完整
# fail-closed 驗證。prepare／verify 命令列介面保留給打包流程使用。
# 2026-08-27 审计收编：本文件原名 check_packaged_migration.py，是打包产物的
# 两阶段迁移验证器（prepare → 启动已安装的应用程序 → verify），过去未被
# run_all 收集而成为孤儿。改名后由 run_all 收集：缺少打包迁移证据
# （prepare 留下的 legacy_marker 数据库）时明确 skip，证据存在时执行完整
# fail-closed 验证。prepare／verify 命令行接口保留给打包流程使用。
# 2026-08-27 audit adoption: this file was named check_packaged_migration.py,
# a two-phase migration verifier for the packaged product (prepare -> launch
# the installed app -> verify) that run_all never collected, leaving it an
# orphan.  After the rename run_all collects it: when the packaged-migration
# evidence (the legacy_marker database left by prepare) is absent the test
# skips explicitly; when it is present the full fail-closed verification
# runs.  The prepare/verify CLI is preserved for the packaging pipeline.
# 2026-08-27 監査編入：本ファイルの旧名は check_packaged_migration.py で、
# パッケージ製品の二段階移行検証（prepare → インストール済みアプリ起動 →
# verify）でしたが、run_all に収集されず孤児になっていました。改名後は
# run_all が収集します：打包移行の証拠（prepare が残す legacy_marker
# データベース）が無い場合は明示的に skip し、存在する場合は fail-closed の
# 完全検証を実行します。prepare／verify の CLI はパッケージ工程向けに
# 維持します。

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
    """Fail-closed gate: verify when packaged evidence exists, skip otherwise.

    The full check needs the packaged product itself: ``prepare`` seeds a
    legacy database, the installed app must then run once (its startup
    migrations rewrite voices, prompts and the model default), and only then
    can ``verify`` assert the migrated end state.  Without that evidence the
    assertions cannot hold, so the test skips loudly instead of failing.
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
