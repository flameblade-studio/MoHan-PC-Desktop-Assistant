from __future__ import annotations

lazy import ast
lazy import json
lazy from dataclasses import dataclass, field
lazy from datetime import datetime
lazy from pathlib import Path
lazy from typing import cast

lazy import pytest

lazy from application.flagship_workflows import (
    FlagshipWorkflowService,
    WorkflowListItem,
    WorkflowRunDisposition,
    WorkflowRuntimePorts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = PROJECT_ROOT / "application" / "flagship_workflows.py"


@dataclass(frozen=True, slots=True)
class FakePlan:
    title: str


@dataclass(frozen=True, slots=True)
class FakeResult:
    message: str


@dataclass(slots=True)
class FakeWorkflow:
    workflow_id: int | None
    name: str
    enabled: bool
    trigger: dict[str, object]
    steps: list[dict[str, object]]
    require_preview: bool = True
    definition: str = "{}"
    serialization_error: Exception | None = None
    plan_error: Exception | None = None
    plan_calls: int = 0

    def to_json(self) -> str:
        if self.serialization_error is not None:
            raise self.serialization_error
        return self.definition

    def to_plan(self) -> FakePlan:
        self.plan_calls += 1
        if self.plan_error is not None:
            raise self.plan_error
        return FakePlan(self.name)


type FakeRow = dict[str, object]


def row_for(
    workflow: FakeWorkflow,
    *,
    workflow_id: int | None = None,
    last_run_at: str | None = None,
) -> FakeRow:
    row_id = workflow.workflow_id if workflow_id is None else workflow_id
    assert row_id is not None
    return {
        "id": row_id,
        "name": workflow.name,
        "enabled": int(workflow.enabled),
        "definition": workflow.definition,
        "last_run_at": last_run_at,
        "workflow": workflow,
    }


class FakeRepository:
    def __init__(
        self,
        rows: list[FakeRow] | None = None,
        *,
        events: list[str] | None = None,
    ) -> None:
        self.rows = list(rows or ())
        self.events = events if events is not None else []
        self.saved: list[tuple[str, str, bool, int | None]] = []
        self.workflow_queries: list[int] = []
        self.workflow_list_queries: list[bool] = []
        self.deleted: list[int] = []
        self.marked: list[int] = []
        self.save_error: Exception | None = None
        self.mark_error: Exception | None = None
        self._next_id = 100

    def save_workflow(
        self,
        name: str,
        definition: str,
        *,
        enabled: bool = True,
        workflow_id: int | None = None,
    ) -> int:
        if self.save_error is not None:
            raise self.save_error
        self.saved.append((name, definition, enabled, workflow_id))
        if workflow_id is not None:
            return workflow_id
        saved_id = self._next_id
        self._next_id += 1
        return saved_id

    def workflows(self, enabled_only: bool = False) -> list[FakeRow]:
        self.workflow_list_queries.append(enabled_only)
        if not enabled_only:
            return list(self.rows)
        return [row for row in self.rows if bool(row["enabled"])]

    def workflow(self, workflow_id: int) -> FakeRow | None:
        self.workflow_queries.append(workflow_id)
        return next(
            (row for row in self.rows if int(row["id"]) == workflow_id),
            None,
        )

    def delete_workflow(self, workflow_id: int) -> bool:
        self.deleted.append(workflow_id)
        original_count = len(self.rows)
        self.rows = [row for row in self.rows if int(row["id"]) != workflow_id]
        return len(self.rows) != original_count

    def mark_workflow_run(self, workflow_id: int) -> None:
        self.events.append(f"mark:{workflow_id}")
        self.marked.append(workflow_id)
        if self.mark_error is not None:
            raise self.mark_error


def workflow_from_row(row: object) -> FakeWorkflow:
    stored = cast("FakeRow", row)["workflow"]
    assert isinstance(stored, FakeWorkflow)
    return stored


class FakeExecutor:
    def __init__(
        self,
        *,
        events: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.events = events if events is not None else []
        self.error = error
        self.plans: list[FakePlan] = []

    def execute(self, plan: FakePlan) -> tuple[FakeResult, ...]:
        self.events.append(f"execute:{plan.title}")
        self.plans.append(plan)
        if self.error is not None:
            raise self.error
        return (FakeResult(f"result:{plan.title}"),)


@dataclass(slots=True)
class PreviewRecorder:
    decisions: list[bool]
    events: list[str] = field(default_factory=list)
    calls: list[tuple[FakeWorkflow, FakePlan]] = field(default_factory=list)

    def __call__(self, workflow: object, plan: FakePlan) -> bool:
        typed_workflow = cast("FakeWorkflow", workflow)
        self.events.append(f"preview:{typed_workflow.name}")
        self.calls.append((typed_workflow, plan))
        return self.decisions.pop(0)


@dataclass(slots=True)
class DueRecorder:
    due_names: frozenset[str]
    calls: list[tuple[FakeWorkflow, datetime, str | None]] = field(default_factory=list)

    def __call__(
        self,
        workflow: object,
        now: datetime,
        last_run_at: str | None,
    ) -> bool:
        typed_workflow = cast("FakeWorkflow", workflow)
        self.calls.append((typed_workflow, now, last_run_at))
        return typed_workflow.name in self.due_names


def never_due(
    _workflow: object,
    _now: datetime,
    _last_run_at: str | None,
) -> bool:
    return False


@dataclass(slots=True)
class ServiceOverrides:
    executor: FakeExecutor | None = None
    due: object = never_due
    preview: object | None = None
    translate: object | None = None
    clock: object | None = None


def make_service(
    repository: FakeRepository,
    overrides: ServiceOverrides | None = None,
) -> FlagshipWorkflowService[FakePlan, FakeResult]:
    selected = overrides or ServiceOverrides()
    executor = selected.executor or FakeExecutor(events=repository.events)
    ports = WorkflowRuntimePorts(
        repository,
        workflow_from_row,
        selected.due,
        executor,
    )
    arguments: dict[str, object] = {}
    if selected.preview is not None:
        arguments["confirm_preview"] = selected.preview
    if selected.translate is not None:
        arguments["translate"] = selected.translate
    if selected.clock is not None:
        arguments["clock"] = selected.clock
    return FlagshipWorkflowService(ports, **arguments)


def workflow(
    workflow_id: int | None,
    name: str,
    *,
    enabled: bool = True,
    trigger: dict[str, object] | None = None,
    require_preview: bool = False,
) -> FakeWorkflow:
    return FakeWorkflow(
        workflow_id,
        name,
        enabled,
        {"type": "manual"} if trigger is None else trigger,
        [{"capability": "step-0"}],
        require_preview,
        definition=f'{{"name":"{name}"}}',
    )


def test_service_imports_only_standard_library_and_domain_with_lazy_imports() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SERVICE_PATH))
    allowed_roots = {
        "__future__",
        "collections",
        "dataclasses",
        "datetime",
        "domain",
        "enum",
        "typing",
    }
    imported_roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.partition(".")[0])
        else:
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        assert getattr(node, "is_lazy", False), f"non-lazy import at line {node.lineno}"

    assert imported_roots <= allowed_roots
    assert (
        not {
            "application",
            "infrastructure",
            "integrations",
            "presentation",
        }
        & imported_roots
    )
    assert "PySide6" not in source
    assert "workflow_engine" not in source
    assert "flagship_core" not in source


