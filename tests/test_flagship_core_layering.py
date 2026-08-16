from __future__ import annotations

lazy import ast
lazy import importlib
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_OWNERS = (
    "application.flagship_action_runtime",
    "domain.flagship_action_models",
    "domain.flagship_action_policy",
    "domain.safe_error",
    "infrastructure.flagship_windows_toolbox",
)
FACADE_OWNER = "presentation.flagship_core"


def imported_modules(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return frozenset(modules)


def imported_alias_target(tree: ast.Module) -> str | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
            and node.func.attr == "import_module"
            and len(node.args) == 1
            and not node.keywords
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
    return None


def test_flagship_core_facade_is_static_and_exact() -> None:
    path = PROJECT_ROOT / "flagship_core.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    assert imported_modules(path) == frozenset({"__future__", "importlib", "sys"})
    assert imported_alias_target(tree) == FACADE_OWNER


def test_flagship_core_public_symbols_preserve_canonical_identity() -> None:
    facade = importlib.import_module("flagship_core")
    presentation_api = importlib.import_module(FACADE_OWNER)
    canonical = tuple(importlib.import_module(name) for name in CANONICAL_OWNERS)
    assert tuple(facade.__all__) == tuple(presentation_api.__all__)
    for name in facade.__all__:
        public_value = getattr(facade, name)
        assert public_value is getattr(presentation_api, name)
        assert any(
            hasattr(owner, name) and public_value is getattr(owner, name)
            for owner in canonical
        )


def test_flagship_products_do_not_route_through_root_facade() -> None:
    violations: list[str] = []
    for layer in (
        "application",
        "domain",
        "infrastructure",
        "integrations",
        "presentation",
    ):
        violations.extend(
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in (PROJECT_ROOT / layer).rglob("*.py")
            if "flagship_core" in imported_modules(path)
        )
    assert violations == []


def test_flagship_core_owners_stay_bounded() -> None:
    owners = tuple(
        owner for owner in CANONICAL_OWNERS if owner != "domain.safe_error"
    ) + (FACADE_OWNER,)
    oversized = {
        owner: len(
            Path(importlib.import_module(owner).__file__)
            .read_text(encoding="utf-8")
            .splitlines()
        )
        for owner in owners
        if len(
            Path(importlib.import_module(owner).__file__)
            .read_text(encoding="utf-8")
            .splitlines()
        )
        > 300
    }
    assert oversized == {}
