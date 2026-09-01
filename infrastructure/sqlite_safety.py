"""SQLite 檔案層級的安全檢查。

2026-09-01 的稽核在持久化層找到兩個缺陷，成因是同一件事：SQLite 對檔案狀態
的回答不能照字面採信。刪除的資料仍在檔案裡，而長度為零的檔案會被當成一個
合法的空資料庫。兩者都不會拋錯，因此呼叫端不會知道出了事。

這些判斷原本各自寫在 `db.py` 與 `profile_transfer.py` 裡，`PRAGMA table_info`
的包裝更是兩邊各一份。集中在這裡，是為了讓「SQLite 說的話要怎麼解讀」只有
一個答案。
"""
from __future__ import annotations

lazy import sqlite3
lazy from pathlib import Path


def classify_db_file(path: Path) -> tuple[bool, bool]:
    """回傳 (是否為零位元組損毀, 是否為既有安裝)。

    零位元組資料庫是損毀，不是全新安裝。斷電、雲端同步中斷或複製失敗都會
    留下 0-byte 檔；SQLite 會把它當成空資料庫，於是下次啟動成功建立新結構，
    使用者看到一份預設設定並開始往上寫。原本的資料還在備份裡，但使用者沒有
    理由知道要去還原。

    必須在建立連線之前分辨：檔案存在但長度為零，與真正的首次安裝，在連線
    之後就完全無法區分了。
    """
    size = path.stat().st_size if path.exists() else -1
    return size == 0, size > 0


def enable_secure_delete(connection: sqlite3.Connection) -> None:
    """讓後續的 DELETE 當下就把頁面內容歸零。

    `DELETE` 只把頁面標記為可重用，內容仍留在檔案裡。要把資料真的排除在
    匯出檔之外，這個設定與事後的 `VACUUM` 兩者都要：這個設定管接下來的
    刪除，`VACUUM` 管快照複製過來時就已經存在的舊空閒頁。
    """
    connection.execute("PRAGMA secure_delete=ON")


def table_columns(connection: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    """回傳一張表的欄位定義列。"""
    return list(connection.execute(f'PRAGMA table_info("{table}")'))


def table_column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    """回傳一張表的欄位名稱集合。"""
    return {str(row["name"]) for row in table_columns(connection, table)}
