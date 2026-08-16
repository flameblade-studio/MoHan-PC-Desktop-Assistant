from __future__ import annotations

lazy import ast
lazy import importlib
lazy import inspect
lazy import os
lazy import sys
lazy import threading
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MAX_COMPATIBILITY_ENTRY_LINES = 200
MAX_COMPATIBILITY_DEFINITION_LINES = 40
MAX_IMPLEMENTATION_OWNER_LINES = 1_200

REQUIRED_PUBLIC_SYMBOLS = frozenset({
    "ASSIST_INTENT_MARKERS",
    "CALENDAR_MARKERS",
    "CALENDAR_WRITE_MARKERS",
    "CHINESE_DAY_COUNTS",
    "CHINESE_MAIL_COUNTS",
    "CORE_PERMISSION_LABELS",
    "CloudHealthSignals",
    "CloudHealthWorker",
    "DRIVE_MARKERS",
    "DRIVE_WRITE_MARKERS",
    "FlagshipControlCenter",
    "FlagshipDraftValues",
    "GESTURE_PERMISSION_CAPABILITIES",
    "GMAIL_MARKERS",
    "GMAIL_SEND_MARKERS",
    "GMAIL_SEND_NEGATIONS",
    "GestureRecorderPort",
    "OAuthSignals",
    "OAuthWorker",
    "READ_INTENT_MARKERS",
    "UnavailableGestureRecorder",
    "WorkflowEditor",
})
REQUIRED_CLASS_SYMBOLS = frozenset({
    "CloudHealthSignals",
    "CloudHealthWorker",
    "FlagshipControlCenter",
    "OAuthSignals",
    "OAuthWorker",
    "WorkflowEditor",
})
EXTRACTED_PUBLIC_OWNER_MODULES = {
    **{
        name: "presentation.flagship.shared"
        for name in REQUIRED_PUBLIC_SYMBOLS
        - REQUIRED_CLASS_SYMBOLS
    },
    "CloudHealthSignals": "presentation.flagship.cloud_health",
    "CloudHealthWorker": "presentation.flagship.cloud_health",
    "FlagshipControlCenter": "presentation.flagship.control_center",
    "OAuthSignals": "presentation.flagship.oauth",
    "OAuthWorker": "presentation.flagship.oauth",
    "WorkflowEditor": "presentation.flagship.workflow_editor",
}
PUBLIC_EXPORT_CASES = tuple(sorted(REQUIRED_PUBLIC_SYMBOLS))
COMPATIBILITY_ENTRY = (ROOT / "flagship_ui.py").resolve()

EXPECTED_SIGNAL_ARITIES = {
    "OAuthSignals": {"done": 2, "failed": 2},
    "CloudHealthSignals": {"done": 2},
    "FlagshipControlCenter": {
        "speak_requested": 2,
        "remote_command_received": 1,
        "emergency_stop_requested": 0,
    },
}

TASK_CENTER_LABELS = {
    "zh-TW": "任務中心",
    "zh-CN": "任务中心",
    "en": "Task Center",
    "ja-JP": "タスクセンター",
}
LANGUAGE_CASES = tuple(TASK_CENTER_LABELS.items())


class _MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class _MemorySecretStoreFactory:
    def __init__(self) -> None:
        self.stores: dict[Path, _MemorySecretStore] = {}

    def __call__(
        self,
        path: Path,
        _description: str = "MoHan protected secret",
    ) -> _MemorySecretStore:
        return self.stores.setdefault(path.resolve(), _MemorySecretStore())


class _PartialInitializationProbeError(RuntimeError):
    """Expected constructor failure used to verify fail-closed Qt cleanup."""


class _FailingSecretStoreFactory:
    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise _PartialInitializationProbeError("partial initialization probe")


class _TranslatorProbe:
    def __init__(self, language: str) -> None:
        self.language = language


def _resolve_export(value: object) -> object:
    resolver = getattr(value, "resolve", None)
    return resolver() if callable(resolver) else value


def _flagship_module() -> object:
    return importlib.import_module("flagship_ui")