def test_crud_uses_the_repository_port_and_preserves_identity() -> None:
    stored = workflow(7, "Stored")
    repository = FakeRepository([row_for(stored)])
    service = make_service(repository)

    created = workflow(None, "Created", enabled=False)
    assert service.save_workflow(created) == 100
    assert repository.saved[-1] == (
        "Created",
        created.definition,
        False,
        None,
    )

    stored.definition = '{"updated":true}'
    assert service.save_workflow(stored) == 7
    assert repository.saved[-1] == (
        "Stored",
        stored.definition,
        True,
        7,
    )
    assert service.workflow(7) is stored
    assert service.workflow(999) is None
    assert repository.workflow_queries == [7, 999]

    assert service.delete_workflow(7) is True
    assert service.delete_workflow(7) is False
    assert repository.deleted == [7, 7]


def test_list_preparation_preserves_order_labels_counts_and_unknown_trigger() -> None:
    scheduled = workflow(
        2,
        "Scheduled",
        enabled=False,
        trigger={"type": "schedule", "time": "08:30"},
    )
    scheduled.steps.append({"capability": "step-1"})
    work_start = workflow(3, "Work", trigger={"type": "work_start"})
    work_start.steps.clear()
    workflows = [
        workflow(1, "Manual"),
        scheduled,
        work_start,
        workflow(4, "Startup", trigger={"type": "app_start"}),
        workflow(5, "Future", trigger={"type": "future"}),
    ]
    repository = FakeRepository([row_for(item) for item in workflows])
    translations = {
        "手動": "Manual",
        "每天 {time}": "Daily at {time}",
        "開始工作時": "On work start",
        "程式啟動時": "On app start",
        "未知": "Unknown",
        "{count} 步": "{count} step(s)",
    }

    def translate(source: str, /, **values: object) -> str:
        return translations[source].format_map(values)

    items = make_service(
        repository,
        ServiceOverrides(translate=translate),
    ).list_workflows()

    assert repository.workflow_list_queries == [False]
    assert [item.workflow_id for item in items] == [1, 2, 3, 4, 5]
    assert [item.trigger_label for item in items] == [
        "Manual",
        "Daily at 08:30",
        "On work start",
        "On app start",
        "Unknown",
    ]
    assert items[0] == WorkflowListItem(
        1,
        "Manual",
        True,
        "manual",
        "Manual",
        1,
        "● Manual　｜　Manual　｜　1 step(s)",
    )
    assert items[1].text == "○ Scheduled　｜　Daily at 08:30　｜　2 step(s)"
    assert items[2].step_count == 0
    assert items[4].trigger_type == "future"


