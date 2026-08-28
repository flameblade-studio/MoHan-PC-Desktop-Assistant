from __future__ import annotations

lazy import ast
lazy import warnings
lazy from contextlib import suppress
lazy from pathlib import Path

lazy from tools.check_layered_imports import (
    FEATURE_COMPOSITION_IMPORTS,
    FORBIDDEN_LAYER_IMPORTS,
    PHYSICALLY_LAYERED_ROOTS,
    ParsedModule,
    compatibility_facade_issues,
    discover_modules,
    legacy_root_ownership,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER_NAMES = (
    "presentation",
    "application",
    "domain",
    "integrations",
    "infrastructure",
)
# Layer-module line-count ratchet (approved by the project owner on 2026-08-28):
# * MAX_LAYER_MODULE_LINES is the global ceiling; the release plan steps it
#   down (v4.5.x = 1200, v4.6 = 1100, then -100 per release) until it meets
#   MAX_NEW_LAYER_MODULE_LINES.
# * Modules absent from LAYER_MODULE_LINE_BASELINE are new and must stay
#   within MAX_NEW_LAYER_MODULE_LINES.
# * Baselined modules may never exceed min(baseline, MAX_LAYER_MODULE_LINES),
#   and the baseline only moves down: whoever slims a module must lower its
#   entry to the new measured count in the same PR (and say so in the PR
#   body); entries at or below MAX_NEW_LAYER_MODULE_LINES must be removed so
#   the module is gated as new from then on.
MAX_LAYER_MODULE_LINES = 1_200
MAX_NEW_LAYER_MODULE_LINES = 800
# Measured 2026-08-28 (re-baselined after the audit-wave PRs #91-#96
# landed; the original scan predated their in-flight line counts) with
# the gate's own counting rule
# (utf-8-sig decode + str.splitlines()).
LAYER_MODULE_LINE_BASELINE = {
    "application.presentation_ports": 1_063,
    "domain.outfit_pack": 974,
    "infrastructure.db": 1_200,
    "infrastructure.profile_transfer": 1_075,
    "integrations.azure_speech": 864,
    "integrations.realtime_voice": 878,
    "integrations.speech": 1_197,
    "presentation.companion_core": 1_132,
    "presentation.companion_face_animation": 1_160,
    "presentation.companion_face_assets": 898,
    "presentation.companion_speech_runtime": 1_182,
    "presentation.companion_visual_dynamics": 960,
    "presentation.dashboard_conversation": 884,
    "presentation.dashboard_settings": 912,
    "presentation.dashboard_shell": 1_198,
    "presentation.dashboard_today_memory": 822,
    "presentation.dashboard_voice": 1_085,
}
MAX_ROOT_APP_LINES = 50
NON_PRODUCT_PYTHON_DIRECTORIES = frozenset({
    "artifacts",  # ignored local generation, training, and validation evidence
    "build-temp",  # generated packaging/build output
    "constants",  # shared, dependency-free constant library (not a product layer)
    "dist",  # generated release/package output
    "native",  # Rust workspace; any Python files below it are generated bindings
    "tests",
    "tmp",  # local recovery and audit evidence, never product code
    "tools",
})
COMPOSITION_ROOT_MODULES = frozenset({"app"})
APP_IMPLEMENTATION_NODES = (
    ast.AsyncFor,
    ast.AsyncWith,
    ast.ClassDef,
    ast.For,
    ast.If,
    ast.Match,
    ast.Try,
    ast.While,
    ast.With,
)


def module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def parse_module(path: Path, source: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source, filename=str(path))


def listed_local_paths() -> tuple[Path, ...]:
    paths = [*PROJECT_ROOT.glob("*.py")]
    for layer in LAYER_NAMES:
        paths.extend((PROJECT_ROOT / layer).rglob("*.py"))
    return tuple(sorted(paths))


def discover_local_modules() -> dict[str, tuple[Path, str]]:
    for _attempt in range(5):
        paths = listed_local_paths()
        try:
            before = {
                path: (path.stat().st_size, path.stat().st_mtime_ns)
                for path in paths
            }
            sources = {
                path: path.read_text(encoding="utf-8-sig")
                for path in paths
            }
            after = {
                path: (path.stat().st_size, path.stat().st_mtime_ns)
                for path in paths
            }
        except FileNotFoundError:
            continue
        if paths == listed_local_paths() and before == after:
            return {
                name: (path, sources[path])
                for path in paths
                if (name := module_name(path))
            }
    raise AssertionError("Product modules changed throughout the architecture scan")


def root_product_module_names(
    modules: dict[str, tuple[Path, str]],
) -> frozenset[str]:
    return frozenset(
        module
        for module, (path, _source) in modules.items()
        if path.parent == PROJECT_ROOT
    )


def five_layer_python_paths() -> dict[str, tuple[Path, ...]]:
    return {
        layer: tuple(sorted((PROJECT_ROOT / layer).rglob("*.py")))
        for layer in LAYER_NAMES
    }


def is_main_guard(node: ast.stmt) -> bool:
    if not isinstance(node, ast.If):
        return False
    comparison = node.test
    if not (
        isinstance(comparison, ast.Compare)
        and len(comparison.ops) == 1
        and isinstance(comparison.ops[0], ast.Eq)
        and len(comparison.comparators) == 1
    ):
        return False
    operands = (comparison.left, comparison.comparators[0])
    return any(
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
        for left, right in (operands, tuple(reversed(operands)))
    )


def top_level_import_targets(tree: ast.Module) -> tuple[str, ...]:
    targets: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return tuple(targets)


def is_module_docstring(position: int, node: ast.stmt) -> bool:
    return (
        position == 0
        and isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def assignment_targets_name(node: ast.stmt, name: str) -> bool:
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = (node.target,)
    else:
        return False
    return any(isinstance(target, ast.Name) and target.id == name for target in targets)


def assignment_value(node: ast.stmt) -> ast.expr | None:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return node.value
    return None


def literal_string_sequence(node: ast.expr | None) -> tuple[str, ...] | None:
    if node is None:
        return None
    value = None
    with suppress(TypeError, ValueError):
        value = ast.literal_eval(node)
    if not isinstance(value, (tuple, list)):
        return None
    if not all(isinstance(name, str) for name in value):
        return None
    return tuple(value)


def is_static_all_assignment(node: ast.stmt) -> bool:
    return assignment_targets_name(node, "__all__") and literal_string_sequence(
        assignment_value(node)
    ) is not None


def app_statement_is_composition_only(position: int, node: ast.stmt) -> bool:
    return (
        is_module_docstring(position, node)
        or isinstance(node, (ast.Import, ast.ImportFrom))
        or (isinstance(node, ast.FunctionDef) and node.name == "main")
        or is_static_all_assignment(node)
        or is_main_guard(node)
    )


def assert_app_import_boundary(
    tree: ast.Module,
    modules: dict[str, tuple[Path, str]],
) -> None:
    imports = top_level_import_targets(tree)
    assert any(
        target == "application" or target.startswith("application.")
        for target in imports
    ), "Root app.py must delegate to a canonical application-layer entrypoint"
    unexpected_imports = tuple(
        target
        for target in imports
        if target.partition(".")[0] not in {"__future__", "application", "sys"}
    )
    assert not unexpected_imports, (
        "Root app.py may import only __future__, sys, and the canonical "
        f"application layer; found {unexpected_imports}"
    )
    forbidden_roots = (
        root_product_module_names(modules) - {"app"}
    ) | frozenset({"presentation", "domain", "integrations", "infrastructure"})
    forbidden_imports = tuple(
        target
        for target in imports
        if target.partition(".")[0] in forbidden_roots
    )
    assert not forbidden_imports, (
        "Root app.py may compose through application only; forbidden imports: "
        f"{forbidden_imports}"
    )


def assert_app_top_level_is_composition_only(tree: ast.Module) -> None:
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    assert all(
        isinstance(function, ast.FunctionDef) and function.name == "main"
        for function in functions
    ), "Root app.py may define only one synchronous main() wrapper"
    assert len(functions) <= 1, "Root app.py may define at most one main() wrapper"
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body), (
        "Root app.py must not own implementation classes"
    )
    unexpected = tuple(
        type(node).__name__
        for position, node in enumerate(tree.body)
        if not app_statement_is_composition_only(position, node)
    )
    assert not unexpected, (
        "Root app.py contains executable or implementation statements outside "
        f"imports, static __all__, main(), and the __main__ guard: {unexpected}"
    )
    for function in functions:
        assert not function.decorator_list, (
            "Root app.py main() must not use decorators"
        )
        assert not (
            function.args.posonlyargs
            or function.args.args
            or function.args.vararg
            or function.args.kwonlyargs
            or function.args.kwarg
        ), "Root app.py main() must not accept arguments"
        nested_implementation = tuple(
            node
            for node in ast.walk(function)
            if node is not function and isinstance(node, APP_IMPLEMENTATION_NODES)
        )
        assert not nested_implementation, (
            "Root app.py main() must remain a flat composition wrapper without "
            "business control flow"
        )


def statement_call(node: ast.stmt) -> ast.Call | None:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return node.value
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
        return node.value
    if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
        return node.exc
    return None


def executable_function_body(function: ast.FunctionDef) -> tuple[ast.stmt, ...]:
    return tuple(
        node
        for position, node in enumerate(function.body)
        if not is_module_docstring(position, node)
    )


def assert_main_wrapper_delegates_once(
    tree: ast.Module,
    aliases: dict[str, str],
) -> None:
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    if not functions:
        return
    body = executable_function_body(functions[0])
    assert len(body) == 1, (
        "Root app.py main() must contain exactly one application-layer delegate call"
    )
    call = statement_call(body[0])
    resolved = resolved_callable_name(call.func, aliases) if call else None
    assert resolved is not None and resolved.startswith("application."), (
        "Root app.py main() may only call its application-layer entrypoint"
    )


def assert_app_delegates_from_main_guard(tree: ast.Module) -> None:
    guards = tuple(node for node in tree.body if is_main_guard(node))
    assert len(guards) == 1, (
        "Root app.py must contain exactly one explicit __name__ == '__main__' guard"
    )
    aliases = import_aliases(tree)
    assert_main_wrapper_delegates_once(tree, aliases)
    guard = guards[0]
    assert not guard.orelse and len(guard.body) == 1, (
        "Root app.py __main__ guard must contain one launch statement and no else"
    )
    assert statement_call(guard.body[0]) is not None, (
        "Root app.py __main__ guard may only invoke the launch entrypoint"
    )
    guard_calls = tuple(
        name
        for node in ast.walk(guard.body[0])
        if isinstance(node, ast.Call)
        if (name := resolved_callable_name(node.func, aliases)) is not None
    )
    allowed_guard_calls = tuple(
        name
        for name in guard_calls
        if name in {"main", "SystemExit", "sys.exit"}
        or name.startswith("application.")
    )
    assert guard_calls and len(allowed_guard_calls) == len(guard_calls), (
        "Root app.py __main__ guard contains calls beyond launch/SystemExit: "
        f"{guard_calls}"
    )
    assert any(
        name == "main" or name.startswith("application.")
        for name in guard_calls
    ), (
        "The root app.py __main__ guard must call main() or the application entrypoint"
    )
    all_calls = tuple(
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (name := resolved_callable_name(node.func, aliases)) is not None
    )
    assert any(
        call == "application" or call.startswith("application.")
        for call in all_calls
    ), "Root app.py must call its imported application-layer entrypoint"


def is_facade_import(node: ast.stmt, owner: str) -> bool:
    if isinstance(node, ast.ImportFrom):
        return node.module in {"__future__", owner}
    if isinstance(node, ast.Import):
        return all(alias.name in {"sys", "importlib", owner} for alias in node.names)
    return False


def module_alias_owner(
    node: ast.stmt,
    aliases: dict[str, str],
) -> str | None:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    target = node.targets[0]
    if not (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Attribute)
        and isinstance(target.value.value, ast.Name)
        and target.value.value.id == "sys"
        and target.value.attr == "modules"
        and isinstance(target.slice, ast.Name)
        and target.slice.id == "__name__"
    ):
        return None
    if isinstance(node.value, ast.Name):
        return aliases.get(node.value.id)
    if not isinstance(node.value, ast.Call) or not is_dynamic_import_call(
        node.value, aliases
    ):
        return None
    argument = dynamic_import_argument(node.value)
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    return None


