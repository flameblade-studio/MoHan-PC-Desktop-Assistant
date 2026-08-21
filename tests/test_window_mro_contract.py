from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy from presentation.companion_window import CompanionWindow
lazy from presentation.dashboard_window import Dashboard

ROOT = Path(__file__).resolve().parents[1]

COMPANION_MIXINS = (
    ("presentation/companion_core.py", "CompanionCoreMixin"),
    ("presentation/companion_proactive.py", "CompanionProactiveMixin"),
    ("presentation/companion_visual_dynamics.py", "CompanionVisualDynamicsMixin"),
    ("presentation/companion_face_animation.py", "CompanionFaceAnimationMixin"),
    ("presentation/companion_speech_runtime.py", "CompanionSpeechRuntimeMixin"),
    ("presentation/companion_platform.py", "CompanionPlatformMixin"),
)
DASHBOARD_MIXINS = (
    ("presentation/dashboard_shell.py", "DashboardShellMixin"),
    ("presentation/dashboard_settings.py", "DashboardSettingsMixin"),
    ("presentation/dashboard_voice.py", "DashboardVoiceMixin"),
    ("presentation/dashboard_conversation.py", "DashboardConversationMixin"),
    ("presentation/dashboard_today_memory.py", "DashboardTodayMemoryMixin"),
    ("presentation/dashboard_platforms.py", "DashboardPlatformMixin"),
)


def _class(path: str, name: str) -> ast.ClassDef:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _method(owner: ast.ClassDef, name: str) -> ast.FunctionDef:
    return next(
        node
        for node in owner.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _direct_method_names(owner: ast.ClassDef) -> set[str]:
    return {
        node.name
        for node in owner.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _method_owners(
    mixins: tuple[tuple[str, str], ...],
) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for path, class_name in mixins:
        for method_name in _direct_method_names(_class(path, class_name)):
            owners.setdefault(method_name, []).append(class_name)
    return owners


def _calls_super_method(method: ast.FunctionDef, name: str) -> bool:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if (
            node.func.attr == name
            and isinstance(receiver, ast.Call)
            and isinstance(receiver.func, ast.Name)
            and receiver.func.id == "super"
        ):
            return True
    return False


def _called_attributes(method: ast.FunctionDef) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _self_qtimer_attributes(owner: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(owner):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        function = node.value.func
        if not isinstance(function, ast.Name) or function.id != "QTimer":
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                names.add(target.attr)
    return names


def _string_literals(method: ast.FunctionDef) -> set[str]:
    return {
        node.value
        for node in ast.walk(method)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _qtimer_construction_count(owner: ast.ClassDef) -> int:
    return sum(
        1
        for node in ast.walk(owner)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "QTimer"
    )


def _mro_identity(owner: type, count: int) -> tuple[tuple[str, str], ...]:
    return tuple(
        (base.__module__, base.__name__) for base in owner.__mro__[:count]
    )


def test_window_mro_is_explicit_and_stable() -> None:
    assert _mro_identity(CompanionWindow, 8) == (
        ("presentation.companion_window", "CompanionWindow"),
        ("presentation.companion_core", "CompanionCoreMixin"),
        ("presentation.companion_proactive", "CompanionProactiveMixin"),
        ("presentation.companion_visual_dynamics", "CompanionVisualDynamicsMixin"),
        ("presentation.companion_face_animation", "CompanionFaceAnimationMixin"),
        ("presentation.companion_speech_runtime", "CompanionSpeechRuntimeMixin"),
        ("presentation.companion_platform", "CompanionPlatformMixin"),
        ("PySide6.QtWidgets", "QMainWindow"),
    )
    assert _mro_identity(Dashboard, 9) == (
        ("presentation.dashboard_window", "Dashboard"),
        (
            "presentation.dashboard_wardrobe_preferences",
            "DashboardWardrobePreferencesMixin",
        ),
        ("presentation.dashboard_shell", "DashboardShellMixin"),
        ("presentation.dashboard_settings", "DashboardSettingsMixin"),
        ("presentation.dashboard_voice", "DashboardVoiceMixin"),
        ("presentation.dashboard_conversation", "DashboardConversationMixin"),
        ("presentation.dashboard_today_memory", "DashboardTodayMemoryMixin"),
        ("presentation.dashboard_platforms", "DashboardPlatformMixin"),
        ("PySide6.QtWidgets", "QDialog"),
    )


def test_each_mixin_method_has_one_direct_owner() -> None:
    for mixins in (COMPANION_MIXINS, DASHBOARD_MIXINS):
        duplicates = {
            name: owners
            for name, owners in _method_owners(mixins).items()
            if len(owners) != 1
        }
        assert duplicates == {}


def test_qt_events_delegate_or_terminate_explicitly() -> None:
    delegated_events = {
        ("presentation/companion_platform.py", "CompanionPlatformMixin"): (
            "mousePressEvent",
            "mouseMoveEvent",
            "mouseReleaseEvent",
        ),
        ("presentation/dashboard_shell.py", "DashboardShellMixin"): (
            "showEvent",
            "hideEvent",
            "changeEvent",
            "mousePressEvent",
            "moveEvent",
        ),
    }
    for (path, class_name), event_names in delegated_events.items():
        owner = _class(path, class_name)
        for event_name in event_names:
            assert _calls_super_method(_method(owner, event_name), event_name)

    close_event = _method(
        _class(
            "presentation/companion_platform.py",
            "CompanionPlatformMixin",
        ),
        "closeEvent",
    )
    assert not _calls_super_method(close_event, "closeEvent")
    assert {
        "_close_proactive_companion_app_bridge",
        "_cancel_adaptive_character_composition",
        "_close_runtime_services",
        "accept",
    } <= _called_attributes(close_event)


def test_every_owned_qtimer_has_an_explicit_stop_owner() -> None:
    companion_timers: set[str] = set()
    for path, class_name in COMPANION_MIXINS:
        owner = _class(path, class_name)
        owned_timers = _self_qtimer_attributes(owner)
        assert _qtimer_construction_count(owner) == len(owned_timers)
        companion_timers.update(owned_timers)

    platform = _class(
        "presentation/companion_platform.py",
        "CompanionPlatformMixin",
    )
    stopped_companion_timers = _string_literals(
        _method(platform, "_stop_window_timers")
    )
    assert companion_timers <= stopped_companion_timers
    assert "proactive_presence_timer" in stopped_companion_timers

    dashboard_timers: set[str] = set()
    for path, class_name in DASHBOARD_MIXINS:
        owner = _class(path, class_name)
        owned_timers = _self_qtimer_attributes(owner)
        expected_indirect_timers = 1 if class_name == "DashboardPlatformMixin" else 0
        assert _qtimer_construction_count(owner) == (
            len(owned_timers) + expected_indirect_timers
        )
        dashboard_timers.update(owned_timers)
    stopped_dashboard_timers = _string_literals(
        _method(platform, "_close_runtime_services")
    )
    assert dashboard_timers <= stopped_dashboard_timers

    platform_owner = _class(
        "presentation/dashboard_platforms.py",
        "DashboardPlatformMixin",
    )
    assert "stop" in _called_attributes(
        _method(platform_owner, "_clear_platform_cards")
    )
    assert "stop" in _called_attributes(_method(platform_owner, "save_platform"))
    assert "stop" in _called_attributes(_method(platform_owner, "save_platforms"))
