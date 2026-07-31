from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from flagship_core import ActionRequest, ActionResult


HIGH_RISK_DOMAINS = {"lock", "alarm_control_panel"}
HEAT_DOMAINS = {"climate", "water_heater"}
ALLOWED_SERVICES = {
    "light": {"turn_on", "turn_off", "toggle"},
    "switch": {"turn_on", "turn_off", "toggle"},
    "fan": {"turn_on", "turn_off", "toggle", "set_percentage"},
    "cover": {"open_cover", "close_cover", "stop_cover"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
    "climate": {"turn_on", "turn_off", "set_temperature", "set_hvac_mode"},
    "media_player": {
        "turn_on",
        "turn_off",
        "media_play",
        "media_pause",
        "volume_set",
    },
}


@dataclass(slots=True)
class HomeAssistantConfig:
    base_url: str
    token: str
    timeout_seconds: float = 8.0
    verify_tls: bool = True


class HomeAssistantError(RuntimeError):
    pass


class HomeAssistantClient:
    def __init__(self, config: HomeAssistantConfig):
        parsed = urllib.parse.urlparse(config.base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Home Assistant 位址必須是完整 HTTP(S) 網址")
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
            "homeassistant.local",
        } and not self._is_private_host(parsed.hostname or ""):
            raise ValueError("非區域網路的 Home Assistant 必須使用 HTTPS")
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    @staticmethod
    def _is_private_host(host: str) -> bool:
        parts = host.split(".")
        if len(parts) != 4 or not all(part.isdigit() for part in parts):
            return False
        values = [int(part) for part in parts]
        return (
            values[0] == 10
            or values[:2] == [192, 168]
            or values[0] == 172
            and 16 <= values[1] <= 31
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = (
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        )
        request = urllib.request.Request(
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
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
                context=context,
            ) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise HomeAssistantError(
                f"Home Assistant HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise HomeAssistantError(f"無法連線 Home Assistant：{exc.reason}") from exc

    def health(self) -> bool:
        response = self._request("GET", "/api/")
        return isinstance(response, dict) and response.get("message") == "API running."

    def states(self) -> list[dict[str, Any]]:
        response = self._request("GET", "/api/states")
        if not isinstance(response, list):
            raise HomeAssistantError("Home Assistant 狀態格式錯誤")
        return [row for row in response if isinstance(row, dict)]

    def state(self, entity_id: str) -> dict[str, Any]:
        self.validate_entity(entity_id)
        response = self._request("GET", f"/api/states/{entity_id}")
        if not isinstance(response, dict):
            raise HomeAssistantError("找不到裝置狀態")
        return response

    @staticmethod
    def validate_entity(entity_id: str) -> tuple[str, str]:
        if "." not in entity_id:
            raise ValueError("裝置必須使用 domain.entity 格式")
        domain, name = entity_id.split(".", 1)
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
        if not domain or not name or any(ch not in allowed for ch in domain + name):
            raise ValueError("裝置識別碼格式不安全")
        return domain, name

    def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
    ) -> Any:
        allowed = ALLOWED_SERVICES.get(domain, set())
        if service not in allowed:
            raise PermissionError(f"不允許的 Home Assistant 服務：{domain}.{service}")
        entity_id = str(data.get("entity_id", ""))
        actual_domain, _name = self.validate_entity(entity_id)
        if actual_domain != domain:
            raise ValueError("服務領域與裝置不一致")
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
            raise ValueError("Home Assistant 參數必須是物件")
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
        return expected is None or current.get("state") == expected


def classify_home_capability(domain: str, service: str) -> str:
    if domain in HIGH_RISK_DOMAINS:
        return "home_lock" if domain == "lock" else "home_alarm"
    if domain in HEAT_DOMAINS and service not in {"turn_off"}:
        return "home_heat"
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
        if battery_value < 20:
            issues.append(
                {
                    "severity": "warning" if battery_value >= 10 else "critical",
                    "entity_id": entity_id,
                    "message": f"{name} 電量只剩 {battery_value:g}%",
                }
            )
    return issues
