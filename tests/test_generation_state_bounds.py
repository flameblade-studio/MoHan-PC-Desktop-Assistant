from __future__ import annotations

lazy import sys
lazy import threading
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.adaptive_character_runtime import (
    AdaptiveCharacterDisposition,
    AdaptiveCharacterRuntime,
)
lazy from application.full_body_performance_bridge import (
    FullBodyBridgeDisposition,
    FullBodyPerformanceBridge,
)
lazy from domain.pose_runtime_loader import PoseRuntimeLoader
lazy from application.visual_context_fusion import FusionDisposition, VisualContextFusion

ITERATIONS = 20_000


def test_visual_fusion_cancel_state_is_scalar_and_old_work_stays_stale() -> None:
    runtime = VisualContextFusion()
    first = runtime.begin_operation()
    runtime.cancel(first)
    assert runtime._operation_state(first) is FusionDisposition.CANCELLED

    for _ in range(ITERATIONS):
        previous = runtime.begin_operation()
        runtime.cancel(previous)
        assert runtime._operation_state(previous) is FusionDisposition.CANCELLED

    current = runtime.begin_operation()
    assert runtime._operation_state(first) is FusionDisposition.STALE
    assert runtime._operation_state(current) is None
    assert runtime._cancelled_generation is None
    assert not any(isinstance(value, (set, list, dict)) for value in vars(runtime).values())


def test_full_body_cancel_state_is_scalar_and_future_cancel_is_ignored() -> None:
    runtime = FullBodyPerformanceBridge(object())  # type: ignore[arg-type]
    first = runtime.begin_operation()
    runtime.cancel(first)
    assert runtime._operation_state(first) is FullBodyBridgeDisposition.CANCELLED

    for _ in range(ITERATIONS):
        generation = runtime.begin_operation()
        runtime.cancel(generation)

    current = runtime.begin_operation()
    runtime.cancel(current + 1)
    assert runtime._operation_state(first) is FullBodyBridgeDisposition.STALE
    assert runtime._operation_state(current) is None
    assert runtime._cancelled_generation is None


def test_adaptive_cancel_state_is_scalar_and_propagates_only_current() -> None:
    full_body = _FullBodyPort()
    runtime = AdaptiveCharacterRuntime(object(), full_body)  # type: ignore[arg-type]
    first = runtime.begin_operation()
    runtime.cancel(first)
    assert runtime._operation_state(first) is AdaptiveCharacterDisposition.CANCELLED

    for _ in range(ITERATIONS):
        generation = runtime.begin_operation()
        runtime.cancel(generation)

    current = runtime.begin_operation()
    propagated_before = len(full_body.cancelled)
    runtime.cancel(current + 1)
    assert len(full_body.cancelled) == propagated_before
    assert runtime._operation_state(first) is AdaptiveCharacterDisposition.STALE
    assert runtime._operation_state(current) is None
    assert runtime._cancelled_generation is None
    assert full_body.cancelled[-1] == current - 1


def test_pose_loader_cancel_state_is_scalar_and_thread_safe() -> None:
    runtime = PoseRuntimeLoader.__new__(PoseRuntimeLoader)
    runtime._lock = threading.Lock()
    runtime._generation = 0
    runtime._cancelled_generation = None

    first = runtime.begin_load()
    runtime.cancel(first)
    assert runtime._generation_state(first) == "cancelled"

    for _ in range(ITERATIONS):
        generation = runtime.begin_load()
        runtime.cancel(generation)

    current = runtime.begin_load()
    runtime.cancel(current + 1)
    assert runtime._generation_state(first) == "stale"
    assert runtime._generation_state(current) is None
    assert runtime._cancelled_generation is None


class _FullBodyPort:
    def __init__(self) -> None:
        self.generation = 0
        self.cancelled: list[int] = []

    @property
    def last_known_good(self) -> None:
        return None

    def begin_operation(self) -> int:
        self.generation += 1
        return self.generation

    def cancel(self, operation_generation: int) -> None:
        self.cancelled.append(operation_generation)

    def dispatch(self, _request: object) -> None:
        return None


def run() -> None:
    test_visual_fusion_cancel_state_is_scalar_and_old_work_stays_stale()
    test_full_body_cancel_state_is_scalar_and_future_cancel_is_ignored()
    test_adaptive_cancel_state_is_scalar_and_propagates_only_current()
    test_pose_loader_cancel_state_is_scalar_and_thread_safe()
    print("GENERATION_STATE_BOUNDS_OK")


if __name__ == "__main__":
    run()
