from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import threading
lazy import time
lazy import webbrowser
lazy from collections.abc import Callable
lazy from dataclasses import asdict, dataclass, field
lazy from enum import IntEnum
lazy from pathlib import Path
lazy from typing import Any
lazy from urllib.parse import urlparse

lazy from platform_contracts import PlatformServicePort
lazy from platform_services import current_platform_services
lazy from safe_error import sanitize_error
lazy from time_utils import local_wall_time


class RiskLevel(IntEnum):
    GREEN = 1
    BLUE = 2
    YELLOW = 3
    RED = 4


RISK_NAMES = frozendict({
    RiskLevel.GREEN: "低風險",
    RiskLevel.BLUE: "一般變更",
    RiskLevel.YELLOW: "外部影響",
    RiskLevel.RED: "高風險",
})


CAPABILITY_RISK: frozendict[str, RiskLevel] = frozendict({
    "read_status": RiskLevel.GREEN,
    "search_local": RiskLevel.GREEN,
    "open_web": RiskLevel.GREEN,
    "open_folder": RiskLevel.GREEN,
    "launch_app": RiskLevel.BLUE,
    "window_list": RiskLevel.GREEN,
    "window_activate": RiskLevel.BLUE,
    "clipboard_read": RiskLevel.GREEN,
    "clipboard_write": RiskLevel.BLUE,
    "create_file": RiskLevel.BLUE,
    "rename_file": RiskLevel.BLUE,
    "move_file": RiskLevel.BLUE,
    "calendar_create": RiskLevel.YELLOW,
    "calendar_update": RiskLevel.YELLOW,
    "calendar_read": RiskLevel.GREEN,
    "email_read": RiskLevel.GREEN,
    "email_send": RiskLevel.YELLOW,
    "cloud_file_read": RiskLevel.GREEN,
    "cloud_file_write": RiskLevel.YELLOW,
    "publish_external": RiskLevel.YELLOW,
    "home_read": RiskLevel.GREEN,
    "home_control": RiskLevel.BLUE,
    "home_lock": RiskLevel.RED,
    "home_alarm": RiskLevel.RED,
    "home_heat": RiskLevel.RED,
    "camera_view": RiskLevel.YELLOW,
    "remote_screen": RiskLevel.YELLOW,
    "remote_file_read": RiskLevel.YELLOW,
    "remote_file_write": RiskLevel.RED,
    "delete_file": RiskLevel.RED,
    "shutdown_pc": RiskLevel.RED,
})


NEVER_AUTOMATE = frozenset({
    "purchase",
    "payment",
    "password_export",
    "disable_security",
    "arbitrary_shell",
    "administrator_shell",
    "home_alarm_disable",
    "home_unlock_unattended",
})


UNTRUSTED_INSTRUCTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*prompt",
    r"developer\s*message",
    r"reveal\s+(the\s+)?(?:password|token|secret|api\s*key)",
    r"bypass\s+(?:permission|confirmation|security)",
    r"忽略.{0,8}(?:先前|以上|系統).{0,8}(?:指示|規則|提示)",
    r"(?:顯示|洩漏|輸出).{0,8}(?:密碼|權杖|金鑰|系統提示詞)",
    r"(?:略過|繞過|停用).{0,8}(?:權限|確認|安全)",
)


