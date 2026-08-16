from __future__ import annotations

lazy import ast
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Final

LAYER_NAMES: Final = (
    "presentation",
    "application",
    "domain",
    "integrations",
    "infrastructure",
)
MIGRATED_ROOT_SEED: Final = {
    "command_parser": "domain",
    "auxiliary_ui_localization": "presentation",
    "companion_core": "presentation",
    "companion_face_animation": "presentation",
    "companion_platform": "presentation",
    "companion_proactive": "presentation",
    "companion_speech_runtime": "presentation",
    "companion_visual_dynamics": "presentation",
    "companion_window": "presentation",
    "dashboard_composition": "presentation",
    "dashboard_conversation": "presentation",
    "dashboard_dialogs": "presentation",
    "dashboard_platforms": "presentation",
    "dashboard_settings": "presentation",
    "dashboard_shared": "presentation",
    "dashboard_shell": "presentation",
    "dashboard_today_memory": "presentation",
    "dashboard_voice": "presentation",
    "dashboard_window": "presentation",
    "first_run_wizard": "presentation",
    "flagship_theme": "presentation",
    "flagship_ui_localization": "presentation",
    "gesture_configuration": "domain",
    "gesture_intent": "domain",
    "gesture_action_dispatcher": "application",
    "gesture_action_router": "application",
    "gesture_application_adapter": "application",
    "profile_transfer_ui": "presentation",
    "settings_ui_localization": "presentation",
    "theme_pack_ui": "presentation",
    "ui_localization": "presentation",
    "ui_localization_ja": "presentation",
    "updater_ui": "presentation",
    "ai_client": "integrations",
    "cloud_connectors": "integrations",
    "home_assistant": "integrations",
    "openai_vision_provider": "integrations",
    "remote_control": "integrations",
    "azure_regions": "integrations",
    "azure_speech": "integrations",
    "azure_voice_catalog": "integrations",
    "realtime_speech_output": "integrations",
    "realtime_voice": "integrations",
    "speech": "integrations",
    "app_resources": "infrastructure",
    "face_assets": "infrastructure",
    "face_renderer": "infrastructure",
    "hand_landmark_provider": "infrastructure",
    "opencv_vision": "infrastructure",
    "backup_manager": "infrastructure",
    "companion_proactivity_preferences_store": "infrastructure",
    "db": "infrastructure",
    "face_identity_store": "infrastructure",
    "framing_preferences_store": "infrastructure",
    "gesture_configuration_store": "infrastructure",
    "gesture_template_store": "infrastructure",
    "memory_index": "infrastructure",
    "openai_vision_preferences_store": "infrastructure",
    "performance_preferences_store": "infrastructure",
    "portable_secret_binding": "infrastructure",
    "portable_secrets": "infrastructure",
    "portable_sensitive": "infrastructure",
    "profile_transfer": "infrastructure",
    "secret_store": "infrastructure",
    "special_occasion_store": "infrastructure",
    "wellbeing_reminder_store": "infrastructure",
    "concurrency_tools": "infrastructure",
    "platform_contracts": "infrastructure",
    "platform_linux": "infrastructure",
    "platform_macos": "infrastructure",
    "platform_services": "infrastructure",
    "platform_windows": "infrastructure",
    "updater": "infrastructure",
    "windows_tools": "infrastructure",
}
FORBIDDEN_LAYER_IMPORTS: Final = {
    "presentation": frozenset({"integrations", "infrastructure"}),
    "application": frozenset({"presentation", "integrations", "infrastructure"}),
    "domain": frozenset(
        {"presentation", "application", "integrations", "infrastructure"}
    ),
    "integrations": frozenset({"presentation", "infrastructure"}),
    "infrastructure": frozenset({"presentation", "integrations"}),
}
# Explicit, audited composition boundaries.  Values are exact module targets,
# never blanket layer exemptions, so an unrelated reverse dependency still
# fails closed.
FEATURE_COMPOSITION_IMPORTS: Final = {
    "application.application_bootstrap": frozenset({
        "infrastructure.app_resources",
        "presentation.companion_window",
    }),
    "application.cloud_vision_ui_bridge": frozenset({
        "infrastructure.openai_vision_preferences_store",
    }),
    "application.gesture_controller": frozenset({
        "infrastructure.hand_landmark_provider",
    }),
    "application.gesture_runtime": frozenset({
        "infrastructure.hand_landmark_provider",
    }),
    "application.packaged_self_test": frozenset({
        "infrastructure.app_resources",
        "integrations.realtime_voice",
        "integrations.speech",
        "presentation.pose_atlas_assets",
    }),
    "application.proactive_companion_composition": frozenset({
        "infrastructure.companion_proactivity_preferences_store",
        "infrastructure.db",
        "infrastructure.special_occasion_store",
        "infrastructure.wellbeing_reminder_store",
    }),
    "application.service_container": frozenset({
        "infrastructure.app_resources",
        "infrastructure.backup_manager",
        "infrastructure.db",
        "infrastructure.face_assets",
        "infrastructure.face_renderer",
        "infrastructure.multimodal_model_provider",
        "infrastructure.platform_contracts",
        "infrastructure.platform_services",
        "infrastructure.profile_transfer",
        "infrastructure.secret_store",
        "infrastructure.updater",
        "infrastructure.windows_tools",
        "integrations",
        "integrations.ai_client",
        "integrations.azure_regions",
        "integrations.azure_speech",
        "integrations.openai_vision_provider",
        "integrations.realtime_speech_output",
        "integrations.realtime_voice",
        "integrations.speech",
    }),
    "application.vision_controller": frozenset({
        "infrastructure.face_identity_store",
        "infrastructure.opencv_vision",
    }),
    "application.wellbeing_runtime": frozenset({
        "infrastructure.special_occasion_store",
        "infrastructure.wellbeing_reminder_store",
    }),
    "presentation.flagship.cloud": frozenset({
        "integrations.cloud_connectors",
    }),
    "presentation.flagship.cloud_health": frozenset({
        "integrations.cloud_connectors",
    }),
    "presentation.flagship.control_center": frozenset({
        "infrastructure.companion_proactivity_preferences_store",
        "infrastructure.db",
        "infrastructure.gesture_configuration_store",
        "infrastructure.gesture_template_store",
        "infrastructure.openai_vision_preferences_store",
        "infrastructure.platform_contracts",
    }),
    "presentation.flagship.home": frozenset({
        "integrations.home_assistant",
    }),
    "presentation.flagship.oauth": frozenset({
        "integrations.cloud_connectors",
    }),
    "presentation.flagship.overview": frozenset({
        "infrastructure.backup_manager",
    }),
    "presentation.flagship.planner": frozenset({
        "integrations.ai_client",
    }),
    "presentation.flagship.remote": frozenset({
        "integrations.remote_control",
    }),
    "presentation.flagship_core": frozenset({
        "infrastructure.flagship_windows_toolbox",
    }),
    "presentation.flagship.runtime": frozenset({
        "infrastructure.face_identity_store",
        "infrastructure.flagship_windows_toolbox",
        "infrastructure.platform_contracts",
        "infrastructure.platform_services",
        "infrastructure.secret_store",
        "infrastructure.windows_tools",
        "integrations.ai_client",
        "integrations.remote_control",
    }),
    "presentation.flagship.settings_security": frozenset({
        "infrastructure.companion_proactivity_preferences_store",
        "infrastructure.gesture_configuration_store",
        "infrastructure.openai_vision_preferences_store",
    }),
}
# Root modules not listed in ``PHYSICALLY_LAYERED_ROOTS`` have not yet moved.
# Keep their intended owner explicit without pretending migration is complete.
LEGACY_ROOT_MODULE_GROUPS: Final = {
    ("presentation", "dashboard-ui"): frozenset({
        "dashboard_composition", "dashboard_conversation", "dashboard_dialogs",
        "dashboard_platforms", "dashboard_settings", "dashboard_shared",
        "dashboard_shell", "dashboard_today_memory", "dashboard_voice",
        "dashboard_window",
    }),
    ("presentation", "companion-ui"): frozenset({
        "companion_core", "companion_face_animation", "companion_platform",
        "companion_proactive", "companion_speech_runtime",
        "companion_visual_dynamics", "companion_window", "first_run_wizard",
    }),
    ("presentation", "flagship-ui"): frozenset({
        "auxiliary_ui_localization", "flagship_theme", "flagship_ui",
        "flagship_core", "flagship_ui_localization", "preview_app", "profile_transfer_ui",
        "settings_ui_localization", "service_status_localization",
        "theme_pack_ui", "ui_localization", "ui_localization_ja", "updater_ui",
    }),
    ("application", "bootstrap"): frozenset({
        "app", "application_bootstrap", "packaged_self_test", "runtime_bootstrap",
        "service_container",
    }),
    ("application", "character"): frozenset({
        "adaptive_character_composition", "adaptive_character_runtime",
        "appearance_renderer", "appearance_session", "body_pose_renderer",
        "character_framing_app_bridge", "full_body_performance_bridge",
        "full_body_render_adapter", "wardrobe_service",
    }),
    ("application", "companion"): frozenset({
        "background_agents", "behavior_director", "companion_phrasebook",
        "desktop_presence", "multisensory_interaction", "object_interaction",
        "proactive_companion_app_bridge", "proactive_companion_composition",
        "proactive_companion_runtime", "special_occasion", "workflow_engine",
    }),
    ("application", "gesture"): frozenset({
        "gesture_action_dispatcher", "gesture_action_router",
        "gesture_application_adapter", "gesture_controller", "gesture_recognizer",
        "gesture_runtime",
    }),
    ("application", "performance"): frozenset({
        "performance_app_bridge", "performance_coordinator", "performance_runtime",
        "speech_performance",
    }),
    ("application", "vision"): frozenset({
        "camera_presence", "cloud_vision_runtime", "cloud_vision_ui_bridge",
        "framing_orchestrator", "local_visual_intelligence", "vision_controller",
        "vision_runtime", "visual_context_fusion", "visual_perception",
        "visual_social_cues", "multimodal_controller", "multimodal_fusion_hub",
    }),
    ("application", "wellbeing"): frozenset({
        "wellbeing_app_bridge", "wellbeing_reminder", "wellbeing_runtime",
    }),
    ("domain", "character-model"): frozenset({
        "appearance_dynamics", "character_body_profile", "character_framing",
        "character_full_body_rig", "character_identity_audit", "character_pose",
        "companion_animation_contract", "expression_system", "face_motion",
        "face_rig", "framing_context_policy", "framing_preferences",
        "full_body_asset_audit", "full_body_asset_evidence", "hand_asset_audit",
        "hand_asset_evidence", "outfit_pack", "pose_atlas_audit",
        "pose_atlas_manifest_builder", "pose_atlas_release_gate", "pose_pack",
        "pose_runtime_loader", "theme_pack", "theme_session",
    }),
    ("domain", "configuration"): frozenset({
        "app_profile", "companion_proactivity_preferences", "contracts",
        "feature_registry", "gesture_configuration", "gesture_intent",
        "immutable_config", "openai_vision_authorization",
        "openai_vision_preferences", "performance_preferences",
        "safe_error", "speech_configuration", "version_info",
    }),
    ("domain", "language-time"): frozenset({
        "command_parser", "language_normalization", "language_support",
        "safe_error_localization", "text_normalizer", "time_utils",
    }),
    ("domain", "speech-model"): frozenset({
        "audio_buffer", "lip_sync", "pcm_audio", "prompt_cache",
        "speech_boundary", "speech_providers",
    }),
    ("domain", "vision-model"): frozenset({
        "air_interaction", "cloud_scene_interpreter", "scene_semantics",
        "vision_domain",
    }),
    ("integrations", "ai-cloud"): frozenset({
        "ai_client", "cloud_connectors", "home_assistant",
        "openai_vision_provider", "remote_control",
    }),
    ("integrations", "speech-providers"): frozenset({
        "azure_regions", "azure_speech", "azure_voice_catalog",
        "realtime_speech_output", "realtime_voice", "speech",
    }),
    ("infrastructure", "assets-rendering"): frozenset({
        "app_resources", "face_assets", "face_renderer", "hand_landmark_provider",
        "multimodal_model_provider", "opencv_vision",
    }),
    ("infrastructure", "persistence"): frozenset({
        "backup_manager", "companion_proactivity_preferences_store", "db",
        "face_identity_store", "framing_preferences_store",
        "gesture_configuration_store", "gesture_template_store", "memory_index",
        "openai_vision_preferences_store", "performance_preferences_store",
        "portable_secret_binding", "portable_secrets", "portable_sensitive",
        "profile_transfer", "secret_store", "special_occasion_store",
        "wellbeing_reminder_store",
    }),
    ("infrastructure", "platform"): frozenset({
        "concurrency_tools", "platform_contracts", "platform_linux",
        "platform_macos", "platform_services", "platform_windows", "updater",
        "windows_tools",
    }),
}