def test_serialization_and_repository_errors_are_not_rewritten() -> None:
    repository = FakeRepository()
    service = make_service(repository)
    serialization_error = ValueError("工作流程定義無法序列化")
    invalid = workflow(None, "Invalid")
    invalid.serialization_error = serialization_error

    with pytest.raises(ValueError) as captured_serialization:
        service.save_workflow(invalid)
    assert captured_serialization.value is serialization_error
    assert repository.saved == []

    repository_error = json.JSONDecodeError("invalid definition", "{", 1)
    repository.save_error = repository_error
    with pytest.raises(json.JSONDecodeError) as captured_repository:
        service.save_workflow(workflow(None, "Repository error"))
    assert captured_repository.value is repository_error


def test_preview_decline_does_not_execute_or_mark() -> None:
    events: list[str] = []
    target = workflow(11, "Needs preview", require_preview=True)
    repository = FakeRepository([row_for(target)], events=events)
    executor = FakeExecutor(events=events)
    preview = PreviewRecorder([False], events=events)
    service = make_service(
        repository,
        ServiceOverrides(executor=executor, preview=preview),
    )

    run = service.execute_workflow(target)

    assert run.disposition is WorkflowRunDisposition.PREVIEW_DECLINED
    assert run.executed is False
    assert run.plan == FakePlan("Needs preview")
    assert run.results == ()
    assert events == ["preview:Needs preview"]
    assert executor.plans == []
    assert repository.marked == []


def test_execution_marks_only_after_the_plan_and_returns_results() -> None:
    events: list[str] = []
    target = workflow(12, "Approved", require_preview=True)
    repository = FakeRepository([row_for(target)], events=events)
    executor = FakeExecutor(events=events)
    preview = PreviewRecorder([True], events=events)
    service = make_service(
        repository,
        ServiceOverrides(executor=executor, preview=preview),
    )

    run = service.execute_workflow(target)

    assert run.disposition is WorkflowRunDisposition.EXECUTED
    assert run.executed is True
    assert run.results == (FakeResult("result:Approved"),)
    assert events == ["preview:Approved", "execute:Approved", "mark:12"]
    assert repository.marked == [12]

    transient = workflow(None, "Transient", require_preview=False)
    transient_run = service.execute_workflow(transient)
    assert transient_run.executed
    assert events[-1] == "execute:Transient"
    assert repository.marked == [12]


