from __future__ import annotations

lazy import ast
lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = PROJECT_ROOT / "presentation" / "companion_window.py"
CORE_PATH = PROJECT_ROOT / "presentation" / "companion_core.py"
PROACTIVE_PATH = PROJECT_ROOT / "presentation" / "companion_proactive.py"
CONTRACT_PATH = Path(__file__).resolve()

EXPECTED_METHODS = frozenset({
    "_initialize_adaptive_character_composition",
    "_on_stale_outfit_pack",
    "_publish_adaptive_idle_frame",
    "_stage_adaptive_character_frame",
    "_dispatch_adaptive_character_frame",
    "_face_motion_with_live_state",
    "_refresh_full_body",
    "_publish_adaptive_character_frame",
    "_cancel_adaptive_character_composition",
    "_release_adaptive_full_body",
    "_hide_legacy_character_overlays",
    "_initialize_runtime_services",
    "_run_first_run_wizard_if_needed",
    "_create_dashboard",
    "_create_gesture_application",
    "_authorize_gesture_action",
    "dashboard_hide_if_available",
    "_set_gesture_audio_muted",
    "_stop_current_speech_from_gesture",
    "_set_gesture_interaction_mode",
    "_acknowledge_gesture",
    "_acknowledge_wave",
    "_on_gesture_recognition",
    "_open_dashboard_from_gesture",
    "_submit_gesture_text_command",
    "_connect_dashboard_signals",
    "_apply_multimodal_result",
    "_connect_speech_service_signals",
    "_initialize_companion_state",
    "_persist_affection",
    "_apply_weather_and_satiety",
    "_observe_personality_mirror",
    "_reload_preference_caches",
    "_current_performance_preferences",
    "_current_framing_preferences",
})


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_node(tree: ast.Module, name: str) -> ast.ClassDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    ]
    assert len(matches) == 1, f"expected one {name}, found {len(matches)}"
    return matches[0]


def _direct_methods(class_node: ast.ClassDef) -> tuple[ast.FunctionDef, ...]:
    return tuple(node for node in class_node.body if isinstance(node, ast.FunctionDef))


def _method_map(class_node: ast.ClassDef) -> dict[str, ast.FunctionDef]:
    methods = _direct_methods(class_node)
    names = tuple(method.name for method in methods)
    assert len(names) == len(set(names)), "duplicate method definitions are forbidden"
    return {method.name: method for method in methods}


def _imported_roots(tree: ast.Module) -> frozenset[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.partition(".")[0])
    return frozenset(roots)


def _dynamic_import_targets(tree: ast.Module) -> frozenset[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        is_dynamic_import = (
            isinstance(function, ast.Name) and function.id == "__import__"
        ) or (isinstance(function, ast.Attribute) and function.attr == "import_module")
        first_argument = node.args[0]
        if (
            is_dynamic_import
            and isinstance(first_argument, ast.Constant)
            and isinstance(first_argument.value, str)
        ):
            targets.add(first_argument.value.partition(".")[0])
    return frozenset(targets)


def _imports_name(tree: ast.Module, module: str, name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == module
        and any(alias.name == name for alias in node.names)
        for node in tree.body
    )


def _class_base_names(class_node: ast.ClassDef) -> tuple[str, ...]:
    return tuple(base.id for base in class_node.bases if isinstance(base, ast.Name))


def test_companion_core_method_and_export_contract_is_fixed() -> None:
    core_tree = _module_tree(CORE_PATH)
    mixin = _class_node(core_tree, "CompanionCoreMixin")
    assert frozenset(_method_map(mixin)) == EXPECTED_METHODS

    exports = [
        node
        for node in core_tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in (
                node.targets if isinstance(node, ast.Assign) else (node.target,)
            )
        )
    ]
    assert len(exports) == 1
    assert ast.literal_eval(exports[0].value) == ("CompanionCoreMixin",)


def test_core_composition_and_contract_do_not_import_app() -> None:
    for path in (WINDOW_PATH, CORE_PATH, PROACTIVE_PATH, CONTRACT_PATH):
        tree = _module_tree(path)
        assert "app" not in _imported_roots(tree), path.name
        assert "app" not in _dynamic_import_targets(tree), path.name


def test_companion_core_imports_independently_without_loading_app() -> None:
    expected = ",".join(sorted(EXPECTED_METHODS))
    probe = """
lazy import inspect
lazy import sys

assert sys.version_info[:2] == (3, 15), sys.version
sys.path.insert(0, sys.argv[1])
assert "app" not in sys.modules
from presentation import companion_core

mixin = companion_core.CompanionCoreMixin
methods = {
    name
    for name, value in vars(mixin).items()
    if inspect.isfunction(value)
}
assert methods == set(sys.argv[2].split(",")), sorted(methods)
assert companion_core.__all__ == ("CompanionCoreMixin",)
assert "app" not in sys.modules
"""
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(PROJECT_ROOT),
            expected,
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_companion_window_uses_the_unique_core_owner_in_canonical_order() -> None:
    window_tree = _module_tree(WINDOW_PATH)
    core_tree = _module_tree(CORE_PATH)
    companion = _class_node(window_tree, "CompanionWindow")
    core = _class_node(core_tree, "CompanionCoreMixin")
    assert frozenset(_method_map(core)) == EXPECTED_METHODS
    assert not EXPECTED_METHODS.intersection(_method_map(companion)), (
        "CompanionWindow must not shadow CompanionCoreMixin behavior"
    )
    assert _imports_name(
        window_tree,
        "presentation.companion_core",
        "CompanionCoreMixin",
    ), "canonical companion composition must import CompanionCoreMixin"
    assert _class_base_names(companion).count("CompanionCoreMixin") == 1
    assert _class_base_names(companion)[:2] == (
        "CompanionCoreMixin",
        "CompanionProactiveMixin",
    )

    initializer = _method_map(companion)["__init__"]
    calls = [
        node.func.attr
        for node in ast.walk(initializer)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert calls.index("_initialize_runtime_services") < calls.index(
        "_initialize_proactive_companion_app_bridge"
    ), "core services must exist before the proactive bridge is composed"
