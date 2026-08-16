from __future__ import annotations

lazy import ast
lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
BOOTSTRAP_PATH = PROJECT_ROOT / "application" / "application_bootstrap.py"
SELF_TEST_PATH = PROJECT_ROOT / "application" / "packaged_self_test.py"


def module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def top_level_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def imported_symbols(tree: ast.Module) -> dict[str, str]:
    imports: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for alias in node.names:
            imports[alias.asname or alias.name] = node.module
    return imports


def called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def string_literals(tree: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_app_is_exact_thirteen_line_thin_delegate() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    assert len(source.splitlines()) == 13
    tree = module_tree(APP_PATH)
    functions = top_level_functions(tree)
    assert set(functions) == {"main"}
    main = functions["main"]
    assert not main.args.args
    assert len(main.body) == 1
    returned = main.body[0]
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert isinstance(returned.value.func, ast.Name)
    assert returned.value.func.id == "run_application"
    assert not returned.value.args
    assert not returned.value.keywords
    assert imported_symbols(tree) == {
        "annotations": "__future__",
        "run_application": "application.application_bootstrap",
    }


def test_bootstrap_owns_runtime_composition_contract() -> None:
    tree = module_tree(BOOTSTRAP_PATH)
    imports = imported_symbols(tree)
    functions = top_level_functions(tree)
    assert imports["QApplication"] == "PySide6.QtWidgets"
    assert imports["CompanionWindow"] == "presentation.companion_window"
    assert imports["run_packaged_self_test"] == "application.packaged_self_test"
    assert {
        "_argument_value",
        "_write_jit_status",
        "_prepare_platform",
        "_create_application",
        "_run_smoke_event_loop",
        "run_application",
    } <= functions.keys()
    run_application = functions["run_application"]
    calls = called_names(run_application)
    literals = string_literals(tree)
    assert {"_write_jit_status", "_create_application", "CompanionWindow"} <= calls
    assert "run_packaged_self_test" in calls
    assert {
        "--self-test",
        "--smoke-auto-exit",
        "--self-test-output=",
        "--jit-status-output=",
    } <= literals


def test_importing_app_does_not_load_qt_or_window_owners() -> None:
    script = """
lazy import sys

lazy import app

for forbidden in ("PySide6", "presentation.companion_window"):
    assert forbidden not in sys.modules, sorted(
        name for name in sys.modules if name == forbidden or name.startswith(forbidden + ".")
    )
print("THIN_APP_IMPORT_OK")
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "THIN_APP_IMPORT_OK"


def test_packaged_self_test_has_one_product_owner() -> None:
    owners = []
    for package in ("application", "domain", "infrastructure", "integrations", "presentation"):
        for path in sorted((PROJECT_ROOT / package).rglob("*.py")):
            functions = top_level_functions(module_tree(path))
            if "run_packaged_self_test" in functions:
                owners.append(path.relative_to(PROJECT_ROOT).as_posix())
    assert owners == ["application/packaged_self_test.py"]
    assert imported_symbols(module_tree(BOOTSTRAP_PATH)).get(
        "run_packaged_self_test"
    ) == "application.packaged_self_test"
    exports = next(
        node
        for node in module_tree(SELF_TEST_PATH).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )
    assert ast.literal_eval(exports.value) == ("run_packaged_self_test",)


def test_entry_and_bootstrap_define_no_windows_or_business_constants() -> None:
    for path in (APP_PATH, BOOTSTRAP_PATH):
        tree = module_tree(path)
        classes = {
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        }
        assert not classes.intersection({"Dashboard", "CompanionWindow"})
        assignments = [
            *(
                target.id
                for target in (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else (node.target,)
                )
                if isinstance(target, ast.Name)
                and target.id.isupper()
                and target.id != "__all__"
            )
            for node in tree.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        assert not assignments, f"business constants in {path.name}: {assignments}"