ROOT_COMPOSITION_ENTRYPOINTS: Final = frozenset({"app"})
PHYSICALLY_LAYERED_ROOTS: Final = {
    **{
        module: layer
        for module in modules
        if module not in ROOT_COMPOSITION_ENTRYPOINTS
    }
    for (layer, _owner), modules in LEGACY_ROOT_MODULE_GROUPS.items()
}


@dataclass(frozen=True, slots=True, order=True)
class LayeredImportIssue:
    code: str
    module: str
    message: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class LayeredImportReport:
    root: Path
    package_modules: tuple[str, ...]
    mapped_root_modules: tuple[str, ...]
    legacy_root_modules: tuple[str, ...]
    issues: tuple[LayeredImportIssue, ...]

    @property
    def modules(self) -> tuple[str, ...]:
        """Backward-compatible physical package inventory."""

        return self.package_modules

    @property
    def passed(self) -> bool:
        return not self.issues

    def format(self) -> str:
        inventory = (
            f"package_modules={len(self.package_modules)} "
            f"mapped_root_modules={len(self.mapped_root_modules)} "
            f"legacy_root_modules={len(self.legacy_root_modules)}"
        )
        if self.passed:
            return f"Layered imports passed ({inventory})."
        lines = [f"Layered imports failed ({len(self.issues)} issues; {inventory}):"]
        for issue in self.issues:
            location = issue.module
            if issue.line is not None:
                location = f"{location}:{issue.line}"
            lines.append(f"- [{issue.code}] {location}: {issue.message}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class ParsedModule:
    name: str
    path: Path
    tree: ast.Module


@dataclass(frozen=True, slots=True, order=True)
class RootModuleOwnership:
    module: str
    layer: str
    owner: str
    location: str = "compatibility-root"


def root_module_ownership() -> tuple[RootModuleOwnership, ...]:
    return tuple(
        sorted(
            RootModuleOwnership(
                module,
                layer,
                owner,
                "composition-root"
                if module in ROOT_COMPOSITION_ENTRYPOINTS
                else "compatibility-root",
            )
            for (layer, owner), modules in LEGACY_ROOT_MODULE_GROUPS.items()
            for module in modules
        )
    )


def legacy_root_ownership() -> tuple[RootModuleOwnership, ...]:
    """Backward-compatible name for the root ownership inventory."""

    return root_module_ownership()


def module_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def discover_modules(root: Path) -> tuple[tuple[ParsedModule, ...], tuple[LayeredImportIssue, ...]]:
    modules: list[ParsedModule] = []
    issues: list[LayeredImportIssue] = []
    for layer in LAYER_NAMES:
        package = root / layer
        if not package.is_dir():
            continue
        for path in sorted(package.rglob("*.py")):
            name = module_name(root, path)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeError) as error:
                issues.append(
                    LayeredImportIssue(
                        "parse_error",
                        name,
                        f"cannot parse module: {error.msg if isinstance(error, SyntaxError) else type(error).__name__}",
                        getattr(error, "lineno", None),
                    )
                )
                continue
            modules.append(ParsedModule(name, path, tree))
    return tuple(modules), tuple(issues)


