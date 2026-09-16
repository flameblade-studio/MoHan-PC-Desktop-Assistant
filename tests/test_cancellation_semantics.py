"""取消操作精確停止指定計畫，緊急停止涵蓋所有執行中的付費工作。

2026-09-02 稽核發現三項需驗證的行為：
1. 同秒、同名、同步數的計畫，各自使用唯一 plan_id。
2. 取消已完成或查無資料的 plan_id，保留其他執行中的計畫。
3. emergency_stop_requested 連接到換裝批次的取消接收者，讓剩餘
   視角呼叫及實際付費操作一起停止。

各測試重現原始觸發條件，再驗證修正後的行為。
"""
from __future__ import annotations

lazy import inspect
lazy import threading


def test_plan_ids_are_unique_within_the_same_second() -> None:
    """同秒、同標題、同步數的兩個計畫，各自使用唯一識別碼。

    舊 seed（created_at + title + len(steps)）在此情形會碰撞。
    """
    from domain.flagship_action_models import ActionPlan

    stamp = "2026-09-02T03:04:05"
    first = ActionPlan(title="整理下載", steps=[], created_at=stamp)
    second = ActionPlan(title="整理下載", steps=[], created_at=stamp)
    assert first.plan_id != second.plan_id, (
        "同一秒建立的同名同步數計畫共用了 plan_id；取消會落到錯的計畫上"
    )
    assert first.plan_id and second.plan_id


def test_cancelling_an_unknown_plan_leaves_running_plans_alone() -> None:
    """取消已完成或查無資料的計畫時，保持正在執行的計畫。"""
    from application.flagship_action_runtime import CancellationRegistry

    registry = CancellationRegistry()
    running = registry.begin("plan-A")
    registry.cancel("plan-Z-already-finished")
    assert not running.is_set(), (
        "未知的 plan_id 取消了正在執行的計畫——這會在使用者取消舊通知時"
        "中止他正在等待的工作"
    )


def test_cancelling_a_known_plan_cancels_only_that_plan() -> None:
    from application.flagship_action_runtime import CancellationRegistry

    registry = CancellationRegistry()
    first = registry.begin("plan-A")
    second = registry.begin("plan-B")
    registry.cancel("plan-A")
    assert first.is_set()
    assert not second.is_set(), "具名取消波及了另一個計畫"


def test_cancel_without_an_identifier_still_stops_everything() -> None:
    """緊急停止仍須完整停止全部計畫。"""
    from application.flagship_action_runtime import CancellationRegistry

    registry = CancellationRegistry()
    events = [registry.begin(f"plan-{index}") for index in range(3)]
    registry.cancel()
    assert all(event.is_set() for event in events), "緊急停止未能停下全部計畫"


def test_default_cancellation_query_never_cancels() -> None:
    """忘了接線的後果必須是「照舊執行」，不是「全部靜默中止」。"""
    from application.self_generating_wardrobe import _never_cancelled

    assert _never_cancelled() is False


def test_generation_checks_cancellation_before_each_paid_view() -> None:
    """取消必須檢查在付費呼叫之前，否則停手也已經扣過款。"""
    # 2026-09-02 第 2 發重驗後改成行為測試：數實際的付費呼叫次數，
    # 而不是搜尋原始碼字串。一開始就已取消 → 零次付費呼叫。
    import types

    import pytest

    from integrations import openai_outfit_generator as gen

    generator = object.__new__(gen.OpenAIOutfitDraftGenerator)
    generator._root = None
    paid = {"n": 0}

    def fake_edit(self, *_edit_arguments):
        paid["n"] += 1
        return b"image"

    generator._checkpointed_edit = types.MethodType(fake_edit, generator)
    generator._design_prompt = lambda request, trends: "design"
    generator._view_prompt = lambda design, view_id, target: "view"
    generator._handheld_prompt = lambda request, view_id, target: "handheld"
    request = types.SimpleNamespace(requested_categories=frozenset({"garment"}))
    with pytest.raises(gen.OutfitGenerationCancelled):
        generator.create(request, (), ("yaw+000-pitch+00",), cancelled=lambda: True)
    assert paid["n"] == 0, "已取消仍送出了付費呼叫"


def test_emergency_stop_is_connected_to_the_generation_controller() -> None:
    """emergency_stop_requested 須連接實際取消接收者。

    舊流程僅 emit 訊號就顯示中止，此測試驗證接收端確實連接。
    """
    from presentation import companion_window

    source = inspect.getsource(companion_window)
    assert "emergency_stop_requested.connect(" in source, (
        "緊急停止訊號仍然沒有接收者"
    )
    connection = source.split("emergency_stop_requested.connect(", 1)[1][:200]
    assert "abort" in connection, "緊急停止接到的不是換裝批次的中止入口"


def test_worker_reports_user_cancellation_apart_from_failure() -> None:
    """使用者主動取消保留取消狀態，並維持下一次生成的可用性。"""
    from presentation import autonomous_outfit_generation_controller as module

    source = inspect.getsource(module)
    assert "cancelled = Signal()" in source
    run_body = source.split("def run(self)", 1)[1].split("def ", 1)[0]
    assert "OutfitGenerationCancelled" in run_body
    cancelled_handler = source.split("def _cancelled(self)", 1)[1].split("def ", 1)[0]
    # 先移除註解再比對實作：初版斷言曾把 LAST_ATTEMPT_KEY 的說明文字
    # 一起納入，造成誤判。此處只檢查實際程式碼。
    code_only = " ".join(
        line.split("#", 1)[0] for line in cancelled_handler.splitlines()
    )
    assert "LAST_ATTEMPT_KEY" not in code_only, (
        '使用者主動取消須保持取消狀態及可用的下一次生成'
    )


def test_cancellation_event_is_cleared_when_generation_restarts() -> None:
    """abort() 之後控制器仍要能再次生成，否則停手一次就永久停用。"""
    from presentation import autonomous_outfit_generation_controller as module

    source = inspect.getsource(module)
    start_body = source.split("def start(self)", 1)[1].split("def ", 1)[0]
    assert "_cancel.clear()" in start_body, (
        "start() 沒有清除取消旗標，abort 之後的生成會立刻被判為取消"
    )


def test_registry_is_thread_safe_under_concurrent_begin_and_cancel() -> None:
    """begin 與 cancel 的跨執行緒呼叫維持同步與一致狀態。"""
    from application.flagship_action_runtime import CancellationRegistry

    registry = CancellationRegistry()
    errors: list[BaseException] = []

    def churn(index: int) -> None:
        try:
            for round_index in range(50):
                name = f"plan-{index}-{round_index}"
                registry.begin(name)
                registry.cancel(name)
                registry.finish(name)
        except BaseException as error:  # noqa: BLE001 - 回報給主執行緒
            errors.append(error)

    threads = [threading.Thread(target=churn, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors, f"併發下發生例外：{errors[:2]}"
