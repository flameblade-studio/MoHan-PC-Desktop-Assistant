from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flagship_core import ActionPlan, ActionRequest, CAPABILITY_RISK


@dataclass(slots=True)
class Workflow:
    workflow_id: int | None
    name: str
    enabled: bool
    trigger: dict[str, Any]
    steps: list[dict[str, Any]]
    require_preview: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("工作流程名稱不可留空")
        if len(self.steps) > 25:
            raise ValueError("單一工作流程最多 25 個步驟")
        trigger_type = str(self.trigger.get("type", "manual"))
        if trigger_type not in {"manual", "schedule", "app_start", "work_start"}:
            raise ValueError("不支援的觸發方式")
        for step in self.steps:
            if not isinstance(step, dict):
                raise ValueError("工作流程步驟格式錯誤")
            capability = str(step.get("capability", ""))
            if capability not in CAPABILITY_RISK:
                raise ValueError(f"不支援的能力：{capability}")
            if not isinstance(step.get("arguments", {}), dict):
                raise ValueError("工具參數必須是物件")

    def to_plan(self, source: str = "workflow") -> ActionPlan:
        self.validate()
        return ActionPlan(
            self.name,
            [
                ActionRequest(
                    str(step["capability"]),
                    str(step.get("description") or step["capability"]),
                    dict(step.get("arguments", {})),
                    source=source,
                    reversible=bool(step.get("reversible", False)),
                )
                for step in self.steps
            ],
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "trigger": self.trigger,
                "steps": self.steps,
                "require_preview": self.require_preview,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_row(cls, row) -> "Workflow":
        payload = json.loads(row["definition"])
        return cls(
            int(row["id"]),
            str(row["name"]),
            bool(row["enabled"]),
            dict(payload.get("trigger", {"type": "manual"})),
            list(payload.get("steps", [])),
            bool(payload.get("require_preview", True)),
        )


def schedule_due(
    workflow: Workflow,
    now: datetime,
    last_run_at: str | None,
) -> bool:
    if not workflow.enabled or workflow.trigger.get("type") != "schedule":
        return False
    at = str(workflow.trigger.get("time", ""))
    if len(at) != 5 or at[2] != ":":
        return False
    try:
        hour, minute = (int(part) for part in at.split(":"))
    except ValueError:
        return False
    if now.hour != hour or now.minute != minute:
        return False
    weekdays = workflow.trigger.get("weekdays", list(range(7)))
    if now.weekday() not in weekdays:
        return False
    if not last_run_at:
        return True
    try:
        last = datetime.fromisoformat(last_run_at)
    except ValueError:
        return True
    return last.date() != now.date() or (
        last.hour,
        last.minute,
    ) != (now.hour, now.minute)
