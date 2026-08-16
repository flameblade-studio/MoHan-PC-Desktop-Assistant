from __future__ import annotations

lazy import ast
lazy import importlib
lazy from pathlib import Path

lazy from tools.check_layered_imports import (
    FEATURE_COMPOSITION_IMPORTS,
    PHYSICALLY_LAYERED_ROOTS,
    inspect_layered_imports,
    legacy_root_ownership,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER_NAMES = frozenset(
    {"presentation", "application", "domain", "integrations", "infrastructure"}
)
FORBIDDEN_DEPENDENCIES = {
    "presentation": frozenset({"integrations", "infrastructure"}),
    "application": frozenset({"presentation", "integrations", "infrastructure"}),
    "domain": frozenset(
        {"presentation", "application", "integrations", "infrastructure"}
    ),
    "integrations": frozenset({"presentation", "infrastructure"}),
    "infrastructure": frozenset({"presentation", "integrations"}),
}


def imported_layers(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(
                alias.name.partition(".")[0]
                for alias in node.names
                if alias.name.partition(".")[0] in LAYER_NAMES
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.partition(".")[0]
            if node.level == 0 and root in LAYER_NAMES:
                dependencies.add(root)
    return dependencies


def test_layer_packages_exist() -> None:
    for layer in LAYER_NAMES:
        package = PROJECT_ROOT / layer
        assert package.is_dir(), f"Missing layer package: {layer}"
        assert (package / "__init__.py").is_file(), (
            f"Missing package marker: {layer}/__init__.py"
        )


def test_app_keeps_one_explicit_entrypoint() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app.py")
    main_functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    entry_guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If) and is_main_guard(node.test)
    ]
    assert len(main_functions) == 1
    assert len(entry_guards) == 1


def is_main_guard(node: ast.expr) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.ops[0], ast.Eq) or len(node.comparators) != 1:
        return False
    operands = (node.left, node.comparators[0])
    return any(
        isinstance(operand, ast.Name) and operand.id == "__name__"
        for operand in operands
    ) and any(
        isinstance(operand, ast.Constant) and operand.value == "__main__"
        for operand in operands
    )


def test_layered_modules_do_not_reverse_dependencies() -> None:
    violations: list[str] = []
    for layer, forbidden in FORBIDDEN_DEPENDENCIES.items():
        for path in sorted((PROJECT_ROOT / layer).rglob("*.py")):
            module = (
                path.relative_to(PROJECT_ROOT)
                .with_suffix("")
                .as_posix()
                .replace("/", ".")
            )
            allowed_feature_layers = frozenset(
                target.partition(".")[0]
                for target in FEATURE_COMPOSITION_IMPORTS.get(
                    module,
                    frozenset(),
                )
            )
            reversed_dependencies = imported_layers(path) & (
                forbidden - allowed_feature_layers
            )
            if reversed_dependencies:
                relative = path.relative_to(PROJECT_ROOT).as_posix()
                violations.append(
                    f"{relative} imports {sorted(reversed_dependencies)}"
                )
    assert not violations, "Reverse layer dependencies:\n" + "\n".join(violations)


def test_every_root_product_module_has_machine_readable_ownership() -> None:
    report = inspect_layered_imports(PROJECT_ROOT)
    actual = frozenset(
        path.stem for path in PROJECT_ROOT.glob("*.py")
    )
    ownership = legacy_root_ownership()

    assert report.passed, report.format()
    assert frozenset(report.mapped_root_modules) == actual
    assert frozenset(entry.module for entry in ownership) >= actual
    assert all(entry.owner and entry.layer in LAYER_NAMES for entry in ownership)
    assert report.legacy_root_modules == ()
    assert all(entry.location != "legacy-root" for entry in ownership)


def test_physical_layer_owners_have_thin_root_facades() -> None:
    for module, layer in PHYSICALLY_LAYERED_ROOTS.items():
        assert layer in LAYER_NAMES
        assert (PROJECT_ROOT / layer / f"{module}.py").is_file()
        root_tree = ast.parse(
            (PROJECT_ROOT / f"{module}.py").read_text(encoding="utf-8")
        )
        definitions = [
            node
            for node in root_tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert definitions == []


def test_compatibility_facades_preserve_module_and_symbol_identity() -> None:
    identity_examples = {
        "gesture_configuration_store": "infrastructure",
        "gesture_template_store": "infrastructure",
        "opencv_vision": "infrastructure",
    }
    for module, layer in identity_examples.items():
        facade = importlib.import_module(module)
        owner = importlib.import_module(f"{layer}.{module}")
        assert facade is owner

    gesture_store = importlib.import_module(
        "infrastructure.gesture_configuration_store"
    )
    gesture_domain = importlib.import_module("domain.gesture_configuration")
    assert (
        gesture_store.import_gesture_configuration.__module__
        == "domain.gesture_configuration"
    )
    assert (
        gesture_store.import_gesture_configuration
        is gesture_domain.import_gesture_configuration
    )
    assert gesture_store.GestureConfiguration is gesture_domain.GestureConfiguration
