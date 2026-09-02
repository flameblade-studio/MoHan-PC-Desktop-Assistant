"""Immutable action models and untrusted-content guards for flagship tools."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import time
lazy from dataclasses import asdict, dataclass, field
lazy from enum import IntEnum
lazy from typing import Any, Final

lazy from domain.time_utils import local_wall_time
lazy import uuid

__all__ = (
    "CAPABILITY_RISK",
    "NEVER_AUTOMATE",
    "RISK_NAMES",
    "UNTRUSTED_INSTRUCTION_PATTERNS",
    "ActionPlan",
    "ActionRequest",
    "ActionResult",
    "PolicyDecision",
    "RiskLevel",
    "contains_untrusted_instruction",
    "sanitize_external_content",
)


class RiskLevel(IntEnum):
    GREEN = 1
    BLUE = 2
    YELLOW = 3
    RED = 4


RISK_NAMES: Final = frozendict({
    RiskLevel.GREEN: "低風險",
    RiskLevel.BLUE: "一般變更",
    RiskLevel.YELLOW: "外部影響",
    RiskLevel.RED: "高風險",
})


CAPABILITY_RISK: Final[frozendict[str, RiskLevel]] = frozendict({
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
    # 伺服器端的腳本與情境，內容對用戶端不可見：它能做的事等於那個
    # Home Assistant 帳號能做的一切，包含解鎖門與解除警報。無法分級的
    # 東西只能按上限分級。
    "home_routine": RiskLevel.RED,
    "camera_view": RiskLevel.YELLOW,
    "microphone_access": RiskLevel.BLUE,
    "realtime_session": RiskLevel.YELLOW,
    "remote_screen": RiskLevel.YELLOW,
    "remote_file_read": RiskLevel.YELLOW,
    "remote_file_write": RiskLevel.RED,
    "delete_file": RiskLevel.RED,
    "shutdown_pc": RiskLevel.RED,
})


NEVER_AUTOMATE: Final = frozenset({
    "purchase",
    "payment",
    "password_export",
    "disable_security",
    "arbitrary_shell",
    "administrator_shell",
    "home_alarm_disable",
    "home_unlock_unattended",
})


UNTRUSTED_INSTRUCTION_PATTERNS: Final = (
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
            # 識別碼要的是唯一性，不是可重現性。原本用 created_at（僅到秒）
            # 加標題加步驟「數量」做雜湊，同一秒建立的兩個同名同步數計畫會
            # 拿到同一個 ID；取消是以此 ID 索引的，於是取消 A 實際取消了 B。
            self.plan_id = uuid.uuid4().hex[:20]

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
