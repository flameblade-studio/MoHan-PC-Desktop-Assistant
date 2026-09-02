"""Cancellable execution and strict plan parsing for flagship actions."""

from __future__ import annotations

lazy import json
lazy import threading
lazy from collections.abc import Callable
lazy from dataclasses import asdict
lazy from typing import Any

lazy from domain.flagship_action_models import (
    CAPABILITY_RISK,
    ActionPlan,
    ActionRequest,
    ActionResult,
    PolicyDecision,
)
lazy from domain.flagship_action_policy import PolicyEngine
lazy from domain.safe_error import sanitize_error

__all__ = (
    "ActionExecutor",
    "CancellationRegistry",
    "parse_plan_json",
)

MAX_PLAN_STEPS = 25

Handler = Callable[[ActionRequest], ActionResult]
Verifier = Callable[[ActionRequest, ActionResult], bool]
Confirm = Callable[[ActionRequest, PolicyDecision, int], bool]
Audit = Callable[[str, dict[str, Any]], None]


# 稽核紀錄裡不該原樣保存的欄位。UI 只顯示摘要 500 字，資料庫卻存到
# 100,000 字；clipboard_read 把整段剪貼簿放進 result.data["text"]，
# clipboard_write 把要寫入的文字放進 request.arguments["text"]，兩者都以
# 未加密 JSON 進 SQLite，而 clear_audit_before() 沒有正式呼叫者，不是短期
# 環形紀錄。金鑰、密碼、私訊都可能在剪貼簿裡。
REDACTED_AUDIT_KEYS = frozenset(
    {"text", "content", "body", "password", "token", "secret"}
)
AUDIT_PREVIEW_CHARS = 64


def redact_audit_payload(value: object) -> object:
    """遞迴遮罩敏感欄位，只留長度與短預覽：稽核仍可讀，但不再是資料倉。"""
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if key in REDACTED_AUDIT_KEYS and isinstance(item, str):
                preview = item[:AUDIT_PREVIEW_CHARS]
                more = "..." if len(item) > AUDIT_PREVIEW_CHARS else ""
                redacted[key] = f"<redacted {len(item)} chars: {preview}{more}>"
            else:
                redacted[key] = redact_audit_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_audit_payload(item) for item in value]
    return value


class CancellationRegistry:
    def __init__(self) -> None:
        self._events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def begin(self, plan_id: str) -> threading.Event:
        with self._lock:
            event = threading.Event()
            self._events[plan_id] = event
            return event

    def cancel(self, plan_id: str | None = None) -> None:
        """取消一個計畫；只有不給 plan_id 才是全部取消（緊急停止）。

        原本「給了 plan_id 但它不在 registry 裡」會落到全部取消的分支：
        使用者從延遲通知按下取消一個**已完成**的計畫，正在執行的另一個
        計畫會被一起中止。找不到目標時，正確的行為是什麼都不做。
        """
        with self._lock:
            if plan_id is None:
                targets = list(self._events.values())
            else:
                event = self._events.get(plan_id)
                targets = [event] if event is not None else []
            for event in targets:
                event.set()

    def finish(self, plan_id: str) -> None:
        with self._lock:
            self._events.pop(plan_id, None)