def _public_classes() -> dict[str, type]:
    module = _flagship_module()
    classes: dict[str, type] = {}
    for name in REQUIRED_CLASS_SYMBOLS:
        value = _resolve_export(getattr(module, name))
        assert isinstance(value, type), f"flagship_ui.{name} is not a class"
        classes[name] = value
    return classes


def _assert_parameter(
    signature: inspect.Signature,
    name: str,
    kind: inspect._ParameterKind,
    *,
    default: object = inspect.Parameter.empty,
) -> None:
    parameter = signature.parameters.get(name)
    assert parameter is not None, f"missing compatible parameter: {name}"
    assert parameter.kind is kind, (
        f"{name} changed from {kind.description} to "
        f"{parameter.kind.description}"
    )
    if default is inspect.Parameter.empty:
        assert parameter.default is inspect.Parameter.empty, (
            f"required parameter {name} unexpectedly gained a default"
        )
    else:
        assert parameter.default == default, (
            f"parameter {name} default changed: {parameter.default!r}"
        )


def _assert_no_new_required_parameters(
    signature: inspect.Signature,
    legacy_names: frozenset[str],
) -> None:
    for parameter in signature.parameters.values():
        assert parameter.kind not in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }, "compatibility constructors must remain explicit"
        if parameter.name in legacy_names:
            continue
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (
            f"new parameter {parameter.name} must be keyword-only"
        )
        assert parameter.default is not inspect.Parameter.empty, (
            f"new parameter {parameter.name} must be optional"
        )


def _signal_arities(owner: type) -> dict[str, int]:
    qt_core = importlib.import_module("PySide6.QtCore")
    signal_type = qt_core.QMetaMethod.Signal
    meta_object = owner.staticMetaObject
    signals: dict[str, int] = {}
    for index in range(meta_object.methodCount()):
        method = meta_object.method(index)
        if method.methodType() != signal_type:
            continue
        name = bytes(method.name()).decode("utf-8")
        signals[name] = method.parameterCount()
    return signals


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _definition_span(node: ast.AST) -> int:
    end_line = getattr(node, "end_lineno", None)
    start_line = getattr(node, "lineno", None)
    assert isinstance(start_line, int) and isinstance(end_line, int)
    return end_line - start_line + 1


def _imports_app(path: Path) -> bool:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".", 1)[0] == "app" for alias in node.names):
                return True
        elif (
            isinstance(node, ast.ImportFrom)
            and (
                (node.module or "").split(".", 1)[0] == "app"
                or (
                    node.module is None
                    and any(alias.name == "app" for alias in node.names)
                )
            )
        ) or _dynamically_imports_app(node):
            return True
    return False


def _dynamically_imports_app(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not node.args:
        return False
    module_name = node.args[0]
    if not (
        isinstance(module_name, ast.Constant)
        and isinstance(module_name.value, str)
        and module_name.value.split(".", 1)[0] == "app"
    ):
        return False
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
    ) or (
        isinstance(node.func, ast.Name)
        and node.func.id in {"__import__", "import_module"}
    )


def _assert_mro_contract(owner: type, required_base: type) -> None:
    mro = owner.__mro__
    assert mro[0] is owner
    assert mro[-1] is object
    assert mro.count(required_base) == 1
    assert len(mro) == len(set(mro)), f"{owner.__name__} has duplicate MRO entries"
    assert all(
        base.__module__.split(".", 1)[0] != "app"
        for base in mro
        if base is not object
    ), f"{owner.__name__} must not inherit from app.py"


def _product_source(value: object) -> Path | None:
    try:
        source = inspect.getsourcefile(value)
    except (TypeError, OSError):
        return None
    if not source:
        return None
    path = Path(source).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return None
    return path if path.suffix == ".py" else None


def _implementation_owner_sources(classes: dict[str, type]) -> frozenset[Path]:
    sources: set[Path] = set()
    for owner in classes.values():
        for base in owner.__mro__:
            source = _product_source(base)
            if source is not None:
                sources.add(source)
        for _name, member in inspect.getmembers(owner):
            source = _product_source(member)
            if source is not None:
                sources.add(source)
    return frozenset(sources)