def facade_statement_is_static(
    position: int,
    node: ast.stmt,
    aliases: dict[str, str],
    owner: str,
) -> bool:
    return (
        is_module_docstring(position, node)
        or is_facade_import(node, owner)
        or is_static_all_assignment(node)
        or module_alias_owner(node, aliases) == owner
    )


def named_compatibility_export_issue(
    facade: str,
    tree: ast.Module,
    owner: str,
) -> str | None:
    imported = tuple(
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == owner
        for alias in node.names
    )
    if not imported:
        return None
    assignments = tuple(
        node
        for node in tree.body
        if assignment_targets_name(node, "__all__")
    )
    if len(assignments) != 1:
        return f"{facade}: named re-export requires exactly one static __all__"
    exported = literal_string_sequence(assignment_value(assignments[0]))
    if exported is None:
        return f"{facade}: __all__ must be a static sequence of strings"
    if len(exported) != len(set(exported)):
        return f"{facade}: __all__ contains duplicate names"
    if set(exported) != set(imported):
        return f"{facade}: imports and __all__ differ"
    return None


def ownership_by_root_module() -> dict[str, tuple[str, str]]:
    return {
        entry.module: (entry.layer, entry.location)
        for entry in legacy_root_ownership()
    }


def root_facade_owners(
    modules: dict[str, tuple[Path, str]],
) -> dict[str, str]:
    ownership = ownership_by_root_module()
    return {
        facade: f"{ownership[facade][0]}.{facade}"
        for facade in root_product_module_names(modules) - COMPOSITION_ROOT_MODULES
        if facade in ownership
    }


