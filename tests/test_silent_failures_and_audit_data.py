"""失敗不得偽裝成成功；稽核紀錄不得變成資料倉。

2026-09-02 稽核第 4 批，四項成因各異但後果同型——呼叫端拿到的值分不出
「沒事」與「壞了」：

1. `_directory_bytes()` 遇到 stat() 失敗就回傳部分總量，容量檢查以此放行。
2. `drain()` 吞掉 worker 例外後回傳 []，與「沒有事件」無法區分。
3. 服裝稽核只檢查每個 pose 的 entries[0]，後層任何缺陷都能出貨。
4. 稽核紀錄原樣保存剪貼簿全文（UI 顯示 500 字，資料庫存到 100,000 字）。

每組都同時驗證「該擋的擋住」與「該放行的仍然放行」。
"""
from __future__ import annotations

lazy import struct
lazy import zlib
lazy from concurrent.futures import Future
lazy from pathlib import Path


# ── 1) 容量掃描 fail-closed ───────────────────────────────────────────────

def test_directory_bytes_reports_measurement_failure_as_none(tmp_path, monkeypatch) -> None:
    """量不完整必須回傳 None，而不是到目前為止的部分總量。"""
    from application import wardrobe_storage

    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    (tmp_path / "b.bin").write_bytes(b"x" * 1000)
    real_stat = Path.stat
    calls = {"n": 0}

    def flaky_stat(self, *args, **kwargs):
        if self.name == "b.bin":
            raise PermissionError("ACL changed mid-scan")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", flaky_stat)
    assert wardrobe_storage._directory_bytes(tmp_path) is None, (
        "stat() 失敗後仍回傳了部分總量——這會讓容量檢查以錯誤的小數字放行"
    )
    del calls


def test_directory_bytes_still_measures_a_healthy_tree(tmp_path) -> None:
    """正例：沒有失敗時要量到完整總量。"""
    from application import wardrobe_storage

    top_level_bytes = 1000
    nested_bytes = 500
    (tmp_path / "a.bin").write_bytes(b"x" * top_level_bytes)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.bin").write_bytes(b"x" * nested_bytes)
    assert wardrobe_storage._directory_bytes(tmp_path) == top_level_bytes + nested_bytes


def test_storage_guard_refuses_generation_when_usage_is_unmeasurable(
    tmp_path, monkeypatch
) -> None:
    """量測失敗 → 不放行，且理由要能被辨認。"""
    from datetime import UTC, datetime

    from application import wardrobe_storage

    outfit_store = tmp_path / "outfits"
    quarantine = tmp_path / "quarantine"
    outfit_store.mkdir()
    quarantine.mkdir()
    (quarantine / "job" ).mkdir()
    (quarantine / "job" / "blob.bin").write_bytes(b"x" * 10)
    monkeypatch.setattr(wardrobe_storage, "_directory_bytes", lambda root: None)

    guard = wardrobe_storage.WardrobeStorageGuard(outfit_store, quarantine)
    status = guard.inspect(datetime.now(UTC), None, special_occasion=True)
    assert status.allowed is False
    assert status.reason == "storage-unmeasurable"


def test_storage_guard_still_allows_when_measurement_succeeds(tmp_path) -> None:
    """正例：健康狀態下 ready 仍要放行。"""
    from datetime import UTC, datetime

    from application import wardrobe_storage

    outfit_store = tmp_path / "outfits"
    quarantine = tmp_path / "quarantine"
    outfit_store.mkdir()
    quarantine.mkdir()
    guard = wardrobe_storage.WardrobeStorageGuard(outfit_store, quarantine)
    status = guard.inspect(datetime.now(UTC), None, special_occasion=True)
    assert status.allowed is True
    assert status.reason == "ready"


# ── 2) 背景 worker 失敗要浮上來 ───────────────────────────────────────────

class _BrokenWorker:
    worker_id = "diagnostic-report"
    interval_seconds = 1.0

    def poll(self):
        raise PermissionError("report locked by ACL")


class _QuietWorker:
    worker_id = "quiet"
    interval_seconds = 1.0

    def poll(self):
        return []


def _scheduler_with_done_future(worker, exc: BaseException | None):
    from application.background_agents import ManagerWorkerScheduler

    scheduler = ManagerWorkerScheduler((worker,), clock=lambda: 1000.0)
    future: Future = Future()
    if exc is None:
        future.set_result([])
    else:
        future.set_exception(exc)
    scheduler._futures[worker.worker_id] = future
    return scheduler


def test_worker_failure_surfaces_as_an_observation() -> None:
    """worker 拋錯時 drain() 不得回傳空清單。"""
    scheduler = _scheduler_with_done_future(_BrokenWorker(), PermissionError("locked"))
    delivered = scheduler.drain()
    assert delivered, "worker 失敗被吞掉，drain() 回傳 []，與『沒有事件』無法區分"
    observation = delivered[0]
    assert observation.worker_id == "diagnostic-report"
    assert observation.event_key == "worker-failed"
    assert observation.metadata.get("status") == "failed"
    assert observation.metadata.get("error") == "PermissionError"


def test_quiet_worker_still_yields_nothing() -> None:
    """正例：真的沒有事件時仍要回傳空清單，不得憑空製造觀察。"""
    scheduler = _scheduler_with_done_future(_QuietWorker(), None)
    assert scheduler.drain() == []


