from __future__ import annotations

lazy import ast
lazy import importlib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_OWNERS = {
    "auxiliary_ui_localization": "presentation.auxiliary_ui_localization",
    "companion_core": "presentation.companion_core",
    "companion_face_animation": "presentation.companion_face_animation",
    "companion_platform": "presentation.companion_platform",
    "companion_proactive": "presentation.companion_proactive",
    "companion_speech_runtime": "presentation.companion_speech_runtime",
    "companion_visual_dynamics": "presentation.companion_visual_dynamics",
    "companion_window": "presentation.companion_window",
    "dashboard_composition": "presentation.dashboard_composition",
    "dashboard_conversation": "presentation.dashboard_conversation",
    "dashboard_dialogs": "presentation.dashboard_dialogs",
    "dashboard_platforms": "presentation.dashboard_platforms",
    "dashboard_settings": "presentation.dashboard_settings",
    "dashboard_shared": "presentation.dashboard_shared",
    "dashboard_shell": "presentation.dashboard_shell",
    "dashboard_today_memory": "presentation.dashboard_today_memory",
    "dashboard_voice": "presentation.dashboard_voice",
    "dashboard_window": "presentation.dashboard_window",
    "first_run_wizard": "presentation.first_run_wizard",
    "flagship_theme": "presentation.flagship_theme",
    "flagship_ui_localization": "presentation.flagship_ui_localization",
    "profile_transfer_ui": "presentation.profile_transfer_ui",
    "settings_ui_localization": "presentation.settings_ui_localization",
    "theme_pack_ui": "presentation.theme_pack_ui",
    "ui_localization": "presentation.ui_localization",
    "ui_localization_ja": "presentation.ui_localization_ja",
    "updater_ui": "presentation.updater_ui",
}


def _imports(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return frozenset(imported)


def test_presentation_owners_never_import_their_root_facades() -> None:
    forbidden = frozenset(PRESENTATION_OWNERS)
    violations: dict[str, list[str]] = {}
    for path in sorted((ROOT / "presentation").glob("*.py")):
        roots = sorted(_imports(path) & forbidden)
        if roots:
            violations[path.relative_to(ROOT).as_posix()] = roots
    assert violations == {}


def _facade_contract(name: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    tree = ast.parse(
        (ROOT / f"{name}.py").read_text(encoding="utf-8"),
        filename=f"{name}.py",
    )
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    ]
    exports = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(imports) == 1
    assert len(exports) == 1
    module = imports[0].module
    assert module is not None
    imported_names = tuple(alias.name for alias in imports[0].names)
    exported_names = ast.literal_eval(exports[0].value)
    return module, imported_names, exported_names


def _alias_target(name: str) -> str | None:
    tree = ast.parse(
        (ROOT / f"{name}.py").read_text(encoding="utf-8"),
        filename=f"{name}.py",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
            and node.func.attr == "import_module"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
    return None


def test_root_facades_export_exact_owner_symbols() -> None:
    for facade_name, owner_name in PRESENTATION_OWNERS.items():
        alias_target = _alias_target(facade_name)
        if alias_target is not None:
            assert alias_target == owner_name
            continue
        module, imported_names, exported_names = _facade_contract(facade_name)
        assert module == owner_name
        assert imported_names
        assert exported_names == imported_names


def test_flagship_theme_public_operations_are_directly_callable() -> None:
    facade = importlib.import_module("flagship_theme")
    owner = importlib.import_module("presentation.flagship_theme")
    for symbol in (
        "FlagshipThemeResult",
        "apply_flagship_theme",
        "create_flagship_ornament",
        "mark_flagship_card",
    ):
        facade_value = getattr(facade, symbol)
        assert callable(facade_value), symbol
        assert facade_value is getattr(owner, symbol)


def test_flagship_ui_receives_callable_theme_operations() -> None:
    flagship_ui = importlib.import_module("flagship_ui")
    owner = importlib.import_module("presentation.flagship_theme")
    for symbol in (
        "apply_flagship_theme",
        "create_flagship_ornament",
    ):
        value = getattr(flagship_ui, symbol)
        assert callable(value), symbol
        assert value is getattr(owner, symbol)