@dataclass(slots=True)
class ActionRequest:
    capability: str
    description: str
    arguments: dict[str, Any] = field(default_factory=dict)
    source: str = "local"
    request_id: str = ""
    reversible: bool = False

    def __post_init__(self) -> None:
        if not self.request_id:
            payload = json.dumps(
                {
                    "capability": self.capability,
                    "description": self.description,
                    "arguments": self.arguments,
                    "source": self.source,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            stamp = f"{time.time_ns()}:{payload}".encode()
            self.request_id = hashlib.sha256(stamp).hexdigest()[:24]


@dataclass(slots=True)
class ActionPlan:
    title: str
    steps: list[ActionRequest]
    plan_id: str = ""
    created_at: str = field(
        default_factory=lambda: local_wall_time().isoformat(timespec="seconds")
    )

    def __post_init__(self) -> None:
        if not self.plan_id:
            seed = f"{self.created_at}:{self.title}:{len(self.steps)}"
            self.plan_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "steps": [asdict(step) for step in self.steps],
        }


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    risk: RiskLevel
    confirmation_count: int
    reason: str


@dataclass(slots=True)
class ActionResult:
    request_id: str
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    cancelled: bool = False


def contains_untrusted_instruction(text: str) -> bool:
    collapsed = re.sub(r"\s+", " ", str(text)).strip()
    return any(
        re.search(pattern, collapsed, re.IGNORECASE)
        for pattern in UNTRUSTED_INSTRUCTION_PATTERNS
    )


def sanitize_external_content(text: str, limit: int = 12000) -> str:
    value = str(text)[:limit]
    if contains_untrusted_instruction(value):
        return (
            "[偵測到外部內容試圖影響工具權限；已將其視為不可信資料。]\n"
            + value
        )
    return value


class PolicyEngine:
    """Central authorization boundary for local, cloud and remote tools."""

    def __init__(
        self,
        permissions: dict[str, str] | None = None,
        *,
        protected_paths: list[str] | None = None,
    ):
        self.permissions = dict(permissions or {})
        self.protected_paths = [
            Path(value).resolve()
            for value in (protected_paths or [])
            if str(value).strip()
        ]

    def permission_mode(self, capability: str) -> str:
        risk = CAPABILITY_RISK.get(capability, RiskLevel.RED)
        fallback = {
            RiskLevel.GREEN: "允許",
            RiskLevel.BLUE: "每次詢問",
            RiskLevel.YELLOW: "每次詢問",
            RiskLevel.RED: "禁止",
        }[risk]
        return str(self.permissions.get(capability, fallback))

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        capability = request.capability
        risk = CAPABILITY_RISK.get(capability, RiskLevel.RED)
        if capability in NEVER_AUTOMATE:
            return PolicyDecision(False, RiskLevel.RED, 0, "此能力永不允許自動執行")
        if request.source not in {"local", "voice", "workflow", "schedule", "remote"}:
            return PolicyDecision(False, RiskLevel.RED, 0, "未知的指令來源")
        if self._touches_protected_path(request):
            return PolicyDecision(False, RiskLevel.RED, 0, "目標位於受保護路徑")
        mode = self.permission_mode(capability)
        if mode == "禁止":
            return PolicyDecision(False, risk, 0, "權限設定為禁止")
        confirmations = 0
        if mode == "每次詢問":
            confirmations = 1
        if risk >= RiskLevel.YELLOW:
            confirmations = max(confirmations, 1)
        if risk == RiskLevel.RED:
            confirmations = 2
        if request.source == "remote":
            confirmations = max(confirmations, 1)
        return PolicyDecision(True, risk, confirmations, "通過本機權限政策")

    def _touches_protected_path(self, request: ActionRequest) -> bool:
        for key in ("path", "source", "destination", "folder"):
            raw = request.arguments.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            try:
                target = Path(raw).expanduser().resolve()
            except (OSError, RuntimeError):
                return True
            for protected in self.protected_paths:
                if target == protected or protected in target.parents:
                    return True
        return False


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
        with self._lock:
            targets = (
                [self._events[plan_id]]
                if plan_id and plan_id in self._events
                else list(self._events.values())
            )
            for event in targets:
                event.set()

    def finish(self, plan_id: str) -> None:
        with self._lock:
            self._events.pop(plan_id, None)


Handler = Callable[[ActionRequest], ActionResult]
Verifier = Callable[[ActionRequest, ActionResult], bool]
Confirm = Callable[[ActionRequest, PolicyDecision, int], bool]
Audit = Callable[[str, dict[str, Any]], None]


class ActionExecutor:
    """Sequential, cancellable and auditable plan execution."""

    def __init__(
        self,
        policy: PolicyEngine,
        *,
        confirm: Confirm | None = None,
        audit: Audit | None = None,
    ):
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

    def execute(self, plan: ActionPlan) -> list[ActionResult]:
        cancel_event = self.cancellations.begin(plan.plan_id)
        self.audit("plan_started", plan.to_dict())
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
            return ActionResult(
                request.request_id,
                False,
                "尚未安裝此工具的執行器",
            )
        handler, verifier = registered
        handler_error: Exception | None = None
        try:
            result = handler(request)
            self._verify_result(request, result, verifier)
        except Exception as exc:  # noqa: BLE001 -- tool boundary
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
                "request": asdict(request),
                "result": asdict(result),
            },
        )


