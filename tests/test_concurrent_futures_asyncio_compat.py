from __future__ import annotations

lazy import ast
lazy import asyncio
lazy import importlib
lazy import subprocess
lazy import sys
lazy import threading
lazy import time
lazy from collections.abc import Iterable
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from unittest.mock import patch

lazy import pytest

lazy from application.background_agents import AgentObservation, ManagerWorkerScheduler
lazy from presentation.flagship.cloud_health import CloudHealthWorker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = "domain/python315_concurrency.py"
BOUNDARY_IMPORTS = {
    "application/background_agents.py": {"Future", "ThreadPoolExecutor"},
    "infrastructure/concurrency_tools.py": {"ThreadPoolExecutor"},
    "presentation/flagship/cloud_health.py": {
        "ThreadPoolExecutor",
        "as_completed",
    },
    "tools/benchmark_native_integrated.py": {"ThreadPoolExecutor"},
    "tools/diagnose_google_services.py": {
        "Future",
        "ThreadPoolExecutor",
        "as_completed",
    },
    "tests/test_remote_concurrency.py": {"ThreadPoolExecutor"},
}
ASYNCIO_EAGER_IMPORTS = (
    "tools/benchmark_native_integrated.py",
    "tests/test_native_concurrency.py",
)
MODULES = tuple(
    path.removesuffix(".py").replace("/", ".") for path in BOUNDARY_IMPORTS
)


def _asyncio_to_thread_result() -> int:
    async def exercise() -> int:
        return await asyncio.to_thread(lambda: 315)

    return asyncio.run(exercise())


def _boundary_import(tree: ast.Module) -> ast.ImportFrom:
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "domain.python315_concurrency"
    ]
    assert len(imports) == 1
    return imports[0]


@pytest.mark.parametrize("module_name", MODULES)
def test_affected_module_import_preserves_asyncio_to_thread(
    module_name: str,
) -> None:
    module = importlib.import_module(module_name)
    importlib.reload(module)

    assert _asyncio_to_thread_result() == 315


def test_concurrency_consumers_use_one_eager_compatibility_boundary() -> None:
    lazy_imports_remain = False
    for relative_path, expected_names in BOUNDARY_IMPORTS.items():
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative_path)
        imported = _boundary_import(tree)

        assert not getattr(imported, "is_lazy", False), relative_path
        assert {alias.name for alias in imported.names} == expected_names
        lazy_imports_remain |= any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            and bool(getattr(node, "is_lazy", False))
            for node in tree.body
        )

    assert lazy_imports_remain, "unrelated PEP 810 lazy imports must remain enabled"


def test_compatibility_boundary_resolves_the_lazy_stdlib_export() -> None:
    source = (PROJECT_ROOT / BOUNDARY_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=BOUNDARY_PATH)
    module_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and any(alias.name == "concurrent.futures" for alias in node.names)
    ]
    thread_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "concurrent.futures.thread"
    ]

    assert len(module_imports) == 1
    assert not getattr(module_imports[0], "is_lazy", False)
    assert len(thread_imports) == 1
    assert not getattr(thread_imports[0], "is_lazy", False)
    assert {alias.name for alias in thread_imports[0].names} == {
        "ThreadPoolExecutor"
    }
    assert (
        "concurrent.futures.ThreadPoolExecutor = ThreadPoolExecutor" in source
    )


@pytest.mark.parametrize(
    "import_order",
    (
        "import asyncio\nimport domain.python315_concurrency",
        "import domain.python315_concurrency\nimport asyncio",
    ),
)
def test_asyncio_to_thread_is_independent_of_import_order(
    import_order: str,
) -> None:
    code = (
        f"{import_order}\n"
        "print(asyncio.run(asyncio.to_thread(lambda: 315)))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "315"


@pytest.mark.parametrize("relative_path", ASYNCIO_EAGER_IMPORTS)
def test_asyncio_import_is_eager_when_to_thread_is_used(
    relative_path: str,
) -> None:
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative_path)
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and any(alias.name == "asyncio" for alias in node.names)
    ]

    assert len(imports) == 1
    assert not getattr(imports[0], "is_lazy", False)


class _OneShotWorker:
    worker_id = "asyncio-compat"
    interval_seconds = 60.0

    def poll(self) -> Iterable[AgentObservation]:
        return (
            AgentObservation(
                worker_id=self.worker_id,
                event_key="completed",
                message="background worker completed",
            ),
        )


def test_background_scheduler_remains_operational() -> None:
    scheduler = ManagerWorkerScheduler(
        [_OneShotWorker()],
        max_workers=1,
        event_cooldown_seconds=0,
        global_cooldown_seconds=0,
    )
    try:
        scheduler.tick()
        deadline = time.monotonic() + 2.0
        observations: list[AgentObservation] = []
        while time.monotonic() < deadline and not observations:
            observations = scheduler.drain()
            if not observations:
                time.sleep(0.005)
    finally:
        scheduler.close()

    assert [item.event_key for item in observations] == ["completed"]
    assert _asyncio_to_thread_result() == 315


def test_cloud_health_probes_remain_concurrent_and_isolated() -> None:
    barrier = threading.Barrier(3)

    def result_after_all_probes_started(result: object) -> object:
        barrier.wait(timeout=2)
        return result

    def failure_after_all_probes_started(error: Exception) -> object:
        barrier.wait(timeout=2)
        raise error

    with (
        patch(
            "presentation.flagship.cloud_health.GmailConnector",
            return_value=SimpleNamespace(
                request=lambda *_args, **_kwargs: result_after_all_probes_started(
                    {"emailAddress": "user@example.com"}
                )
            ),
        ),
        patch(
            "presentation.flagship.cloud_health.GoogleCalendarConnector",
            return_value=SimpleNamespace(
                request=lambda *_args, **_kwargs: result_after_all_probes_started(
                    {"items": []}
                )
            ),
        ),
        patch(
            "presentation.flagship.cloud_health.GoogleDriveConnector",
            return_value=SimpleNamespace(
                request=lambda *_args, **_kwargs: failure_after_all_probes_started(
                    PermissionError("scope")
                )
            ),
        ),
    ):
        results = CloudHealthWorker("google", "test-token")._google_probes()

    assert results["Gmail"]["ok"] is True
    assert results["Calendar"]["ok"] is True
    assert results["Drive"]["ok"] is False
    assert _asyncio_to_thread_result() == 315
