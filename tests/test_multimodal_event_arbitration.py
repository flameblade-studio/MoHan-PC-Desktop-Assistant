from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QCoreApplication
lazy from PySide6.QtTest import QSignalSpy

lazy from companion_proactivity_preferences import CompanionProactivityPreferences
lazy from gesture_action_dispatcher import (
    GestureActionDispatcher,
    GestureDispatchDisposition,
)
lazy from gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionRouter,
    GestureActionSafety,
    GestureTrigger,
)
lazy from gesture_configuration import (
    GestureAction,
    GestureBinding,
    GestureConfiguration,
)
lazy from multisensory_interaction import InteractionKind, ProactiveInteraction
lazy from proactive_companion_app_bridge import (
    ProactiveAppDisposition,
    ProactiveAppEvent,
    ProactiveAppState,
    ProactiveCompanionAppBridge,
)
lazy from proactive_companion_runtime import (
    CandidatePriority,
    NormalizedCompanionEnvironment,
    ProactiveCompanionRequest,
    ProactiveCompanionRuntime,
    ProactiveSource,
)
lazy from speech_boundary import SpeechTimingCollector
lazy from vision_controller import VisionController
lazy from vision_domain import IdentityObservation, IdentityState, SceneUnderstanding
lazy from wellbeing_app_bridge import SpeakRequest

NOW = datetime(2027, 1, 8, 12, tzinfo=UTC)
EXPECTED_REPORT_COUNT = 2
EXPECTED_OPERATION_ID = 7


class DeviceRecorder:
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
        self.calls.append(("command", command))


class MemoryIdentities:
    pass


class DeferredPool:
    def __init__(self) -> None:
        self.tasks: list[object] = []
        self.clear_calls = 0
        self.wait_calls = 0

    def start(self, task: object) -> None:
        self.tasks.append(task)

    def clear(self) -> None:
        self.clear_calls += 1

    def waitForDone(self, _milliseconds: int) -> None:
        self.wait_calls += 1


class VisionProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def analyze_frame(
        self,
        _rgb_bytes: bytes,
        _width: int,
        _height: int,
    ) -> SceneUnderstanding:
        self.calls += 1
        if self.fail:
            raise RuntimeError("private provider failure")
        return SceneUnderstanding(
            IdentityObservation(IdentityState.NO_FACE),
            (),
            (),
            (),
        )


class Runtime:
    def __init__(self) -> None:
        self.reports: list[tuple[str, bool]] = []
        self.proposals = 0

    def propose(self, _environment: object, _preferences: object):
        self.proposals += 1
        token = f"delivery-{self.proposals}"
        return ProactiveCompanionRequest(
            SpeakRequest("Neutral reminder.", "wellbeing", token),
            ProactiveInteraction(InteractionKind.GENTLE_CHECK_IN, "gentle"),
            ProactiveSource.WELLBEING,
            CandidatePriority.REST,
            token,
        )

    def report_spoken(self, token: str, *, succeeded: bool) -> bool:
        self.reports.append((token, succeeded))
        return succeeded


class ValueStore:
    def __init__(self, value: object) -> None:
        self.value = value

    def load(self) -> object:
        return self.value


class SpeechPort:
    def __init__(self, *, accept: bool = True) -> None:
        self.accept = accept
        self.submissions: list[tuple[int, object]] = []

    def submit(
        self,
        _request: object,
        _performance: object,
        *,
        generation: int,
        completed: object,
    ) -> bool:
        self.submissions.append((generation, completed))
        return self.accept

    def finish(self, index: int, succeeded: bool) -> None:
        callback = self.submissions[index][1]
        callback(succeeded)


def configured_gesture(
    gesture_id: str,
    action: GestureAction,
) -> GestureConfiguration:
    configuration = GestureConfiguration(enabled=True)
    definition = configuration.definition(gesture_id).with_binding(
        GestureBinding(action)
    )
    return configuration.replace_definition(definition)


def proactive_state(**changes: object) -> ProactiveAppState:
    value = ProactiveAppState(
        generation=1,
        now=NOW,
        language="en",
        user_title="there",
        session_user_active=True,
        camera_enabled=False,
    )
    return replace(value, **changes)


def proactive_bridge(*, speech_accepts: bool = True):
    runtime = Runtime()
    speech = SpeechPort(accept=speech_accepts)
    bridge = ProactiveCompanionAppBridge(
        lambda _phrasebook: runtime,
        ValueStore(CompanionProactivityPreferences()),
        ValueStore(None),
        speech,
    )
    return bridge, runtime, speech


