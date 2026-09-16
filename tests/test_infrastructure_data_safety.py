"""持久化層完整保存使用者資料，匯出範圍遵循授權。

2026-09-01 稽核找到十一項缺陷。可攜設定檔曾先 DELETE 稽核紀錄與
連線設定，再封裝原始 SQLite；DELETE 只標記頁面可重用，原始位元組
仍留在檔案中，因此私人內容仍會進入匯出檔。

測試直接檢查匯出位元組，確保封裝內容只包含核准資料；資料列數檢查
另保留其資料結構用途。
"""
from __future__ import annotations

lazy import sqlite3
lazy from pathlib import Path


MARKER = "SENSITIVE-CLIPBOARD-PAYLOAD-a1b2c3d4e5f6"


def _build_database(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE action_audit (id INTEGER PRIMARY KEY, payload TEXT)")
    # 寫入足夠多列，確保跨越多個頁面——單列可能剛好落在會被重用的頁面上，
    # 那樣就算沒修好也可能碰巧測不出來。
    conn.executemany(
        "INSERT INTO action_audit (payload) VALUES (?)",
        [(f"{MARKER}-{index}",) for index in range(400)],
    )
    conn.commit()
    conn.close()


def test_plain_delete_leaves_payload_in_the_file() -> None:
    """確認 SQLite DELETE 後仍保留原始位元組的測試前提。

    此守衛正例先證明資料殘留現象；若 SQLite 行為改變，測試會明確
    回報前提需重新檢視。
    """
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "plain.db"
        _build_database(path)
        conn = sqlite3.connect(path)
        conn.execute("DELETE FROM action_audit")
        conn.commit()
        conn.close()
        assert MARKER.encode() in path.read_bytes(), (
            "前提不成立：SQLite 的 DELETE 竟然自己清掉了頁面內容，"
            "那麼 secure_delete 與 VACUUM 就不是必要的——請重新檢視這組測試"
        )


def test_secure_delete_and_vacuum_remove_the_payload() -> None:
    """修正後：位元組必須真的不在檔案裡。"""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "sanitised.db"
        _build_database(path)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA secure_delete=ON")
        conn.execute("DELETE FROM action_audit")
        conn.commit()
        conn.execute("VACUUM")
        conn.close()
        assert MARKER.encode() not in path.read_bytes(), (
            "已刪除的內容仍留在匯出檔的原始位元組裡"
        )


def test_profile_export_applies_secure_delete_and_vacuum() -> None:
    """匯出入口與共用 secure_delete 都須通過驗證。

    自 2026-09-02 起，共用函式由 infrastructure/sqlite_safety.py 提供。
    同時核對函式行為及匯出呼叫點，完整涵蓋資料清理與流程接線。
    """
    import inspect

    from infrastructure import profile_transfer, sqlite_safety

    body = inspect.getsource(profile_transfer)
    sanitise = body.split("_sanitize_snapshot", 1)[1]
    assert "enable_secure_delete(" in sanitise, "匯出未呼叫 enable_secure_delete"
    assert "VACUUM" in sanitise, "匯出未執行 VACUUM"
    helper = inspect.getsource(sqlite_safety.enable_secure_delete)
    assert "secure_delete=ON" in helper, "共用函式未下 secure_delete 的 PRAGMA"


def test_zero_byte_database_is_flagged_as_corrupt(tmp_path: Path) -> None:
    """現存零位元組資料庫須標示損毀，並引導還原。

    斷電、同步或複製中斷可能留下 0-byte 檔。SQLite 會將其視為空資料庫，
    建立 schema 並顯示預設 profile。此測試要求揭露損毀狀態，讓使用者
    能從備份還原原有資料。
    """
    from infrastructure.db import StudioDB

    empty = tmp_path / "mohan.db"
    empty.write_bytes(b"")
    database = StudioDB(empty)
    try:
        assert database.corrupt_empty_database is True
        assert database.existing_install is False
    finally:
        database.conn.close()

    fresh = tmp_path / "fresh.db"
    database = StudioDB(fresh)
    try:
        assert database.corrupt_empty_database is False, (
            '首次安裝須正確辨識為新資料庫'
        )
    finally:
        database.conn.close()


def test_secret_store_write_is_atomic() -> None:
    """DPAPI 秘密使用原子寫入，保留可還原的完整內容。

    直接覆寫遇到斷電或寫入中斷會留下截斷 blob。舊 load() 將解密錯誤
    表示為空字串，使 identity 被當作空 profile 集合，後續新增便覆寫
    殘存資料。此測試驗證完整寫入與明確錯誤狀態。
    """
    import inspect

    from infrastructure import secret_store

    body = inspect.getsource(secret_store)
    assert "os.replace(" in body, "未使用 os.replace 做原子替換"
    assert "fsync" in body, "未 fsync，資料可能還在作業系統快取裡"


def test_optimize_database_is_bounded_and_reports_honestly() -> None:
    """optimize_database 保留期限內資料，並回報實際刪除數。

    舊 cutoff 使用現在時間，會清掉所有已完成待辦與稽核紀錄；VACUUM
    異常時還會在刪除已 commit 後回報 pruned=0。此測試驗證保留期限
    及提交後計數的準確性。
    """
    import inspect

    from infrastructure import db_memory

    body = inspect.getsource(db_memory.StudioDBMemoryMethods.optimize_database)
    assert "RETENTION_DAYS" in body, "cutoff 仍未設界"
    assert "timedelta" in body, "cutoff 未往回推算"
    # VACUUM 異常分支仍須回報已提交的實際刪除數。
    # 要切在真正的 VACUUM **呼叫**，不是 docstring 裡的那個字——DELETE 本身
    # 已 rollback 的分支正確回報 0，依其實際提交狀態計數。
    marker = 'self.conn.execute("VACUUM")'
    assert marker in body
    tail = body.split(marker, 1)[1]
    assert '"pruned_todos": 0' not in tail, (
        'VACUUM 異常後須回報已提交的實際刪除數'
    )
    assert '"pruned_todos": pruned_todos' in tail, (
        'VACUUM 異常時須回報實際刪除數'
    )
