from __future__ import annotations

lazy import argparse
lazy import ast
lazy import os
lazy import subprocess
lazy import sys
lazy from collections.abc import Sequence
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

TESTS_DIR = Path(__file__).resolve().parent
SENSITIVE_ENVIRONMENT_VARIABLES = (
    "OPENAI_API_KEY",
    "WORDPRESS_APP_PASSWORD",
    "WORDPRESS_BASE_URL",
    "WORDPRESS_DOWNLOAD_PAGE_ID",
    "WORDPRESS_USERNAME",
)
SENSITIVE_ENVIRONMENT_MARKERS = (
    "AUTH",
    "CREDENTIAL",
    "KEY",
    "PASSWORD",
    "SECRET",
    "TOKEN",
)
MALFORMED_TEST_EXIT_CODE = 2
COLLECTION_AUDIT_EXIT_CODE = 3
TEST_TIMEOUT_EXIT_CODE = 124
# Non-test .py files that legitimately live in tests/ without being collected.
# Anything else that carries assert statements is an orphan checker (like the
# former check_packaged_migration.py) and fails the collection audit.
ORPHAN_EXEMPT_FILES = frozenset({"run_all.py", "__init__.py", "conftest.py"})
TEST_TIMEOUT_SECONDS = 600
# A single retry absorbs the timing-sensitive Qt flakiness that surfaces on
# slow CI runners (event-loop races, transient file locks) without masking a
# deterministic failure: a test must fail twice in a row to fail the suite.
TEST_RETRY_ATTEMPTS = 1


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MoHan's Python tests in isolated child processes."
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Total number of deterministic, non-overlapping shards.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Zero-based shard index to run.",
    )
    arguments = parser.parse_args(tuple(argv or ()))
    if arguments.shard_count < 1:
        parser.error("--shard-count must be at least 1")
    if not 0 <= arguments.shard_index < arguments.shard_count:
        parser.error("--shard-index must be within the configured shard count")
    return arguments


def _select_shard(
    tests: Sequence[Path],
    *,
    shard_index: int,
    shard_count: int,
) -> tuple[Path, ...]:
    """Select one stable round-robin shard without overlap."""

    return tuple(
        test
        for index, test in enumerate(tests)
        if index % shard_count == shard_index
    )


def _run_test_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> int:
    """Run one test behind a small patchable process boundary."""

    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        env=environment,
        timeout=TEST_TIMEOUT_SECONDS,
    )
    return completed.returncode


def _is_main_guard(node: ast.stmt) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _pytest_node_names(tree: ast.Module) -> tuple[str, ...]:
    """Return pytest-collectable top-level nodes in source order."""

    return tuple(
        node.name
        for node in tree.body
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
        or isinstance(node, ast.ClassDef)
        and (
            node.name.startswith("Test")
            or any(
                (
                    isinstance(base, ast.Attribute)
                    and isinstance(base.value, ast.Name)
                    and base.value.id == "unittest"
                    and base.attr == "TestCase"
                )
                or isinstance(base, ast.Name)
                and base.id == "TestCase"
                for base in node.bases
            )
        )
    )


def _local_function_calls(
    node: ast.AST,
    function_names: frozenset[str],
) -> frozenset[str]:
    """Return local functions explicitly called by one node."""

    return frozenset(
        child.func.id
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id in function_names
    )


def _invoked_function_collection_members(
    node: ast.AST,
    function_names: frozenset[str],
) -> frozenset[str]:
    """Return functions invoked through an explicit local collection loop."""

    collections: dict[str, frozenset[str]] = {}
    for child in ast.walk(node):
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(child, ast.Assign) and len(child.targets) == 1:
            target = child.targets[0]
            value = child.value
        elif isinstance(child, ast.AnnAssign):
            target = child.target
            value = child.value
        if (
            not isinstance(target, ast.Name)
            or not isinstance(value, (ast.List, ast.Set, ast.Tuple))
            or not value.elts
            or not all(
                isinstance(element, ast.Name) and element.id in function_names
                for element in value.elts
            )
        ):
            continue
        collections[target.id] = frozenset(
            element.id for element in value.elts if isinstance(element, ast.Name)
        )

    invoked: set[str] = set()
    for child in ast.walk(node):
        if (
            not isinstance(child, ast.For)
            or not isinstance(child.target, ast.Name)
            or not isinstance(child.iter, ast.Name)
            or child.iter.id not in collections
        ):
            continue
        if any(
            isinstance(loop_child, ast.Call)
            and isinstance(loop_child.func, ast.Name)
            and loop_child.func.id == child.target.id
            for statement in child.body
            for loop_child in ast.walk(statement)
        ):
            invoked.update(collections[child.iter.id])
    return frozenset(invoked)


def _invoked_local_functions(
    node: ast.AST,
    function_names: frozenset[str],
) -> frozenset[str]:
    return _local_function_calls(
        node,
        function_names,
    ) | _invoked_function_collection_members(node, function_names)


