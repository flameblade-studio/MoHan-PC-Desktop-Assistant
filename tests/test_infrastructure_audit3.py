"""第 3 發 infrastructure 稽核（2026-09-02）的回歸。

七項裡的六項在這裡有測試；第 1 項（更新清單與安裝程式同源、沒有獨立發布者
簽章）是發行流程與金鑰託管的決策，不是程式碼修補。
"""
from __future__ import annotations

lazy import os
lazy import sqlite3
lazy import zipfile
lazy from datetime import UTC, datetime
lazy from pathlib import Path

lazy import pytest

lazy from infrastructure import windows_tools
lazy from infrastructure.backup_manager import BackupManager
lazy from infrastructure.db import StudioDB
lazy from infrastructure.framing_preferences_store import (
    FramingPreferencesStore,
    FramingPreferencesStoreError,
)
lazy from infrastructure.portable_import_checks import read_portable_settings
lazy from infrastructure.profile_transfer import (
    PortableProfileManager,
    ProfileTransferError,
    is_portable_setting,
)
lazy from infrastructure.gesture_configuration_store import (
    GestureConfigurationStore,
    GestureConfigurationStoreError,
)
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
    OpenAIVisionPreferencesStoreError,
)
lazy from infrastructure.performance_preferences_store import (
    PerformancePreferencesStore,
    PerformancePreferencesStoreError,
)
lazy from infrastructure.secret_store import SecretDecryptError, SecretStore
lazy from infrastructure.special_occasion_store import (
    SpecialOccasionStore,
    SpecialOccasionStoreError,
)
lazy from infrastructure.wellbeing_reminder_store import (
    WellbeingReminderStore,
    WellbeingReminderStoreError,
)

windows_only = pytest.mark.skipif(
    os.name != "nt", reason="DPAPI 與 user32 只在 Windows 上"
)
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


# ---- #3 DPAPI：沒有 blob 是空字串；有 blob 解不開必須出錯 ----


def test_secret_store_missing_blob_is_empty(tmp_path: Path) -> None:
    assert SecretStore(tmp_path / "none.dpapi", "test").load() == ""


@windows_only
def test_secret_store_undecryptable_blob_raises(tmp_path: Path) -> None:
    store = SecretStore(tmp_path / "key.dpapi", "test")
    store.save("secret-value")
    assert store.load() == "secret-value"
    blob = store.path.read_bytes()
    store.path.write_bytes(bytes(len(blob)))  # 同長度的全零：DPAPI 必然拒絕
    with pytest.raises(SecretDecryptError) as failure:
        store.load()
    assert isinstance(failure.value, OSError)
    assert "key.dpapi" in str(failure.value)


# ---- #5 備份：只有 verify() 通過的檔案算備份 ----


class _FakeDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE t(x)")
        self.conn.commit()


def test_unverifiable_backup_neither_satisfies_recent_nor_outranks_real(
    tmp_path: Path,
) -> None:
    manager = BackupManager(_FakeDB(tmp_path / "main.db"), tmp_path / "backups")
    real = manager.create("manual")
    assert manager.verify(real)
    two_days_ago = real.stat().st_mtime - 2 * 86400
    os.utime(real, (two_days_ago, two_days_ago))  # 真備份已過期，該再備份
    bogus = tmp_path / "backups" / "mohan-29991231-235959-000000.db"
    bogus.write_bytes(b"")  # 斷電情境：有 .db、沒 manifest，mtime 是「剛剛」
    assert not manager.verify(bogus)

    created = manager.automatic_if_due(hours=24)
    assert created is not None and manager.verify(created)

    manager.prune(keep_daily=1, keep_monthly=0)
    assert created.exists()  # 最新的真備份留下
    assert not real.exists()  # 較舊的真備份依保留數被清
    assert bogus.exists()  # 無法驗證的檔案不參與排名、也不動它


# ---- #7 Win32 回傳值 ----


class _FakeUser32:
    def __init__(
        self, *, rect_fail_hwnd: int | None = None, enum_ok: bool = True
    ) -> None:
        self.rect_fail_hwnd = rect_fail_hwnd
        self.enum_ok = enum_ok

    def IsWindowVisible(self, hwnd):  # noqa: N802 - Win32 名稱
        return 1

    def GetWindowTextLengthW(self, hwnd):  # noqa: N802
        return 9

    def GetWindowTextW(self, hwnd, buffer, size):  # noqa: N802
        buffer.value = f"window-{hwnd}"
        return len(buffer.value)

    def GetWindowRect(self, hwnd, rect_ref):  # noqa: N802
        if hwnd == self.rect_fail_hwnd:
            return 0
        rect = rect_ref._obj
        rect.left, rect.top, rect.right, rect.bottom = 1, 2, 3, 4
        return 1

    def EnumWindows(self, callback, lparam):  # noqa: N802
        if not self.enum_ok:
            return 0
        for hwnd in (11, 22, 33):
            callback(hwnd, lparam)
        return 1


