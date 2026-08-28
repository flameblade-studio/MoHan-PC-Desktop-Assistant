from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication

lazy from domain.gesture_configuration import GestureAction, GestureConfiguration
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

PRIVATE_FRAME = b"transient-private-rgb"


def _silence_hand(
    *,
    side: Handedness = Handedness.RIGHT,
    tip_x: float = 0.50,
) -> HandObservation:
    points = [HandLandmark(0.50, 0.76, 0.0) for _ in range(21)]
    points[0] = HandLandmark(0.50, 0.82, 0.0)
    points[5] = HandLandmark(tip_x, 0.68, 0.0)
    points[6] = HandLandmark(tip_x, 0.62, 0.0)
    points[8] = HandLandmark(tip_x, 0.50, 0.0)
    for base, pip, tip, x in (
        (9, 10, 12, 0.46),
        (13, 14, 16, 0.54),
        (17, 18, 20, 0.60),
    ):
        points[base] = HandLandmark(x, 0.72, 0.0)
        points[pip] = HandLandmark(x, 0.74, 0.0)
        points[tip] = HandLandmark(0.50, 0.76, 0.0)
    return HandObservation(side, 0.98, tuple(points))


def _open_palm(*, side: Handedness = Handedness.LEFT) -> HandObservation:
    points = [HandLandmark(0.28, 0.82, 0.0) for _ in range(21)]
    points[0] = HandLandmark(0.28, 0.84, 0.0)
    for base, pip, tip, x in (
        (5, 6, 8, 0.16),
        (9, 10, 12, 0.24),
        (13, 14, 16, 0.32),
        (17, 18, 20, 0.40),
    ):
        points[base] = HandLandmark(x, 0.68, 0.0)
        points[pip] = HandLandmark(x, 0.54, 0.0)
        points[tip] = HandLandmark(x, 0.30, 0.0)
    points[2] = HandLandmark(0.20, 0.70, 0.0)
    points[4] = HandLandmark(0.08, 0.56, 0.0)
    return HandObservation(side, 0.96, tuple(points))


def _lips(x: float = 0.50) -> LipRegion:
    return LipRegion(NormalizedPoint(x, 0.50), 0.12, 0.08)


def _enabled() -> GestureConfiguration:
    return GestureConfiguration(enabled=True)


def test_silence_requires_three_frames_and_point_two_seconds() -> None:
    runtime = GestureRuntime()
    hand = _silence_hand()
    results = tuple(
        runtime.update(moment, (hand,), _enabled(), lips=_lips())
        for moment in (10.0, 10.10, 10.201)
    )

    assert results[0].decision is None
    assert results[1].decision is None
    assert results[2].decision is not None
    assert results[2].decision.gesture_id == "silence"
    assert results[2].decision.action is GestureAction.MUTE_AUDIO


def test_silence_candidate_suppresses_general_gesture_recognition() -> None:
    runtime = GestureRuntime()
    hands = (_silence_hand(), _open_palm())

    first = runtime.update(20.0, hands, _enabled(), lips=_lips())
    second = runtime.update(20.10, hands, _enabled(), lips=_lips())
    triggered = runtime.update(20.201, hands, _enabled(), lips=_lips())

    assert first.recognitions == () and first.decision is None
    assert second.recognitions == () and second.decision is None
    assert triggered.recognitions == ()
    assert triggered.decision is not None
    assert triggered.decision.action is GestureAction.MUTE_AUDIO


def test_missing_lips_wrong_hand_and_stale_lips_do_not_trigger() -> None:
    configuration = _enabled()
    hand = _silence_hand()

    without_lips = GestureRuntime()
    no_lip_results = tuple(
        without_lips.update(moment, (hand,), configuration)
        for moment in (30.0, 30.10, 30.201)
    )
    assert all(
        result.decision is None
        or result.decision.action is not GestureAction.MUTE_AUDIO
        for result in no_lip_results
    )

    wrong_hand = _silence_hand(tip_x=0.88)
    mismatched = GestureRuntime()
    wrong_results = tuple(
        mismatched.update(moment, (wrong_hand,), configuration, lips=_lips())
        for moment in (31.0, 31.10, 31.201)
    )
    assert all(
        result.decision is None
        or result.decision.action is not GestureAction.MUTE_AUDIO
        for result in wrong_results
    )

    application = QCoreApplication.instance() or QCoreApplication([])
    clock = _Clock(40.0)
    state = _controller_harness(clock, (_silence_hand(),))
    state.controller.set_lip_region(_lips(), clock.now)
    clock.now = 41.51
    _run_three_frames(state, application, (41.51, 41.61, 41.71))
    assert not any(
        decision.action is GestureAction.MUTE_AUDIO
        for decision in state.dispatcher.decisions
    )
    state.close()