def root_facade_static_violations(
    modules: dict[str, tuple[Path, str]],
) -> tuple[str, ...]:
    violations: list[str] = []
    for facade, owner in sorted(root_facade_owners(modules).items()):
        path, source = modules[facade]
        tree = parse_module(path, source)
        aliases = import_aliases(tree)
        for position, node in enumerate(tree.body):
            if not facade_statement_is_static(position, node, aliases, owner):
                violations.append(
                    f"{facade}:{getattr(node, 'lineno', 0)} {type(node).__name__}"
                )
    return tuple(violations)


def root_modules_with_implementation(
    modules: dict[str, tuple[Path, str]],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                violation.partition(":")[0]
                for violation in root_facade_static_violations(modules)
            }
        )
    )


def resolve_from_base(
    current_module: str,
    current_path: Path,
    node: ast.ImportFrom,
) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = current_module.split(".")
    if current_path.name != "__init__.py":
        package_parts.pop()
    keep = max(0, len(package_parts) - node.level + 1)
    base_parts = package_parts[:keep]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def callable_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = callable_name(node.value)
        return f"{owner}.{node.attr}" if owner else None
    return None


def import_aliases(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            aliases.update(
                {
                    alias.asname or alias.name.partition(".")[0]: alias.name
                    for alias in node.names
                }
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            aliases.update(
                {
                    alias.asname or alias.name: f"{node.module}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                }
            )
    return aliases


def resolved_callable_name(node: ast.expr, aliases: dict[str, str]) -> str | None:
    function = callable_name(node)
    if function is None:
        return None
    head, separator, tail = function.partition(".")
    resolved = aliases.get(head, head)
    return f"{resolved}.{tail}" if separator else resolved


def dynamic_import_argument(node: ast.Call) -> ast.expr | None:
    if node.args:
        return node.args[0]
    return next(
        (keyword.value for keyword in node.keywords if keyword.arg == "name"),
        None,
    )


def is_dynamic_import_call(node: ast.Call, aliases: dict[str, str]) -> bool:
    return resolved_callable_name(node.func, aliases) in {
        "__import__",
        "builtins.__import__",
        "importlib.import_module",
    }


def resolve_dynamic_import(
    current_module: str,
    current_path: Path,
    target: str,
) -> str:
    level = len(target) - len(target.lstrip("."))
    if level == 0:
        return target
    package_parts = current_module.split(".")
    if current_path.name != "__init__.py":
        package_parts.pop()
    keep = max(0, len(package_parts) - level + 1)
    suffix = target[level:]
    return ".".join((*package_parts[:keep], *suffix.split("."))).rstrip(".")


def declared_imports(
    current_module: str,
    current_path: Path,
    source: str,
) -> tuple[tuple[str, int], ...]:
    tree = parse_module(current_path, source)
    aliases = import_aliases(tree)
    targets: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend((alias.name, node.lineno) for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        base = resolve_from_base(current_module, current_path, node)
        if base:
            targets.append((base, node.lineno))
        targets.extend(
            (f"{base}.{alias.name}" if base else alias.name, node.lineno)
            for alias in node.names
            if alias.name != "*"
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not is_dynamic_import_call(node, aliases):
            continue
        target = dynamic_import_argument(node)
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            targets.append(
                (
                    resolve_dynamic_import(
                        current_module,
                        current_path,
                        target.value,
                    ),
                    node.lineno,
                )
            )
    return tuple(dict.fromkeys(targets))


def local_import_targets(
    target: str,
    known_modules: frozenset[str],
) -> frozenset[str]:
    parts = target.split(".")
    direct = frozenset(
        candidate
        for index in range(1, len(parts) + 1)
        if (candidate := ".".join(parts[:index])) in known_modules
    )
    if direct:
        return direct
    root = parts[0]
    ownership = ownership_by_root_module().get(root)
    if ownership is None:
        return frozenset()
    owner = f"{ownership[0]}.{root}"
    return frozenset({owner}) if owner in known_modules else frozenset()


def complete_import_graph(
    modules: dict[str, tuple[Path, str]],
) -> dict[str, frozenset[str]]:
    known_modules = frozenset(modules)
    return {
        module: frozenset(
            target
            for imported, _line in declared_imports(module, path, source)
            for target in local_import_targets(imported, known_modules)
        )
        for module, (path, source) in modules.items()
    }


def modules_reaching(
    graph: dict[str, frozenset[str]],
    destination: str,
) -> tuple[str, ...]:
    reverse_graph: dict[str, set[str]] = {module: set() for module in graph}
    for source, targets in graph.items():
        for target in targets:
            reverse_graph[target].add(source)

    reached = {destination}
    pending = [destination]
    while pending:
        current = pending.pop()
        for source in reverse_graph[current] - reached:
            reached.add(source)
            pending.append(source)
    reached.remove(destination)
    return tuple(sorted(reached))


def strongly_connected_components(
    graph: dict[str, frozenset[str]],
) -> tuple[tuple[str, ...], ...]:
    next_index = 0
    indexes: dict[str, int] = {}
    low_links: dict[str, int] = {}
    active: list[str] = []
    active_nodes: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal next_index
        indexes[node] = next_index
        low_links[node] = next_index
        next_index += 1
        active.append(node)
        active_nodes.add(node)

        for target in sorted(graph[node]):
            if target not in indexes:
                visit(target)
                low_links[node] = min(low_links[node], low_links[target])
            elif target in active_nodes:
                low_links[node] = min(low_links[node], indexes[target])

        if low_links[node] != indexes[node]:
            return
        component: list[str] = []
        while active:
            member = active.pop()
            active_nodes.remove(member)
            component.append(member)
            if member == node:
                break
        components.append(tuple(sorted(component)))

    for module in sorted(graph):
        if module not in indexes:
            visit(module)
    return tuple(sorted(components))


def test_every_existing_root_product_module_has_one_classification() -> None:
    actual = root_product_module_names(discover_local_modules())
    entries = legacy_root_ownership()
    declared = tuple(entry.module for entry in entries)
    duplicates = tuple(
        sorted(module for module in frozenset(declared) if declared.count(module) != 1)
    )
    assert not duplicates, f"Duplicate root ownership classifications: {duplicates}"
    assert actual <= frozenset(declared), (
        f"Unclassified root modules: {tuple(sorted(actual - frozenset(declared)))}"
    )


def test_five_layer_gate_scans_every_python_module_not_only_package_markers() -> None:
    inventory = five_layer_python_paths()
    expected_paths = frozenset(
        path.resolve()
        for paths in inventory.values()
        for path in paths
    )
    modules = discover_local_modules()
    scanned_paths = frozenset(
        path.resolve()
        for module, (path, _source) in modules.items()
        if module.partition(".")[0] in LAYER_NAMES
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        checker_modules, checker_parse_issues = discover_modules(PROJECT_ROOT)
    checker_paths = frozenset(module.path.resolve() for module in checker_modules)
    per_layer = {
        layer: len(paths)
        for layer, paths in inventory.items()
    }
    assert scanned_paths == expected_paths, (
        "Five-layer architecture scan does not cover every Python module: "
        f"expected={len(expected_paths)}, scanned={len(scanned_paths)}, "
        f"per_layer={per_layer}, "
        f"missing={tuple(sorted(str(path) for path in expected_paths - scanned_paths))}, "
        f"unexpected={tuple(sorted(str(path) for path in scanned_paths - expected_paths))}"
    )
    assert checker_paths == expected_paths, (
        "The production five-layer checker does not cover every Python module: "
        f"expected={len(expected_paths)}, checked={len(checker_paths)}, "
        f"per_layer={per_layer}, parse_issues={checker_parse_issues}"
    )
    assert len(scanned_paths) > len(LAYER_NAMES), (
        "A five-layer gate must report full module coverage, not merely "
        f"'{len(LAYER_NAMES)} modules checked': per_layer={per_layer}"
    )
    assert all(per_layer.values()), (
        f"Every canonical layer must contain Python modules: {per_layer}"
    )


def test_root_app_is_required_thin_composition_entrypoint() -> None:
    path = PROJECT_ROOT / "app.py"
    assert path.is_file(), (
        "Required root app.py composition entrypoint is missing; "
        "application/app.py is not a substitute"
    )

    source = path.read_text(encoding="utf-8-sig")
    physical_lines = len(source.splitlines())
    assert physical_lines <= MAX_ROOT_APP_LINES, (
        "Root app.py must be a composition-only entrypoint with at most "
        f"50 physical lines; found {physical_lines}"
    )
    tree = parse_module(path, source)
    assert_app_import_boundary(tree, discover_local_modules())
    assert_app_top_level_is_composition_only(tree)
    assert_app_delegates_from_main_guard(tree)


def test_root_classification_has_no_orphaned_records() -> None:
    actual = root_product_module_names(discover_local_modules())
    declared = frozenset(entry.module for entry in legacy_root_ownership())
    physically_layered = frozenset(PHYSICALLY_LAYERED_ROOTS)
    orphaned = tuple(sorted(declared - actual - physically_layered))
    assert not orphaned, (
        f"Root classification contains {len(orphaned)} orphaned records: "
        + ", ".join(orphaned)
    )


def test_no_legacy_root_classification_records_remain() -> None:
    actual = root_product_module_names(discover_local_modules())
    legacy = tuple(
        entry.module
        for entry in legacy_root_ownership()
        if entry.location == "legacy-root"
        and entry.module in actual
        and entry.module not in COMPOSITION_ROOT_MODULES
    )
    assert not legacy, (
        "legacy-root classification must reach zero before release "
        f"({len(legacy)} remain): "
        + ", ".join(legacy)
    )


def test_no_root_legacy_implementation_remains() -> None:
    modules = discover_local_modules()
    expected_facades = root_product_module_names(modules) - COMPOSITION_ROOT_MODULES
    declared_facades = frozenset(root_facade_owners(modules))
    unowned = tuple(sorted(expected_facades - declared_facades))
    missing_owners = tuple(
        sorted(
            f"{facade} -> {owner}"
            for facade, owner in root_facade_owners(modules).items()
            if owner not in modules
        )
    )
    implementation_modules = root_modules_with_implementation(modules)
    assert not implementation_modules, (
        "Root legacy implementation count must be zero; executable root "
        f"modules remain ({len(implementation_modules)}): "
        + ", ".join(implementation_modules)
    )
    assert not unowned, f"Unowned root implementations: {unowned}"
    assert not missing_owners, (
        "Root compatibility facades lack canonical implementations: "
        f"{missing_owners}"
    )


def test_all_compatibility_roots_are_thin_reexports() -> None:
    modules = discover_local_modules()
    root_modules = tuple(
        ParsedModule(
            module,
            path,
            parse_module(path, source),
        )
        for module, (path, source) in modules.items()
        if path.parent == PROJECT_ROOT
    )
    issues = compatibility_facade_issues(root_modules)
    assert not issues, "Compatibility roots contain implementation:\n" + "\n".join(
        f"{issue.module}:{issue.line or 0} {issue.message}" for issue in issues
    )


def test_compatibility_roots_contain_only_static_glue_statements() -> None:
    modules = discover_local_modules()
    violations = root_facade_static_violations(modules)
    assert not violations, "Compatibility roots contain executable logic:\n" + "\n".join(
        violations
    )


def test_named_compatibility_exports_are_static_and_exact() -> None:
    modules = discover_local_modules()
    violations: list[str] = []
    for facade, owner in sorted(root_facade_owners(modules).items()):
        path, source = modules[facade]
        tree = parse_module(path, source)
        issue = named_compatibility_export_issue(facade, tree, owner)
        if issue is not None:
            violations.append(issue)
    assert not violations, "Invalid compatibility exports:\n" + "\n".join(violations)


def test_product_dynamic_import_targets_are_static() -> None:
    violations: list[str] = []
    for module, (path, source) in discover_local_modules().items():
        tree = parse_module(path, source)
        aliases = import_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_dynamic_import_call(node, aliases):
                continue
            argument = dynamic_import_argument(node)
            if not (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            ):
                violations.append(f"{module}:{node.lineno}")
    assert not violations, (
        "Dynamic product imports must use statically auditable module names: "
        + ", ".join(sorted(violations))
    )


def test_product_sources_emit_no_python315_syntax_warnings() -> None:
    violations: list[str] = []
    for module, (path, source) in discover_local_modules().items():
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", SyntaxWarning)
            ast.parse(source, filename=str(path))
        violations.extend(
            f"{module}: {warning.message}"
            for warning in captured
            if issubclass(warning.category, SyntaxWarning)
        )
    assert not violations, "Python 3.15 syntax warnings:\n" + "\n".join(violations)


def test_layered_modules_never_route_through_root_compatibility_facades() -> None:
    modules = discover_local_modules()
    violations: set[tuple[str, int, str, str]] = set()
    for module, (path, source) in sorted(modules.items()):
        if module.partition(".")[0] not in LAYER_NAMES:
            continue
        for target, line in declared_imports(module, path, source):
            facade = target.partition(".")[0]
            owner_layer = PHYSICALLY_LAYERED_ROOTS.get(facade)
            if owner_layer is None:
                continue
            violations.add((module, line, facade, owner_layer))
    assert not violations, (
        "Layer modules must import canonical owners instead of routing through "
        "root compatibility facades:\n"
        + "\n".join(
            f"{module}:{line} -> {facade} -> {owner_layer}.{facade}"
            for module, line, facade, owner_layer in sorted(violations)
        )
    )


def test_layer_modules_never_import_any_root_product_entrypoint() -> None:
    modules = discover_local_modules()
    root_modules = root_product_module_names(modules) | frozenset(
        entry.module for entry in legacy_root_ownership()
    )
    violations: set[tuple[str, int, str]] = set()
    for module, (path, source) in sorted(modules.items()):
        if module.partition(".")[0] not in LAYER_NAMES:
            continue
        for target, line in declared_imports(module, path, source):
            root_target = target.partition(".")[0]
            if root_target in root_modules:
                violations.add((module, line, root_target))
    assert not violations, "Layer modules depend on root product entrypoints:\n" + "\n".join(
        f"{module}:{line} -> {target}"
        for module, line, target in sorted(violations)
    )


def test_layer_packages_have_no_reverse_dependencies() -> None:
    modules = discover_local_modules()
    known_modules = frozenset(modules)
    ownership = ownership_by_root_module()
    violations: set[tuple[str, int, str]] = set()
    for module, (path, source) in sorted(modules.items()):
        source_layer = module.partition(".")[0]
        if source_layer not in LAYER_NAMES:
            continue
        for target, line in declared_imports(module, path, source):
            target_root = target.partition(".")[0]
            allowed_feature_targets = FEATURE_COMPOSITION_IMPORTS.get(
                module,
                frozenset(),
            )
            canonical_targets = local_import_targets(target, known_modules)
            target_layer = (
                next(iter(canonical_targets)).partition(".")[0]
                if canonical_targets
                else (
                    target_root
                    if target_root in LAYER_NAMES
                    else ownership.get(target_root, ("", ""))[0]
                )
            )
            if (
                target_layer in FORBIDDEN_LAYER_IMPORTS[source_layer]
                and not canonical_targets.intersection(allowed_feature_targets)
            ):
                violations.add((module, line, target_root))
    assert not violations, "Reverse layer dependencies:\n" + "\n".join(
        f"{module}:{line} -> {target}"
        for module, line, target in sorted(violations)
    )


def layer_module_line_counts() -> dict[str, int]:
    return {
        module: len(source.splitlines())
        for module, (_path, source) in discover_local_modules().items()
        if module.partition(".")[0] in LAYER_NAMES
    }


def layer_module_line_limit(module: str) -> int:
    baseline = LAYER_MODULE_LINE_BASELINE.get(module, MAX_NEW_LAYER_MODULE_LINES)
    return min(baseline, MAX_LAYER_MODULE_LINES)


def test_layer_implementations_do_not_hide_in_new_giant_modules() -> None:
    oversized = tuple(
        sorted(
            f"{module}={lines} (limit {layer_module_line_limit(module)})"
            for module, lines in layer_module_line_counts().items()
            if lines > layer_module_line_limit(module)
        )
    )
    assert not oversized, (
        "Layer modules must honour the line-count ratchet (new modules stay "
        f"within {MAX_NEW_LAYER_MODULE_LINES} lines, baselined modules within "
        f"min(baseline, {MAX_LAYER_MODULE_LINES})): " + ", ".join(oversized)
    )


def test_layer_module_line_baseline_only_ratchets_down() -> None:
    counts = layer_module_line_counts()
    orphaned = tuple(sorted(frozenset(LAYER_MODULE_LINE_BASELINE) - frozenset(counts)))
    assert not orphaned, (
        "Line-count baseline lists modules that no longer exist; remove them: "
        + ", ".join(orphaned)
    )
    stale = tuple(
        sorted(
            f"{module}: baseline {baseline} -> measured {counts[module]}"
            for module, baseline in LAYER_MODULE_LINE_BASELINE.items()
            if counts[module] < baseline
        )
    )
    assert not stale, (
        "Slimmed modules must ratchet their baseline down to the measured "
        "count in the same PR: " + ", ".join(stale)
    )
    graduated = tuple(
        sorted(
            f"{module}={baseline}"
            for module, baseline in LAYER_MODULE_LINE_BASELINE.items()
            if baseline <= MAX_NEW_LAYER_MODULE_LINES
        )
    )
    assert not graduated, (
        f"Baseline entries at or below {MAX_NEW_LAYER_MODULE_LINES} lines "
        "must be removed so the module is gated as new: " + ", ".join(graduated)
    )


def test_no_unclassified_product_package_can_bypass_layer_rules() -> None:
    unexpected = tuple(
        sorted(
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in PROJECT_ROOT.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and path.name not in LAYER_NAMES
            and path.name not in NON_PRODUCT_PYTHON_DIRECTORIES
            and any(path.rglob("*.py"))
        )
    )
    assert not unexpected, (
        "Python product packages must declare one of the five architecture layers: "
        + ", ".join(unexpected)
    )


def test_complete_local_product_import_graph_has_no_cycles() -> None:
    graph = complete_import_graph(discover_local_modules())
    cyclic_components = tuple(
        component
        for component in strongly_connected_components(graph)
        if len(component) > 1
        or (len(component) == 1 and component[0] in graph[component[0]])
    )
    assert not cyclic_components, "Local product import cycles:\n" + "\n".join(
        " -> ".join(component) for component in cyclic_components
    )


def test_product_modules_do_not_depend_on_app_composition_entrypoint() -> None:
    graph = complete_import_graph(discover_local_modules())
    assert "app" in graph, (
        "Required root app.py composition entrypoint is missing; "
        "a layered application.app module cannot replace it"
    )
    violations = modules_reaching(graph, "app")
    assert not violations, (
        "Product modules depend directly or transitively on root app.py: "
        f"{violations}"
    )


def test_cycle_analysis_detects_a_compatibility_round_trip() -> None:
    graph = {
        "companion_window": frozenset({"presentation.companion_window"}),
        "presentation.companion_window": frozenset({"companion_window"}),
    }
    assert strongly_connected_components(graph) == (
        ("companion_window", "presentation.companion_window"),
    )


def test_dynamic_imports_are_included_in_architecture_analysis() -> None:
    source = """
lazy import importlib as loader
lazy from importlib import import_module as load

DIRECT = loader.import_module("app_resources")
ALIASED = load("integrations.speech")
BUILTIN = __import__("db")
RELATIVE = load(".service")
"""
    targets = frozenset(
        target
        for target, _line in declared_imports(
            "application.sample",
            PROJECT_ROOT / "application" / "sample.py",
            source,
        )
    )
    assert {
        "app_resources",
        "integrations.speech",
        "db",
        "application.service",
    } <= targets