def test_worker_failure_is_deduplicated_like_any_other_event() -> None:
    """失敗走同一條去重與冷卻：連續兩次 drain 不會重複打擾使用者。"""
    scheduler = _scheduler_with_done_future(_BrokenWorker(), PermissionError("locked"))
    assert scheduler.drain()
    scheduler._futures["diagnostic-report"] = _scheduler_with_done_future(
        _BrokenWorker(), PermissionError("locked")
    )._futures["diagnostic-report"]
    assert scheduler.drain() == [], "同一個失敗在冷卻期內被重複送出"


# ── 3) 服裝稽核檢查每一層 ─────────────────────────────────────────────────

def _png(width: int, height: int, alpha: int, coverage: float = 1.0) -> bytes:
    """最小 RGBA PNG。alpha 只塗在左上角 coverage 比例的區塊，其餘全透明。

    稽核數的是非零 alpha 像素數：一張「合格的服裝層」必須大部分透明。
    第一版夾具把每個像素都塗成 alpha 40，全幅非零，於是合格層被判 overbroad
    ——那是夾具不像真實資產，不是產品誤判。
    """
    rows = max(1, int(height * coverage))
    cols = max(1, int(width * coverage))
    painted = bytes([200, 200, 200, alpha]) * cols + bytes(4) * (width - cols)
    clear = bytes(4) * width
    raw = b"".join(
        b"\x00" + (painted if y < rows else clear) for y in range(height)
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _manifest(view_id: str, layers: list[str]) -> dict[str, object]:
    return {
        "looks": [
            {
                "variants": [
                    {
                        "poses": {
                            view_id: [
                                {"slot": f"layer{i}", "path": path}
                                for i, path in enumerate(layers)
                            ]
                        }
                    }
                ]
            }
        ]
    }


def test_auditor_inspects_every_layer_not_only_the_first(tmp_path) -> None:
    """第一層合格、第二層 Alpha 全不透明——舊稽核放行，新稽核必須擋。"""
    from integrations.openai_outfit_generator import (
        HALF_SIZE,
        GeneratedOutfitImageAuditor,
    )

    view_id = "cheek-rest"  # 半身視角，避開需要專案根目錄的臉部遮罩檢查
    width, height = HALF_SIZE
    source = tmp_path / "source" / "assets"
    source.mkdir(parents=True)
    (source / "good.png").write_bytes(_png(width, height, alpha=200, coverage=0.3))
    (source / "opaque.png").write_bytes(_png(width, height, alpha=255))

    auditor = GeneratedOutfitImageAuditor(project_root=None)
    issues = auditor.audit(
        tmp_path,
        _manifest(view_id, ["assets/good.png", "assets/opaque.png"]),
    )
    assert any(issue.endswith(":layer1:overbroad-alpha") for issue in issues), (
        f"第二層 100% 不透明卻未被標記：{issues}"
    )
    assert not any(issue.endswith(":layer0:overbroad-alpha") for issue in issues), (
        "合格的第一層被誤判"
    )


def test_single_layer_issue_ids_are_unchanged(tmp_path) -> None:
    """正例：單層 pose 的 issue id 維持原格式，不影響既有消費者。"""
    from integrations.openai_outfit_generator import (
        HALF_SIZE,
        GeneratedOutfitImageAuditor,
    )

    view_id = "cheek-rest"
    width, height = HALF_SIZE
    source = tmp_path / "source" / "assets"
    source.mkdir(parents=True)
    (source / "opaque.png").write_bytes(_png(width, height, alpha=255))

    issues = GeneratedOutfitImageAuditor(project_root=None).audit(
        tmp_path, _manifest(view_id, ["assets/opaque.png"])
    )
    assert f"garment:{view_id}:overbroad-alpha" in issues
    assert not any(":layer0:" in issue for issue in issues)


# ── 4) 稽核 payload 遮罩 ──────────────────────────────────────────────────

def test_audit_redacts_clipboard_text_but_keeps_shape() -> None:
    from application.flagship_action_runtime import redact_audit_payload

    secret = "sk-live-" + "a" * 200
    payload = {
        "plan_id": "p1",
        "request": {"capability": "clipboard_write", "arguments": {"text": secret}},
        "result": {"success": True, "data": {"text": secret}},
    }
    redacted = redact_audit_payload(payload)
    flat = repr(redacted)
    assert secret not in flat, "剪貼簿全文仍原樣進入稽核紀錄"
    assert "sk-live-" in flat, "遮罩後應保留短預覽，否則稽核失去可讀性"
    assert "208 chars" in flat, "遮罩後應保留長度"
    assert redacted["plan_id"] == "p1"
    assert redacted["request"]["capability"] == "clipboard_write"
    assert redacted["result"]["success"] is True


def test_audit_redaction_leaves_non_sensitive_fields_alone() -> None:
    """正例：路徑、能力名稱、布林值等必須原樣保留。"""
    from application.flagship_action_runtime import redact_audit_payload

    payload = {"capability": "open_folder", "arguments": {"path": "D:/x"}, "ok": True}
    assert redact_audit_payload(payload) == payload


def test_plan_started_and_action_result_both_go_through_redaction() -> None:
    """兩個稽核入口都要遮罩：clipboard_write 的文字在 plan_started 就出現了。"""
    import inspect

    from application import flagship_action_runtime as module

    source = inspect.getsource(module)
    assert 'self.audit("plan_started", redact_audit_payload(' in source
    record = source.split("def _record_result", 1)[1].split("def ", 1)[0]
    redacted_fields = 2  # request 與 result
    assert record.count("redact_audit_payload(") == redacted_fields, (
        "request 與 result 都必須經過遮罩"
    )
