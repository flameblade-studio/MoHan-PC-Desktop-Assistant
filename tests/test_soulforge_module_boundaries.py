from __future__ import annotations

lazy import ast
lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "docs" / "soulforge" / "module-boundary.json"


@dataclass(frozen=True, slots=True, order=True)
class ImportEdge:
    importer: str
    imported: str
    line: int
    lazy: bool


def _load_boundary() -> dict[str, object]:
    payload = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _module_name(root_name: str, path: Path) -> str:
    relative = path.relative_to(ROOT / root_name).with_suffix("")
    parts = (root_name, *relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _discover_modules(source_roots: tuple[str, ...]) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for root_name in source_roots:
        package_root = ROOT / root_name
        for path in sorted(package_root.rglob("*.py")):
            name = _module_name(root_name, path)
            assert name not in modules, name
            modules[name] = path
    return modules


def _classification_map(payload: dict[str, object]) -> dict[str, str]:
    raw = payload["classifications"]
    assert isinstance(raw, dict)
    result: dict[str, str] = {}
    for classification, names in raw.items():
        assert classification in {
            "engine",
            "mohan_product_shell",
            "huapu",
            "pending_split",
        }
        assert isinstance(names, list)
        assert names == sorted(names)
        for name in names:
            assert isinstance(name, str)
            assert name not in result, name
            result[name] = classification
    return result


def _resolve_from_base(
    module_name: str,
    path: Path,
    node: ast.ImportFrom,
) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = module_name.split(".")
    if path.name != "__init__.py":
        package_parts.pop()
    keep = max(0, len(package_parts) - node.level + 1)
    base_parts = package_parts[:keep]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _local_target(target: str, known: frozenset[str]) -> str | None:
    candidate = target
    while candidate:
        if candidate in known:
            return candidate
        candidate, separator, _remainder = candidate.rpartition(".")
        if not separator:
            return None
    return None


def _importlib_bindings(tree: ast.AST) -> tuple[frozenset[str], frozenset[str]]:
    """Names bound to the importlib module and to importlib.import_module."""

    modules = {"importlib"}
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "importlib"
            )
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "importlib":
            functions.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "import_module"
            )
    return frozenset(modules), frozenset(functions)


def _literal_dynamic_import(
    node: ast.Call,
    importlib_names: frozenset[str] = frozenset({"importlib"}),
    import_module_names: frozenset[str] = frozenset(),
) -> str | None:
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    value = node.args[0].value
    if not isinstance(value, str):
        return None
    function = node.func
    if isinstance(function, ast.Name) and function.id in {"__import__", *import_module_names}:
        return value
    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id in importlib_names
        and function.attr == "import_module"
    ):
        return value
    return None


