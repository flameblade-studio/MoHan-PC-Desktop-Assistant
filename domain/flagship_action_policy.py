"""Pure authorization policy for flagship actions."""

from __future__ import annotations

lazy from pathlib import Path

lazy from domain.flagship_action_models import (
    CAPABILITY_RISK,
    NEVER_AUTOMATE,
    ActionRequest,
    PolicyDecision,
    RiskLevel,
)

__all__ = ("PolicyEngine",)


# 合法的權限模式。不在此集合內的值一律視為損壞，退回風險預設。
PERMISSION_MODES = frozenset({"允許", "每次詢問", "禁止"})

class PolicyEngine:
    """Evaluate local, cloud, and remote actions without performing I/O."""

    def __init__(
        self,
        permissions: dict[str, str] | None = None,
        *,
        protected_paths: list[str] | None = None,
    ) -> None:
        self.permissions = dict(permissions or {})
        self.protected_paths = [
            Path(value).resolve()
            for value in (protected_paths or [])
            if str(value).strip()
        ]

    def permission_mode(self, capability: str) -> str:
        """該能力的權限模式。未知值一律退回風險預設，不得 fail-open。"""
        risk = CAPABILITY_RISK.get(capability, RiskLevel.RED)
        fallback = {
            RiskLevel.GREEN: "允許",
            RiskLevel.BLUE: "每次詢問",
            RiskLevel.YELLOW: "每次詢問",
            RiskLevel.RED: "禁止",
        }[risk]
        mode = str(self.permissions.get(capability, fallback))
        # 未知字串必須 fail-closed，退回依風險等級決定的預設值。
        # 先前直接原樣回傳，而 evaluate() 只封鎖精確字串「禁止」——於是
        # 任何損壞值（設定匯入、版本遷移、手動編輯、DB 損壞）都會得到
        # allowed=True 且 confirmations=0。GREEN 與 BLUE 能力因此免確認執行；
        # YELLOW/RED 靠風險等級的保底才沒事，那是巧合不是設計。
        if mode not in PERMISSION_MODES:
            return fallback
        return mode

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
        confirmations = 1 if mode == "每次詢問" else 0
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
            if any(
                target == protected or protected in target.parents
                for protected in self.protected_paths
            ):
                return True
        return False
