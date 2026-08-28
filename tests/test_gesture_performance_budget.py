from __future__ import annotations

lazy import gc
lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication
lazy from PySide6.QtGui import QColor, QImage

lazy from application.camera_presence import CameraPresenceController
lazy from domain.gesture_configuration import GestureConfiguration
lazy from application.gesture_controller import GestureController
lazy from domain.gesture_intent import LipRegion, NormalizedPoint
lazy from application.gesture_runtime import GestureRuntime
lazy from infrastructure.hand_landmark_provider import (
    Handedness,
    HandLandmark,
    HandLandmarkResult,
    HandLandmarkStatus,
    HandObservation,
    MirrorMode,
)

PRIVATE_FRAME = b"performance-contract-private-frame"
MIN_GESTURE_SAMPLE_COUNT = 10
MAX_GESTURE_SAMPLE_COUNT = 11
VISION_SAMPLE_COUNT = 2
MIN_GESTURE_INTERVAL = 0.099
MIN_VISION_INTERVAL = 0.999
MAX_RUNTIME_STATE_ENTRIES = 2


class _Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_camera_sampling_has_independent_one_and_ten_hertz_budgets() -> None:
    clock = _Clock(100.0)
    controller = CameraPresenceController(clock=clock)
    controller._active = True
    controller.configure_gesture_sampling(True)
    image = QImage(4, 2, QImage.Format_RGB888)
    image.fill(QColor("#778899"))
    gesture_times: list[float] = []
    vision_times: list[float] = []
    controller.gesture_frame_ready.connect(
        lambda _frame, _width, _height: gesture_times.append(clock.now)
    )
    controller.vision_frame_ready.connect(
        lambda _frame, _width, _height: vision_times.append(clock.now)
    )

    for index in range(101):
        clock.now = 100.0 + index / 100.0
        controller._emit_due_rgb_frames(image, clock.now)

    assert MIN_GESTURE_SAMPLE_COUNT <= len(gesture_times) <= MAX_GESTURE_SAMPLE_COUNT
    assert len(vision_times) == VISION_SAMPLE_COUNT
    assert all(
        later - earlier >= MIN_GESTURE_INTERVAL
        for earlier, later in pairwise(gesture_times)
    )
    assert vision_times[1] - vision_times[0] >= MIN_VISION_INTERVAL


def test_controller_allows_one_inference_and_drops_busy_frames() -> None:
    state = _controller_harness()
    state.controller.submit_frame(PRIVATE_FRAME, 1, 1)
    for _ in range(100):
        state.controller.submit_frame(b"drop-while-busy", 1, 1)

    assert len(state.pool.tasks) == 1
    assert state.provider.calls == 0
    state.pool.run()
    QCoreApplication.processEvents()
    assert state.provider.calls == 1
    state.close()


def test_completed_inference_releases_raw_frame_reference() -> None:
    state = _controller_harness()
    state.controller.submit_frame(PRIVATE_FRAME, 1, 1)
    task = state.pool.run()
    QCoreApplication.processEvents()
    gc.collect()

    assert not _contains_identity(state.controller, PRIVATE_FRAME)
    assert not _contains_identity(task, PRIVATE_FRAME)
    assert not _contains_identity(state.provider, PRIVATE_FRAME)
    assert not _contains_identity(state.runtime, PRIVATE_FRAME)
    state.close()


def test_runtime_state_remains_bounded_during_many_skeleton_updates() -> None:
    runtime = GestureRuntime()
    configuration = GestureConfiguration(enabled=True)
    hand = _open_palm()
    initial_shape = _runtime_state_shape(runtime)

    for index in range(5_000):
        runtime.update(200.0 + index * 0.02, (hand,), configuration)

    final_shape = _runtime_state_shape(runtime)
    assert initial_shape[0] == final_shape[0]
    assert final_shape[1] <= MAX_RUNTIME_STATE_ENTRIES
    assert final_shape[2] <= MAX_RUNTIME_STATE_ENTRIES
    assert final_shape[3] <= len(configuration.definitions)


