from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication

lazy from application.gesture_action_router import (
    GestureActionDecision as OwnerGestureActionDecision,
)
lazy from application.gesture_action_router import (
    GestureActionDisposition as OwnerGestureActionDisposition,
)
lazy from application.gesture_action_router import (
    GestureActionSafety as OwnerGestureActionSafety,
)
lazy from domain.air_interaction import AirHandSample
lazy from gesture_action_router import (
    GestureActionDecision,
)
lazy from gesture_configuration import GestureAction, GestureConfiguration
lazy from gesture_controller import GestureController
lazy from gesture_runtime import GestureRuntimeResult
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkResult,
    HandLandmarkStatus,
)

FRAME = b"private-rgb-frame"


class DeferredPool:
    def __init__(self) -> None:
        self.tasks: list[object] = []
        self.clear_count = 0

    def start(self, task: object) -> None:
        self.tasks.append(task)

    def clear(self) -> None:
        self.clear_count += 1
        self.tasks.clear()

    def waitForDone(self, _milliseconds: int) -> bool:
        return True

    def run(self, index: int = 0) -> object:
        task = self.tasks[index]
        task.run()  # type: ignore[attr-defined]
        return task


class Provider:
    def __init__(
        self,
        statuses: tuple[HandLandmarkStatus, ...] = (HandLandmarkStatus.OK,),
    ) -> None:
        self.statuses = list(statuses)
        self.calls: list[tuple[int, int, int]] = []
        self.cancel_count = 0

    def analyze(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
        *,
        mirror: object,
    ) -> HandLandmarkResult:
        assert mirror is not None
        self.calls.append((len(rgb_bytes), width, height))
        status = self.statuses.pop(0) if self.statuses else HandLandmarkStatus.OK
        return HandLandmarkResult(status, len(self.calls))

    def cancel(self) -> None:
        self.cancel_count += 1


READY_DECISION = OwnerGestureActionDecision(
    OwnerGestureActionDisposition.READY,
    "open-palm",
    GestureAction.STOP_SPEECH,
    OwnerGestureActionSafety.LOCAL_REVERSIBLE,
)


class Runtime:
    def __init__(self, *, decision: GestureActionDecision | None = READY_DECISION) -> None:
        self.decision = decision
        self.calls: list[tuple[float, tuple[object, ...], GestureConfiguration]] = []
        self.cancel_count = 0
        self.reset_count = 0

    def update(self, observed_at, hands, configuration) -> GestureRuntimeResult:
        self.calls.append((observed_at, hands, configuration))
        return GestureRuntimeResult(observed_at, (), self.decision)

    def cancel(self) -> None:
        self.cancel_count += 1

    def reset(self) -> None:
        self.reset_count += 1


class Dispatcher:
    def __init__(self) -> None:
        self.decisions: list[GestureActionDecision] = []

    def dispatch(self, decision: GestureActionDecision) -> object:
        self.decisions.append(decision)
        return object()


@dataclass(slots=True)
class Harness:
    controller: GestureController
    provider: Provider
    runtime: Runtime
    dispatcher: Dispatcher
    pool: DeferredPool
    temporary: TemporaryDirectory[str]


def harness(
    *,
    statuses: tuple[HandLandmarkStatus, ...] = (HandLandmarkStatus.OK,),
    decision: GestureActionDecision | None = READY_DECISION,
) -> Harness:
    provider = Provider(statuses)
    runtime = Runtime(decision=decision)
    dispatcher = Dispatcher()
    pool = DeferredPool()
    temporary = TemporaryDirectory()
    model_directory = Path(temporary.name)
    (model_directory / "palm_detection_mediapipe_2023feb.onnx").write_bytes(b"model")
    (model_directory / "handpose_estimation_mediapipe_2023feb.onnx").write_bytes(b"model")
    controller = GestureController(
        dispatcher,
        model_directory=model_directory,
        provider_factory=lambda: provider,
        runtime=runtime,
    )
    controller._pool = pool  # type: ignore[assignment]
    return Harness(controller, provider, runtime, dispatcher, pool, temporary)


def enabled() -> GestureConfiguration:
    return GestureConfiguration(enabled=True)


def run_task(state: Harness, application: QCoreApplication, index: int = 0) -> object:
    task = state.pool.run(index)
    application.processEvents()
    return task


