from __future__ import annotations

lazy import ast
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_ROOT = ROOT / "presentation"
WINDOW_PATH = PRESENTATION_ROOT / "companion_window.py"
CORE_PATH = PRESENTATION_ROOT / "companion_core.py"
PROACTIVE_PATH = PRESENTATION_ROOT / "companion_proactive.py"
SPEECH_PATH = PRESENTATION_ROOT / "companion_speech_runtime.py"
PLATFORM_PATH = PRESENTATION_ROOT / "companion_platform.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"module must define {name}.")


def _method(owner: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in owner.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{owner.name} must define {name}().")


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def _loaded_names(node: ast.AST) -> set[str]:
    return {
        item.id
        for item in ast.walk(node)
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)
    }


def assert_bridge_types_are_imported_at_the_composition_root(
    tree: ast.Module,
) -> None:
    imported: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "application.proactive_companion_app_bridge":
            continue
        imported.update(alias.name for alias in node.names)
    required = {
        "ProactiveAppEvent",
        "ProactiveAppState",
        "ProactiveCompanionAppBridge",
    }
    assert required <= imported, (
        "CompanionProactiveMixin must import the typed proactive bridge boundary: "
        f"{sorted(required - imported)}"
    )


def assert_factory_dependency_is_injected(window: ast.ClassDef) -> None:
    initializer = _method(window, "__init__")
    parameters = {
        argument.arg
        for argument in (*initializer.args.args, *initializer.args.kwonlyargs)
    }
    assert "proactive_companion_factory" in parameters, (
        "CompanionWindow must accept a proactive_companion_factory dependency "
        "instead of constructing the bridge's service graph inline."
    )
    assert "_initialize_proactive_companion_app_bridge" in _called_attributes(
        initializer
    ), "CompanionWindow must initialize the optional bridge at composition time."


def assert_dispatch_normalizes_disabled_vision_and_timer_state(
    window: ast.ClassDef,
) -> None:
    dispatch = _method(window, "_dispatch_proactive_companion")
    names = _loaded_names(dispatch)
    calls = _called_attributes(dispatch)
    assert {"ProactiveAppEvent", "ProactiveAppState"} <= names
    assert "dispatch" in calls
    assert "timer_trigger" in {argument.arg for argument in dispatch.args.args}, (
        "The app boundary must accept existing timer reminders without requiring "
        "camera recognition."
    )
    source = ast.get_source_segment(
        PROACTIVE_PATH.read_text(encoding="utf-8-sig"),
        dispatch,
    )
    assert source is not None
    for state_field in ("enabled", "camera_enabled", "session_user_active"):
        assert state_field in source, (
            "The app bridge state must explicitly normalize " + state_field + "."
        )
    assert "proactive_interaction_mode" in source, (
        "The desktop companion must consume the canonical mode saved by the "
        "flagship control center, not only the retired proactive_mode key."
    )


def assert_existing_entrypoints_route_through_the_bridge(
    proactive: ast.ClassDef,
    platform: ast.ClassDef,
) -> None:
    visual = _method(proactive, "_consider_visual_interaction")
    reminders = _method(platform, "check_reminders")
    for method in (visual, reminders):
        calls = _called_attributes(method)
        assert "_dispatch_proactive_companion" in calls, (
            f"{method.name}() must submit through ProactiveCompanionAppBridge."
        )
        assert "speak" not in calls, (
            f"{method.name}() must not directly speak system recognition or "
            "reminder text."
        )
    visual_source = ast.get_source_segment(
        PROACTIVE_PATH.read_text(encoding="utf-8-sig"),
        visual,
    )
    assert visual_source is not None
    assert "proactive_interaction_mode" in visual_source, (
        "Visual activity cadence must use the mode saved by the control center."
    )


def assert_speech_completion_and_shutdown_are_committed_once(
    speech: ast.ClassDef,
    platform: ast.ClassDef,
) -> None:
    completed = _method(speech, "_complete_speech_audio_finished")
    assert "_complete_proactive_companion_speech" in _called_attributes(completed), (
        "Successful audio completion must report the bridge's two-phase commit."
    )
    close_event = _method(platform, "closeEvent")
    assert "_close_proactive_companion_app_bridge" in _called_attributes(
        close_event
    ), "Window shutdown must cancel pending proactive delivery safely."


def _imported_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.partition(".")[0])
    return roots


def _base_names(owner: ast.ClassDef) -> tuple[str, ...]:
    return tuple(base.id for base in owner.bases if isinstance(base, ast.Name))


def run() -> None:
    window_tree = _tree(WINDOW_PATH)
    proactive_tree = _tree(PROACTIVE_PATH)
    speech_tree = _tree(SPEECH_PATH)
    platform_tree = _tree(PLATFORM_PATH)
    window = _class(window_tree, "CompanionWindow")
    proactive = _class(proactive_tree, "CompanionProactiveMixin")
    speech = _class(speech_tree, "CompanionSpeechRuntimeMixin")
    platform = _class(platform_tree, "CompanionPlatformMixin")

    assert _base_names(window)[:2] == (
        "CompanionCoreMixin",
        "CompanionProactiveMixin",
    ), "core initialization must precede proactive bridge initialization"
    assert_bridge_types_are_imported_at_the_composition_root(proactive_tree)
    assert_factory_dependency_is_injected(window)
    assert_dispatch_normalizes_disabled_vision_and_timer_state(proactive)
    assert_existing_entrypoints_route_through_the_bridge(proactive, platform)
    assert_speech_completion_and_shutdown_are_committed_once(speech, platform)

    proactive_methods = {
        node.name for node in proactive.body if isinstance(node, ast.FunctionDef)
    }
    assert not proactive_methods.intersection(
        node.name for node in window.body if isinstance(node, ast.FunctionDef)
    ), "CompanionWindow must not shadow proactive behavior owners"
    for path in (
        WINDOW_PATH,
        CORE_PATH,
        PROACTIVE_PATH,
        SPEECH_PATH,
        PLATFORM_PATH,
    ):
        assert "app" not in _imported_roots(_tree(path)), path.name
    print("PROACTIVE_COMPANION_APP_WIRING_OK")


def test_proactive_companion_app_wiring() -> None:
    run()


if __name__ == "__main__":
    run()
