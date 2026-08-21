from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from contextlib import contextmanager
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

lazy from application.presentation_ports import PresentationPorts
lazy from companion_window import CompanionWindow
lazy from flagship_ui import CORE_PERMISSION_LABELS
lazy from gesture_action_dispatcher import (
    GestureActionDispatcher,
    GestureDispatchDisposition,
    GestureDispatchResult,
)
lazy from gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionSafety,
)
lazy from gesture_configuration import (
    GestureAction,
    GestureConfiguration,
    GestureSource,
)
lazy from gesture_controller import GestureController
lazy from gesture_runtime import GestureRuntimeResult
lazy from infrastructure.db import StudioDB
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkResult,
    HandLandmarkStatus,
)
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from service_container import CompanionServices


class MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class OfflineSpeechEngine(QObject):
    finished = Signal()
    failed = Signal(str)
    viseme_cue = Signal(str, float)

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return None

    def speak(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("Authorization tests must not produce speech.")

    def stop(self) -> None:
        return None


class OfflineRealtime(QObject):
    status_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    speaking_changed = Signal(bool)
    viseme_cue = Signal(str, float)
    failed = Signal(str)
    output_text_started = Signal(int)
    output_text_delta = Signal(int, str)
    output_text_done = Signal(int)
    output_interrupted = Signal(int)

    running = False

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return None

    def start(self, _request: object) -> None:
        raise AssertionError("Authorization tests must not open a cloud session.")

    def stop(self) -> int:
        self.running = False
        return 0

    def set_external_playback_active(self, _active: bool) -> None:
        return None


class OfflineListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        raise AssertionError("Authorization tests must not open the microphone.")


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=("portable-zip",),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(root / "data", root / "config", root / "cache")

    def set_autostart(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("Authorization tests must not change device settings.")

    def open_path(self, _path: Path) -> None:
        raise AssertionError("Gesture text must not invoke the OS directly.")


class OfflineVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return []


class OfflinePanel(QWidget):
    def __init__(self, *args: object, **_kwargs: object) -> None:
        parent = next(
            (value for value in reversed(args) if isinstance(value, QWidget)),
            None,
        )
        super().__init__(parent)


def offline_presentation_ports() -> PresentationPorts:
    unavailable = lambda *_args, **_kwargs: None
    return PresentationPorts(
        ai_worker_factory=unavailable,
        voice_catalog=OfflineVoiceCatalog(),
        profile_manager_factory=unavailable,
        update_manager_factory=unavailable,
        portable_secret_binder=unavailable,
        autostart_configurator=unavailable,
        validate_face_assets=lambda _path: (),
        face_renderer_factory=unavailable,
        visible_windows=list,
    )


class ActionRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def show_control_center(self) -> None:
        self.calls.append(("show", None))

    def hide_control_center(self) -> None:
        self.calls.append(("hide", None))

    def set_audio_muted(self, muted: bool) -> None:
        self.calls.append(("muted", muted))

    def stop_current_speech(self) -> None:
        self.calls.append(("stop-speech", None))

    def toggle_listening(self) -> None:
        self.calls.append(("toggle-listening", None))

    def set_realtime_enabled(self, enabled: bool) -> None:
        self.calls.append(("realtime", enabled))

    def set_interaction_mode(self, mode: str) -> None:
        self.calls.append(("mode", mode))

    def acknowledge_positive(self) -> None:
        self.calls.append(("positive", None))

    def submit_safe_text_command(self, command: str) -> None:
        self.calls.append(("safe-command", command))


def _decision(
    action: GestureAction,
    safety: GestureActionSafety,
    *,
    command: str = "",
) -> GestureActionDecision:
    return GestureActionDecision(
        GestureActionDisposition.READY,
        "custom:authorization-contract",
        action,
        safety,
        command,
        GestureSource.CUSTOM,
    )


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


@contextmanager
def _running_window():
    application = _application()
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        db = StudioDB(root / "mohan.db")
        db.set_setting("onboarding_complete", True)
        secret = MemorySecretStore()
        services = CompanionServices(
            db=db,
            secret_store=secret,
            local_tts=OfflineSpeechEngine(),
            cloud_tts=OfflineSpeechEngine(),
            realtime=OfflineRealtime(),
            listener=OfflineListener(),
            presentation_ports=offline_presentation_ports(),
            azure_speech=OfflineSpeechEngine(),
            azure_hd_speech=OfflineSpeechEngine(),
            azure_secret_store=secret,
            azure_hd_secret_store=secret,
            secret_store_factory=lambda *_args: MemorySecretStore(),
            platform_services=OfflinePlatformServices(root),
        )
        window: CompanionWindow | None = None
        try:
            with (
                patch.object(QTimer, "start", return_value=None),
                patch.object(CompanionWindow, "speak", return_value=None),
                patch(
                    "presentation.dashboard_settings.PortableProfilePanel",
                    OfflinePanel,
                ),
                patch("presentation.dashboard_settings.UpdatePanel", OfflinePanel),
            ):
                window = CompanionWindow(
                    startup_speech=False,
                    services=services,
                    defer_visual_startup=True,
                )
            yield application, window
        finally:
            if window is not None:
                window.close()
            application.processEvents()
            db.close()


def _persist_permission_mode(window: CompanionWindow, mode: str) -> None:
    if mode not in {"禁止", "每次詢問", "允許"}:
        raise ValueError("Permission mode is not canonical.")
    capabilities = set(CORE_PERMISSION_LABELS)
    capabilities.update({
        "microphone_access",
        "microphone_listen",
        "realtime_session",
        "gesture_toggle_listening",
        "gesture_start_realtime",
    })
    window.db.set_setting(
        "flagship_permissions",
        dict.fromkeys(capabilities, mode),
    )
    window.db.set_setting(
        "gesture_permissions",
        {
            GestureAction.TOGGLE_LISTENING.value: mode,
            GestureAction.START_REALTIME.value: mode,
        },
    )
    center = window.dashboard.flagship_center
    for combo in center._permission_controls.values():
        index = combo.findData(mode)
        if index >= 0:
            combo.setCurrentIndex(index)
    center._configure_executor()


def test_local_reversible_actions_execute_without_authorization() -> None:
    recorder = ActionRecorder()

    def unexpected_authorization(_decision: GestureActionDecision) -> bool:
        raise AssertionError("A local reversible gesture requested authorization.")

    dispatcher = GestureActionDispatcher(
        recorder,
        authorize=unexpected_authorization,
    )
    cases = (
        (GestureAction.SHOW_DASHBOARD, ("show", None)),
        (GestureAction.MUTE_AUDIO, ("muted", True)),
        (GestureAction.STOP_SPEECH, ("stop-speech", None)),
        (GestureAction.STOP_REALTIME, ("realtime", False)),
    )
    for action, expected in cases:
        result = dispatcher.dispatch(
            _decision(action, GestureActionSafety.LOCAL_REVERSIBLE)
        )
        assert result.disposition is GestureDispatchDisposition.EXECUTED
        assert recorder.calls[-1] == expected


def test_sensitive_actions_respect_persisted_three_state_permission() -> None:
    decisions = (
        _decision(
            GestureAction.TOGGLE_LISTENING,
            GestureActionSafety.DEVICE_ACCESS,
        ),
        _decision(
            GestureAction.START_REALTIME,
            GestureActionSafety.CLOUD_SESSION,
        ),
    )
    with _running_window() as (_application_instance, window):
        application_dispatcher = window._gesture_controller._dispatcher
        authorizer = application_dispatcher._authorize
        assert callable(authorizer), (
            "CompanionWindow must compose a persisted gesture authorizer for "
            "microphone and Realtime actions."
        )
        recorder = ActionRecorder()
        dispatcher = GestureActionDispatcher(recorder, authorize=authorizer)

        _persist_permission_mode(window, "禁止")
        with patch.object(
            QMessageBox,
            "question",
            side_effect=AssertionError("Blocked permission must not prompt."),
        ):
            blocked = tuple(dispatcher.dispatch(item) for item in decisions)
        assert all(
            item.disposition is GestureDispatchDisposition.DENIED for item in blocked
        )
        assert recorder.calls == []

        _persist_permission_mode(window, "每次詢問")
        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.No,
        ) as denied_prompt:
            denied = tuple(dispatcher.dispatch(item) for item in decisions)
        assert denied_prompt.call_count == len(decisions)
        assert all(
            item.disposition is GestureDispatchDisposition.DENIED for item in denied
        )
        assert recorder.calls == []

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.Yes,
        ) as allowed_prompt:
            allowed_once = tuple(dispatcher.dispatch(item) for item in decisions)
        assert allowed_prompt.call_count == len(decisions)
        assert all(item.executed for item in allowed_once)
        assert recorder.calls == [
            ("toggle-listening", None),
            ("realtime", True),
        ]

        recorder.calls.clear()
        _persist_permission_mode(window, "允許")
        microphone, realtime = decisions
        with patch.object(
            QMessageBox,
            "question",
            side_effect=AssertionError("Persisted Allow must not prompt."),
        ):
            microphone_allowed = dispatcher.dispatch(microphone)
        assert microphone_allowed.executed
        # Realtime is an external-impact capability in the existing policy.
        # Its stronger safety floor still asks once even when the persisted
        # capability mode is Allow.
        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.Yes,
        ) as realtime_confirmation:
            realtime_allowed = dispatcher.dispatch(realtime)
        assert realtime_confirmation.call_count == 1
        assert realtime_allowed.executed
        assert recorder.calls == [
            ("toggle-listening", None),
            ("realtime", True),
        ]