def assert_disabled_and_missing_models_fail_closed(
    application: QCoreApplication,
) -> None:
    state = harness(statuses=(HandLandmarkStatus.MODEL_MISSING,))
    state.controller.configure(GestureConfiguration(), camera_available=True)
    state.controller.submit_frame(FRAME, 3, 2)
    assert state.pool.tasks == []
    assert state.provider.calls == []

    state.controller.configure(enabled(), camera_available=True)
    state.controller.submit_frame(FRAME, 3, 2)
    run_task(state, application)
    assert state.runtime.calls == []
    assert state.dispatcher.decisions == []
    assert not state.controller.sampling_enabled


def assert_visual_perception_samples_hands_without_enabling_actions(
    application: QCoreApplication,
) -> None:
    state = harness(decision=None)
    emitted: list[tuple[AirHandSample, ...]] = []
    state.controller.hand_samples_changed.connect(
        lambda hands, _observed_at: emitted.append(hands)
    )
    health = state.controller.configure(
        GestureConfiguration(),
        camera_available=True,
        perception_enabled=True,
    )

    assert health.ready
    assert state.controller.sampling_enabled
    state.controller.submit_frame(FRAME, 3, 2)
    run_task(state, application)

    assert emitted
    assert state.dispatcher.decisions == []


def assert_busy_drops_frames_and_worker_is_deferred(
    application: QCoreApplication,
) -> None:
    state = harness(decision=None)
    state.controller.configure(enabled(), camera_available=True)
    state.controller.submit_frame(FRAME, 3, 2)
    state.controller.submit_frame(b"dropped-frame", 3, 2)
    assert len(state.pool.tasks) == 1
    assert state.provider.calls == []
    run_task(state, application)
    assert len(state.provider.calls) == 1
    assert state.provider.calls[0] == (len(FRAME), 3, 2)


def assert_only_current_generation_dispatches_and_each_frame_has_one_action(
    application: QCoreApplication,
) -> None:
    state = harness()
    state.controller.configure(enabled(), camera_available=True)
    state.controller.submit_frame(FRAME, 3, 2)
    stale_task = state.pool.tasks[0]
    state.controller.configure(enabled(), camera_available=True)
    stale_task.run()  # type: ignore[attr-defined]
    application.processEvents()
    assert state.dispatcher.decisions == []

    state.controller.submit_frame(FRAME, 3, 2)
    run_task(state, application, index=-1)
    assert state.dispatcher.decisions == [READY_DECISION]


def assert_cancel_stop_and_three_failures_disable(
    application: QCoreApplication,
) -> None:
    state = harness(
        statuses=(
            HandLandmarkStatus.INFERENCE_FAILED,
            HandLandmarkStatus.INFERENCE_FAILED,
            HandLandmarkStatus.INFERENCE_FAILED,
        )
    )
    state.controller.configure(enabled(), camera_available=True)
    for index in range(3):
        state.controller.submit_frame(FRAME, 3, 2)
        run_task(state, application, index=-1)
    assert not state.controller.sampling_enabled
    assert state.runtime.calls == []
    state.controller.stop()
    assert state.runtime.reset_count >= 1
    state.controller.submit_frame(FRAME, 3, 2)
    assert len(state.provider.calls) == 3


def assert_completed_task_releases_original_bytes(
    application: QCoreApplication,
) -> None:
    state = harness(decision=None)
    state.controller.configure(enabled(), camera_available=True)
    state.controller.submit_frame(FRAME, 3, 2)
    task = run_task(state, application)
    assert FRAME not in _object_values(state.controller)
    assert FRAME not in _object_values(task)


def _object_values(value: object) -> tuple[object, ...]:
    try:
        return tuple(vars(value).values())
    except TypeError:
        return ()


def run() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    assert application is not None
    assert_disabled_and_missing_models_fail_closed(application)
    assert_visual_perception_samples_hands_without_enabling_actions(application)
    assert_busy_drops_frames_and_worker_is_deferred(application)
    assert_only_current_generation_dispatches_and_each_frame_has_one_action(application)
    assert_cancel_stop_and_three_failures_disable(application)
    assert_completed_task_releases_original_bytes(application)
    print("GESTURE_CONTROLLER_OK")


if __name__ == "__main__":
    run()
