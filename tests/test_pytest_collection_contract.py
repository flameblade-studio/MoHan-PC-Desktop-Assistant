from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy import pytest

lazy from tests.run_all import _pytest_node_names

TESTS_DIR = Path(__file__).resolve().parent


def _test_files_requested_by_pytest(arguments: tuple[str, ...]) -> set[Path]:
    requested: set[Path] = set()
    for argument in arguments:
        candidate = Path(argument.split("::", maxsplit=1)[0])
        if not candidate.exists():
            continue
        if candidate.is_dir():
            requested.update(candidate.glob("test_*.py"))
        elif candidate.name.startswith("test_") and candidate.suffix == ".py":
            requested.add(candidate)
    return {path.resolve() for path in requested}


def test_every_test_module_has_pytest_nodes_or_run() -> None:
    invalid: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        has_run = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "run"
            for node in tree.body
        )
        if not has_run and not _pytest_node_names(tree):
            invalid.append(path.name)
    assert not invalid, (
        "test modules require at least one pytest node or a top-level run(): "
        + ", ".join(invalid)
    )


def test_every_requested_test_module_collected_at_least_one_item(
    request: pytest.FixtureRequest,
) -> None:
    requested = _test_files_requested_by_pytest(tuple(request.config.args))
    collected = {Path(str(item.path)).resolve() for item in request.session.items}
    missing = sorted(path.name for path in requested - collected)
    assert not missing, "pytest collected zero items from: " + ", ".join(missing)