def _calls_framework_main(node: ast.AST, module_name: str) -> bool:
    """Return whether a node delegates collection to a test framework."""

    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and isinstance(child.func.value, ast.Name)
        and child.func.value.id == module_name
        and child.func.attr == "main"
        for child in ast.walk(node)
    )


def _is_pure_delegate(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    reached_functions: frozenset[str],
) -> bool:
    """Return whether a pytest wrapper only calls an already-run function."""

    if (
        node.decorator_list
        or node.args.posonlyargs
        or node.args.args
        or node.args.kwonlyargs
        or node.args.vararg is not None
        or node.args.kwarg is not None
    ):
        return False
    statements = list(node.body)
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        statements.pop(0)
    if len(statements) != 1:
        return False
    statement = statements[0]
    value = (
        statement.value
        if isinstance(statement, (ast.Expr, ast.Return))
        else None
    )
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in reached_functions
        and not value.args
        and not value.keywords
    )


def _pytest_nodes_missing_from_main(
    tree: ast.Module,
    main_guards: tuple[ast.If, ...],
) -> tuple[str, ...]:
    """Find pytest nodes not exercised by the file's direct entry point."""

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    function_names = frozenset(functions)
    pending = set().union(
        *(
            _invoked_local_functions(guard, function_names)
            for guard in main_guards
        )
    )
    reached: set[str] = set()
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        pending.update(
            _invoked_local_functions(functions[name], function_names) - reached
        )

    pytest_nodes = _pytest_node_names(tree)
    covered = {
        name
        for name in pytest_nodes
        if name in reached
        or (
            name in functions
            and _is_pure_delegate(functions[name], frozenset(reached))
        )
    }
    if any(_calls_framework_main(guard, "unittest") for guard in main_guards):
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name not in pytest_nodes:
                continue
            covered.add(node.name)
            pending.update(_invoked_local_functions(node, function_names))
        while pending:
            name = pending.pop()
            if name in reached:
                continue
            reached.add(name)
            pending.update(
                _invoked_local_functions(functions[name], function_names) - reached
            )
        covered.update(reached)
    if any(_calls_framework_main(guard, "pytest") for guard in main_guards):
        covered.update(pytest_nodes)
    return tuple(name for name in pytest_nodes if name not in covered)


def _test_commands(test: Path) -> tuple[list[str], ...]:
    source = test.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test))
    commands: list[list[str]] = []
    main_guards = tuple(
        node for node in tree.body if _is_main_guard(node)
    )
    pytest_nodes = _pytest_node_names(tree)
    if main_guards:
        commands.append([sys.executable, str(test)])
        missing_nodes = _pytest_nodes_missing_from_main(tree, main_guards)
        if missing_nodes:
            commands.append(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    *(f"{test}::{name}" for name in missing_nodes),
                    "-q",
                ]
            )
    elif pytest_nodes:
        commands.append(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                str(test),
                "-q",
            ]
        )
    if not commands:
        commands.append(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                str(test),
                "-q",
            ]
        )
    return tuple(commands)


def _isolated_environment(test_root: Path) -> dict[str, str]:
    locations = {
        "LOCALAPPDATA": test_root / "local-app-data",
        "APPDATA": test_root / "app-data",
        "TEMP": test_root / "temp",
        "TMP": test_root / "tmp",
        "PYTHONPYCACHEPREFIX": test_root / "python-cache",
    }
    for location in locations.values():
        location.mkdir(parents=True, exist_ok=True)

    environment = {
        name: value
        for name, value in os.environ.items()
        if not any(marker in name.upper() for marker in SENSITIVE_ENVIRONMENT_MARKERS)
    }
    environment.pop("MOHAN_DATA_DIR", None)
    # GitHub Actions injects GIT_CONFIG_COUNT/KEY_n/VALUE_n as one atomic
    # protocol.  The generic secret filter removes KEY_n; retaining COUNT (or
    # VALUE_n) leaves git itself malformed.  Tests must receive none of it.
    environment.pop("GIT_CONFIG_COUNT", None)
    for name in tuple(environment):
        if name.startswith("GIT_CONFIG_VALUE_"):
            environment.pop(name, None)
    environment.update({name: str(location) for name, location in locations.items()})
    import_roots = [str(TESTS_DIR.parent)]
    # The project-owned Python 3.15 runtime keeps its source-built Qt wheel in
    # this compatibility root.  Preserve test isolation while making that
    # explicit, repository-scoped dependency visible to child processes.
    qt_compat = TESTS_DIR.parent / ".qt315-compat-full" / "Lib" / "site-packages"
    if qt_compat.is_dir():
        import_roots.append(str(qt_compat))
    environment["PYTHONPATH"] = os.pathsep.join(import_roots)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.update(dict.fromkeys(SENSITIVE_ENVIRONMENT_VARIABLES, ""))
    return environment


