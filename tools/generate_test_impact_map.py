from __future__ import annotations

lazy import argparse
lazy import ast
lazy from collections.abc import Iterable, Sequence
lazy import fnmatch
lazy import json
lazy from collections import defaultdict
lazy from pathlib import Path, PurePosixPath
lazy import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPACT_MAP = ROOT / "tests" / "impact_map.json"
DERIVED_ORIGIN = "tools/generate_test_impact_map.py"
SOURCE_ROOTS = frozenset(
    {
        "application",
        "domain",
        "infrastructure",
        "integrations",
        "presentation",
        "tools",
    }
)
SOURCE_SUFFIXES = frozenset({".py", ".pyi"})
NATIVE_SOURCE_SUFFIXES = frozenset({".rs", ".toml"})
# Product-neutral cores reached through thin ``tools/`` compatibility facades.
# A test that imports a facade exercises the core behind it, so the derivation
# follows facade -> core edges (and edges inside the core) transitively.
FACADE_CORE_PREFIXES = ("huapu/",)
# Keep this mapping empty unless a tracked source has no executable test surface.
# Every exception must name the exact path and provide a durable engineering reason.
SOURCE_COVERAGE_EXCEPTIONS: dict[str, str] = {}


def _normalise_repo_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _literal_pattern(path: str) -> str:
    """Escape an exact repository path for fnmatch.fnmatchcase."""

    return path.replace("[", "[[]").replace("?", "[?]").replace("*", "[*]")