class ActionExecutor:
    """Execute one plan sequentially through explicit policy and tool ports."""

    def __init__(
        self,
        policy: PolicyEngine,
        *,
        confirm: Confirm | None = None,
        audit: Audit | None = None,
    ) -> None:
        self.policy = policy
        self.confirm = confirm or (lambda _request, _decision, _index: False)
        self.audit = audit or (lambda _event, _payload: None)
        self.handlers: dict[str, tuple[Handler, Verifier | None]] = {}
        self.cancellations = CancellationRegistry()
        self._completed_ids: set[str] = set()

    def register(
        self,
        capability: str,
        handler: Handler,
        verifier: Verifier | None = None,
    ) -> None:
        self.handlers[capability] = (handler, verifier)

    def unregister(self, capability: str) -> None:
        """Remove a capability so a disabled integration cannot linger.

        Later plans that still request the capability receive the regular
        "尚未安裝此工具的執行器" failure instead of reaching a stale handler.
        """

        self.handlers.pop(capability, None)

    def execute(self, plan: ActionPlan) -> list[ActionResult]:
        cancel_event = self.cancellations.begin(plan.plan_id)
        self.audit("plan_started", redact_audit_payload(plan.to_dict()))
        results: list[ActionResult] = []
        try:
            for request in plan.steps:
                result = self._preflight_result(request, cancel_event)
                if result is None:
                    result = self._execute_handler(request)
                results.append(result)
                self._record_result(plan, request, result)
                if not result.success:
                    break
                self._completed_ids.add(request.request_id)
        finally:
            self.cancellations.finish(plan.plan_id)
            self.audit(
                "plan_finished",
                {
                    "plan_id": plan.plan_id,
                    "success": bool(results) and all(item.success for item in results),
                    "result_count": len(results),
                },
            )
        return results

    def _preflight_result(
        self,
        request: ActionRequest,
        cancel_event: threading.Event,
    ) -> ActionResult | None:
        if cancel_event.is_set():
            return ActionResult(
                request.request_id,
                False,
                "任務已由使用者取消",
                cancelled=True,
            )
        if request.request_id in self._completed_ids:
            return ActionResult(
                request.request_id,
                True,
                "重複請求已安全略過",
                verified=True,
            )
        decision = self.policy.evaluate(request)
        if not decision.allowed:
            return ActionResult(
                request.request_id,
                False,
                f"安全政策已阻擋：{decision.reason}",
            )
        if not self._confirm_request(request, decision):
            return ActionResult(
                request.request_id,
                False,
                "使用者未授權執行",
                cancelled=True,
            )
        return None

    def _confirm_request(
        self,
        request: ActionRequest,
        decision: PolicyDecision,
    ) -> bool:
        return all(
            self.confirm(request, decision, index)
            for index in range(1, decision.confirmation_count + 1)
        )

    def _execute_handler(self, request: ActionRequest) -> ActionResult:
        registered = self.handlers.get(request.capability)
        if registered is None:
            return ActionResult(request.request_id, False, "尚未安裝此工具的執行器")
        handler, verifier = registered
        handler_error: Exception | None = None
        try:
            result = handler(request)
            self._verify_result(request, result, verifier)
        except Exception as exc:
            handler_error = exc

        if handler_error is not None:
            safe_failure = str(sanitize_error(handler_error))
            del handler_error
            return ActionResult(
                request.request_id,
                False,
                f"工具執行失敗：{safe_failure}",
            )
        return result

    @staticmethod
    def _verify_result(
        request: ActionRequest,
        result: ActionResult,
        verifier: Verifier | None,
    ) -> None:
        if not result.success:
            return
        result.verified = bool(verifier(request, result)) if verifier else True
        if not result.verified:
            result.success = False
            result.message = "工具回報完成，但結果驗證未通過"

    def _record_result(
        self,
        plan: ActionPlan,
        request: ActionRequest,
        result: ActionResult,
    ) -> None:
        self.audit(
            "action_result",
            {
                "plan_id": plan.plan_id,
                "request": redact_audit_payload(asdict(request)),
                "result": redact_audit_payload(asdict(result)),
            },
        )


def parse_plan_json(value: str, *, source: str = "local") -> ActionPlan:
    """Parse model output without granting capabilities or trusting prose."""

    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise TypeError("任務計畫必須是 JSON 物件")
    title = str(payload.get("title", "")).strip()[:120]
    raw_steps = payload.get("steps")
    if not title:
        raise ValueError("任務計畫缺少標題")
    if not isinstance(raw_steps, list):
        raise TypeError("任務計畫步驟必須是陣列")
    if len(raw_steps) > MAX_PLAN_STEPS:
        raise ValueError("單一任務最多 25 個步驟")
    steps: list[ActionRequest] = []
    for raw in raw_steps:
        if not isinstance(raw, dict):
            raise TypeError("任務步驟格式錯誤")
        capability = str(raw.get("capability", "")).strip()
        description = str(raw.get("description", "")).strip()[:300]
        arguments = raw.get("arguments", {})
        if capability not in CAPABILITY_RISK:
            raise ValueError(f"不支援的能力：{capability}")
        if not description:
            raise ValueError("任務步驟缺少說明")
        if not isinstance(arguments, dict):
            raise TypeError("任務步驟參數必須是物件")
        steps.append(
            ActionRequest(
                capability,
                description,
                arguments,
                source=source,
                reversible=bool(raw.get("reversible", False)),
            )
        )
    return ActionPlan(title, steps)
