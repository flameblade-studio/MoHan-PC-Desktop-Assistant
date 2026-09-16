from __future__ import annotations

lazy import json
lazy import ssl
lazy from dataclasses import dataclass
lazy from typing import Any
lazy from urllib.error import HTTPError, URLError
lazy from urllib.parse import urlparse
lazy from urllib.request import Request, urlopen

lazy from domain.flagship_action_models import ActionRequest, ActionResult
lazy from domain.safe_error import sanitize_error

HIGH_RISK_DOMAINS = frozenset({"lock", "alarm_control_panel"})
HEAT_DOMAINS = frozenset({"climate", "water_heater"})
# 內容由服務端執行的網域：用戶端以例行作業能力處理它們。
OPAQUE_DOMAINS = frozenset({"script", "scene"})
IPV4_OCTET_COUNT = 4
PRIVATE_CLASS_A_FIRST_OCTET = 10
PRIVATE_CLASS_B_FIRST_OCTET = 172
PRIVATE_CLASS_B_SECOND_OCTET_MIN = 16
PRIVATE_CLASS_B_SECOND_OCTET_MAX = 31
LOW_BATTERY_THRESHOLD = 20
CRITICAL_BATTERY_THRESHOLD = 10
ALLOWED_SERVICES = frozendict({
    "light": frozenset({"turn_on", "turn_off", "toggle"}),
    "switch": frozenset({"turn_on", "turn_off", "toggle"}),
    "fan": frozenset({"turn_on", "turn_off", "toggle", "set_percentage"}),
    "cover": frozenset({"open_cover", "close_cover", "stop_cover"}),
    "scene": frozenset({"turn_on"}),
    "script": frozenset({"turn_on"}),
    "climate": frozenset({"turn_on", "turn_off", "set_temperature", "set_hvac_mode"}),
    "media_player": frozenset({
        "turn_on",
        "turn_off",
        "media_play",
        "media_pause",
        "volume_set",
    }),
})


@dataclass(slots=True)
class HomeAssistantConfig:
    base_url: str
    token: str
    timeout_seconds: float = 8.0
    verify_tls: bool = True


class HomeAssistantError(RuntimeError):
    pass


def _sanitized_external_error(
    error: BaseException | str,
    *,
    http_status: int | None = None,
) -> str:
    """Keep remote detail inside the service boundary after sanitization."""
    safe_input = UnicodeError() if isinstance(error, json.JSONDecodeError) else error
    return str(sanitize_error(safe_input, http_status=http_status))