def test_denial_never_reaches_sensitive_action_port() -> None:
    recorder = ActionRecorder()
    dispatcher = GestureActionDispatcher(
        recorder,
        authorize=lambda _decision: False,
    )
    for decision in (
        _decision(
            GestureAction.TOGGLE_LISTENING,
            GestureActionSafety.DEVICE_ACCESS,
        ),
        _decision(
            GestureAction.START_REALTIME,
            GestureActionSafety.CLOUD_SESSION,
        ),
    ):
        result = dispatcher.dispatch(decision)
        assert result.disposition is GestureDispatchDisposition.DENIED
    assert recorder.calls == []


def test_custom_command_reuses_send_chat_instead_of_direct_os_access() -> None:
    command = "請顯示今天的工作摘要"
    with _running_window() as (_application_instance, window):
        dashboard = window.dashboard
        chat_calls: list[tuple[str, str]] = []
        dashboard.send_chat = lambda: chat_calls.append((
            dashboard._input_source,
            dashboard.chat_input.text(),
        ))
        result = window._gesture_controller._dispatcher.dispatch(
            _decision(
                GestureAction.CUSTOM_COMMAND,
                GestureActionSafety.POLICY_ROUTED,
                command=command,
            )
        )
        assert result.disposition is GestureDispatchDisposition.EXECUTED
        assert chat_calls == [("gesture", command)]