def _import_edges(
    module_name: str,
    path: Path,
    known: frozenset[str],
) -> tuple[ImportEdge, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    importlib_names, import_module_names = _importlib_bindings(tree)
    edges: set[ImportEdge] = set()
    for node in ast.walk(tree):
        targets: list[str] = []
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_base(module_name, path, node)
            if base:
                targets.append(base)
            targets.extend(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
            )
        elif isinstance(node, ast.Call):
            target = _literal_dynamic_import(
                node, importlib_names, import_module_names
            )
            if target is not None:
                targets.append(target)
        for target in targets:
            local = _local_target(target, known)
            if local is None or local == module_name:
                continue
            edges.add(
                ImportEdge(
                    module_name,
                    local,
                    node.lineno,
                    bool(getattr(node, "is_lazy", False)),
                )
            )
    return tuple(sorted(edges))


def _violations(
    modules: dict[str, Path],
    classifications: dict[str, str],
    forbidden: frozenset[tuple[str, str]],
) -> tuple[ImportEdge, ...]:
    known = frozenset(modules)
    violations: list[ImportEdge] = []
    for name, path in modules.items():
        source = classifications[name]
        for edge in _import_edges(name, path, known):
            target = classifications[edge.imported]
            if (source, target) in forbidden:
                violations.append(edge)
    return tuple(sorted(violations))


def _violation_key(edge: ImportEdge) -> tuple[str, str]:
    return edge.importer, edge.imported


def test_every_soulforge_candidate_module_has_one_explicit_owner() -> None:
    payload = _load_boundary()
    roots = tuple(payload["source_roots"])
    assert all(isinstance(value, str) for value in roots)
    modules = _discover_modules(roots)
    classifications = _classification_map(payload)
    assert set(classifications) == set(modules)


def test_soulforge_engine_dependencies_do_not_exceed_the_baseline() -> None:
    payload = _load_boundary()
    roots = tuple(payload["source_roots"])
    modules = _discover_modules(roots)
    classifications = _classification_map(payload)
    raw_directions = payload["forbidden_dependency_directions"]
    assert isinstance(raw_directions, list)
    forbidden = frozenset(
        (str(item["from"]), str(item["to"]))
        for item in raw_directions
        if isinstance(item, dict)
    )
    current = _violations(modules, classifications, forbidden)
    raw_baseline = payload["violation_baseline"]
    assert isinstance(raw_baseline, list)
    baseline: set[tuple[str, str]] = set()
    for item in raw_baseline:
        assert isinstance(item, dict)
        assert isinstance(item.get("line"), int) and int(item["line"]) > 0
        assert isinstance(item.get("reason"), str) and str(item["reason"]).strip()
        key = str(item["importer"]), str(item["imported"])
        assert key not in baseline, key
        assert key[0] in modules, f"baseline importer is not classified: {key[0]}"
        assert key[1] in modules, f"baseline target is not classified: {key[1]}"
        assert (
            classifications[key[0]],
            classifications[key[1]],
        ) in forbidden, f"baseline entry is not a forbidden direction: {key}"
        baseline.add(key)
    new_violations = tuple(
        edge for edge in current if _violation_key(edge) not in baseline
    )
    assert not new_violations, new_violations
    # Lock every reduction: a removed violation must also leave the baseline,
    # otherwise the same edge could silently return later.
    stale = baseline - {_violation_key(edge) for edge in current}
    assert not stale, f"remove resolved edges from violation_baseline: {sorted(stale)}"


def test_import_scan_treats_eager_lazy_relative_and_dynamic_imports_equally(
    tmp_path: Path,
) -> None:
    package = tmp_path / "application"
    package.mkdir()
    source = package / "feature.py"
    source.write_text(
        "import domain.version_info\n"
        "lazy import domain.version_info\n"
        "lazy from domain import version_info\n"
        "from . import product_bridge\n"
        "importlib.import_module('domain.hand_asset_audit')\n"
        "__import__('domain.pose_atlas_audit')\n",
        encoding="utf-8",
        newline="\n",
    )
    known = frozenset({
        "application.feature",
        "application.product_bridge",
        "domain",
        "domain.hand_asset_audit",
        "domain.pose_atlas_audit",
        "domain.version_info",
    })
    edges = _import_edges("application.feature", source, known)
    targets = {edge.imported for edge in edges}
    assert targets == {
        "application.product_bridge",
        "domain",
        "domain.hand_asset_audit",
        "domain.pose_atlas_audit",
        "domain.version_info",
    }
    version_edges = tuple(
        edge for edge in edges if edge.imported == "domain.version_info"
    )
    assert {edge.lazy for edge in version_edges} == {False, True}


def test_empty_baseline_rejects_a_synthetic_new_violation(tmp_path: Path) -> None:
    engine = tmp_path / "engine.py"
    shell = tmp_path / "shell.py"
    engine.write_text("lazy import shell\n", encoding="utf-8", newline="\n")
    shell.write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    modules = {"engine": engine, "shell": shell}
    classifications = {"engine": "engine", "shell": "mohan_product_shell"}
    violations = _violations(
        modules,
        classifications,
        frozenset({("engine", "mohan_product_shell")}),
    )
    assert tuple(_violation_key(edge) for edge in violations) == (("engine", "shell"),)


def test_import_scan_resolves_importlib_aliases(tmp_path: Path) -> None:
    source = tmp_path / "feature.py"
    source.write_text(
        "lazy import importlib as loader\n"
        "lazy from importlib import import_module\n"
        "lazy from importlib import import_module as load\n"
        "loader.import_module('shell_a')\n"
        "import_module('shell_b')\n"
        "load('shell_c')\n",
        encoding="utf-8",
        newline="\n",
    )
    known = frozenset({"feature", "shell_a", "shell_b", "shell_c"})
    edges = _import_edges("feature", source, known)
    assert {edge.imported for edge in edges} == {"shell_a", "shell_b", "shell_c"}
