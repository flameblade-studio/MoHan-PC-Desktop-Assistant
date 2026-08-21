from __future__ import annotations

lazy import os
lazy import sys
lazy from collections.abc import Callable
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

lazy from gesture_action_dispatcher import (
    GestureDispatchDisposition,
    GestureDispatchResult,
)
lazy from gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionSafety,
)
lazy from gesture_configuration import GestureAction, GestureConfiguration
lazy from gesture_controller import GestureController, _HandAnalysisOutcome
lazy from gesture_runtime import GestureRuntimeResult
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkResult,
    HandLandmarkStatus,
)

_DECISION = GestureActionDecision(
    GestureActionDisposition.READY,
    "open-palm",
    GestureAction.SHOW_DASHBOARD,
    GestureActionSafety.LOCAL_REVERSIBLE,
)

EXPECTED_FRAME_COUNT = 2


class UnexpectedDispatchFailure(Exception):
    pass


class Provider:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(
        self,
        _rgb_bytes: bytes,
        _width: int,
        _height: int,
        *,
        mirror: object,
    ) -> HandLandmarkResult:
        assert mirror is not None
        self.calls += 1
        return HandLandmarkResult(HandLandmarkStatus.OK, self.calls)

    def cancel(self) -> None:
        return None


class Runtime:
    def update(
        self,
        observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        return GestureRuntimeResult(observed_at, (), _DECISION)

    def cancel(self) -> None:
        return None

    def reset(self) -> None:
        return None


class ImmediatePool:
    def start(self, task: object) -> None:
        task.run()  # type: ignore[attr-defined]

    def clear(self) -> None:
        return None

    def waitForDone(self, _milliseconds: int) -> bool:
        return True


class RecoveringDispatcher:
    def __init__(self) -> None:
        self.calls = 0

    def dispatch(self, decision: object) -> GestureDispatchResult:
        assert isinstance(decision, GestureActionDecision)
        self.calls += 1
        if self.calls == 1:
            raise UnexpectedDispatchFailure("private dispatcher detail")
        return GestureDispatchResult(
            GestureDispatchDisposition.EXECUTED,
            decision.action,
            "executed",
        )


class ProcessControlDispatcher:
    def __init__(self, failure: BaseException) -> None:
        self._failure = failure

    def dispatch(self, _decision: object) -> GestureDispatchResult:
        raise self._failure


def _application() -> QCoreApplication:
    application = QCoreApplication.instance()
    return application if application is not None else QCoreApplication([])


def _controller(
    dispatcher: RecoveringDispatcher | ProcessControlDispatcher,
) -> tuple[GestureController, Provider]:
    provider = Provider()
    controller = GestureController(
        dispatcher,
        provider_factory=lambda: provider,
        runtime=Runtime(),
    )
    controller._pool = ImmediatePool()  # type: ignore[assignment]
    controller.configure(GestureConfiguration(enabled=True), camera_available=True)
    return controller, provider


def test_dispatch_exception_is_failed_without_poisoning_qt_or_next_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = _application()
    dispatcher = RecoveringDispatcher()
    controller, provider = _controller(dispatcher)
    results: list[GestureDispatchResult] = []
    escaped: list[BaseException] = []
    event_loop_completed: list[bool] = []
    controller.dispatch_completed.connect(results.append)

    def record_escaped(
        _exception_type: type[BaseException],
        exception: BaseException,
        _traceback: object,
    ) -> None:
        escaped.append(exception)

    monkeypatch.setattr(sys, "excepthook", record_escaped)
    event_loop = QEventLoop()

    def exercise_frames() -> None:
        controller.submit_frame(b"\x00\x00\x00", 1, 1)
        controller.submit_frame(b"\x01\x01\x01", 1, 1)
        event_loop_completed.append(True)
        event_loop.quit()

    QTimer.singleShot(0, exercise_frames)
    QTimer.singleShot(1000, event_loop.quit)
    try:
        event_loop.exec()
        application.processEvents()
    finally:
        controller.close()

    assert event_loop_completed == [True]
    assert escaped == []
    assert provider.calls == EXPECTED_FRAME_COUNT
    assert dispatcher.calls == EXPECTED_FRAME_COUNT
    assert len(results) == EXPECTED_FRAME_COUNT
    assert results[0].disposition is GestureDispatchDisposition.FAILED
    assert results[0].action is GestureAction.SHOW_DASHBOARD
    assert results[0].reason_code == "dispatch-boundary-failed"
    assert "private dispatcher detail" not in results[0].reason_code
    assert results[1].disposition is GestureDispatchDisposition.EXECUTED
    assert results[1].reason_code == "executed"


@pytest.mark.parametrize(
    "failure_factory",
    (KeyboardInterrupt, SystemExit),
    ids=("keyboard-interrupt", "system-exit"),
)
def test_process_control_exceptions_are_not_swallowed(
    failure_factory: Callable[[], BaseException],
) -> None:
    controller, provider = _controller(ProcessControlDispatcher(failure_factory()))
    outcome = _HandAnalysisOutcome(
        provider,
        HandLandmarkResult(HandLandmarkStatus.OK, 1),
    )
    generation = controller._generation
    try:
        with pytest.raises(failure_factory):
            controller._analysis_completed(outcome, generation)
    finally:
        controller.close()