def tracked_paths(root: Path = ROOT) -> tuple[str, ...]:
    """Return tracked paths plus pending untracked changes known to Git."""

    completed = subprocess.run(
        ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed with exit {completed.returncode}: {detail}")
    candidates = (
        _normalise_repo_path(path.decode("utf-8"))
        for path in completed.stdout.split(b"\0")
        if path
    )
    return tuple(
        sorted(
            path
            for path in candidates
            if (root / PurePosixPath(path)).is_file()
        )
    )


def product_and_tool_sources(paths: Iterable[str]) -> tuple[str, ...]:
    """Select tracked product and tool source files covered by the fast tier."""

    selected: list[str] = []
    for path in paths:
        pure = PurePosixPath(path)
        if not pure.parts:
            continue
        is_package_source = (
            pure.parts[0] in SOURCE_ROOTS and pure.suffix in SOURCE_SUFFIXES
        )
        is_native_source = (
            pure.parts[0] == "native" and pure.suffix in NATIVE_SOURCE_SUFFIXES
        )
        if is_package_source or is_native_source or path in {"app.py", "version_info.py"}:
            selected.append(path)
    return tuple(sorted(selected))


def _module_name(path: str) -> str | None:
    pure = PurePosixPath(path)
    if pure.suffix not in SOURCE_SUFFIXES:
        return None
    without_suffix = pure.with_suffix("")
    parts = without_suffix.parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _module_index(paths: Iterable[str]) -> dict[str, str]:
    modules: dict[str, str] = {}
    for path in paths:
        module = _module_name(path)
        if module is not None:
            modules[module] = path
    return modules


def _current_package(path: str) -> tuple[str, ...]:
    module = _module_name(path)
    if module is None:
        return ()
    parts = tuple(module.split("."))
    if PurePosixPath(path).name == "__init__.py":
        return parts
    return parts[:-1]


def _resolve_module(
    module: str,
    modules: dict[str, str],
) -> tuple[str, ...]:
    resolved: set[str] = set()
    parts = module.split(".")
    for end in range(1, len(parts) + 1):
        candidate = ".".join(parts[:end])
        path = modules.get(candidate)
        if path is not None:
            resolved.add(path)
    return tuple(sorted(resolved))


def _imported_paths(
    tree: ast.Module,
    *,
    path: str,
    modules: dict[str, str],
) -> tuple[str, ...]:
    imported: set[str] = set()
    package = _current_package(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.update(_resolve_module(alias.name, modules))
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            keep = len(package) - (node.level - 1)
            if keep < 0:
                continue
            prefix = package[:keep]
            module_parts = tuple((node.module or "").split("."))
            base = ".".join((*prefix, *(part for part in module_parts if part)))
        else:
            base = node.module or ""
        if base:
            imported.update(_resolve_module(base, modules))
        for alias in node.names:
            if alias.name == "*":
                continue
            candidate = ".".join(part for part in (base, alias.name) if part)
            imported.update(_resolve_module(candidate, modules))
    return tuple(sorted(imported))


def _literal_path_parts(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = _normalise_repo_path(node.value)
        return tuple(part for part in PurePosixPath(value).parts if part not in {".", "/"})
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _literal_path_parts(node.left)
        right = _literal_path_parts(node.right)
        if right is None:
            return None
        return (*(left or ()), *right)
    if isinstance(node, (ast.Name, ast.Attribute, ast.Call)):
        return ()
    return None


def _referenced_paths(
    tree: ast.Module,
    *,
    tracked: frozenset[str],
    unique_names: dict[str, str],
    modules: dict[str, str],
) -> tuple[str, ...]:
    referenced: set[str] = set()
    for node in ast.walk(tree):
        parts = _literal_path_parts(node)
        if parts:
            candidate = _normalise_repo_path(PurePosixPath(*parts).as_posix())
            if candidate in tracked:
                referenced.add(candidate)
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = _normalise_repo_path(node.value)
        if value in tracked:
            referenced.add(value)
        unique_path = unique_names.get(PurePosixPath(value).name)
        if unique_path is not None and value == PurePosixPath(value).name:
            referenced.add(unique_path)
        if value in modules:
            referenced.add(modules[value])
    return tuple(sorted(referenced))


def derive_test_associations(
    root: Path,
    paths: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """Map paths to tests through local imports and repository-path reads."""

    tracked = frozenset(paths)
    modules = _module_index(paths)
    names: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        names[PurePosixPath(path).name].append(path)
    unique_names = {
        name: candidates[0]
        for name, candidates in names.items()
        if len(candidates) == 1
    }
    dependencies: dict[str, tuple[str, ...]] = {}
    references: dict[str, tuple[str, ...]] = {}
    for path in paths:
        if PurePosixPath(path).suffix not in SOURCE_SUFFIXES:
            continue
        source_path = root / PurePosixPath(path)
        if not source_path.is_file():
            continue
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=path)
        dependencies[path] = _imported_paths(tree, path=path, modules=modules)
        references[path] = _referenced_paths(
            tree,
            tracked=tracked,
            unique_names=unique_names,
            modules=modules,
        )

    associations: dict[str, set[str]] = defaultdict(set)
    test_paths = tuple(
        path
        for path in paths
        if PurePosixPath(path).parent == PurePosixPath("tests")
        and PurePosixPath(path).name.startswith("test_")
        and PurePosixPath(path).suffix == ".py"
    )
    for test_path in test_paths:
        related: set[str] = set()
        pending = [test_path]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            current_dependencies = dependencies.get(current, ())
            related.update(current_dependencies)
            related.update(references.get(current, ()))
            for dependency in current_dependencies:
                if dependency in visited or dependency not in dependencies:
                    continue
                if dependency.startswith(("tests/", *FACADE_CORE_PREFIXES)):
                    pending.append(dependency)
                elif dependency.startswith("tools/"):
                    cores = tuple(
                        core
                        for core in dependencies[dependency]
                        if core.startswith(FACADE_CORE_PREFIXES)
                    )
                    related.update(cores)
                    pending.extend(cores)
        for related_path in related:
            if related_path != test_path:
                associations[related_path].add(PurePosixPath(test_path).name)
    if "tests/conftest.py" in tracked:
        associations["tests/conftest.py"].update(
            PurePosixPath(test_path).name for test_path in test_paths
        )
    return {
        path: tuple(sorted(test_names))
        for path, test_names in sorted(associations.items())
        if test_names
    }


def derived_rules(
    associations: dict[str, tuple[str, ...]],
) -> list[dict[str, object]]:
    """Group exact paths that share the same deterministically derived tests."""

    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for path, tests in associations.items():
        grouped[tests].append(path)
    return [
        {
            "paths": sorted(_literal_pattern(path) for path in paths),
            "tests": list(tests),
            "origin": DERIVED_ORIGIN,
        }
        for tests, paths in sorted(grouped.items(), key=lambda item: (item[0], item[1]))
    ]


def regenerated_document(
    root: Path,
    document: dict[str, object],
    paths: Sequence[str],
) -> dict[str, object]:
    """Replace only generated rules and preserve every owner-authored rule."""

    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError("impact map rules must be a list")
    manual_rules = [
        rule
        for rule in raw_rules
        if not isinstance(rule, dict) or rule.get("origin") != DERIVED_ORIGIN
    ]
    associations = derive_test_associations(root, paths)
    regenerated = dict(document)
    regenerated["rules"] = [*manual_rules, *derived_rules(associations)]
    return regenerated


def render_document(document: dict[str, object]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def mapped_tests_for_path(
    path: str,
    rules: Sequence[object],
    test_names: frozenset[str],
) -> tuple[str, ...]:
    """Apply the same path and special-entry semantics as tests/run_all.py."""

    mapped: set[str] = set()
    for raw_rule in rules:
        if not isinstance(raw_rule, dict):
            continue
        patterns = raw_rule.get("paths")
        entries = raw_rule.get("tests")
        if not isinstance(patterns, list) or not isinstance(entries, list):
            continue
        if not any(
            isinstance(pattern, str) and fnmatch.fnmatchcase(path, pattern)
            for pattern in patterns
        ):
            continue
        for entry in entries:
            if entry == "$self":
                candidate = PurePosixPath(path).name
                if path.startswith("tests/") and candidate in test_names:
                    mapped.add(candidate)
            elif entry == "$matching_test":
                candidate = f"test_{PurePosixPath(path).stem}.py"
                if candidate in test_names:
                    mapped.add(candidate)
            elif isinstance(entry, str):
                mapped.add(entry)
    return tuple(sorted(mapped))


def uncovered_paths(
    paths: Sequence[str],
    document: dict[str, object],
) -> tuple[str, ...]:
    tests = frozenset(
        PurePosixPath(path).name
        for path in paths
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError("impact map rules must be a list")
    return tuple(
        path
        for path in paths
        if not mapped_tests_for_path(path, raw_rules, tests)
    )


def _print_audit(paths: Sequence[str], document: dict[str, object]) -> None:
    uncovered = uncovered_paths(paths, document)
    grouped: dict[str, int] = defaultdict(int)
    for path in uncovered:
        pure = PurePosixPath(path)
        grouped[pure.parts[0] if len(pure.parts) > 1 else "<root>"] += 1
    print(f"TRACKED_PATHS={len(paths)}")
    print(f"UNMAPPED_PATHS={len(uncovered)}")
    for group, count in sorted(grouped.items()):
        print(f"UNMAPPED_GROUP={group}:{count}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate deterministic test-impact rules from test imports and paths."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--map", type=Path, default=DEFAULT_IMPACT_MAP)
    arguments = parser.parse_args(argv)

    map_path = arguments.map.resolve()
    document = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("impact map root must be an object")
    paths = tracked_paths(ROOT)
    if arguments.audit:
        _print_audit(paths, document)
        return 0

    expected = render_document(regenerated_document(ROOT, document, paths))
    current = map_path.read_text(encoding="utf-8")
    if arguments.check:
        if current != expected:
            print(
                "tests/impact_map.json differs from deterministic derivation; "
                "run tools/generate_test_impact_map.py"
            )
            return 1
        print("TEST_IMPACT_MAP_CURRENT")
        return 0

    map_path.write_text(expected, encoding="utf-8", newline="\n")
    print(f"WROTE_TEST_IMPACT_MAP={map_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