def discover_root_modules(
    root: Path,
) -> tuple[tuple[ParsedModule, ...], tuple[LayeredImportIssue, ...]]:
    modules: list[ParsedModule] = []
    issues: list[LayeredImportIssue] = []
    for path in sorted(root.glob("*.py")):
        name = path.stem
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError) as error:
            issues.append(
                LayeredImportIssue(
                    "parse_error",
                    name,
                    "cannot parse root module: "
                    + (
                        error.msg
                        if isinstance(error, SyntaxError)
                        else type(error).__name__
                    ),
                    getattr(error, "lineno", None),
                )
            )
            continue
        modules.append(ParsedModule(name, path, tree))
    return tuple(modules), tuple(issues)


def ownership_issues(
    root_modules: tuple[ParsedModule, ...],
    ownership: tuple[RootModuleOwnership, ...],
    physical_modules: frozenset[str],
) -> list[LayeredImportIssue]:
    actual = frozenset(module.name for module in root_modules)
    declared = [entry.module for entry in ownership]
    declared_set = frozenset(declared)
    issues = [
        LayeredImportIssue(
            "root_module_unmapped",
            module,
            "root product module requires an explicit layer and owner",
        )
        for module in sorted(actual - declared_set)
    ]
    issues.extend(
        LayeredImportIssue(
            "root_mapping_orphaned",
            module,
            "root ownership names a module that does not exist",
        )
        for module in sorted(declared_set - actual - physical_modules)
    )
    duplicate_names = {
        module for module in declared_set if declared.count(module) != 1
    }
    issues.extend(
        LayeredImportIssue(
            "root_mapping_duplicate",
            module,
            "root product module must have exactly one ownership record",
        )
        for module in sorted(duplicate_names)
    )
    for entry in ownership:
        issues.extend(_ownership_entry_issues(entry))
    return issues


