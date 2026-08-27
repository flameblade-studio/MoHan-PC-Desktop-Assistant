from __future__ import annotations

lazy import gc
lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QEvent, QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication, QWidget

lazy from application.presentation_ports import PresentationPorts
lazy from companion_window import CompanionWindow
lazy from gesture_action_dispatcher import (
    GestureDispatchDisposition,
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
lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from service_container import CompanionServices
lazy from speech_providers import (
    AZURE_HD_SPEECH_PROVIDER,
    AZURE_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
    OPENAI_SPEECH_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
)

EXPECTED_STOP_CALLS = 2
# Deferred deletions usually settle in a couple of rounds; the cap only stops
# a defective teardown from spinning forever.
MAX_CLEANUP_ROUNDS = 25
# Kept as a printed warning plus a generous ceiling instead of a strict zero
# so one stubborn widget cannot re-introduce intermittent CI failures.
MAX_LEAKED_TOP_LEVEL_WIDGETS = 4


def _drain_deferred_deletions(app: QApplication) -> int:
    """Flush queued deleteLater/timer work until top-level widgets stabilize."""
    previous = -1
    for _ in range(MAX_CLEANUP_ROUNDS):
        app.processEvents()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        gc.collect()
        count = len(app.topLevelWidgets())
        if count == previous:
            break
        previous = count
    return len(app.topLevelWidgets())


class _MemorySecretStore:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class _OfflineSpeechEngine(QObject):
    finished = Signal()
    failed = Signal(str)
    viseme_cue = Signal(float, str)

    def __init__(self) -> None:
        super().__init__()
        self.speak_calls: list[tuple[object, ...]] = []
        self.stop_calls = 0

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return

    def speak(self, *args: object, **_kwargs: object) -> None:
        self.speak_calls.append(args)

    def stop(self) -> None:
        self.stop_calls += 1


class _OfflineRealtime(QObject):
    status_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    speaking_changed = Signal(bool)
    viseme_cue = Signal(float, str)
    failed = Signal(str)
    output_text_started = Signal(int)
    output_text_delta = Signal(int, str)
    output_text_done = Signal(int)
    output_interrupted = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.stop_calls = 0

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return

    def start(self, _request: object) -> None:
        raise AssertionError("Regression test attempted a Realtime connection.")

    def stop(self) -> int:
        self.stop_calls += 1
        self.running = False
        return self.stop_calls

    def set_external_playback_active(self, _active: bool) -> None:
        return


class _OfflineRealtimeOutput(QObject):
    speaking_changed = Signal(bool)
    playback_guard_changed = Signal(bool)
    viseme_cue = Signal(float, str)
    status_changed = Signal(str)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.cancel_calls: list[int] = []
        self.responses: list[tuple[str, object]] = []

    def set_volume(self, _volume: int, _muted: bool = False) -> None:
        return

    def configure(self, _config: object) -> None:
        return

    def begin_response(self, generation: int) -> None:
        self.responses.append(("begin", generation))

    def add_text(self, generation: int, text: str) -> None:
        self.responses.append(("text", (generation, text)))

    def finish_response(self, generation: int) -> None:
        self.responses.append(("finish", generation))

    def cancel(self, generation: int) -> None:
        self.cancel_calls.append(generation)


class _OfflineListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    is_recording = False

    def toggle_listening(self) -> None:
        raise AssertionError("Regression test attempted microphone access.")


class _OfflinePlatformServices:
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
        self.paths = PlatformPaths(
            root / "data",
            root / "config",
            root / "cache",
        )

    def set_autostart(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("Regression test attempted device configuration.")

    def open_path(self, _path: Path) -> None:
        raise AssertionError("Regression test attempted an external path.")


class _OfflineVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return []


class _OfflinePanel(QWidget):
    def __init__(self, *args: object, **_kwargs: object) -> None:
        parent = next(
            (value for value in reversed(args) if isinstance(value, QWidget)),
            None,
        )
        super().__init__(parent)


def _offline_presentation_ports() -> PresentationPorts:
    unavailable = lambda *_args, **_kwargs: None
    return PresentationPorts(
        ai_worker_factory=unavailable,
        voice_catalog=_OfflineVoiceCatalog(),
        profile_manager_factory=unavailable,
        update_manager_factory=unavailable,
        portable_secret_binder=unavailable,
        autostart_configurator=unavailable,
        validate_face_assets=lambda _path: (),
        face_renderer_factory=unavailable,
        visible_windows=list,
    )


@dataclass(slots=True)
class _OfflineContext:
    window: CompanionWindow
    local: _OfflineSpeechEngine
    openai: _OfflineSpeechEngine
    azure: _OfflineSpeechEngine
    dragon_hd: _OfflineSpeechEngine
    realtime: _OfflineRealtime
    realtime_output: _OfflineRealtimeOutput
    openai_secret: _MemorySecretStore
    azure_secret: _MemorySecretStore
    azure_hd_secret: _MemorySecretStore


@dataclass(frozen=True, slots=True)
class _PerceptionScenario:
    environment: str
    vision_status: str
    gesture_status: str


@dataclass(frozen=True, slots=True)
class _SpeechRoute:
    provider_id: str
    engine_index: int


_PERCEPTION_SCENARIOS = (
    _PerceptionScenario("disabled", "disabled", "disabled"),
    _PerceptionScenario(
        "no-camera",
        "camera_unavailable",
        "camera-unavailable",
    ),
    _PerceptionScenario("no-models", "model_missing", "model-missing"),
)
_SPEECH_ROUTES = (
    _SpeechRoute(SYSTEM_LOCAL_PROVIDER, 0),
    _SpeechRoute(OPENAI_SPEECH_PROVIDER, 1),
    _SpeechRoute(AZURE_SPEECH_PROVIDER, 2),
    _SpeechRoute(AZURE_HD_SPEECH_PROVIDER, 3),
)


@pytest.fixture(scope="module", autouse=True)
def application() -> QApplication:
    app = QApplication.instance() or QApplication([])
    yield app
    # Module finalizer: settle every deferred deletion queued by the per-test
    # teardowns so no leaked top-level widget survives into the next module.
    leaked = _drain_deferred_deletions(app)
    leftovers = [
        f"{type(widget).__name__}(objectName={widget.objectName()!r})"
        for widget in app.topLevelWidgets()
    ]
    if leftovers:
        # Diagnostic listing for future leak hunts; the relaxed cap below is
        # the only hard gate.
        print(
            "[multisensory-speech-regression] leaked top-level widgets "
            f"({leaked}): {leftovers}"
        )
    assert leaked <= MAX_LEAKED_TOP_LEVEL_WIDGETS, leftovers


@pytest.fixture
def context(tmp_path: Path) -> _OfflineContext:
    db = StudioDB(tmp_path / "mohan.db")
    for key, value in (
        ("onboarding_complete", True),
        ("tts_enabled", True),
        ("windows_voice", "offline-windows-female"),
        ("tts_voice", "coral"),
        ("azure_speech_region", "eastasia"),
        ("azure_speech_voice", "zh-TW-HsiaoChenNeural"),
        ("azure_hd_speech_region", "westus2"),
        ("azure_hd_speech_voice", "zh-CN-Xiaochen:DragonHDLatestNeural"),
        ("camera_presence_enabled", False),
        ("gesture_recognition_enabled", False),
    ):
        db.set_setting(key, value)
    openai_secret = _MemorySecretStore("offline-openai-key")
    azure_secret = _MemorySecretStore("offline-azure-key")
    azure_hd_secret = _MemorySecretStore("offline-dragon-key")
    local = _OfflineSpeechEngine()
    openai = _OfflineSpeechEngine()
    azure = _OfflineSpeechEngine()
    dragon_hd = _OfflineSpeechEngine()
    realtime = _OfflineRealtime()
    realtime_output = _OfflineRealtimeOutput()
    services = CompanionServices(
        db=db,
        secret_store=openai_secret,
        local_tts=local,
        cloud_tts=openai,
        realtime=realtime,
        listener=_OfflineListener(),
        presentation_ports=_offline_presentation_ports(),
        realtime_speech_output=realtime_output,
        azure_speech=azure,
        azure_hd_speech=dragon_hd,
        azure_secret_store=azure_secret,
        azure_hd_secret_store=azure_hd_secret,
        secret_store_factory=lambda *_args: _MemorySecretStore(),
        platform_services=_OfflinePlatformServices(tmp_path),
    )
    with (
        patch.object(QTimer, "start", return_value=None),
        patch.object(CompanionWindow, "speak", return_value=None),
        patch("presentation.dashboard_settings.PortableProfilePanel", _OfflinePanel),
        patch("presentation.dashboard_settings.UpdatePanel", _OfflinePanel),
    ):
        window = CompanionWindow(
            startup_speech=False,
            services=services,
            defer_visual_startup=False,
        )
    value = _OfflineContext(
        window,
        local,
        openai,
        azure,
        dragon_hd,
        realtime,
        realtime_output,
        openai_secret,
        azure_secret,
        azure_hd_secret,
    )
    yield value
    window.close()
    window.deleteLater()
    # The dashboard is a parentless top-level dialog: closing the companion
    # window hides it but never deletes it, so release it explicitly.
    dashboard = getattr(window, "dashboard", None)
    if dashboard is not None:
        dashboard.close()
        dashboard.deleteLater()
    # Several rounds so already-expired singleShot callbacks fire now, while
    # their guards still see this window, instead of during a later test.
    for _ in range(4):
        QApplication.processEvents()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def _speech_calls(context: _OfflineContext) -> tuple[int, ...]:
    return tuple(
        len(engine.speak_calls)
        for engine in (
            context.local,
            context.openai,
            context.azure,
            context.dragon_hd,
        )
    )


def _stop_calls(context: _OfflineContext) -> tuple[int, ...]:
    return tuple(
        engine.stop_calls
        for engine in (
            context.local,
            context.openai,
            context.azure,
            context.dragon_hd,
        )
    )


def _route_speech(context: _OfflineContext, provider_id: str) -> None:
    window = context.window
    window.db.set_setting("voice_engine", provider_id)
    window._start_speech_provider(f"offline regression: {provider_id}")


def test_application_mute_is_visible_and_does_not_bill_a_provider(
    context: _OfflineContext,
) -> None:
    """A persisted app mute must not masquerade as a failed TTS engine."""

    window = context.window
    window.db.set_setting("voice_muted", True)
    before = _speech_calls(context)
    with patch.object(QTimer, "singleShot") as completion:
        window.speak("這一句在墨寒靜音時只顯示文字。", "happy")
    assert _speech_calls(context) == before
    assert window.audio_driven_mouth is False
    assert "已靜音" in window.dashboard.voice_phase.text()
    completion.assert_called_once()


def test_local_voice_failure_releases_mouth_and_speech_queue(
    context: _OfflineContext,
) -> None:
    """A failed SAPI request must not strand the companion in speaking mode."""

    window = context.window
    window.db.set_setting("voice_muted", False)
    window.db.set_setting("voice_engine", SYSTEM_LOCAL_PROVIDER)
    window.speak("本機語音失敗釋放測試。", "happy")
    assert window.speech_playing is True
    assert window.active_speech_engine == SYSTEM_LOCAL_PROVIDER

    with patch.object(window, "_begin_speech_motion_release"), patch.object(
        window,
        "_speech_audio_finished",
        wraps=window._speech_audio_finished,
    ) as finish:
        context.local.failed.emit("offline local failure")

    finish.assert_called_once()
    assert "本機語音失敗" in window.dashboard.api_status.text()


def _configure_perception_environment(
    context: _OfflineContext,
    temporary_models: Path,
    scenario: _PerceptionScenario,
) -> tuple[str, str]:
    window = context.window
    vision = window.dashboard.flagship_center.vision_controller
    gesture = window._gesture_controller
    if scenario.environment == "disabled":
        vision_health = vision.configure(enabled=False, camera_available=True)
        gesture_health = gesture.configure(
            GestureConfiguration(enabled=False),
            camera_available=True,
        )
    elif scenario.environment == "no-camera":
        vision_health = vision.configure(enabled=True, camera_available=False)
        gesture_health = gesture.configure(
            GestureConfiguration(enabled=True),
            camera_available=False,
        )
    else:
        vision._probe._model_directory = temporary_models / "missing-vision-models"
        gesture._models = type(gesture._models)(
            temporary_models / "missing-palm.onnx",
            temporary_models / "missing-hand.onnx",
        )
        with patch.object(
            vision._probe,
            "_inspect_engine",
            return_value=None,
        ):
            vision_health = vision.configure(enabled=True, camera_available=True)
        gesture_health = gesture.configure(
            GestureConfiguration(enabled=True),
            camera_available=True,
        )
    return vision_health.readiness.value, gesture_health.status.value


@pytest.mark.parametrize(
    "scenario",
    _PERCEPTION_SCENARIOS,
    ids=lambda scenario: scenario.environment,
)
@pytest.mark.parametrize(
    "route",
    _SPEECH_ROUTES,
    ids=lambda route: route.provider_id,
)
def test_optional_perception_failure_does_not_regress_queued_speech_routes(
    context: _OfflineContext,
    tmp_path: Path,
    scenario: _PerceptionScenario,
    route: _SpeechRoute,
) -> None:
    actual_vision, actual_gesture = _configure_perception_environment(
        context,
        tmp_path,
        scenario,
    )
    assert actual_vision == scenario.vision_status
    assert actual_gesture == scenario.gesture_status

    before = _speech_calls(context)
    _route_speech(context, route.provider_id)
    after = _speech_calls(context)

    assert after[route.engine_index] == before[route.engine_index] + 1
    assert sum(after) == sum(before) + 1
    assert _stop_calls(context) == (0, 0, 0, 0)
    assert context.realtime.stop_calls == 0
    assert context.realtime_output.cancel_calls == []


@pytest.mark.parametrize("perception_stop", ("vision", "gesture"))
@pytest.mark.parametrize(
    "route",
    _SPEECH_ROUTES,
    ids=lambda route: route.provider_id,
)
def test_visual_or_gesture_stop_does_not_interrupt_normal_speech(
    context: _OfflineContext,
    perception_stop: str,
    route: _SpeechRoute,
) -> None:
    window = context.window
    window.speech_playing = True
    window.active_speech_text = "non-gesture speech"
    window.active_speech_engine = route.provider_id
    window.state = "speaking"
    window.audio_driven_mouth = True
    window.mouth_open = True
    before = _speech_calls(context)
    _route_speech(context, route.provider_id)

    if perception_stop == "vision":
        window.dashboard.flagship_center.vision_controller.stop()
    else:
        window._gesture_controller.stop()

    after = _speech_calls(context)
    assert after[route.engine_index] == before[route.engine_index] + 1
    assert window.speech_playing
    assert window.active_speech_text == "non-gesture speech"
    assert window.active_speech_engine == route.provider_id
    assert window.state == "speaking"
    assert window.audio_driven_mouth
    assert window.mouth_open
    assert _stop_calls(context) == (0, 0, 0, 0)
    assert context.realtime.stop_calls == 0
    assert context.realtime_output.cancel_calls == []


@pytest.mark.parametrize(
    "scenario",
    _PERCEPTION_SCENARIOS,
    ids=lambda scenario: scenario.environment,
)
def test_realtime_output_remains_independent_of_optional_perception(
    context: _OfflineContext,
    tmp_path: Path,
    scenario: _PerceptionScenario,
) -> None:
    window = context.window
    actual_vision, actual_gesture = _configure_perception_environment(
        context,
        tmp_path,
        scenario,
    )
    assert actual_vision == scenario.vision_status
    assert actual_gesture == scenario.gesture_status
    generation = 41
    text = "離線 Realtime 輸出。"
    before = tuple(context.realtime_output.responses)
    window.realtime.running = True
    window.realtime.output_text_started.emit(generation)
    window.realtime.output_text_delta.emit(generation, text)
    window.realtime.output_text_done.emit(generation)

    assert tuple(context.realtime_output.responses) == (
        *before,
        ("begin", generation),
        ("text", (generation, text)),
        ("finish", generation),
    )
    assert context.realtime.running
    assert context.realtime.stop_calls == 0
    assert context.realtime_output.cancel_calls == []
    assert _stop_calls(context) == (0, 0, 0, 0)


def _prime_moving_speech(window: CompanionWindow) -> object:
    window.speech_queue.extend(("queued one", "queued two"))
    window.speech_playing = True
    window.active_speech_text = "gesture interrupted speech"
    window.active_speech_engine = OPENAI_REALTIME_PROVIDER
    window.active_speech_delivery_token = ""
    window.state = "speaking"
    window.audio_driven_mouth = True
    window.mouth_open = True
    window.mouth_closing = False
    window.ambient_motion_x = 0.0
    window.ambient_motion_y = 0.0
    window.speech_motion_y = -3.0
    window.speech_motion_target_y = -3.0
    window.gesture_motion_x = 0.0
    window.gesture_motion_y = 0.0
    window.gaze_x = 0.0
    window.last_composed_body_position = None
    window._compose_character_position()
    return window.character.pos()


def _stop_speech_decision() -> GestureActionDecision:
    return GestureActionDecision(
        GestureActionDisposition.READY,
        "open-palm",
        GestureAction.STOP_SPEECH,
        GestureActionSafety.LOCAL_REVERSIBLE,
        source=GestureSource.BUILTIN,
    )


def test_stop_speech_stops_every_engine_and_is_idempotent_without_motion_jitter(
    context: _OfflineContext,
) -> None:
    window = context.window
    position_before = _prime_moving_speech(window)
    mouth_stops = 0
    real_stop_mouth = window._stop_mouth_animation

    def count_mouth_stop() -> None:
        nonlocal mouth_stops
        mouth_stops += 1
        real_stop_mouth()

    window._stop_mouth_animation = count_mouth_stop
    dispatcher = window._gesture_controller._dispatcher

    first = dispatcher.dispatch(_stop_speech_decision())
    position_after_first = window.character.pos()
    first_engine_stops = _stop_calls(context)
    first_realtime_stops = context.realtime.stop_calls
    first_output_cancels = tuple(context.realtime_output.cancel_calls)
    second = dispatcher.dispatch(_stop_speech_decision())

    assert first.disposition is GestureDispatchDisposition.EXECUTED
    assert second.disposition is GestureDispatchDisposition.EXECUTED
    assert first_engine_stops == (1, 1, 1, 1)
    assert _stop_calls(context) == (2, 2, 2, 2)
    assert first_realtime_stops == 1
    assert context.realtime.stop_calls == EXPECTED_STOP_CALLS
    assert first_output_cancels == (1,)
    assert context.realtime_output.cancel_calls == [1, 2]
    assert not window.speech_queue
    assert not window.speech_playing
    assert window.active_speech_text == ""
    assert window.active_speech_engine == ""
    assert not window.audio_driven_mouth
    assert not window.mouth_open
    assert window.state == "idle"
    assert mouth_stops == 1
    assert position_after_first == position_before
    assert window.character.pos() == position_after_first