class WindowsToolbox:
    """Small, explicit Windows tool surface; never executes arbitrary shell."""

    def __init__(
        self,
        *,
        allowed_folders: list[str] | None = None,
        allowed_apps: dict[str, str] | None = None,
        allowed_websites: list[str] | None = None,
        platform_services: PlatformServicePort | None = None,
    ):
        self.platform_services = (
            platform_services or current_platform_services()
        )
        self.allowed_folders = [
            Path(value).expanduser().resolve()
            for value in (allowed_folders or [])
            if str(value).strip()
        ]
        self.allowed_apps = {
            name.casefold(): str(Path(path).expanduser().resolve())
            for name, path in (allowed_apps or {}).items()
            if name.strip() and str(path).strip()
        }
        self.allowed_websites = [
            value.rstrip("/")
            for value in (allowed_websites or [])
            if str(value).strip()
        ]

    def register_with(self, executor: ActionExecutor) -> None:
        executor.register("open_web", self.open_web)
        executor.register("open_folder", self.open_folder)
        executor.register("launch_app", self.launch_app)
        executor.register("search_local", self.search_local)
        executor.register("create_file", self.create_file, self.verify_file)
        executor.register("rename_file", self.rename_file, self.verify_destination)
        executor.register("move_file", self.move_file, self.verify_destination)

    def _allowed_path(self, raw: str, *, must_exist: bool = False) -> Path:
        if not self.allowed_folders:
            raise PermissionError("尚未設定允許操作的資料夾")
        target = Path(raw).expanduser().resolve()
        if not any(root == target or root in target.parents for root in self.allowed_folders):
            raise PermissionError("路徑不在允許清單內")
        if must_exist and not target.exists():
            raise FileNotFoundError(target)
        return target

    def open_web(self, request: ActionRequest) -> ActionResult:
        value = str(request.arguments.get("url", "")).strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("只允許完整的 HTTP 或 HTTPS 網址")
        if not self.allowed_websites:
            raise PermissionError("尚未設定允許開啟的網站")
        allowed = False
        for entry in self.allowed_websites:
            allowed_parsed = urlparse(entry)
            if (
                allowed_parsed.scheme in {"http", "https"}
                and parsed.hostname == allowed_parsed.hostname
                and (
                    parsed.path or "/"
                ).startswith(allowed_parsed.path or "/")
            ):
                allowed = True
                break
        if not allowed:
            raise PermissionError("網址不在允許清單內")
        opened = webbrowser.open(value, new=2)
        return ActionResult(request.request_id, bool(opened), "已開啟網站")

    def open_folder(self, request: ActionRequest) -> ActionResult:
        target = self._allowed_path(
            str(request.arguments.get("path", "")),
            must_exist=True,
        )
        if not target.is_dir():
            raise NotADirectoryError(target)
        self.platform_services.open_path(target)
        return ActionResult(request.request_id, True, f"已開啟資料夾：{target}")

    def launch_app(self, request: ActionRequest) -> ActionResult:
        name = str(request.arguments.get("name", "")).strip().casefold()
        target = self.allowed_apps.get(name)
        if not target:
            raise PermissionError("程式不在允許清單內")
        if not Path(target).is_file():
            raise FileNotFoundError(target)
        self.platform_services.open_path(Path(target))
        return ActionResult(request.request_id, True, f"已啟動：{name}")

    def create_file(self, request: ActionRequest) -> ActionResult:
        target = self._allowed_path(str(request.arguments.get("path", "")))
        if target.exists():
            raise FileExistsError("預設禁止覆寫既有檔案")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(request.arguments.get("content", ""))
        target.write_text(content, encoding="utf-8")
        return ActionResult(
            request.request_id,
            True,
            f"已建立檔案：{target.name}",
            {"path": str(target), "size": target.stat().st_size},
        )

    def search_local(self, request: ActionRequest) -> ActionResult:
        query = str(request.arguments.get("query", "")).strip().casefold()
        if not query:
            raise ValueError("搜尋文字不可留空")
        results: list[dict[str, Any]] = []
        for root in self.allowed_folders:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if len(results) >= 200:
                    break
                try:
                    relative = path.relative_to(root)
                except ValueError:
                    continue
                if query not in path.name.casefold():
                    continue
                results.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "relative": str(relative),
                        "is_file": path.is_file(),
                    }
                )
        return ActionResult(
            request.request_id,
            True,
            f"找到 {len(results)} 個符合項目",
            {"results": results, "truncated": len(results) >= 200},
        )

    def rename_file(self, request: ActionRequest) -> ActionResult:
        return self._relocate(request)

    def move_file(self, request: ActionRequest) -> ActionResult:
        return self._relocate(request)

    def _relocate(self, request: ActionRequest) -> ActionResult:
        source = self._allowed_path(
            str(request.arguments.get("source", "")),
            must_exist=True,
        )
        destination = self._allowed_path(
            str(request.arguments.get("destination", ""))
        )
        if destination.exists():
            raise FileExistsError("目的地已存在，預設禁止覆寫")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        return ActionResult(
            request.request_id,
            True,
            f"已移動至：{destination}",
            {"source": str(source), "destination": str(destination)},
        )

    @staticmethod
    def verify_file(_request: ActionRequest, result: ActionResult) -> bool:
        raw = result.data.get("path")
        return isinstance(raw, str) and Path(raw).is_file()

    @staticmethod
    def verify_destination(
        _request: ActionRequest,
        result: ActionResult,
    ) -> bool:
        destination = result.data.get("destination")
        source = result.data.get("source")
        return (
            isinstance(destination, str)
            and Path(destination).exists()
            and isinstance(source, str)
            and not Path(source).exists()
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
    if len(raw_steps) > 25:
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