def _ownership_entry_issues(
    entry: RootModuleOwnership,
) -> list[LayeredImportIssue]:
    issues: list[LayeredImportIssue] = []
    if entry.layer not in LAYER_NAMES:
        issues.append(
            LayeredImportIssue(
                "root_mapping_layer_invalid",
                entry.module,
                f"unknown target layer: {entry.layer}",
            )
        )
    expected_location = (
        "composition-root"
        if entry.module in ROOT_COMPOSITION_ENTRYPOINTS
        else "compatibility-root"
    )
    if not entry.owner.strip() or entry.location != expected_location:
        issues.append(
            LayeredImportIssue(
                "root_mapping_owner_invalid",
                entry.module,
                "root mapping requires a non-empty owner and honest location",
            )
        )
    return issues


def compatibility_facade_issues(
    root_modules: tuple[ParsedModule, ...],
) -> list[LayeredImportIssue]:
    by_name = {module.name: module for module in root_modules}
    issues: list[LayeredImportIssue] = []
    for name, layer in sorted(PHYSICALLY_LAYERED_ROOTS.items()):
        issue = _compatibility_facade_issue(by_name.get(name), name, layer)
        if issue is not None:
            issues.append(issue)
    return issues


def _compatibility_facade_issue(
    module: ParsedModule | None,
    name: str,
    layer: str,
) -> LayeredImportIssue | None:
    implementation = module.path.parent / layer / f"{name}.py" if module else None
    if module is None or implementation is None or not implementation.is_file():
        return LayeredImportIssue(
            "physical_owner_missing",
            name,
            f"expected implementation at {layer}/{name}.py",
        )
    expected_owner = f"{layer}.{name}"
    allowed = [
        statement
        for position, statement in enumerate(module.tree.body)
        if not _allowed_facade_statement(statement, position, expected_owner)
    ]
    imports_owner = any(
        (
            isinstance(statement, ast.ImportFrom)
            and statement.module == expected_owner
        )
        or (
            isinstance(statement, ast.Import)
            and any(
                alias.name == expected_owner and alias.asname == "_implementation"
                for alias in statement.names
            )
        )
        or (
            isinstance(statement, ast.Assign)
            and _is_import_module_call(statement.value, expected_owner)
        )
        for statement in module.tree.body
    )
    if not allowed and imports_owner:
        return None
    return LayeredImportIssue(
        "compatibility_facade_not_thin",
        name,
        f"root facade must only re-export {expected_owner}",
        getattr(allowed[0], "lineno", None) if allowed else None,
    )