def test_selfie_mirror_keeps_lips_and_hand_in_one_coordinate_space() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    clock = _Clock(50.0)
    mirrored_hand = _silence_hand(tip_x=0.80)
    state = _controller_harness(clock, (mirrored_hand,), mirror=MirrorMode.SELFIE)
    state.controller.set_lip_region(_lips(0.20), clock.now)

    _run_three_frames(state, application, (50.0, 50.10, 50.201))

    assert len(state.dispatcher.decisions) == 1
    assert state.dispatcher.decisions[0].action is GestureAction.MUTE_AUDIO
    state.close()


def test_silence_cooldown_does_not_dispatch_twice() -> None:
    runtime = GestureRuntime()
    hand = _silence_hand()
    decisions = []
    for moment in (60.0, 60.10, 60.201, 60.30, 60.50, 61.0, 62.19):
        result = runtime.update(moment, (hand,), _enabled(), lips=_lips())
        if result.decision is not None:
            decisions.append(result.decision)

    assert [decision.action for decision in decisions] == [GestureAction.MUTE_AUDIO]


def test_controller_releases_source_frame_after_fusion() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    clock = _Clock(70.0)
    state = _controller_harness(clock, (_silence_hand(),))
    state.controller.set_lip_region(_lips(), clock.now)
    state.controller.submit_frame(PRIVATE_FRAME, 1, 1)
    task = state.pool.run()
    application.processEvents()

    assert PRIVATE_FRAME not in _object_values(state.controller)
    assert PRIVATE_FRAME not in _object_values(task)
    assert PRIVATE_FRAME not in _object_values(state.provider)
    assert PRIVATE_FRAME not in _object_values(state.runtime)
    state.close()


class _Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class _Provider:
    def __init__(self, hands: tuple[HandObservation, ...]) -> None:
        self._hands = hands
        self.frame_sizes: list[int] = []

    def analyze(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
        *,
        mirror: MirrorMode,
    ) -> HandLandmarkResult:
        assert isinstance(mirror, MirrorMode)
        assert width > 0 and height > 0
        self.frame_sizes.append(len(rgb_bytes))
        return HandLandmarkResult(HandLandmarkStatus.OK, len(self.frame_sizes), self._hands)

    def cancel(self) -> None:
        return None


class _Dispatcher:
    def __init__(self) -> None:
        self.decisions: list[object] = []

    def dispatch(self, decision: object) -> object:
        self.decisions.append(decision)
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
class _ControllerHarness:
    controller: GestureController
    provider: _Provider
    runtime: GestureRuntime
    dispatcher: _Dispatcher
    pool: _DeferredPool
    _temporary: TemporaryDirectory[str]

    def close(self) -> None:
        self.controller.close()
        self._temporary.cleanup()


def _controller_harness(
    clock: _Clock,
    hands: tuple[HandObservation, ...],
    *,
    mirror: MirrorMode = MirrorMode.SELFIE,
) -> _ControllerHarness:
    provider = _Provider(hands)
    runtime = GestureRuntime()
    dispatcher = _Dispatcher()
    pool = _DeferredPool()
    temporary = TemporaryDirectory()
    controller = GestureController(
        dispatcher,
        model_directory=Path(temporary.name),
        provider_factory=lambda: provider,
        runtime=runtime,
        clock=clock,
        mirror=mirror,
    )
    controller._pool = pool  # type: ignore[assignment]
    controller.configure(_enabled(), camera_available=True)
    return _ControllerHarness(
        controller,
        provider,
        runtime,
        dispatcher,
        pool,
        temporary,
    )


def _run_three_frames(
    state: _ControllerHarness,
    application: QCoreApplication,
    times: tuple[float, float, float],
) -> None:
    for moment in times:
        state.controller._clock.now = moment  # type: ignore[attr-defined]
        state.controller.submit_frame(b"rgb", 1, 1)
        state.pool.run()
        application.processEvents()


def _object_values(value: object) -> tuple[object, ...]:
    try:
        return tuple(vars(value).values())
    except TypeError:
        return ()


def run() -> None:
    test_silence_requires_three_frames_and_point_two_seconds()
    test_silence_candidate_suppresses_general_gesture_recognition()
    test_missing_lips_wrong_hand_and_stale_lips_do_not_trigger()
    test_selfie_mirror_keeps_lips_and_hand_in_one_coordinate_space()
    test_silence_cooldown_does_not_dispatch_twice()
    test_controller_releases_source_frame_after_fusion()
    print("GESTURE_SILENCE_FUSION_OK")


if __name__ == "__main__":
    run()