class HomeAssistantClient:
    def __init__(self, config: HomeAssistantConfig):
        parsed = urlparse(config.base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("請輸入完整的 Home Assistant HTTP(S) 網址")
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
            "homeassistant.local",
        } and not self._is_private_host(parsed.hostname or ""):
            raise ValueError("遠端 Home Assistant 請使用 HTTPS；區域網路可使用 HTTP")
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    @staticmethod
    def _is_private_host(host: str) -> bool:
        parts = host.split(".")
        if len(parts) != IPV4_OCTET_COUNT or not all(part.isdigit() for part in parts):
            return False
        values = [int(part) for part in parts]
        return (
            values[0] == PRIVATE_CLASS_A_FIRST_OCTET
            or values[:2] == [192, 168]
            or values[0] == PRIVATE_CLASS_B_FIRST_OCTET
            and PRIVATE_CLASS_B_SECOND_OCTET_MIN <= values[1] <= PRIVATE_CLASS_B_SECOND_OCTET_MAX
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        request_failure: str | None = None
        try:
            data = (
                json.dumps(payload).encode("utf-8")
                if payload is not None
                else None
            )
            request = Request(
                f"{self.base_url}{path}",
                data=data,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.config.token}",
                    "Content-Type": "application/json",
                },
            )
            context = None
            if not self.config.verify_tls:
                context = ssl._create_unverified_context()
            with urlopen(
                request,
                timeout=self.config.timeout_seconds,
                context=context,
            ) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except (
            HTTPError,
            URLError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            request_failure = _sanitized_external_error(exc)
        raise HomeAssistantError(request_failure)

    def health(self) -> bool:
        response = self._request("GET", "/api/")
        return isinstance(response, dict) and response.get("message") == "API running."

    def states(self) -> list[dict[str, Any]]:
        response = self._request("GET", "/api/states")
        if not isinstance(response, list):
            raise HomeAssistantError("Home Assistant 狀態回應需要清單格式")
        return [row for row in response if isinstance(row, dict)]

    def state(self, entity_id: str) -> dict[str, Any]:
        self.validate_entity(entity_id)
        response = self._request("GET", f"/api/states/{entity_id}")
        if not isinstance(response, dict):
            raise HomeAssistantError("裝置狀態回應需要物件格式")
        # 代理或 API 回 200 + {} 時，完整欄位要求能讓畫面清楚區分
        # 真正讀到的 unknown 狀態與狀態資料待補的回應。
        if "entity_id" not in response or "state" not in response:
            raise HomeAssistantError("裝置狀態回應需要 entity_id 與 state 欄位")
        return response

    @staticmethod
    def validate_entity(entity_id: str) -> tuple[str, str]:
        if "." not in entity_id:
            raise ValueError("裝置請使用 domain.entity 格式")
        domain, name = entity_id.split(".", 1)
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
        if not domain or not name or any(ch not in allowed for ch in domain + name):
            raise ValueError("裝置識別碼請使用小寫英數與底線")
        return domain, name

    def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
    ) -> Any:
        allowed = ALLOWED_SERVICES.get(domain, set())
        if service not in allowed:
            raise PermissionError(
                f"請選擇允許清單中的 Home Assistant 服務：{domain}.{service}"
            )
        entity_id = str(data.get("entity_id", ""))
        actual_domain, _name = self.validate_entity(entity_id)
        if actual_domain != domain:
            raise ValueError("服務領域與裝置領域需要一致")
        return self._request("POST", f"/api/services/{domain}/{service}", data)

    def action_read(self, request: ActionRequest) -> ActionResult:
        entity_id = str(request.arguments.get("entity_id", ""))
        state = self.state(entity_id)
        return ActionResult(
            request.request_id,
            True,
            f"{entity_id}：{state.get('state', 'unknown')}",
            {"state": state},
        )

    def action_control(self, request: ActionRequest) -> ActionResult:
        domain = str(request.arguments.get("domain", ""))
        service = str(request.arguments.get("service", ""))
        data = request.arguments.get("data", {})
        if not isinstance(data, dict):
            raise TypeError("Home Assistant 參數必須是物件")
        response = self.call_service(domain, service, data)
        return ActionResult(
            request.request_id,
            True,
            f"已執行 {domain}.{service}",
            {"response": response, "entity_id": data.get("entity_id", "")},
        )

    def verify_control(
        self,
        request: ActionRequest,
        result: ActionResult,
    ) -> bool:
        entity_id = str(result.data.get("entity_id", ""))
        if not entity_id:
            return False
        current = self.state(entity_id)
        service = str(request.arguments.get("service", ""))
        expected = {"turn_on": "on", "turn_off": "off"}.get(service)
        if expected is None:
            # toggle、set_percentage、open_cover、scene.turn_on、script.turn_on
            # 需要各自的預期狀態才能完成比對。此處回傳 False，讓執行器
            # 清楚標示目前的結果尚待驗證；toggle 需要保留呼叫前狀態，
            # 相關資料流可在 action_control 擴充時補上。
            return False
        return current.get("state") == expected


def classify_home_capability(domain: str, service: str) -> str:
    if domain in HIGH_RISK_DOMAINS:
        return "home_lock" if domain == "lock" else "home_alarm"
    if domain in HEAT_DOMAINS and service != "turn_off":
        return "home_heat"
    if domain in OPAQUE_DOMAINS:
        # script.turn_on 與 scene.turn_on 的內容在伺服器上執行，
        # 用戶端以 home_routine 分類，讓可能包含 lock 或 alarm 動作的
        # 例行作業沿用高風險確認流程。
        return "home_routine"
    return "home_control"


def home_health_issues(states: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for row in states:
        entity_id = str(row.get("entity_id", ""))
        state = str(row.get("state", ""))
        attributes = row.get("attributes", {})
        if not isinstance(attributes, dict):
            attributes = {}
        name = str(attributes.get("friendly_name", entity_id))
        if state in {"unavailable", "unknown"}:
            issues.append(
                {
                    "severity": "warning",
                    "entity_id": entity_id,
                    "message": f"{name} 目前{state}",
                }
            )
        battery = attributes.get("battery_level")
        if battery is None and entity_id.startswith("sensor.") and entity_id.endswith(
            "_battery"
        ):
            battery = state
        try:
            battery_value = float(battery)
        except (TypeError, ValueError):
            continue
        if battery_value < LOW_BATTERY_THRESHOLD:
            issues.append(
                {
                    "severity": "warning" if battery_value >= CRITICAL_BATTERY_THRESHOLD else "critical",
                    "entity_id": entity_id,
                    "message": f"{name} 電量只剩 {battery_value:g}%",
                }
            )
    return issues