def _allowed_facade_statement(
    statement: ast.stmt,
    position: int,
    expected_owner: str,
) -> bool:
    if (
        position == 0
        and isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    ):
        return True
    if isinstance(statement, ast.ImportFrom):
        return statement.module in {"__future__", expected_owner}
    if isinstance(statement, ast.Import):
        return all(
            alias.name in {"importlib", "sys"}
            or (
                alias.name == expected_owner
                and alias.asname == "_implementation"
            )
            for alias in statement.names
        )
    if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return False
    targets = (
        statement.targets
        if isinstance(statement, ast.Assign)
        else (statement.target,)
    )
    if any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in targets
    ):
        return True
    return (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Subscript)
        and isinstance(statement.targets[0].value, ast.Attribute)
        and isinstance(statement.targets[0].value.value, ast.Name)
        and statement.targets[0].value.value.id == "sys"
        and statement.targets[0].value.attr == "modules"
        and isinstance(statement.targets[0].slice, ast.Name)
        and statement.targets[0].slice.id == "__name__"
        and (
            (
                isinstance(statement.value, ast.Name)
                and statement.value.id == "_implementation"
            )
            or _is_import_module_call(statement.value, expected_owner)
        )
    )


def _is_import_module_call(value: ast.expr, expected_owner: str) -> bool:
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id == "importlib"
        and value.func.attr == "import_module"
        and len(value.args) == 1
        and not value.keywords
        and isinstance(value.args[0], ast.Constant)
        and value.args[0].value == expected_owner
    )