def assert_playback_suppresses_proactive_while_stop_gesture_wins() -> None:
    environment = NormalizedCompanionEnvironment(
        now=NOW,
        user_present=True,
        absence_duration_seconds=0.0,
        focus_active=False,
        meeting_active=False,
        fullscreen_active=False,
        seconds_since_user_interaction=60.0 * 60.0,
        reminder_trigger=None,
        language="en",
        user_title="there",
        speech_active=True,
    )
    assert not ProactiveCompanionRuntime._may_interrupt(
        environment,
        CompanionProactivityPreferences(),
    )

    devices = DeviceRecorder()
    router = GestureActionRouter(cooldown_seconds=2.0)
    configuration = configured_gesture("open-palm", GestureAction.STOP_SPEECH)
    first = router.route(GestureTrigger("open-palm", 0.99, 10.0), configuration)
    result = GestureActionDispatcher(devices).dispatch(first)
    assert result.executed
    assert devices.calls == [("stop-speech", None)]
    repeated = router.route(
        GestureTrigger("open-palm", 0.99, 11.0),
        configuration,
    )
    assert repeated.disposition is GestureActionDisposition.COOLDOWN
    assert not GestureActionDispatcher(devices).dispatch(repeated).executed
    assert devices.calls == [("stop-speech", None)]


def assert_device_claims_fail_closed_without_recursive_calls() -> None:
    devices = DeviceRecorder()
    listening = GestureActionDecision(
        GestureActionDisposition.READY,
        "open-palm",
        GestureAction.TOGGLE_LISTENING,
        GestureActionSafety.DEVICE_ACCESS,
    )
    missing = GestureActionDispatcher(devices).dispatch(listening)
    assert missing.disposition is GestureDispatchDisposition.CONFIRMATION_REQUIRED
    assert devices.calls == []

    def broken_authorizer(_decision: object) -> bool:
        raise RuntimeError("private authorization failure")

    failed = GestureActionDispatcher(
        devices,
        authorize=broken_authorizer,
    ).dispatch(listening)
    assert failed.disposition is GestureDispatchDisposition.FAILED
    assert failed.reason_code == "authorization-boundary-failed"
    assert devices.calls == []


def assert_vision_is_single_flight_and_stale_work_cannot_publish() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    controller = VisionController(MemoryIdentities())  # type: ignore[arg-type]
    pool = DeferredPool()
    provider = VisionProvider()
    controller._pool = pool  # type: ignore[assignment]
    controller._provider = provider  # type: ignore[assignment]
    controller._enabled = True
    scenes = QSignalSpy(controller.scene_changed)

    controller.submit_frame(b"first", 1, 1)
    controller.submit_frame(b"dropped-while-busy", 1, 1)
    assert len(pool.tasks) == 1
    task = pool.tasks[0]
    controller.stop()
    task.run()
    application.processEvents()
    assert scenes.count() == 0
    assert pool.clear_calls == 1
    assert provider.calls == 1

    controller.close()
    assert pool.wait_calls == 1


def assert_vision_failure_stays_inside_its_provider_boundary() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    controller = VisionController(MemoryIdentities())  # type: ignore[arg-type]
    pool = DeferredPool()
    provider = VisionProvider(fail=True)
    controller._pool = pool  # type: ignore[assignment]
    controller._provider = provider  # type: ignore[assignment]
    controller._enabled = True
    health = QSignalSpy(controller.health_changed)
    controller.submit_frame(b"rgb", 1, 1)
    task = pool.tasks[0]
    task.run()
    application.processEvents()
    assert controller._consecutive_analysis_failures == 1
    assert health.count() == 0
    assert not controller._busy
    controller.close()


def assert_proactive_timeout_close_and_provider_failure_release_once() -> None:
    bridge, runtime, speech = proactive_bridge()
    first = bridge.dispatch(ProactiveAppEvent(proactive_state(generation=1)))
    assert first.disposition is ProactiveAppDisposition.SUBMITTED
    expired = bridge.dispatch(
        ProactiveAppEvent(
            proactive_state(generation=2, now=NOW + timedelta(minutes=6))
        )
    )
    assert expired.disposition is ProactiveAppDisposition.SUBMITTED
    assert runtime.reports == [("delivery-1", False)]
    speech.finish(0, True)
    assert runtime.reports == [("delivery-1", False)]
    bridge.close()
    assert runtime.reports == [
        ("delivery-1", False),
        ("delivery-2", False),
    ]
    speech.finish(1, True)
    assert len(runtime.reports) == EXPECTED_REPORT_COUNT

    rejected, rejected_runtime, _speech = proactive_bridge(
        speech_accepts=False
    )
    result = rejected.dispatch(ProactiveAppEvent(proactive_state()))
    assert result.disposition is ProactiveAppDisposition.LKG
    assert rejected_runtime.reports == [("delivery-1", False)]


def assert_speech_timing_is_deduplicated_data_not_a_control_loop() -> None:
    class Boundary:
        audio_offset = 10_000_000
        duration = 2_000_000
        boundary_type = "word"

    collector = SpeechTimingCollector(7)
    first = collector.word_boundary(Boundary())
    assert first is not None
    assert first.operation_id == EXPECTED_OPERATION_ID
    assert collector.word_boundary(Boundary()) is None


def run() -> None:
    assert_playback_suppresses_proactive_while_stop_gesture_wins()
    assert_device_claims_fail_closed_without_recursive_calls()
    assert_vision_is_single_flight_and_stale_work_cannot_publish()
    assert_vision_failure_stays_inside_its_provider_boundary()
    assert_proactive_timeout_close_and_provider_failure_release_once()
    assert_speech_timing_is_deduplicated_data_not_a_control_loop()
    print("MULTIMODAL_EVENT_ARBITRATION_OK")


if __name__ == "__main__":
    run()
