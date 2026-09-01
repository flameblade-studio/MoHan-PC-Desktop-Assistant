"""持久化層不得靜默遺失或洩漏使用者資料。

2026-09-01 的獨立稽核在 infrastructure/ 找到十一項缺陷，最嚴重的一項是：
可攜設定檔匯出會 DELETE 掉稽核紀錄與連線設定，然後直接打包原始 SQLite
檔案——而 SQLite 的 DELETE 只把頁面標記為可重用，內容仍留在檔案裡。
那個功能存在的唯一目的就是排除那些資料，而它沒有做到。

這裡的測試刻意驗證**位元組層級**的結果，不是驗證資料列數。原本的測試只
數刪除後還剩幾列，那種測試對這個缺陷完全無感。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


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
    """先證明這個缺陷是真的，否則下面那個測試證明不了任何事。

    這是「守衛的正例」：如果 SQLite 其實會自己清乾淨，那修正就沒有意義，
    而這個測試會失敗並告訴我們前提錯了。
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
    """匯出路徑本身必須做這兩件事，不是只有測試裡做。"""
    import inspect

    from infrastructure import profile_transfer

    body = inspect.getsource(profile_transfer)
    sanitise = body.split("_sanitize_snapshot", 1)[1]
    assert "secure_delete=ON" in sanitise, "匯出未啟用 secure_delete"
    assert "VACUUM" in sanitise, "匯出未執行 VACUUM"


def test_zero_byte_database_is_flagged_as_corrupt(tmp_path: Path) -> None:
    """零位元組資料庫是損毀，不是全新安裝。

    斷電、雲端同步中斷或複製失敗都會留下 0-byte 檔。SQLite 會把它當成空
    資料庫，於是應用成功建立新 schema、使用者看到預設 profile，接著正常
    操作開始往上寫。原本的資料還在備份裡，但使用者沒有理由知道要去還原。
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
            "真正的首次安裝不得被誤判為損毀"
        )
    finally:
        database.conn.close()


def test_secret_store_write_is_atomic() -> None:
    """DPAPI 秘密必須原子寫入。

    先前直接覆寫正式檔案。斷電或磁碟寫入失敗會留下截斷的 blob，下一次
    load() 解密失敗回傳空字串——而空字串與「尚未設定」無法區分，臉部
    identity 因此被當成零個 profile，接著新增一筆就把殘骸覆寫成新的真相。
    """
    import inspect

    from infrastructure import secret_store

    body = inspect.getsource(secret_store)
    assert "os.replace(" in body, "未使用 os.replace 做原子替換"
    assert "fsync" in body, "未 fsync，資料可能還在作業系統快取裡"


def test_optimize_database_is_bounded_and_reports_honestly() -> None:
    """optimize_database 不得刪光全部，也不得在刪除後回報 0。

    原本 cutoff 是「現在」，於是這個宣稱 bounded cleanup 的函式會刪掉每一筆
    已完成待辦與整個稽核紀錄；而 VACUUM 失敗時回報 pruned=0，但刪除早已
    commit——呼叫端會以為什麼都沒發生。
    """
    import inspect

    from infrastructure import db_memory

    body = inspect.getsource(db_memory.StudioDBMemoryMethods.optimize_database)
    assert "RETENTION_DAYS" in body, "cutoff 仍未設界"
    assert "timedelta" in body, "cutoff 未往回推算"
    # VACUUM 失敗的分支必須回報實際刪除數，不得歸零。
    # 要切在真正的 VACUUM **呼叫**，不是 docstring 裡的那個字——DELETE 本身
    # 失敗時 rollback 後回傳 0 是正確的，不能一起算進來。
    marker = 'self.conn.execute("VACUUM")'
    assert marker in body
    tail = body.split(marker, 1)[1]
    assert '"pruned_todos": 0' not in tail, (
        "VACUUM 失敗時仍回報刪除 0 筆——刪除已經 commit，那是謊報"
    )
    assert '"pruned_todos": pruned_todos' in tail, (
        "VACUUM 失敗時必須回報實際刪除數"
    )