def reverse_app_issues(
    root_modules: tuple[ParsedModule, ...],
) -> list[LayeredImportIssue]:
    graph, direct_lines = _root_import_graph(root_modules)

    reaches_app: dict[str, bool] = {}

    def reaches(module: str, active: set[str]) -> bool:
        if module == "app":
            return True
        if module in reaches_app:
            return reaches_app[module]
        if module in active:
            return False
        result = any(reaches(target, {*active, module}) for target in graph[module])
        reaches_app[module] = result
        return result

    issues: list[LayeredImportIssue] = []
    for module in sorted(graph):
        if module == "app" or not reaches(module, set()):
            continue
        direct = module in direct_lines
        issues.append(
            LayeredImportIssue(
                "reverse_import_app" if direct else "transitive_reverse_import_app",
                module,
                "root product modules must not depend on the thin app entrypoint",
                direct_lines.get(module),
            )
        )
    return issues


def _root_import_graph(
    root_modules: tuple[ParsedModule, ...],
) -> tuple[dict[str, set[str]], dict[str, int]]:
    known = frozenset(module.name for module in root_modules)
    graph = {module.name: set() for module in root_modules}
    direct_lines: dict[str, int] = {}
    for module in root_modules:
        for target, line in imported_targets(module, known):
            local = local_target(target, known)
            if local is None:
                continue
            graph[module.name].add(local)
            if local == "app":
                direct_lines[module.name] = line
    return graph, direct_lines


def resolve_from_base(module: ParsedModule, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = module.name.split(".")
    if package_parts and module.path.name != "__init__.py":
        package_parts.pop()
    keep = max(0, len(package_parts) - node.level + 1)
    base_parts = package_parts[:keep]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def imported_targets(module: ParsedModule, known: frozenset[str]) -> tuple[tuple[str, int], ...]:
    targets: list[tuple[str, int]] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Import):
            targets.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = resolve_from_base(module, node)
            if base and node.module:
                targets.append((base, node.lineno))
            for alias in node.names:
                candidate = f"{base}.{alias.name}" if base else alias.name
                if candidate in known:
                    targets.append((candidate, node.lineno))
    return tuple(dict.fromkeys(targets))