def test_plan_executor_and_mark_errors_propagate_without_false_marking() -> None:
    target = workflow(13, "Failure", require_preview=False)
    plan_error = ValueError("無法建立安全計畫：unsafe")
    target.plan_error = plan_error
    repository = FakeRepository([row_for(target)])
    executor = FakeExecutor(events=repository.events)
    service = make_service(repository, ServiceOverrides(executor=executor))

    with pytest.raises(ValueError) as captured_plan:
        service.execute_workflow(target)
    assert captured_plan.value is plan_error
    assert repository.events == []
    assert repository.marked == []

    target.plan_error = None
    executor_error = RuntimeError("executor failed")
    executor.error = executor_error
    with pytest.raises(RuntimeError) as captured_executor:
        service.execute_workflow(target)
    assert captured_executor.value is executor_error
    assert repository.events == ["execute:Failure"]
    assert repository.marked == []

    repository.events.clear()
    executor.error = None
    mark_error = RuntimeError("mark failed")
    repository.mark_error = mark_error
    with pytest.raises(RuntimeError) as captured_mark:
        service.execute_workflow(target)
    assert captured_mark.value is mark_error
    assert repository.events == ["execute:Failure", "mark:13"]


def test_due_workflows_use_injected_clock_policy_and_enabled_rows_only() -> None:
    now = datetime.fromisoformat("2026-08-14T08:30:00")
    due = workflow(21, "Due", require_preview=False)
    not_due = workflow(22, "Not due", require_preview=False)
    declined = workflow(23, "Declined", require_preview=True)
    disabled = workflow(24, "Disabled due", enabled=False, require_preview=False)
    repository = FakeRepository([
        row_for(due, last_run_at="2026-08-13T08:30:00"),
        row_for(not_due),
        row_for(declined),
        row_for(disabled),
    ])
    due_policy = DueRecorder(frozenset({"Due", "Declined", "Disabled due"}))
    preview = PreviewRecorder([False])
    clock_calls: list[str] = []

    def clock() -> datetime:
        clock_calls.append("clock")
        return now

    service = make_service(
        repository,
        ServiceOverrides(
            due=due_policy,
            preview=preview,
            clock=clock,
        ),
    )
    runs = service.run_due_workflows()

    assert clock_calls == ["clock"]
    assert repository.workflow_list_queries == [True]
    assert [item[0].name for item in due_policy.calls] == [
        "Due",
        "Not due",
        "Declined",
    ]
    assert due_policy.calls[0][1:] == (now, "2026-08-13T08:30:00")
    assert [run.disposition for run in runs] == [
        WorkflowRunDisposition.EXECUTED,
        WorkflowRunDisposition.PREVIEW_DECLINED,
    ]
    assert repository.marked == [21]


def test_closed_due_poll_is_inert_before_clock_or_storage_access() -> None:
    repository = FakeRepository()

    def forbidden_clock() -> datetime:
        raise AssertionError("closed polling must not read the clock")

    service = make_service(repository, ServiceOverrides(clock=forbidden_clock))
    assert service.run_due_workflows(closed=True) == ()
    assert repository.workflow_list_queries == []


def test_work_started_executes_only_enabled_work_start_workflows() -> None:
    started = workflow(31, "Started", trigger={"type": "work_start"})
    manual = workflow(32, "Manual")
    disabled = workflow(
        33,
        "Disabled",
        enabled=False,
        trigger={"type": "work_start"},
    )
    repository = FakeRepository([row_for(started), row_for(manual), row_for(disabled)])
    service = make_service(repository)

    runs = service.work_started()

    assert repository.workflow_list_queries == [True]
    assert len(runs) == 1
    assert runs[0].workflow_id == 31
    assert runs[0].executed
    assert repository.marked == [31]