def test_silence_fusion_retains_only_short_lived_geometry() -> None:
    state = _controller_harness()
    lips = LipRegion(NormalizedPoint(0.5, 0.5), 0.12, 0.08)
    state.controller.set_lip_region(lips, state.clock.now)

    assert state.controller._latest_lip_region == LipRegion(
        NormalizedPoint(0.5, 0.5),
        0.12,
        0.08,
    )
    assert not _contains_bytes(state.controller._latest_lip_region)
    assert not _contains_identity(state.controller, PRIVATE_FRAME)

    state.clock.now += 1.501
    assert state.controller._current_lip_region(state.clock.now) is None
    assert state.controller._latest_lip_region is None
    state.close()


def _open_palm() -> HandObservation:
    points = [HandLandmark(0.50, 0.82, 0.0) for _ in range(21)]
    for base, pip, tip, x in (
        (5, 6, 8, 0.34),
        (9, 10, 12, 0.45),
        (13, 14, 16, 0.56),
        (17, 18, 20, 0.66),
    ):
        points[base] = HandLandmark(x, 0.68, 0.0)
        points[pip] = HandLandmark(x, 0.53, 0.0)
        points[tip] = HandLandmark(x, 0.30, 0.0)
    points[2] = HandLandmark(0.42, 0.70, 0.0)
    points[4] = HandLandmark(0.24, 0.56, 0.0)
    return HandObservation(Handedness.RIGHT, 0.98, tuple(points))


def _runtime_state_shape(runtime: GestureRuntime) -> tuple[int, int, int, int]:
    recognizer = runtime._recognizer
    router = runtime._router
    wave_items = 0
    candidates = 0
    routed_items = 0
    if recognizer is not None:
        wave_items = sum(len(history) for history in recognizer._wave.values())
        candidates = sum(value is not None for value in recognizer._candidate.values())
    if router is not None:
        routed_items = len(router._last_triggered_at)
    return len(vars(runtime)), wave_items, candidates, routed_items


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
        *,
        mirror: MirrorMode,
    ) -> HandLandmarkResult:
        assert rgb_bytes and width > 0 and height > 0
        assert isinstance(mirror, MirrorMode)
        self.calls += 1
        return HandLandmarkResult(HandLandmarkStatus.OK, self.calls)

    def cancel(self) -> None:
        return None


class _Dispatcher:
    def dispatch(self, _decision: object) -> object:
        return object()


class _DeferredPool:
    def __init__(self) -> None:
        self.tasks: list[object] = []

    def start(self, task: object) -> None:
        self.tasks.append(task)

    def clear(self) -> None:
        self.tasks.clear()

    def waitForDone(self, _milliseconds: int) -> bool:
        return True

    def run(self) -> object:
        task = self.tasks.pop(0)
        task.run()  # type: ignore[attr-defined]
        return task


@dataclass(slots=True)
class _Harness:
    controller: GestureController
    provider: _Provider
    runtime: GestureRuntime
    pool: _DeferredPool
    clock: _Clock
    temporary: TemporaryDirectory[str]

    def close(self) -> None:
        self.controller.close()
        self.temporary.cleanup()


def _controller_harness() -> _Harness:
    QCoreApplication.instance() or QCoreApplication([])
    provider = _Provider()
    runtime = GestureRuntime()
    pool = _DeferredPool()
    clock = _Clock(300.0)
    temporary = TemporaryDirectory()
    controller = GestureController(
        _Dispatcher(),
        model_directory=Path(temporary.name),
        provider_factory=lambda: provider,
        runtime=runtime,
        clock=clock,
    )
    controller._pool = pool  # type: ignore[assignment]
    controller.configure(GestureConfiguration(enabled=True), camera_available=True)
    return _Harness(controller, provider, runtime, pool, clock, temporary)


def _contains_identity(owner: object, target: object) -> bool:
    try:
        return any(value is target for value in vars(owner).values())
    except TypeError:
        return False


def _contains_bytes(owner: object) -> bool:
    try:
        return any(isinstance(value, (bytes, bytearray, memoryview)) for value in vars(owner).values())
    except TypeError:
        return False


def run() -> None:
    test_camera_sampling_has_independent_one_and_ten_hertz_budgets()
    test_controller_allows_one_inference_and_drops_busy_frames()
    test_completed_inference_releases_raw_frame_reference()
    test_runtime_state_remains_bounded_during_many_skeleton_updates()
    test_silence_fusion_retains_only_short_lived_geometry()
    print("GESTURE_PERFORMANCE_BUDGET_OK")


if __name__ == "__main__":
    run()
