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


def test_retired_root_facades_never_return() -> None:
    # The root-facade retirement (2026-08-28) deleted every presentation
    # compatibility shim from the repository root; each owner module is the
    # single import path from now on.
    for facade_name, owner_name in PRESENTATION_OWNERS.items():
        assert not (ROOT / f"{facade_name}.py").exists(), facade_name
        assert (
            ROOT / Path(*owner_name.split("."))
        ).with_suffix(".py").is_file(), owner_name


def test_flagship_theme_public_operations_are_directly_callable() -> None:
    owner = importlib.import_module("presentation.flagship_theme")
    for symbol in (
        "FlagshipThemeResult",
        "apply_flagship_theme",
        "create_flagship_ornament",
        "mark_flagship_card",
    ):
        assert callable(getattr(owner, symbol)), symbol


def test_flagship_ui_receives_callable_theme_operations() -> None:
    flagship_ui = importlib.import_module("presentation.flagship_ui")
    owner = importlib.import_module("presentation.flagship_theme")
    for symbol in (
        "apply_flagship_theme",
        "create_flagship_ornament",
    ):
        value = getattr(flagship_ui, symbol)
        assert callable(value), symbol
        assert value is getattr(owner, symbol)