def _flagship_implementation_sources(classes: dict[str, type]) -> frozenset[Path]:
    sources = set(_implementation_owner_sources(classes))
    sources.update((ROOT / "presentation" / "flagship").rglob("*.py"))
    sources.update(ROOT.glob("flagship*.py"))
    sources.update((ROOT / "presentation").glob("flagship*.py"))
    return frozenset(
        path.resolve()
        for path in sources
        if path.is_file() and path.resolve() != COMPATIBILITY_ENTRY
    )


def _public_export_owner_sources() -> dict[str, Path]:
    compatibility_module = _flagship_module()
    sources: dict[str, Path] = {}
    for name in REQUIRED_PUBLIC_SYMBOLS:
        owner_module_name = EXTRACTED_PUBLIC_OWNER_MODULES.get(name)
        if owner_module_name is None:
            owner = _resolve_export(vars(compatibility_module)[name])
            owner_module_name = owner.__module__
        owner_module = importlib.import_module(owner_module_name)
        module_file = getattr(owner_module, "__file__", None)
        assert module_file is not None, f"{name} has no inspectable owner module"
        source = Path(module_file).resolve()
        assert source.suffix == ".py", f"{name} owner is not Python source: {source}"
        try:
            source.relative_to(ROOT)
        except ValueError:
            pytest.fail(f"{name} owner escaped the product tree: {source}")
        sources[name] = source
    return sources