def _contains_assertions(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError, SyntaxError, UnicodeError:
        # An unreadable checker still counts as an orphan: fail closed.
        return True
    return any(isinstance(node, ast.Assert) for node in ast.walk(tree))


def _collection_audit_errors(collected: Sequence[Path]) -> tuple[str, ...]:
    """Reconcile the tests/ directory manifest with the collected set.

    Two guarantees keep orphan checkers from silently losing coverage again:
    the number of ``test_*.py`` files on disk must equal the number the
    runner collected, and no other ``.py`` file in tests/ may contain assert
    statements unless it is a known non-test file (``ORPHAN_EXEMPT_FILES``).
    """

    errors: list[str] = []
    present = tuple(
        path
        for path in sorted(TESTS_DIR.iterdir())
        if path.is_file()
        and path.suffix == ".py"
        and path.name.startswith("test_")
    )
    if len(present) != len(collected):
        errors.append(
            f"collection mismatch: {len(present)} test_*.py files present "
            f"but {len(collected)} collected"
        )
    collected_names = frozenset(path.name for path in collected)
    for path in sorted(TESTS_DIR.glob("*.py")):
        if path.name in collected_names or path.name in ORPHAN_EXEMPT_FILES:
            continue
        if _contains_assertions(path):
            errors.append(
                f"orphan checker is never collected: {path.name} "
                "(rename it to test_*.py or add it to ORPHAN_EXEMPT_FILES)"
            )
    return tuple(errors)


def _print_retried_modules(retried_modules: Sequence[str]) -> None:
    """Keep intermittent failures visible even when a retry rescued them."""

    if retried_modules:
        print(
            "RETRIED_MODULES: " + ", ".join(retried_modules),
            flush=True,
        )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    all_tests = tuple(sorted(TESTS_DIR.glob("test_*.py")))
    if not all_tests:
        print("No tests found.", file=sys.stderr)
        return 2
    audit_errors = _collection_audit_errors(all_tests)
    if audit_errors:
        for error in audit_errors:
            print(f"COLLECTION_AUDIT: {error}", file=sys.stderr)
        return COLLECTION_AUDIT_EXIT_CODE
    tests = _select_shard(
        all_tests,
        shard_index=arguments.shard_index,
        shard_count=arguments.shard_count,
    )
    if not tests:
        print("No tests selected for this shard.", file=sys.stderr)
        return 2
    retried_modules: list[str] = []
    with TemporaryDirectory(prefix="mohan-test-suite-") as suite_temp:
        suite_root = Path(suite_temp)
        for index, test in enumerate(tests, start=1):
            print(f"[{index}/{len(tests)}] {test.name}", flush=True)
            try:
                commands = _test_commands(test)
            except OSError, SyntaxError, UnicodeError:
                print(
                    f"FAILED: {test.name} (exit {MALFORMED_TEST_EXIT_CODE})",
                    file=sys.stderr,
                )
                _print_retried_modules(retried_modules)
                return MALFORMED_TEST_EXIT_CODE
            for command_index, command in enumerate(commands, start=1):
                returncode = _run_with_retry(
                    command,
                    test,
                    command_index,
                    suite_root,
                    index,
                    retried_modules,
                )
                if returncode:
                    if returncode == TEST_TIMEOUT_EXIT_CODE:
                        print(
                            f"FAILED: {test.name} "
                            f"(timeout {TEST_TIMEOUT_SECONDS}s)",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            f"FAILED: {test.name} (exit {returncode})",
                            file=sys.stderr,
                        )
                    _print_retried_modules(retried_modules)
                    return returncode
    # A module that only passed after a retry still exits 0, but the summary
    # must name it so intermittent failures never stay invisible.
    _print_retried_modules(retried_modules)
    print(f"ALL_{len(tests)}_TESTS_OK")
    return 0


def _run_with_retry(
    command: list[str],
    test: Path,
    command_index: int,
    suite_root: Path,
    index: int,
    retried_modules: list[str],
) -> int:
    """Run one test command, retrying once on a fresh isolated environment.

    Timing-sensitive Qt tests occasionally fail on slow CI runners because of
    event-loop races or a transient file lock left by a prior attempt.  A
    single retry in a brand-new temporary directory absorbs that noise while
    still failing deterministically broken tests (which fail twice in a row).
    """
    for attempt in range(TEST_RETRY_ATTEMPTS + 1):
        attempt_root = suite_root / (
            f"{index:03d}-{test.stem}-attempt{attempt}"
        )
        try:
            returncode = _run_test_process(
                command,
                cwd=TESTS_DIR.parent,
                environment=_isolated_environment(
                    attempt_root / f"{command_index:02d}"
                ),
            )
        except subprocess.TimeoutExpired:
            # The caller prints the single, stable timeout line; a timeout is
            # never retried because it signals a genuinely hung test, not a
            # timing race.
            return TEST_TIMEOUT_EXIT_CODE
        if returncode == 0:
            return 0
        if attempt < TEST_RETRY_ATTEMPTS:
            if test.name not in retried_modules:
                retried_modules.append(test.name)
            print(
                f"RETRY: {test.name} (attempt {attempt + 1} failed, "
                f"retrying in a fresh environment)",
                file=sys.stderr,
            )
    return returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
