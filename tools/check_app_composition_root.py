from __future__ import annotations

lazy import ast
lazy import json
lazy import sys
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from typing import Final

MAX_PHYSICAL_LINES: Final = 50
BOOTSTRAP_OWNER_MARKERS: Final = ("bootstrap", "composition_root")
FORBIDDEN_IMPORT_SEGMENTS: Final = frozenset(
    {
        "adapter",
        "adapters",
        "client",
        "clients",
        "database",
        "db",
        "gateway",
        "gateways",
        "infrastructure",
        "integration",
        "integrations",
        "persistence",
        "provider",
        "providers",
        "repository",
        "repositories",
        "store",
        "stores",
    }
)
FORBIDDEN_IMPORT_SUFFIXES: Final = tuple(
    f"_{segment}" for segment in FORBIDDEN_IMPORT_SEGMENTS
)


@dataclass(frozen=True, slots=True)
class CompositionRootIssue:
    code: str
    message: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class CompositionRootReport:
    path: str
    physical_lines: int
    issues: tuple[CompositionRootIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class ImportedOwner:
    local_name: str
    module: str


def _issue(code: str, message: str, node: ast.AST | None = None) -> CompositionRootIssue:
    return CompositionRootIssue(code, message, getattr(node, "lineno", None))


def _imported_owners(tree: ast.Module) -> dict[str, ImportedOwner]:
    owners: dict[str, ImportedOwner] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.partition(".")[0]
                owners[local_name] = ImportedOwner(local_name, alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local_name = alias.asname or alias.name
                owners[local_name] = ImportedOwner(local_name, node.module)
    return owners


def _import_module_names(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    return (node.module,) if node.module else ()


def _is_infrastructure_detail(module: str) -> bool:
    segments = module.casefold().split(".")
    return any(
        segment in FORBIDDEN_IMPORT_SEGMENTS
        or segment.endswith(FORBIDDEN_IMPORT_SUFFIXES)
        for segment in segments
    )


def _validate_imports(tree: ast.Module) -> list[CompositionRootIssue]:
    issues: list[CompositionRootIssue] = []
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        issues.extend(
            _issue(
                "infrastructure_import_forbidden",
                f"app.py must not import integration or infrastructure detail: {module}",
                node,
            )
            for module in _import_module_names(node)
            if _is_infrastructure_detail(module)
        )
    return issues


def _is_module_docstring(node: ast.AST, position: int) -> bool:
    return (
        position == 0
        and isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_all_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "__all__"
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__"


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If) or node.orelse:
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


def _called_name(call: ast.Call) -> tuple[str, ...] | None:
    names: list[str] = []
    current: ast.expr = call.func
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    names.append(current.id)
    return tuple(reversed(names))


def _single_main_call(function: ast.FunctionDef) -> ast.Call | None:
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
    if len(body) != 1:
        return None
    statement = body[0]
    if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Call):
        return statement.value
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return statement.value
    return None


def _validate_main(
    functions: list[ast.FunctionDef],
    owners: dict[str, ImportedOwner],
) -> list[CompositionRootIssue]:
    if len(functions) != 1:
        return [
            _issue(
                "main_definition_required",
                "app.py must define exactly one synchronous main() function.",
            )
        ]
    function = functions[0]
    issues: list[CompositionRootIssue] = []
    if function.args.args or function.args.posonlyargs or function.args.kwonlyargs or function.args.vararg or function.args.kwarg:
        issues.append(_issue("main_arguments_forbidden", "main() must not accept arguments.", function))
    if function.decorator_list:
        issues.append(_issue("main_decorator_forbidden", "main() must not use decorators.", function))
    call = _single_main_call(function)
    if call is None or call.args or call.keywords:
        issues.append(
            _issue(
                "main_not_thin_delegate",
                "main() must contain only one argument-free call to an imported bootstrap owner.",
                function,
            )
        )
        return issues
    called_name = _called_name(call)
    owner = owners.get(called_name[0]) if called_name else None
    if owner is None:
        issues.append(
            _issue(
                "bootstrap_owner_not_imported",
                "main() must delegate to a callable owned by an imported bootstrap module.",
                call,
            )
        )
        return issues
    if not any(marker in owner.module.casefold() for marker in BOOTSTRAP_OWNER_MARKERS):
        issues.append(
            _issue(
                "bootstrap_owner_not_explicit",
                f"Bootstrap owner must be explicit in its module name: {owner.module}",
                call,
            )
        )
    return issues


def _validate_guard(guards: list[ast.If]) -> list[CompositionRootIssue]:
    if len(guards) != 1:
        return [
            _issue(
                "main_guard_required",
                'app.py must contain exactly one if __name__ == "__main__" guard.',
            )
        ]
    guard = guards[0]
    if len(guard.body) != 1:
        return [_issue("main_guard_not_thin", "The __main__ guard must only call main().", guard)]
    statement = guard.body[0]
    call = statement.exc if isinstance(statement, ast.Raise) else getattr(statement, "value", None)
    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "SystemExit":
        call = call.args[0] if len(call.args) == 1 else None
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "main"
        and not call.args
        and not call.keywords
    ):
        return [_issue("main_guard_not_thin", "The __main__ guard must only call main().", guard)]
    return []


def _validate_top_level(
    tree: ast.Module,
) -> tuple[list[CompositionRootIssue], list[ast.FunctionDef], list[ast.If]]:
    issues: list[CompositionRootIssue] = []
    functions: list[ast.FunctionDef] = []
    guards: list[ast.If] = []
    for position, node in enumerate(tree.body):
        if _is_module_docstring(node, position) or isinstance(node, (ast.Import, ast.ImportFrom)) or _is_all_assignment(node):
            continue
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            functions.append(node)
        elif _is_main_guard(node):
            guards.append(node)
        else:
            issues.append(_forbidden_top_level_issue(node))
    return issues, functions, guards


def _forbidden_top_level_issue(node: ast.AST) -> CompositionRootIssue:
    if isinstance(node, ast.ClassDef):
        special_codes = {
            "Dashboard": "dashboard_defined_in_app",
            "CompanionWindow": "companion_window_defined_in_app",
        }
        code = special_codes.get(node.name, "top_level_class_forbidden")
        return _issue(code, f"app.py must not define class {node.name}.", node)
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return _issue(
            "business_constant_defined_in_app",
            "Only __all__ may be assigned in app.py.",
            node,
        )
    return _issue(
        "top_level_statement_forbidden",
        f"Top-level {type(node).__name__} is not allowed in app.py.",
        node,
    )


def inspect_composition_root(path: Path) -> CompositionRootReport:
    source = path.read_text(encoding="utf-8")
    physical_lines = len(source.splitlines())
    issues: list[CompositionRootIssue] = []
    if physical_lines > MAX_PHYSICAL_LINES:
        issues.append(
            CompositionRootIssue(
                "physical_line_limit_exceeded",
                f"app.py has {physical_lines} physical lines; maximum is {MAX_PHYSICAL_LINES}.",
            )
        )
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        issues.append(CompositionRootIssue("syntax_error", str(error), error.lineno))
        return CompositionRootReport(str(path), physical_lines, tuple(issues))

    top_level_issues, functions, guards = _validate_top_level(tree)
    issues.extend(top_level_issues)
    issues.extend(_validate_imports(tree))
    issues.extend(_validate_main(functions, _imported_owners(tree)))
    issues.extend(_validate_guard(guards))
    return CompositionRootReport(str(path), physical_lines, tuple(issues))


def _default_app_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app.py"


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    path = Path(arguments[0]).resolve() if arguments else _default_app_path()
    report = inspect_composition_root(path)
    payload = {
        "passed": report.passed,
        "path": report.path,
        "physical_lines": report.physical_lines,
        "issues": [asdict(issue) for issue in report.issues],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
