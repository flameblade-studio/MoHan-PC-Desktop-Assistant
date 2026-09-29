from __future__ import annotations

lazy import os
lazy import subprocess
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest

lazy from tests.run_all import (
    ISOLATED_TEST_CHILD,
    TEST_TIMEOUT_SECONDS,
    _isolated_environment,
    _test_commands,
)

_PYTEST_TEMPORARY_DIRECTORY: TemporaryDirectory[str] | None = None


class IsolatedModuleFailure(Exception):
    """Report a failing isolated command for one test module."""


class IsolatedModule(pytest.Module):
    """Collect a test module without importing it into pytest's process."""

    def collect(self) -> list[pytest.Item]:
        return [IsolatedModuleItem.from_parent(self, name="isolated")]


class IsolatedModuleItem(pytest.Item):
    """Execute the same isolated commands used by tests/run_all.py."""

    def runtest(self) -> None:
        test_path = Path(str(self.path))
        with TemporaryDirectory(prefix="mohan-pytest-run-") as temporary:
            temporary_root = Path(temporary)
            for index, command in enumerate(_test_commands(test_path), start=1):
                environment = _isolated_environment(
                    temporary_root / f"command-{index:02d}"
                )
                try:
                    completed = subprocess.run(
                        command,
                        cwd=test_path.parents[1],
                        check=False,
                        capture_output=True,
                        encoding="utf-8",
                        errors="replace",
                        env=environment,
                        text=True,
                        timeout=TEST_TIMEOUT_SECONDS,
                    )
                except subprocess.TimeoutExpired as error:
                    raise IsolatedModuleFailure(
                        f"{test_path.name} timed out after "
                        f"{TEST_TIMEOUT_SECONDS} seconds\n"
                        f"command: {subprocess.list2cmdline(command)}\n"
                        f"stdout:\n{error.stdout or ''}\n"
                        f"stderr:\n{error.stderr or ''}"
                    ) from error
                if completed.returncode:
                    raise IsolatedModuleFailure(
                        f"{test_path.name} exited with {completed.returncode}\n"
                        f"command: {subprocess.list2cmdline(command)}\n"
                        f"stdout:\n{completed.stdout}\n"
                        f"stderr:\n{completed.stderr}"
                    )

    def repr_failure(self, excinfo: pytest.ExceptionInfo[BaseException]) -> str:
        if isinstance(excinfo.value, IsolatedModuleFailure):
            return str(excinfo.value)
        return super().repr_failure(excinfo)

    def reportinfo(self) -> tuple[Path, int | None, str]:
        return self.path, 0, f"isolated test module: {self.name}"


def pytest_configure(config: pytest.Config) -> None:
    global _PYTEST_TEMPORARY_DIRECTORY
    if config.option.basetemp is not None:
        return
    _PYTEST_TEMPORARY_DIRECTORY = TemporaryDirectory(
        prefix="mohan-pytest-main-",
        ignore_cleanup_errors=True,
    )
    config.option.basetemp = _PYTEST_TEMPORARY_DIRECTORY.name


def pytest_unconfigure(config: pytest.Config) -> None:
    del config
    global _PYTEST_TEMPORARY_DIRECTORY
    if _PYTEST_TEMPORARY_DIRECTORY is not None:
        _PYTEST_TEMPORARY_DIRECTORY.cleanup()
        _PYTEST_TEMPORARY_DIRECTORY = None


def pytest_pycollect_makemodule(
    module_path: Path,
    parent: pytest.Collector,
) -> pytest.Module | None:
    node_selection_requested = any(
        "::" in str(argument) for argument in parent.config.args
    )
    if os.environ.get(ISOLATED_TEST_CHILD) == "1" or node_selection_requested:
        return None
    return IsolatedModule.from_parent(parent, path=module_path)
