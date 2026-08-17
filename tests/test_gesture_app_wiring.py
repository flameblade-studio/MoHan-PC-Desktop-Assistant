from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication, QWidget

lazy from application.presentation_ports import PresentationPorts
lazy from companion_window import CompanionWindow
lazy from gesture_action_dispatcher import (
    GestureActionDispatcher,
    GestureDispatchDisposition,
)
lazy from gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionSafety,
)
lazy from gesture_application_adapter import GestureApplicationAdapter
lazy from gesture_configuration import GestureAction, GestureSource
lazy from gesture_controller import GestureController
lazy from infrastructure.db import StudioDB
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

    def __init__(self) -> None:
        super().__init__()
        self.stop_calls = 0

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return None

    def speak(self, *_args, **_kwargs) -> None:
        raise AssertionError("Gesture wiring test attempted speech output.")

    def stop(self) -> None:
        self.stop_calls += 1


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

    def start(self, _request) -> None:
        raise AssertionError("Gesture wiring test attempted a Realtime connection.")

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
        raise AssertionError("Gesture wiring test attempted microphone access.")


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

    def set_autostart(self, *_args, **_kwargs) -> None:
        raise AssertionError("Gesture wiring test attempted device configuration.")

    def open_path(self, _path: Path) -> None:
        raise AssertionError("Gesture wiring test attempted to open an external path.")


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


def decision(
    action: GestureAction,
    *,
    command: str = "",
) -> GestureActionDecision:
    safety = (
        GestureActionSafety.POLICY_ROUTED
        if action is GestureAction.CUSTOM_COMMAND
        else GestureActionSafety.LOCAL_REVERSIBLE
    )
    return GestureActionDecision(
        GestureActionDisposition.READY,
        "test-gesture",
        action,
        safety,
        command,
        GestureSource.CUSTOM,
    )


@pytest.fixture(scope="module", autouse=True)
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path: Path) -> CompanionWindow:
    db = StudioDB(tmp_path / "mohan.db")
    db.set_setting("onboarding_complete", True)
    secret = MemorySecretStore()
    local = OfflineSpeechEngine()
    cloud = OfflineSpeechEngine()
    azure = OfflineSpeechEngine()
    azure_hd = OfflineSpeechEngine()
    services = CompanionServices(
        db=db,
        secret_store=secret,
        local_tts=local,
        cloud_tts=cloud,
        realtime=OfflineRealtime(),
        listener=OfflineListener(),
        presentation_ports=offline_presentation_ports(),
        azure_speech=azure,
        azure_hd_speech=azure_hd,
        azure_secret_store=secret,
        azure_hd_secret_store=secret,
        secret_store_factory=lambda *_args: MemorySecretStore(),
        platform_services=OfflinePlatformServices(tmp_path),
    )
    with (
        patch.object(QTimer, "start", return_value=None),
        patch.object(CompanionWindow, "speak", return_value=None),
        patch("presentation.dashboard_settings.PortableProfilePanel", OfflinePanel),
        patch("presentation.dashboard_settings.UpdatePanel", OfflinePanel),
    ):
        companion = CompanionWindow(
            startup_speech=False,
            services=services,
            defer_visual_startup=True,
        )
    yield companion
    companion.close()
    QApplication.processEvents()


def dispatch(
    dispatcher: GestureActionDispatcher,
    action: GestureAction,
    *,
    command: str = "",
) -> None:
    result = dispatcher.dispatch(decision(action, command=command))
    assert result.disposition is GestureDispatchDisposition.EXECUTED


def test_one_controller_dispatcher_and_adapter_are_shared(
    window: CompanionWindow,
) -> None:
    controller = window._gesture_controller
    dispatcher = controller._dispatcher
    adapter = window._gesture_application

    assert isinstance(controller, GestureController)
    assert isinstance(dispatcher, GestureActionDispatcher)
    assert isinstance(adapter, GestureApplicationAdapter)
    assert dispatcher._actions is adapter
    assert window.dashboard.gesture_controller is controller
    assert window.dashboard.flagship_center._gesture_controller is controller
    assert window.dashboard.flagship_center._gesture_recorder is controller


def test_gesture_actions_reuse_existing_application_paths(
    window: CompanionWindow,
) -> None:
    dispatcher = window._gesture_controller._dispatcher
    dashboard = window.dashboard

    chat_calls: list[tuple[str, str]] = []
    dashboard.send_chat = lambda: chat_calls.append((
        dashboard._input_source,
        dashboard.chat_input.text(),
    ))
    dispatch(
        dispatcher,
        GestureAction.CUSTOM_COMMAND,
        command="請顯示今天的工作摘要",
    )
    assert chat_calls == [("gesture", "請顯示今天的工作摘要")]

    dispatch(dispatcher, GestureAction.MUTE_AUDIO)
    assert dashboard.voice_muted.isChecked() is True
    dispatch(dispatcher, GestureAction.UNMUTE_AUDIO)
    assert dashboard.voice_muted.isChecked() is False

    # Opening the console from a wave intentionally acknowledges the user
    # through the existing speech path.  Keep this wiring test offline while
    # asserting that the acknowledgement remains part of the interaction.
    with patch.object(window, "speak") as speak:
        dispatch(dispatcher, GestureAction.SHOW_DASHBOARD)
    speak.assert_called_once()
    assert dashboard.isVisible()
    dispatch(dispatcher, GestureAction.HIDE_DASHBOARD)
    assert not dashboard.isVisible()

    dispatch(dispatcher, GestureAction.WORK_MODE)
    assert dashboard.mode_combo.currentData() == "工作"
    dispatch(dispatcher, GestureAction.COMPANION_MODE)
    assert dashboard.mode_combo.currentData() == "陪伴"
    dispatch(dispatcher, GestureAction.DO_NOT_DISTURB_MODE)
    assert dashboard.mode_combo.currentData() == "勿擾"

    state_calls: list[tuple[str, str, float]] = []
    window.set_state = lambda state, *, source, intensity: state_calls.append((
        state,
        source,
        intensity,
    ))
    dispatch(dispatcher, GestureAction.POSITIVE_ACKNOWLEDGEMENT)
    assert state_calls == [("happy", "conversation", 0.55)]

    engines = (window.tts, window.azure_tts, window.azure_hd_tts)
    dispatch(dispatcher, GestureAction.STOP_SPEECH)
    assert [engine.stop_calls for engine in engines] == [1, 1, 1]
    assert not window.speech_queue


def test_wave_recognition_acknowledges_with_expression_and_greeting(
    window: CompanionWindow,
) -> None:
    state_calls: list[tuple[str, str, float]] = []
    speak_calls: list[tuple[str, str]] = []
    window.set_state = lambda state, *, source, intensity: state_calls.append((
        state,
        source,
        intensity,
    ))
    window.speak = lambda text, state: speak_calls.append((text, state))

    wave = Mock()
    wave.gesture_id = "wave"
    wave.triggered = True
    result = Mock()
    result.recognitions = (wave,)
    window._on_gesture_recognition(result)

    assert state_calls == [("happy", "visual", 0.6)]
    assert speak_calls == [("嗨，我在這裡！", "happy")]

    state_calls.clear()
    speak_calls.clear()
    other = Mock()
    other.gesture_id = "open-palm"
    other.triggered = True
    ignored = Mock()
    ignored.recognitions = (other,)
    window._on_gesture_recognition(ignored)

    assert state_calls == []
    assert speak_calls == []
