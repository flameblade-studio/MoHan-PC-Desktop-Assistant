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
MAX_OWNER_LINE_COUNT = 300


def imported_modules(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return frozenset(modules)


def test_flagship_core_api_is_static_and_exact() -> None:
    path = PROJECT_ROOT / "presentation" / "flagship_core.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not any(
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for node in tree.body
    )
    assert imported_modules(path) <= frozenset({"__future__", *CANONICAL_OWNERS})


def test_flagship_core_public_symbols_preserve_canonical_identity() -> None:
    presentation_api = importlib.import_module(FACADE_OWNER)
    canonical = tuple(importlib.import_module(name) for name in CANONICAL_OWNERS)
    for name in presentation_api.__all__:
        public_value = getattr(presentation_api, name)
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
        > MAX_OWNER_LINE_COUNT
    }
    assert oversized == {}
