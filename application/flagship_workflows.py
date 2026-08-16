from __future__ import annotations

lazy from collections.abc import Iterable, Mapping, Sequence
lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from enum import StrEnum
lazy from typing import Protocol, cast

lazy from domain.time_utils import local_wall_time

__all__ = (
    "FlagshipWorkflowService",
    "WorkflowClockPort",
    "WorkflowDuePort",
    "WorkflowExecutorPort",
    "WorkflowFactoryPort",
    "WorkflowListItem",
    "WorkflowPort",
    "WorkflowPreviewPort",
    "WorkflowRepositoryPort",
    "WorkflowRowPort",
    "WorkflowRun",
    "WorkflowRunDisposition",
    "WorkflowRuntimePorts",
    "WorkflowTextPort",
)


class WorkflowRowPort(Protocol):
    """Read one persistence row without coupling the use case to SQLite."""

    def __getitem__(self, key: str, /) -> object: ...


class WorkflowPort[PlanT](Protocol):
    """Domain workflow behavior required by the flagship use case."""

    @property
    def workflow_id(self) -> int | None: ...

    @property
    def name(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    @property
    def trigger(self) -> Mapping[str, object]: ...

    @property
    def steps(self) -> Sequence[Mapping[str, object]]: ...

    @property
    def require_preview(self) -> bool: ...

    def to_json(self) -> str: ...

    def to_plan(self) -> PlanT: ...


class WorkflowRepositoryPort(Protocol):
    """Persistence operations used by workflow application coordination."""

    def save_workflow(
        self,
        name: str,
        definition: str,
        *,
        enabled: bool = True,
        workflow_id: int | None = None,
    ) -> int: ...

    def workflows(
        self,
        enabled_only: bool = False,
    ) -> Iterable[WorkflowRowPort]: ...

    def workflow(self, workflow_id: int) -> WorkflowRowPort | None: ...

    def delete_workflow(self, workflow_id: int) -> bool: ...

    def mark_workflow_run(self, workflow_id: int) -> None: ...


class WorkflowFactoryPort[PlanT](Protocol):
    def __call__(self, row: WorkflowRowPort, /) -> WorkflowPort[PlanT]: ...


class WorkflowDuePort[PlanT](Protocol):
    def __call__(
        self,
        workflow: WorkflowPort[PlanT],
        now: datetime,
        last_run_at: str | None,
        /,
    ) -> bool: ...


class WorkflowExecutorPort[PlanT, ResultT](Protocol):
    def execute(self, plan: PlanT) -> Iterable[ResultT]: ...


class WorkflowPreviewPort[PlanT](Protocol):
    def __call__(
        self,
        workflow: WorkflowPort[PlanT],
        plan: PlanT,
        /,
    ) -> bool: ...


class WorkflowClockPort(Protocol):
    def __call__(self, /) -> datetime: ...


class WorkflowTextPort(Protocol):
    def __call__(self, source: str, /, **values: object) -> str: ...


@dataclass(frozen=True, slots=True)
class WorkflowRuntimePorts[PlanT, ResultT]:
    """Injected domain and I/O boundaries required by workflow coordination."""

    repository: WorkflowRepositoryPort
    workflow_from_row: WorkflowFactoryPort[PlanT]
    schedule_due: WorkflowDuePort[PlanT]
    executor: WorkflowExecutorPort[PlanT, ResultT]


class WorkflowRunDisposition(StrEnum):
    EXECUTED = "executed"
    PREVIEW_DECLINED = "preview-declined"


@dataclass(frozen=True, slots=True)
class WorkflowListItem:
    workflow_id: int
    name: str
    enabled: bool
    trigger_type: str
    trigger_label: str
    step_count: int
    text: str


@dataclass(frozen=True, slots=True)
class WorkflowRun[PlanT, ResultT]:
    disposition: WorkflowRunDisposition
    workflow_id: int | None
    plan: PlanT
    results: tuple[ResultT, ...]

    @property
    def executed(self) -> bool:
        return self.disposition is WorkflowRunDisposition.EXECUTED


def _source_text(source: str, /, **values: object) -> str:
    return source.format_map(values) if values else source


def _decline_preview[PlanT](
    _workflow: WorkflowPort[PlanT],
    _plan: PlanT,
    /,
) -> bool:
    return False


class FlagshipWorkflowService[PlanT, ResultT]:
    """Coordinate flagship workflows through injected, provider-neutral ports."""

    def __init__(
        self,
        ports: WorkflowRuntimePorts[PlanT, ResultT],
        *,
        confirm_preview: WorkflowPreviewPort[PlanT] | None = None,
        translate: WorkflowTextPort = _source_text,
        clock: WorkflowClockPort = local_wall_time,
    ) -> None:
        self._repository = ports.repository
        self._workflow_from_row = ports.workflow_from_row
        self._schedule_due = ports.schedule_due
        self._executor = ports.executor
        self._confirm_preview = (
            _decline_preview if confirm_preview is None else confirm_preview
        )
        self._translate = translate
        self._clock = clock

    def save_workflow(self, workflow: WorkflowPort[PlanT]) -> int:
        """Create or update a workflow while preserving persistence errors."""

        definition = workflow.to_json()
        if workflow.workflow_id is None:
            return self._repository.save_workflow(
                workflow.name,
                definition,
                enabled=workflow.enabled,
            )
        return self._repository.save_workflow(
            workflow.name,
            definition,
            enabled=workflow.enabled,
            workflow_id=workflow.workflow_id,
        )

    def workflow(self, workflow_id: int) -> WorkflowPort[PlanT] | None:
        row = self._repository.workflow(workflow_id)
        return None if row is None else self._workflow_from_row(row)

    def delete_workflow(self, workflow_id: int) -> bool:
        return self._repository.delete_workflow(workflow_id)

    def list_workflows(self) -> tuple[WorkflowListItem, ...]:
        items: list[WorkflowListItem] = []
        for row in self._repository.workflows():
            workflow = self._workflow_from_row(row)
            items.append(self._list_item(row, workflow))
        return tuple(items)

    def execute_workflow(
        self,
        workflow: WorkflowPort[PlanT],
    ) -> WorkflowRun[PlanT, ResultT]:
        plan = workflow.to_plan()
        if workflow.require_preview and not self._confirm_preview(workflow, plan):
            return WorkflowRun(
                WorkflowRunDisposition.PREVIEW_DECLINED,
                workflow.workflow_id,
                plan,
                (),
            )

        results = tuple(self._executor.execute(plan))
        if workflow.workflow_id:
            self._repository.mark_workflow_run(workflow.workflow_id)
        return WorkflowRun(
            WorkflowRunDisposition.EXECUTED,
            workflow.workflow_id,
            plan,
            results,
        )

    def run_due_workflows(
        self,
        *,
        closed: bool = False,
        now: datetime | None = None,
    ) -> tuple[WorkflowRun[PlanT, ResultT], ...]:
        if closed:
            return ()
        current_time = self._clock() if now is None else now
        runs: list[WorkflowRun[PlanT, ResultT]] = []
        for row in self._repository.workflows(enabled_only=True):
            workflow = self._workflow_from_row(row)
            last_run_at = cast("str | None", row["last_run_at"])
            if self._schedule_due(workflow, current_time, last_run_at):
                runs.append(self.execute_workflow(workflow))
        return tuple(runs)

    def work_started(self) -> tuple[WorkflowRun[PlanT, ResultT], ...]:
        runs: list[WorkflowRun[PlanT, ResultT]] = []
        for row in self._repository.workflows(enabled_only=True):
            workflow = self._workflow_from_row(row)
            if workflow.trigger.get("type") == "work_start":
                runs.append(self.execute_workflow(workflow))
        return tuple(runs)

    def _list_item(
        self,
        row: WorkflowRowPort,
        workflow: WorkflowPort[PlanT],
    ) -> WorkflowListItem:
        trigger_type = str(workflow.trigger.get("type"))
        trigger_label = self._trigger_label(workflow, trigger_type)
        step_count = len(workflow.steps)
        text = (
            f"{'●' if workflow.enabled else '○'} "
            f"{workflow.name}　｜　{trigger_label}　｜　"
            + self._translate("{count} 步", count=step_count)
        )
        return WorkflowListItem(
            int(row["id"]),
            workflow.name,
            workflow.enabled,
            trigger_type,
            trigger_label,
            step_count,
            text,
        )

    def _trigger_label(
        self,
        workflow: WorkflowPort[PlanT],
        trigger_type: str,
    ) -> str:
        if trigger_type == "manual":
            return self._translate("手動")
        if trigger_type == "schedule":
            return self._translate(
                "每天 {time}",
                time=workflow.trigger.get("time", ""),
            )
        if trigger_type == "work_start":
            return self._translate("開始工作時")
        if trigger_type == "app_start":
            return self._translate("程式啟動時")
        return self._translate("未知")