def _offline_platform(root: Path) -> object:
    contracts = importlib.import_module("platform_contracts")

    class OfflinePlatform:
        capabilities = contracts.PlatformCapabilities(
            platform_id="windows",
            display_name="Windows test boundary",
            system_local_speech=True,
            verified_female_voice_catalog=True,
            offline_speech_recognition=True,
            secure_secret_storage=True,
            desktop_autostart=False,
            native_window_management=False,
            published_installers=("test",),
        )
        paths = contracts.PlatformPaths(
            data=root / "data",
            config=root / "config",
            cache=root / "cache",
        )

        def set_autostart(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("flagship construction attempted autostart")

        def open_path(self, path: Path) -> None:
            raise AssertionError(f"flagship construction attempted to open {path}")

    return OfflinePlatform()


def _select_data(combo: object, value: str) -> None:
    index = combo.findData(value)
    assert index >= 0, f"missing canonical combo value: {value}"
    combo.setCurrentIndex(index)


def _record_cleanup(
    errors: list[Exception],
    operation: str,
    callback: Callable[[], object],
) -> object | None:
    try:
        return callback()
    except Exception as error:  # noqa: BLE001 -- preserve every cleanup failure
        error.add_note(operation)
        errors.append(error)
        return None


def _verify_thread_pool_stopped(
    widget: object,
    *,
    required: bool,
) -> list[Exception]:
    errors: list[Exception] = []
    thread_pool = getattr(widget, "thread_pool", None)
    if required and thread_pool is None:
        errors.append(AssertionError("FlagshipControlCenter must expose thread_pool"))
        return errors
    if thread_pool is None:
        return errors

    drained = _record_cleanup(
        errors,
        "waiting for the flagship thread pool",
        lambda: thread_pool.waitForDone(1_500),
    )
    if drained is False:
        errors.append(
            AssertionError("flagship thread pool did not drain in 1.5 seconds")
        )
    active_count = _record_cleanup(
        errors,
        "checking the flagship thread pool",
        thread_pool.activeThreadCount,
    )
    if active_count not in (None, 0):
        errors.append(
            AssertionError(
                f"flagship thread pool retained {active_count} active task(s)"
            )
        )
    return errors


def _verify_timers_stopped(timers: object | None) -> list[Exception]:
    if not isinstance(timers, tuple):
        return []
    errors: list[Exception] = []
    for timer in timers:
        is_active = _record_cleanup(
            errors,
            "checking a flagship child timer",
            timer.isActive,
        )
        if is_active is True:
            errors.append(
                AssertionError("flagship cleanup left a child QTimer active")
            )
    return errors


def _close_widget(
    application: object,
    widget: object,
    *,
    require_flagship_contract: bool,
) -> None:
    qt_core = importlib.import_module("PySide6.QtCore")
    cleanup_errors: list[Exception] = []
    timers = _record_cleanup(
        cleanup_errors,
        "enumerating child timers during flagship cleanup",
        lambda: tuple(widget.findChildren(qt_core.QTimer)),
    )
    _record_cleanup(cleanup_errors, "closing the flagship Qt window", widget.close)
    close_services = getattr(widget, "close_services", None)
    if require_flagship_contract and not callable(close_services):
        cleanup_errors.append(
            AssertionError("FlagshipControlCenter must expose close_services()")
        )
    if callable(close_services):
        _record_cleanup(cleanup_errors, "closing flagship services", close_services)
    _record_cleanup(
        cleanup_errors,
        "processing Qt close events",
        application.processEvents,
    )

    cleanup_errors.extend(
        _verify_thread_pool_stopped(
            widget,
            required=require_flagship_contract,
        )
    )
    cleanup_errors.extend(_verify_timers_stopped(timers))

    _record_cleanup(
        cleanup_errors,
        "scheduling the flagship Qt window for deletion",
        widget.deleteLater,
    )
    _record_cleanup(
        cleanup_errors,
        "dispatching deferred Qt deletions",
        lambda: application.sendPostedEvents(None, qt_core.QEvent.DeferredDelete),
    )
    _record_cleanup(
        cleanup_errors,
        "processing deferred Qt deletions",
        application.processEvents,
    )

    if cleanup_errors:
        raise ExceptionGroup("flagship Qt cleanup failed", cleanup_errors)


def _close_center(application: object, center: object) -> None:
    _close_widget(
        application,
        center,
        require_flagship_contract=True,
    )


def _active_thread_ids() -> frozenset[int]:
    return frozenset(
        thread.ident
        for thread in threading.enumerate()
        if thread.is_alive() and thread.ident is not None
    )


def _raise_cleanup_errors(
    primary_error: BaseException | None,
    cleanup_errors: list[Exception],
    label: str,
) -> None:
    if not cleanup_errors:
        return
    grouped_errors: list[BaseException] = [*cleanup_errors]
    if primary_error is not None:
        grouped_errors.insert(0, primary_error)
    raise BaseExceptionGroup(label, grouped_errors) from None


def _close_known_centers(
    application: object,
    centers: list[object],
) -> tuple[list[Exception], set[int]]:
    errors: list[Exception] = []
    attempted_widget_ids: set[int] = set()
    for center in reversed(centers):
        attempted_widget_ids.add(id(center))
        _record_cleanup(
            errors,
            "closing a constructed FlagshipControlCenter",
            lambda center=center: _close_center(application, center),
        )
    return errors, attempted_widget_ids


def _close_transient_widgets(
    application: object,
    baseline_widgets: frozenset[object],
    attempted_widget_ids: set[int],
) -> list[Exception]:
    errors: list[Exception] = []
    _record_cleanup(
        errors,
        "processing events before enumerating transient Qt windows",
        application.processEvents,
    )
    transient_widgets = _record_cleanup(
        errors,
        "enumerating transient Qt windows after a failed construction",
        lambda: tuple(
            widget
            for widget in application.topLevelWidgets()
            if widget not in baseline_widgets
            and id(widget) not in attempted_widget_ids
        ),
    )
    if not isinstance(transient_widgets, tuple):
        return errors
    for widget in transient_widgets:
        try:
            widget.objectName()
        except RuntimeError:
            # Qt can delete child-owned transient widgets while Python still
            # holds their wrappers.  They are already closed and cannot leak.
            continue
        _record_cleanup(
            errors,
            "closing a partially constructed flagship Qt window",
            lambda widget=widget: _close_widget(
                application,
                widget,
                require_flagship_contract=False,
            ),
        )
    return errors


def _verify_no_lifecycle_residue(
    application: object,
    baseline_widgets: frozenset[object],
    baseline_threads: frozenset[int],
) -> list[Exception]:
    errors: list[Exception] = []
    _record_cleanup(
        errors,
        "processing events before lifecycle residue verification",
        application.processEvents,
    )
    leaked_widgets = _record_cleanup(
        errors,
        "verifying that no transient Qt windows survived cleanup",
        lambda: tuple(
            widget
            for widget in application.topLevelWidgets()
            if widget not in baseline_widgets
        ),
    )
    live_leaked_widgets: tuple[object, ...] = ()
    if isinstance(leaked_widgets, tuple):
        live_leaked_widgets = tuple(
            widget
            for widget in leaked_widgets
            if _qt_wrapper_is_alive(widget)
        )
    if live_leaked_widgets:
        errors.append(
            AssertionError(
                "flagship lifecycle left top-level Qt windows alive: "
                f"{[type(widget).__name__ for widget in live_leaked_widgets]}"
            )
        )
    leaked_threads = _active_thread_ids() - baseline_threads
    if leaked_threads:
        errors.append(
            AssertionError(
                "flagship lifecycle left Python thread(s) alive: "
                f"{sorted(leaked_threads)}"
            )
        )
    return errors


def _qt_wrapper_is_alive(widget: object) -> bool:
    try:
        widget.objectName()
    except RuntimeError:
        return False
    return True


def _cleanup_language_case(
    application: object,
    *,
    open_centers: list[object],
    baseline_widgets: frozenset[object],
    baseline_threads: frozenset[int],
    database: object | None,
) -> list[Exception]:
    cleanup_errors, attempted_widget_ids = _close_known_centers(
        application,
        open_centers,
    )
    cleanup_errors.extend(
        _close_transient_widgets(
            application,
            baseline_widgets,
            attempted_widget_ids,
        )
    )
    if database is not None:
        _record_cleanup(
            cleanup_errors,
            "closing the isolated flagship test database",
            database.close,
        )
    cleanup_errors.extend(
        _verify_no_lifecycle_residue(
            application,
            baseline_widgets,
            baseline_threads,
        )
    )
    return cleanup_errors


def _cleanup_partial_center_case(
    application: object,
    center: object,
    baseline_widgets: frozenset[object],
    baseline_threads: frozenset[int],
) -> list[Exception]:
    cleanup_errors: list[Exception] = []
    _record_cleanup(
        cleanup_errors,
        "closing a partially initialized FlagshipControlCenter",
        lambda: _close_widget(
            application,
            center,
            require_flagship_contract=False,
        ),
    )
    cleanup_errors.extend(
        _close_transient_widgets(
            application,
            baseline_widgets,
            {id(center)},
        )
    )
    cleanup_errors.extend(
        _verify_no_lifecycle_residue(
            application,
            baseline_widgets,
            baseline_threads,
        )
    )
    return cleanup_errors


@pytest.mark.parametrize("name", PUBLIC_EXPORT_CASES)
def test_public_exports_preserve_the_exact_owner_identity(name: str) -> None:
    module = _flagship_module()
    exports = set(getattr(module, "__all__", ()))
    assert name in exports, f"flagship_ui.__all__ lost the published symbol {name}"
    assert name in vars(module), f"flagship_ui lost the published symbol {name}"

    if name in EXTRACTED_PUBLIC_OWNER_MODULES:
        owner_module_name = EXTRACTED_PUBLIC_OWNER_MODULES[name]
        owner_module = importlib.import_module(owner_module_name)
        owner = _resolve_export(getattr(owner_module, name))
    else:
        owner = _resolve_export(vars(module)[name])
        owner_module = importlib.import_module(owner.__module__)

    assert vars(module)[name] is owner, (
        f"flagship_ui.{name} must be the exact owner-module export"
    )
    assert getattr(owner_module, name) is owner


def test_legacy_constructor_signatures_remain_compatible() -> None:
    classes = _public_classes()
    for name, owner in classes.items():
        owner_module = importlib.import_module(owner.__module__)
        assert getattr(owner_module, name) is owner
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    keyword_only = inspect.Parameter.KEYWORD_ONLY

    oauth = inspect.signature(classes["OAuthWorker"])
    for name in ("provider_id", "client_id", "client_secret", "scopes"):
        _assert_parameter(oauth, name, positional)
    _assert_no_new_required_parameters(
        oauth,
        frozenset({"provider_id", "client_id", "client_secret", "scopes"}),
    )

    cloud = inspect.signature(classes["CloudHealthWorker"])
    _assert_parameter(cloud, "provider_id", positional)
    _assert_parameter(cloud, "token", positional)
    _assert_parameter(cloud, "language", positional, default="zh-TW")
    _assert_no_new_required_parameters(
        cloud,
        frozenset({"provider_id", "token", "language"}),
    )

    editor = inspect.signature(classes["WorkflowEditor"])
    _assert_parameter(editor, "parent", positional, default=None)
    _assert_parameter(editor, "language", keyword_only, default="zh-TW")
    _assert_no_new_required_parameters(
        editor,
        frozenset({"parent", "language"}),
    )

    center = inspect.signature(classes["FlagshipControlCenter"])
    _assert_parameter(center, "db", positional)
    _assert_parameter(center, "data_path", positional)
    _assert_parameter(center, "parent", positional, default=None)
    _assert_parameter(center, "platform_services", keyword_only, default=None)
    _assert_parameter(center, "secret_store_factory", keyword_only, default=None)
    _assert_parameter(center, "language", keyword_only, default="zh-TW")
    _assert_no_new_required_parameters(
        center,
        frozenset({
            "db",
            "data_path",
            "parent",
            "platform_services",
            "secret_store_factory",
            "language",
        }),
    )


def test_required_qt_inheritance_and_signals_remain_compatible() -> None:
    qt_core = importlib.import_module("PySide6.QtCore")
    qt_widgets = importlib.import_module("PySide6.QtWidgets")
    classes = _public_classes()

    required_bases = {
        "OAuthSignals": qt_core.QObject,
        "OAuthWorker": qt_core.QRunnable,
        "CloudHealthSignals": qt_core.QObject,
        "CloudHealthWorker": qt_core.QRunnable,
        "WorkflowEditor": qt_widgets.QDialog,
        "FlagshipControlCenter": qt_widgets.QWidget,
    }
    for class_name, required_base in required_bases.items():
        owner = classes[class_name]
        assert issubclass(owner, required_base)
        _assert_mro_contract(owner, required_base)

    for class_name, expected in EXPECTED_SIGNAL_ARITIES.items():
        actual = _signal_arities(classes[class_name])
        assert expected.items() <= actual.items(), class_name


def test_flagship_ui_is_a_thin_compatibility_entry() -> None:
    entry_path = ROOT / "flagship_ui.py"
    source_lines = entry_path.read_text(encoding="utf-8").splitlines()
    assert len(source_lines) <= MAX_COMPATIBILITY_ENTRY_LINES, (
        "flagship_ui.py must be a thin compatibility entry, not an implementation "
        f"module ({len(source_lines)} lines)"
    )

    entry_tree = _tree(entry_path)
    definitions = [
        node
        for node in entry_tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    oversized = {
        node.name: _definition_span(node)
        for node in definitions
        if _definition_span(node) > MAX_COMPATIBILITY_DEFINITION_LINES
    }
    assert oversized == {}, (
        "flagship_ui.py contains implementation instead of compatibility glue: "
        f"{oversized}"
    )


def test_flagship_compatibility_entry_does_not_depend_on_app() -> None:
    entry_path = ROOT / "flagship_ui.py"
    assert not _imports_app(entry_path), "flagship_ui.py must not import app.py"


def test_flagship_public_implementations_are_owned_outside_the_entry() -> None:
    classes = _public_classes()
    still_owned = {
        name: owner.__module__
        for name, owner in classes.items()
        if owner.__module__ == "flagship_ui"
    }
    assert still_owned == {}, (
        "published classes must have real owners outside the compatibility entry: "
        f"{still_owned}"
    )


def test_flagship_control_center_owns_each_decoupled_responsibility() -> None:
    center = _public_classes()["FlagshipControlCenter"]
    expected_owners = {
        "_companion_tab": "presentation.flagship.companion",
        "_gesture_interaction_card": "presentation.flagship.gesture_editor",
        "_openai_vision_preference_card": "presentation.flagship.vision",
        "save_draft_settings": "presentation.flagship.settings_security",
    }
    actual = {
        method_name: inspect.getmodule(getattr(center, method_name)).__name__
        for method_name in expected_owners
    }
    assert actual == expected_owners


def test_every_public_export_owner_is_bounded() -> None:
    oversized_owners: dict[str, tuple[str, int, int]] = {}
    for name, source in _public_export_owner_sources().items():
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        limit = (
            MAX_COMPATIBILITY_ENTRY_LINES
            if source == COMPATIBILITY_ENTRY
            else MAX_IMPLEMENTATION_OWNER_LINES
        )
        if line_count > limit:
            oversized_owners[name] = (
                str(source.relative_to(ROOT)),
                line_count,
                limit,
            )
    assert oversized_owners == {}, (
        "every published flagship export must have a bounded, inspectable owner "
        f"(path, lines, limit): {oversized_owners}"
    )


def test_flagship_has_no_replacement_giant_implementation_owner() -> None:
    implementation_sources = _flagship_implementation_sources(_public_classes())
    assert implementation_sources, "no flagship implementation modules were resolved"
    oversized_owners = {
        str(path.relative_to(ROOT)): len(
            path.read_text(encoding="utf-8").splitlines()
        )
        for path in implementation_sources
        if len(path.read_text(encoding="utf-8").splitlines())
        > MAX_IMPLEMENTATION_OWNER_LINES
    }
    assert oversized_owners == {}, (
        "flagship_ui.py was replaced by another oversized implementation owner: "
        f"{oversized_owners}"
    )


def test_flagship_implementation_owners_do_not_depend_on_app() -> None:
    implementation_sources = _flagship_implementation_sources(_public_classes())
    reverse_dependencies = [
        str(path.relative_to(ROOT))
        for path in implementation_sources
        if _imports_app(path)
    ]
    assert reverse_dependencies == [], (
        "flagship implementation owners must not depend on app.py: "
        f"{reverse_dependencies}"
    )


def _qt_application() -> object:
    qt_widgets = importlib.import_module("PySide6.QtWidgets")
    application = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    application.setQuitOnLastWindowClosed(False)
    application.processEvents()
    return application


def test_partial_initialization_cleanup_preserves_the_primary_error() -> None:
    flagship_module = _flagship_module()
    center_class = _public_classes()["FlagshipControlCenter"]
    application = _qt_application()
    baseline_widgets = frozenset(application.topLevelWidgets())
    baseline_threads = _active_thread_ids()

    constructor_error: BaseException | None = None
    cleanup_errors: list[Exception] = []
    partial_center = center_class.__new__(center_class)
    original_translator = vars(flagship_module)["FlagshipTranslator"]
    temporary = TemporaryDirectory(prefix="mohan-flagship-partial-init-")
    try:
        flagship_module.FlagshipTranslator = _TranslatorProbe
        center_class.__init__(
            partial_center,
            None,
            Path(temporary.name),
            secret_store_factory=_FailingSecretStoreFactory(),
        )
    except _PartialInitializationProbeError as error:
        constructor_error = error
    finally:
        primary_error = sys.exception() or constructor_error
        _record_cleanup(
            cleanup_errors,
            "restoring the real FlagshipTranslator after the probe",
            lambda: setattr(
                flagship_module,
                "FlagshipTranslator",
                original_translator,
            ),
        )
        cleanup_errors.extend(
            _cleanup_partial_center_case(
                application,
                partial_center,
                baseline_widgets,
                baseline_threads,
            )
        )
        _record_cleanup(
            cleanup_errors,
            "removing the partial-initialization temporary directory",
            temporary.cleanup,
        )
        _raise_cleanup_errors(
            primary_error,
            cleanup_errors,
            "partial initialization cleanup failed after the primary error",
        )

    assert isinstance(constructor_error, _PartialInitializationProbeError), (
        "the constructor probe did not fail at the requested initialization boundary"
    )


def _assert_language_settings_round_trip(
    application: object,
    database_module: object,
    center_class: type,
    language: str,
    task_label: str,
) -> None:
    baseline_widgets = frozenset(application.topLevelWidgets())
    baseline_threads = _active_thread_ids()
    open_centers: list[object] = []
    database: object | None = None

    temporary = TemporaryDirectory(prefix=f"mohan-flagship-{language}-")
    language_root = Path(temporary.name)
    try:
        database = database_module.StudioDB(language_root / "mohan.db")
        database.set_setting("camera_presence_enabled", False)
        database.set_setting("face_identity_enabled", False)
        secrets = _MemorySecretStoreFactory()
        platform = _offline_platform(language_root)

        center = center_class(
            database,
            language_root,
            platform_services=platform,
            secret_store_factory=secrets,
            language=language,
        )
        open_centers.append(center)
        application.processEvents()
        assert center.language == language
        assert center.tabs.tabText(0) == task_label
        _select_data(center.proactive_mode, "active")
        center.minimum_away_minutes.setValue(7)
        center.conversation_silence_minutes.setValue(31)
        _select_data(center._permission_controls["email_send"], "禁止")
        assert center.save_draft_settings() is True
        persisted = database.settings_snapshot()
        _close_center(application, center)
        open_centers.remove(center)

        reopened = center_class(
            database,
            language_root,
            platform_services=platform,
            secret_store_factory=secrets,
            language=language,
        )
        open_centers.append(reopened)
        application.processEvents()
        assert reopened.tabs.tabText(0) == task_label
        assert reopened.proactive_mode.currentData() == "active"
        assert reopened.minimum_away_minutes.value() == 7
        assert reopened.conversation_silence_minutes.value() == 31
        assert reopened._permission_controls["email_send"].currentData() == "禁止"
        assert database.settings_snapshot() == persisted
    finally:
        primary_error = sys.exception()
        cleanup_errors = _cleanup_language_case(
            application,
            open_centers=open_centers,
            baseline_widgets=baseline_widgets,
            baseline_threads=baseline_threads,
            database=database,
        )
        _record_cleanup(
            cleanup_errors,
            f"removing the {language} flagship temporary directory",
            temporary.cleanup,
        )
        _raise_cleanup_errors(
            primary_error,
            cleanup_errors,
            f"{language} flagship lifecycle or cleanup failed",
        )


@pytest.mark.parametrize(
    ("language", "task_label"),
    LANGUAGE_CASES,
    ids=tuple(language for language, _label in LANGUAGE_CASES),
)
def test_four_language_settings_round_trip_and_qt_lifecycle(
    language: str,
    task_label: str,
) -> None:
    database_module = importlib.import_module("db")
    center_class = _public_classes()["FlagshipControlCenter"]
    application = _qt_application()
    _assert_language_settings_round_trip(
        application,
        database_module,
        center_class,
        language,
        task_label,
    )


def run() -> None:
    for name in PUBLIC_EXPORT_CASES:
        test_public_exports_preserve_the_exact_owner_identity(name)
    test_legacy_constructor_signatures_remain_compatible()
    test_required_qt_inheritance_and_signals_remain_compatible()
    test_flagship_ui_is_a_thin_compatibility_entry()
    test_flagship_compatibility_entry_does_not_depend_on_app()
    test_flagship_public_implementations_are_owned_outside_the_entry()
    test_flagship_has_no_replacement_giant_implementation_owner()
    test_flagship_implementation_owners_do_not_depend_on_app()
    test_partial_initialization_cleanup_preserves_the_primary_error()
    for language, task_label in LANGUAGE_CASES:
        test_four_language_settings_round_trip_and_qt_lifecycle(
            language,
            task_label,
        )
    print("FLAGSHIP_UI_DECOUPLING_CONTRACT_OK")


if __name__ == "__main__":
    run()
