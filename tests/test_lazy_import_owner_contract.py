from __future__ import annotations

lazy import ast
lazy from dataclasses import dataclass
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATTERNS = ("app_*.py", "dashboard_*.py", "companion_*.py")


@dataclass(frozen=True)
class LazyOwnerViolation:
    consumer: str
    line: int
    provider: str
    name: str


def module_tree(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )


def directly_defined_names(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            continue
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        names.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    return frozenset(names)


def explicitly_exported_names(tree: ast.Module) -> frozenset[str]:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in targets
        ):
            continue
        try:
            exported = ast.literal_eval(node.value)
        except (TypeError, ValueError):
            return frozenset()
        if not isinstance(exported, (tuple, list)):
            return frozenset()
        return frozenset(name for name in exported if isinstance(name, str))
    return frozenset()


def directly_imported_names(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name != "*"
            )
    return frozenset(names)


def valid_provider_names(tree: ast.Module) -> frozenset[str]:
    owned = directly_defined_names(tree)
    reexported = explicitly_exported_names(tree) & directly_imported_names(tree)
    return owned | reexported


def compatibility_alias_target(tree: ast.Module) -> str | None:
    aliases = {
        **{
            alias.asname or alias.name.partition(".")[0]: alias.name
            for alias in node.names
        }
        for node in tree.body
        if isinstance(node, ast.Import)
    }
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Attribute)
            and isinstance(target.value.value, ast.Name)
            and aliases.get(target.value.value.id) == "sys"
            and target.value.attr == "modules"
            and isinstance(target.slice, ast.Name)
            and target.slice.id == "__name__"
            and isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and aliases.get(value.func.value.id) == "importlib"
            and value.func.attr == "import_module"
            and len(value.args) == 1
            and not value.keywords
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            continue
        return value.args[0].value
    return None


def local_module_path(module: str) -> Path | None:
    candidate = PROJECT_ROOT.joinpath(*module.split(".")).with_suffix(".py")
    if candidate.is_file():
        return candidate
    package = PROJECT_ROOT.joinpath(*module.split("."), "__init__.py")
    return package if package.is_file() else None


def lazy_imports(tree: ast.Module) -> tuple[ast.ImportFrom, ...]:
    return tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and bool(getattr(node, "is_lazy", False))
    )


def core_module_paths() -> tuple[Path, ...]:
    paths = {
        *PROJECT_ROOT.glob(pattern)
        for pattern in CORE_PATTERNS
    }
    return tuple(sorted(paths, key=lambda path: path.name))


def find_lazy_owner_violations() -> tuple[LazyOwnerViolation, ...]:
    violations: list[LazyOwnerViolation] = []
    for consumer_path in core_module_paths():
        for imported in lazy_imports(module_tree(consumer_path)):
            if imported.level or not imported.module:
                continue
            provider_path = local_module_path(imported.module)
            if provider_path is None:
                continue
            provider_tree = module_tree(provider_path)
            alias_target = compatibility_alias_target(provider_tree)
            if alias_target is not None:
                provider_path = local_module_path(alias_target)
                assert provider_path is not None, (
                    f"missing compatibility alias target: {alias_target}"
                )
                provider_tree = module_tree(provider_path)
            valid_names = valid_provider_names(provider_tree)
            for alias in imported.names:
                if alias.name == "*" or alias.name in valid_names:
                    continue
                violations.append(
                    LazyOwnerViolation(
                        consumer_path.name,
                        imported.lineno,
                        imported.module,
                        alias.name,
                    )
                )
    return tuple(violations)


def test_companion_core_imports_expression_poses_from_its_true_owner() -> None:
    imports = lazy_imports(
        module_tree(PROJECT_ROOT / "presentation" / "companion_core.py")
    )
    expression_pose_sources = {
        imported.module
        for imported in imports
        if any(alias.name == "EXPRESSION_POSES" for alias in imported.names)
    }

    assert expression_pose_sources == {"domain.companion_animation_contract"}
    assert "companion_speech_runtime" not in expression_pose_sources


def test_core_modules_do_not_chain_lazy_import_proxies() -> None:
    violations = find_lazy_owner_violations()
    assert not violations, (
        "lazy imports must target the defining module or an explicit __all__ "
        f"re-export: {violations}"
    )


def test_owner_detection_accepts_classes_functions_and_constants() -> None:
    tree = ast.parse(
        "class OwnedClass:\n"
        "    def method(self):\n"
        "        return None\n"
        "def owned_function():\n"
        "    return None\n"
        "OWNED_CONSTANT = 1\n"
    )

    assert valid_provider_names(tree) == {
        "OwnedClass",
        "owned_function",
        "OWNED_CONSTANT",
    }
    assert "method" not in valid_provider_names(tree)


def test_explicit_all_allows_only_intentional_reexports() -> None:
    explicit = ast.parse(
        "lazy from true_owner import PublicName, PrivateName\n"
        "__all__ = ('PublicName',)\n",
    )
    implicit = ast.parse("lazy from true_owner import ProxyName\n")
    invented = ast.parse("__all__ = ('MissingName',)\n")

    assert "PublicName" in valid_provider_names(explicit)
    assert "PrivateName" not in valid_provider_names(explicit)
    assert "ProxyName" not in valid_provider_names(implicit)
    assert "MissingName" not in valid_provider_names(invented)
