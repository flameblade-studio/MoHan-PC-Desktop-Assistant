from __future__ import annotations

lazy import ast
lazy from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_MODULE = "app"
EXTRACTED_PUBLIC_SYMBOLS: dict[str, frozenset[str]] = {
    "domain.app_profile": frozenset({
        "DEFAULT_PROFILE",
        "ProfileLocalizationContext",
        "ProfileSettingsValues",
        "default_persona_for_language",
        "persona_for_profile",
        "personalize_text",
        "profile_setting",
        "profile_window_title",
    }),
    "domain.speech_configuration": frozenset({
        "AZURE_HD_SECRET_POLICY",
        "AZURE_SECRET_POLICY",
        "OPENAI_SECRET_POLICY",
        "OPENAI_VOICE_ORDER",
        "QueuedSpeech",
        "REALTIME_UNSUPPORTED_TTS_VOICES",
        "REALTIME_VOICES",
        "SecretInputPolicy",
        "SpeechCredentials",
        "TTS_VOICES",
        "VOICE_ENGINE_AZURE",
        "VOICE_ENGINE_AZURE_HD",
        "VOICE_ENGINE_OPENAI",
        "VOICE_ENGINE_REALTIME",
        "VOICE_ENGINE_SYSTEM",
        "VOICE_ENGINE_WINDOWS",
        "VOICE_GENERATION_PROMPT",
        "combo_data_or_custom_text",
        "migrate_voice_defaults",
    }),
    "presentation.dashboard_composition": frozenset({
        "DashboardDependencies",
        "create_portable_secret_callbacks",
    }),
    "presentation.dashboard_conversation": frozenset({
        "DashboardConversationMixin",
        "classify_memory_text",
    }),
    "application.adaptive_character_composition": frozenset({
        "AdaptiveCharacterComposition",
        "AdaptiveCharacterFactory",
        "create_adaptive_character_composition",
    }),
    "presentation.dashboard_dialogs": frozenset({
        "ArchivedMemoryDialog",
        "ChatHistoryDialog",
        "ClickableLabel",
        "IdeaEditorDialog",
        "MemoryEditorDialog",
        "TodoRow",
        "ZoomTextBrowser",
    }),
    "presentation.dashboard_shared": frozenset({
        "MEMORY_CATEGORIES",
        "TODO_CATEGORIES",
        "memory_category_label",
    }),
    "presentation.dashboard_shell": frozenset({"DashboardShellMixin"}),
    "presentation.dashboard_settings": frozenset({"DashboardSettingsMixin"}),
    "presentation.dashboard_platforms": frozenset({
        "DashboardPlatformMixin",
        "PLATFORM_STATUSES",
        "PlatformCardControls",
        "platform_status_label",
    }),
    "presentation.dashboard_today_memory": frozenset({
        "DashboardTodayMemoryMixin",
        "MemoryTabActions",
    }),
    "presentation.dashboard_voice": frozenset({"DashboardVoiceMixin"}),
    "presentation.companion_proactive": frozenset({
        "CompanionProactiveMixin",
    }),
    "presentation.companion_platform": frozenset({
        "CompanionPlatformMixin",
        "REMINDER_LINES",
        "reminder_line",
    }),
    "presentation.companion_speech_runtime": frozenset({
        "CompanionSpeechRuntimeMixin",
    }),
    "presentation.companion_core": frozenset({"CompanionCoreMixin"}),
    "presentation.companion_face_animation": frozenset({"CompanionFaceAnimationMixin"}),
    "presentation.companion_visual_dynamics": frozenset({"CompanionVisualDynamicsMixin"}),
    "presentation.companion_window": frozenset({"CompanionWindow"}),
    "presentation.dashboard_window": frozenset({"Dashboard"}),
    "presentation.first_run_wizard": frozenset({"FirstRunWizard"}),
}


def module_path(module: str) -> Path:
    return PROJECT_ROOT.joinpath(*module.split(".")).with_suffix(".py")