class UnexpectedActionFailure(Exception):
    pass


class FailingActions(ActionRecorder):
    def show_control_center(self) -> None:
        raise UnexpectedActionFailure("private implementation detail")


def test_dispatcher_contains_unexpected_action_failures() -> None:
    result = GestureActionDispatcher(FailingActions()).dispatch(
        _decision(
            GestureAction.SHOW_DASHBOARD,
            GestureActionSafety.LOCAL_REVERSIBLE,
        )
    )
    assert result.disposition is GestureDispatchDisposition.FAILED
    assert result.reason_code == "action-boundary-failed"
    assert "private implementation detail" not in result.reason_code


class ControllerRuntime:
    def __init__(self, decision: GestureActionDecision) -> None:
        self.decision = decision

    def update(
        self,
        observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        return GestureRuntimeResult(observed_at, (), self.decision)

    def cancel(self) -> None:
        return None

    def reset(self) -> None:
        return None


class ControllerProvider:
    def analyze(
        self,
        _rgb_bytes: bytes,
        _width: int,
        _height: int,
        *,
        mirror: object,
    ) -> HandLandmarkResult:
        assert mirror is not None
        return HandLandmarkResult(HandLandmarkStatus.OK, 1)

    def cancel(self) -> None:
        return None


class ImmediatePool:
    def start(self, task: object) -> None:
        task.run()  # type: ignore[attr-defined]

    def clear(self) -> None:
        return None

    def waitForDone(self, _milliseconds: int) -> bool:
        return True


class FailingDispatcher:
    def dispatch(self, _decision: object) -> GestureDispatchResult:
        raise UnexpectedActionFailure("must not escape the Qt slot")


def test_dispatch_failure_stays_inside_qt_event_boundary() -> None:
    _application()
    decision = _decision(
        GestureAction.SHOW_DASHBOARD,
        GestureActionSafety.LOCAL_REVERSIBLE,
    )
    provider = ControllerProvider()
    controller = GestureController(
        FailingDispatcher(),
        provider_factory=lambda: provider,
        runtime=ControllerRuntime(decision),
    )
    captured: list[GestureDispatchResult] = []
    controller.dispatch_completed.connect(captured.append)
    controller._pool = ImmediatePool()  # type: ignore[assignment]
    controller.configure(GestureConfiguration(enabled=True), camera_available=True)
    try:
        controller.submit_frame(b"transient-rgb", 1, 1)
        _application().processEvents()
    finally:
        controller.close()
    assert len(captured) == 1
    assert captured[0].disposition is GestureDispatchDisposition.FAILED
    assert captured[0].action is GestureAction.SHOW_DASHBOARD
    assert captured[0].reason_code == "dispatch-boundary-failed"


def test_dispatch_result_is_visible_in_control_center_audit() -> None:
    result = GestureDispatchResult(
        GestureDispatchDisposition.EXECUTED,
        GestureAction.SHOW_DASHBOARD,
        "executed",
    )
    with _running_window() as (application, window):
        window._gesture_controller.dispatch_completed.emit(result)
        application.processEvents()
        matching = []
        for row in window.db.audit_rows(50):
            if "gesture" not in str(row["event_type"]):
                continue
            payload = json.loads(str(row["payload"]))
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if all(
                value in serialized
                for value in (
                    GestureAction.SHOW_DASHBOARD.value,
                    GestureDispatchDisposition.EXECUTED.value,
                    result.reason_code,
                )
            ):
                matching.append(row)
        assert matching, (
            "Gesture dispatch results must enter a user-visible audit path with "
            "canonical action, disposition, and reason values."
        )
        window.dashboard.flagship_center.refresh_audit()
        assert GestureAction.SHOW_DASHBOARD.value in (
            window.dashboard.flagship_center.audit_view.toPlainText()
        )


def run() -> None:
    tests = (
        test_local_reversible_actions_execute_without_authorization,
        test_sensitive_actions_respect_persisted_three_state_permission,
        test_denial_never_reaches_sensitive_action_port,
        test_custom_command_reuses_send_chat_instead_of_direct_os_access,
        test_dispatcher_contains_unexpected_action_failures,
        test_dispatch_failure_stays_inside_qt_event_boundary,
        test_dispatch_result_is_visible_in_control_center_audit,
    )
    failures: list[str] = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("GESTURE_AUTHORIZATION_CONTRACT_OK")


if __name__ == "__main__":
    run()
