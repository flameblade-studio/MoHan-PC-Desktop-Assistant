from __future__ import annotations

lazy import ast
lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOW_BASES = {
    "presentation.companion_window": (
        "CompanionCoreMixin",
        "CompanionProactiveMixin",
        "CompanionVisualDynamicsMixin",
        "CompanionFaceAnimationMixin",
        "CompanionSpeechRuntimeMixin",
        "CompanionPlatformMixin",
        "QMainWindow",
    ),
    "presentation.dashboard_window": (
        "DashboardWardrobePreferencesMixin",
        "DashboardWardrobeMakeupMixin",
        "DashboardShellMixin",
        "DashboardSettingsMixin",
        "DashboardVoiceMixin",
        "DashboardConversationMixin",
        "DashboardTodayMemoryMixin",
        "DashboardPlatformMixin",
        "QDialog",
    ),
}
MIXIN_OWNERS = {
    "CompanionCoreMixin": "presentation.companion_core",
    "CompanionProactiveMixin": "presentation.companion_proactive",
    "CompanionVisualDynamicsMixin": "presentation.companion_visual_dynamics",
    "CompanionFaceAnimationMixin": "presentation.companion_face_animation",
    "CompanionSpeechRuntimeMixin": "presentation.companion_speech_runtime",
    "CompanionPlatformMixin": "presentation.companion_platform",
    "DashboardShellMixin": "presentation.dashboard_shell",
    "DashboardSettingsMixin": "presentation.dashboard_settings",
    "DashboardVoiceMixin": "presentation.dashboard_voice",
    "DashboardConversationMixin": "presentation.dashboard_conversation",
    "DashboardTodayMemoryMixin": "presentation.dashboard_today_memory",
    "DashboardPlatformMixin": "presentation.dashboard_platforms",
    "DashboardWardrobePreferencesMixin": (
        "presentation.dashboard_wardrobe_preferences"
    ),
    "DashboardWardrobeMakeupMixin": "presentation.dashboard_wardrobe_makeup",
}


def module_tree(module: str) -> ast.Module:
    path = PROJECT_ROOT.joinpath(*module.split(".")).with_suffix(".py")
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def class_bases(module: str) -> tuple[str, ...]:
    expected_class = (
        "CompanionWindow"
        if module == "presentation.companion_window"
        else "Dashboard"
    )
    class_node = next(
        node
        for node in module_tree(module).body
        if isinstance(node, ast.ClassDef) and node.name == expected_class
    )
    return tuple(
        base.id if isinstance(base, ast.Name) else ast.unparse(base)
        for base in class_node.bases
    )


def imported_owner(tree: ast.Module, symbol: str) -> str | None:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if any((alias.asname or alias.name) == symbol for alias in node.names):
            return node.module
    return None


def top_level_classes(tree: ast.Module) -> set[str]:
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def test_composition_modules_import_without_loading_app() -> None:
    script = """
import sys

from application import application_bootstrap
import presentation.companion_window
import presentation.dashboard_window

assert "app" not in sys.modules, sorted(
    name for name in sys.modules if name == "app" or name.startswith("app.")
)
print("WINDOW_COMPOSITION_IMPORTS_OK")
"""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "WINDOW_COMPOSITION_IMPORTS_OK"


def test_window_mixin_order_is_explicit() -> None:
    for module, expected in WINDOW_BASES.items():
        assert class_bases(module) == expected


def test_mixins_are_imported_from_and_defined_by_true_owners() -> None:
    app_tree = module_tree("app")
    app_classes = top_level_classes(app_tree)
    for window_module in WINDOW_BASES:
        window_tree = module_tree(window_module)
        for mixin in WINDOW_BASES[window_module][:-1]:
            owner = MIXIN_OWNERS[mixin]
            assert imported_owner(window_tree, mixin) == owner
            assert mixin in top_level_classes(module_tree(owner))
            assert mixin not in app_classes
            assert imported_owner(app_tree, mixin) is None