@windows_only
def test_window_closed_between_calls_is_skipped_not_zero_rect(monkeypatch) -> None:
    monkeypatch.setattr(
        windows_tools, "_user32", lambda: _FakeUser32(rect_fail_hwnd=22)
    )
    rows = windows_tools.visible_windows()
    assert [row["hwnd"] for row in rows] == [11, 33]
    assert all(row["rect"] == [1, 2, 3, 4] for row in rows)


@windows_only
def test_enum_windows_failure_is_an_error_not_an_empty_success(monkeypatch) -> None:
    monkeypatch.setattr(windows_tools, "_user32", lambda: _FakeUser32(enum_ok=False))
    with pytest.raises(OSError):
        windows_tools.visible_windows()


# ---- #6 五個 store：後端讀取失敗要拋型別化錯誤，不回預設值 ----


class _BrokenSettings:
    def read(self, keys):
        raise sqlite3.OperationalError("disk I/O error")


class _EmptySettings:
    def read(self, keys):
        return {}


@pytest.mark.parametrize(
    ("factory", "error", "call"),
    [
        (WellbeingReminderStore, WellbeingReminderStoreError, lambda s: s.load(NOW)),
        (SpecialOccasionStore, SpecialOccasionStoreError, lambda s: s.load(NOW)),
        (
            OpenAIVisionPreferencesStore,
            OpenAIVisionPreferencesStoreError,
            lambda s: s.load(),
        ),
        (
            PerformancePreferencesStore,
            PerformancePreferencesStoreError,
            lambda s: s.load(),
        ),
        (GestureConfigurationStore, GestureConfigurationStoreError, lambda s: s.load()),
        (FramingPreferencesStore, FramingPreferencesStoreError, lambda s: s.load()),
    ],
    ids=["wellbeing", "occasion", "vision", "performance", "gesture", "framing"],
)
def test_backend_read_failure_raises_typed_error(factory, error, call) -> None:
    with pytest.raises(error):
        call(factory(_BrokenSettings()))
    # 「從未保存」仍然是預設值，不是錯誤。
    assert call(factory(_EmptySettings())) is not None


# ---- #2 匯出白名單：不可攜的表不能夾帶出去 ----


def test_export_clears_every_table_outside_the_portable_allowlist(
    tmp_path: Path,
) -> None:
    db = StudioDB(tmp_path / "source" / "mohan.db")
    db.add_todo("帶傘")
    db.conn.execute(
        "INSERT INTO memory_archive(original_id,snapshot,reason,archived_at) "
        "VALUES(1,'我的身分證字號是 A123456789','test','2026-09-02T00:00:00')"
    )
    db.conn.commit()
    manager = PortableProfileManager(db, tmp_path / "source" / "backups")
    bundle, _manifest = manager.export_profile(tmp_path / "out")
    with zipfile.ZipFile(bundle) as archive:
        profile_bytes = archive.read("profile.db")
    assert b"A123456789" not in profile_bytes
    exported = tmp_path / "exported.db"
    exported.write_bytes(profile_bytes)
    connection = sqlite3.connect(exported)
    try:
        assert connection.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM todos").fetchone()[0] == 1
    finally:
        connection.close()


# ---- #4 匯入不得繞過正常寫入路徑的驗證 ----


def _incoming_like(db: StudioDB, table: str) -> sqlite3.Connection:
    incoming = sqlite3.connect(":memory:")
    incoming.row_factory = sqlite3.Row
    schema = db.conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()[0]
    incoming.execute(schema)
    return incoming


@pytest.mark.parametrize(
    ("name", "definition", "message"),
    [
        ("", '{"steps": []}', "名稱留空"),
        ("夜間備份", "not-json", "不是合法 JSON"),
    ],
)
def test_import_rejects_workflow_rows_save_workflow_would_reject(
    tmp_path: Path, name: str, definition: str, message: str
) -> None:
    db = StudioDB(tmp_path / "mohan.db")
    manager = PortableProfileManager(db, tmp_path / "backups")
    incoming = _incoming_like(db, "workflows")
    incoming.execute(
        "INSERT INTO workflows(name,definition,enabled,created_at,updated_at) "
        "VALUES(?,?,1,'2026-09-02T00:00:00','2026-09-02T00:00:00')",
        (name, definition),
    )
    with pytest.raises(ProfileTransferError, match=message):
        manager._read_table_payload(incoming, "workflows")


def test_import_rejects_setting_values_that_are_not_json(tmp_path: Path) -> None:
    db = StudioDB(tmp_path / "mohan.db")
    manager = PortableProfileManager(db, tmp_path / "backups")
    incoming = _incoming_like(db, "settings")
    incoming.execute(
        "INSERT INTO settings(key,value) VALUES('assistant_name','not-json')"
    )
    assert manager is not None  # 目標資料庫存在，與正式匯入同一前提
    with pytest.raises(ProfileTransferError, match="assistant_name"):
        read_portable_settings(
            incoming, is_portable=is_portable_setting, error=ProfileTransferError
        )