def module_tree(module: str) -> ast.Module:
    path = module_path(module)
    assert path.is_file(), f"missing extracted module: {path.name}"
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def local_modules() -> frozenset[str]:
    return frozenset(
        path.stem
        for path in PROJECT_ROOT.glob("*.py")
        if path.stem != "__init__"
    )


def imported_local_roots(
    tree: ast.Module,
    local: frozenset[str],
) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = (alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            candidates = (node.module.partition(".")[0],)
        else:
            continue
        roots.update(candidate for candidate in candidates if candidate in local)
    return roots


def local_import_graph() -> dict[str, set[str]]:
    local = local_modules()
    return {
        module: imported_local_roots(module_tree(module), local)
        for module in local
    }


def assert_acyclic(graph: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module: str, trail: tuple[str, ...]) -> None:
        if module in visiting:
            cycle_start = trail.index(module)
            cycle = trail[cycle_start:] + (module,)
            raise AssertionError("local import cycle: " + " -> ".join(cycle))
        if module in visited:
            return
        visiting.add(module)
        for dependency in sorted(graph[module]):
            visit(dependency, trail + (module,))
        visiting.remove(module)
        visited.add(module)

    for module in sorted(graph):
        visit(module, ())


def top_level_definitions(tree: ast.Module) -> set[str]:
    definitions: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.add(node.name)
            continue
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        definitions.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    return definitions


def declared_exports(tree: ast.Module) -> frozenset[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        assert isinstance(value, tuple)
        assert all(isinstance(item, str) for item in value)
        return frozenset(value)
    return None


def test_extracted_symbols_belong_to_their_true_owner() -> None:
    for module, expected in EXTRACTED_PUBLIC_SYMBOLS.items():
        tree = module_tree(module)
        definitions = top_level_definitions(tree)
        assert expected <= definitions, (
            f"{module}.py must define its owned symbols: "
            f"{sorted(expected - definitions)}"
        )
        exports = declared_exports(tree)
        if exports is not None:
            assert expected <= exports, (
                f"{module}.__all__ must expose its owned symbols: "
                f"{sorted(expected - exports)}"
            )


def test_extracted_modules_do_not_import_app_directly_or_transitively() -> None:
    local = local_modules()
    graph = local_import_graph()

    def reaches_app(module: str, visited: set[str]) -> bool:
        if module == APP_MODULE:
            return True
        if module in visited:
            return False
        visited.add(module)
        dependencies = graph.get(module)
        if dependencies is None:
            dependencies = imported_local_roots(module_tree(module), local)
        return any(reaches_app(dependency, visited) for dependency in dependencies)

    for module in EXTRACTED_PUBLIC_SYMBOLS:
        dependencies = imported_local_roots(module_tree(module), local)
        assert APP_MODULE not in dependencies, f"{module}.py must not import app"
        assert not reaches_app(module, set()), (
            f"{module}.py must not depend transitively on app"
        )


def test_local_import_graph_is_acyclic() -> None:
    assert_acyclic(local_import_graph())


def test_app_no_longer_owns_or_exports_extracted_public_symbols() -> None:
    app_tree = module_tree(APP_MODULE)
    definitions = top_level_definitions(app_tree)
    exports = declared_exports(app_tree) or frozenset()
    extracted = frozenset().union(*EXTRACTED_PUBLIC_SYMBOLS.values())
    duplicates = (definitions | exports) & extracted
    assert not duplicates, (
        "app.py must not define or export extracted symbols: "
        f"{sorted(duplicates)}"
    )


def run() -> None:
    test_extracted_symbols_belong_to_their_true_owner()
    test_extracted_modules_do_not_import_app_directly_or_transitively()
    test_local_import_graph_is_acyclic()
    test_app_no_longer_owns_or_exports_extracted_public_symbols()


if __name__ == "__main__":
    run()