def local_target(target: str, known: frozenset[str]) -> str | None:
    candidate = target
    while candidate:
        if candidate in known:
            return candidate
        candidate, separator, _ = candidate.rpartition(".")
        if not separator:
            return None
    return None


def dependency_issues(
    modules: tuple[ParsedModule, ...],
) -> tuple[list[LayeredImportIssue], dict[str, set[str]]]:
    known = frozenset(module.name for module in modules)
    graph = {module.name: set() for module in modules}
    issues: list[LayeredImportIssue] = []
    for module in modules:
        source_layer = module.name.partition(".")[0]
        allowed_feature_targets = FEATURE_COMPOSITION_IMPORTS.get(
            module.name,
            frozenset(),
        )
        forbidden = FORBIDDEN_LAYER_IMPORTS[source_layer]
        for target, line in imported_targets(module, known):
            target_layer = target.partition(".")[0]
            if (
                source_layer in {"integrations", "infrastructure"}
                and "." not in target
                and target in PHYSICALLY_LAYERED_ROOTS
            ):
                issues.append(
                    LayeredImportIssue(
                        "compatibility_facade_dependency",
                        module.name,
                        f"physical layer must import the canonical owner of {target}",
                        line,
                    )
                )
            if target_layer in forbidden and target not in allowed_feature_targets:
                issues.append(
                    LayeredImportIssue(
                        "reverse_dependency",
                        module.name,
                        f"{source_layer} must not import {target_layer} ({target}).",
                        line,
                    )
                )
            local = local_target(target, known)
            if local is not None:
                graph[module.name].add(local)
    return issues, graph


def canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    body = cycle[:-1]
    rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
    smallest = min(rotations)
    return (*smallest, smallest[0])


def find_cycles(graph: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str], active: set[str]) -> None:
        if node in active:
            start = path.index(node)
            cycles.add(canonical_cycle([*path[start:], node]))
            return
        active.add(node)
        path.append(node)
        for target in sorted(graph[node]):
            visit(target, path, active)
        path.pop()
        active.remove(node)

    for module in sorted(graph):
        visit(module, [], set())
    return tuple(sorted(cycles))


def inspect_layered_imports(
    root: Path,
    *,
    root_ownership: tuple[RootModuleOwnership, ...] | None = None,
) -> LayeredImportReport:
    resolved_root = root.resolve()
    modules, package_parse_issues = discover_modules(resolved_root)
    root_modules, root_parse_issues = discover_root_modules(resolved_root)
    ownership = root_module_ownership() if root_ownership is None else root_ownership
    physical_root_names = frozenset(
        module.name.rpartition(".")[2]
        for module in modules
        if "." in module.name
    )
    dependency_findings, graph = dependency_issues(modules)
    cycle_findings = [
        LayeredImportIssue(
            "import_cycle",
            cycle[0],
            " -> ".join(cycle),
        )
        for cycle in find_cycles(graph)
    ]
    issues = tuple(
        sorted(
            (
                *package_parse_issues,
                *root_parse_issues,
                *dependency_findings,
                *cycle_findings,
                *ownership_issues(root_modules, ownership, physical_root_names),
                *(
                    compatibility_facade_issues(root_modules)
                    if root_ownership is None
                    else ()
                ),
                *reverse_app_issues(root_modules),
            )
        )
    )
    return LayeredImportReport(
        resolved_root,
        tuple(module.name for module in modules),
        tuple(module.name for module in root_modules),
        tuple(entry.module for entry in ownership if entry.location == "legacy-root"),
        issues,
    )


def main(argv: tuple[str, ...] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    root = Path(arguments[0]) if arguments else Path(__file__).resolve().parents[1]
    report = inspect_layered_imports(root)
    print(report.format())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
