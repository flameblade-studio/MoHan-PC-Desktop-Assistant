from __future__ import annotations

lazy import math
lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum
lazy from pathlib import Path
lazy from typing import NotRequired, Protocol, TypedDict, Unpack

lazy from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

lazy from application.gesture_action_dispatcher import (
    GestureDispatchDisposition,
    GestureDispatchResult,
)
lazy from application.gesture_runtime import GestureRuntime
lazy from application.vision_runtime import bundled_model_directory
lazy from domain.air_interaction import AirHandPoint, AirHandSample, HandSide
lazy from domain.gesture_configuration import (
    GestureConfiguration,
    GestureLandmark,
    GestureSample,
)
lazy from domain.gesture_intent import LipRegion, NormalizedPoint
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkProvider,
    HandLandmarkResult,
    HandLandmarkStatus,
    HandModelPaths,
    MirrorMode,
)

PALM_MODEL_FILENAME = "palm_detection_mediapipe_2023feb.onnx"
HAND_MODEL_FILENAME = "handpose_estimation_mediapipe_2023feb.onnx"
_FAILURE_LIMIT = 3
_LIP_REGION_MAXIMUM_AGE_SECONDS = 1.5
_TASK_BOUNDARY_ERRORS = (Exception,)


class GestureControllerStatus(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    CAMERA_UNAVAILABLE = "camera-unavailable"
    MODEL_MISSING = "model-missing"
    MODEL_LOAD_FAILED = "model-load-failed"
    INFERENCE_FAILED = "inference-failed"


@dataclass(frozen=True, slots=True)
class GestureControllerHealth:
    status: GestureControllerStatus
    detail_code: str = ""

    @property
    def ready(self) -> bool:
        return self.status is GestureControllerStatus.READY


class GestureDispatchPort(Protocol):
    def dispatch(self, decision: object) -> GestureDispatchResult: ...


class _GestureControllerDependencies(TypedDict):
    provider_factory: NotRequired[Callable[[], HandLandmarkProvider] | None]
    runtime: NotRequired[GestureRuntime | None]
    clock: NotRequired[Callable[[], float]]


@dataclass(frozen=True, slots=True)
class _HandAnalysisOutcome:
    provider: HandLandmarkProvider
    result: HandLandmarkResult


@dataclass(frozen=True, slots=True)
class _HandAnalysisRequest:
    rgb_bytes: bytes
    width: int
    height: int
    generation: int
    mirror: MirrorMode


class _HandAnalysisSignals(QObject):
    completed = Signal(object, int)
    failed = Signal(str, int)


class _HandAnalysisTask(QRunnable):
    """Own one transient frame and erase its reference after inference."""

    def __init__(
        self,
        provider: HandLandmarkProvider | None,
        provider_factory: Callable[[], HandLandmarkProvider],
        request: _HandAnalysisRequest,
    ) -> None:
        super().__init__()
        self.signals = _HandAnalysisSignals()
        self._provider = provider
        self._provider_factory = provider_factory
        self._request = request

    def run(self) -> None:
        try:
            provider = self._provider or self._provider_factory()
            result = provider.analyze(
                self._request.rgb_bytes,
                self._request.width,
                self._request.height,
                mirror=self._request.mirror,
            )
            self.signals.completed.emit(
                _HandAnalysisOutcome(provider, result),
                self._request.generation,
            )
        except _TASK_BOUNDARY_ERRORS as exc:
            self.signals.failed.emit(
                type(exc).__name__,
                self._request.generation,
            )
        finally:
            self._request = _HandAnalysisRequest(
                b"",
                0,
                0,
                self._request.generation,
                self._request.mirror,
            )
            self._provider = None


class GestureController(QObject):
    """Run optional hand inference off-thread and dispatch audited decisions."""

    health_changed = Signal(object)
    recognition_changed = Signal(object)
    dispatch_completed = Signal(object)
    hand_samples_changed = Signal(object, float)

    def __init__(
        self,
        dispatcher: GestureDispatchPort,
        *,
        model_directory: Path | None = None,
        mirror: MirrorMode = MirrorMode.SELFIE,
        **dependencies: Unpack[_GestureControllerDependencies],
    ) -> None:
        super().__init__()
        if not callable(getattr(dispatcher, "dispatch", None)):
            raise TypeError("Gesture controller dispatcher must be available.")
        if not isinstance(mirror, MirrorMode):
            raise TypeError("Gesture controller mirror mode must be canonical.")
        root = model_directory or bundled_model_directory()
        self._models = HandModelPaths(
            root / PALM_MODEL_FILENAME,
            root / HAND_MODEL_FILENAME,
        )
        provider_factory = dependencies.get("provider_factory")
        runtime = dependencies.get("runtime")
        self._provider_factory_injected = provider_factory is not None
        self._provider_factory = provider_factory or (
            lambda: HandLandmarkProvider(self._models)
        )
        self._dispatcher = dispatcher
        self._runtime = runtime or GestureRuntime()
        self._clock = dependencies.get("clock", time.monotonic)
        self._mirror = mirror
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._provider: HandLandmarkProvider | None = None
        self._configuration = GestureConfiguration()
        self._enabled = False
        self._perception_enabled = False
        self._busy = False
        self._generation = 0
        self._consecutive_failures = 0
        self._latest_hand = None
        self._latest_hand_observed_at = float("-inf")
        self._latest_lip_region: LipRegion | None = None
        self._latest_lip_observed_at = float("-inf")
        self._health = GestureControllerHealth(GestureControllerStatus.DISABLED)

    @property
    def health(self) -> GestureControllerHealth:
        return self._health

    @property
    def sampling_enabled(self) -> bool:
        return self._enabled and self._health.ready

    @property
    def _effective_configuration(self) -> GestureConfiguration:
        """Configuration the runtime should observe.

        The gesture store persists hand-gesture *bindings* while camera
        perception is a UI-level preference. When the camera is enabled the
        controller becomes READY through ``perception_enabled`` even if the
        persisted binding set is disabled, so the runtime must treat the
        configuration as enabled in that case or every recognition is dropped.
        """
        if self._perception_enabled and not self._configuration.enabled:
            return replace(self._configuration, enabled=True)
        return self._configuration

    def configure(
        self,
        configuration: GestureConfiguration,
        *,
        camera_available: bool,
        perception_enabled: bool = False,
    ) -> GestureControllerHealth:
        if not isinstance(configuration, GestureConfiguration):
            raise TypeError("Gesture controller configuration must be canonical.")
        if type(camera_available) is not bool:
            raise TypeError("Gesture camera availability must be boolean.")
        if type(perception_enabled) is not bool:
            raise TypeError("Hand perception state must be boolean.")
        self._cancel_pending()
        self._configuration = configuration
        self._perception_enabled = perception_enabled
        if not configuration.enabled and not perception_enabled:
            return self._set_health(GestureControllerStatus.DISABLED)
        if not camera_available:
            return self._set_health(GestureControllerStatus.CAMERA_UNAVAILABLE)
        if self._models.missing and not self._provider_factory_injected:
            return self._set_health(GestureControllerStatus.MODEL_MISSING)
        self._enabled = True
        return self._set_health(GestureControllerStatus.READY)

    def submit_frame(self, rgb_bytes: bytes, width: int, height: int) -> None:
        if not self.sampling_enabled or self._busy:
            return
        if not isinstance(rgb_bytes, bytes):
            return
        self._busy = True
        generation = self._generation
        task = _HandAnalysisTask(
            self._provider,
            self._provider_factory,
            _HandAnalysisRequest(
                rgb_bytes,
                width,
                height,
                generation,
                self._mirror,
            ),
        )
        task.signals.completed.connect(self._analysis_completed)
        task.signals.failed.connect(self._analysis_failed)
        self._pool.start(task)

    def set_lip_region(
        self,
        lips: LipRegion | None,
        observed_at: float,
    ) -> None:
        """Accept transient face evidence without retaining a source frame."""

        if not math.isfinite(observed_at):
            self._clear_lip_region()
            return
        if lips is not None and not isinstance(lips, LipRegion):
            self._clear_lip_region()
            return
        self._latest_lip_region = self._canonical_lip_region(lips)
        self._latest_lip_observed_at = (
            observed_at if lips is not None else float("-inf")
        )

    def available(self) -> bool:
        """Expose whether custom recording can use a recent local hand sample."""

        return self.sampling_enabled

    def record(self, gesture_id: str) -> GestureSample | None:
        """Implement the UI recorder boundary from the latest transient hand."""

        if not isinstance(gesture_id, str) or not gesture_id.startswith("custom:"):
            raise ValueError("Custom gesture recording requires a custom identifier.")
        return self.capture_sample()

    def capture_sample(
        self,
        *,
        maximum_age_seconds: float = 1.0,
    ) -> GestureSample | None:
        """Return one recent skeleton without retaining pixels or blocking the UI."""

        if maximum_age_seconds <= 0.0:
            raise ValueError("Gesture sample age must be positive.")
        hand = self._latest_hand
        age = float(self._clock()) - self._latest_hand_observed_at
        if not self.sampling_enabled or hand is None or not 0.0 <= age <= maximum_age_seconds:
            self._latest_hand = None
            return None
        return GestureSample(
            tuple(
                GestureLandmark(point.x, point.y, point.z)
                for point in hand.landmarks
            )
        )

    def stop(self) -> None:
        self._reset_pending()
        self._configuration = GestureConfiguration()
        self._perception_enabled = False
        self._set_health(GestureControllerStatus.DISABLED)

    def cancel(self) -> None:
        """Cancel pending inference while preserving the configured state."""

        self._generation += 1
        self._busy = False
        self._pool.clear()
        self._runtime.cancel()
        self._latest_hand = None
        self._latest_hand_observed_at = float("-inf")
        self._clear_lip_region()
        if self._provider is not None:
            self._provider.cancel()

    def close(self) -> None:
        self.stop()
        self._pool.waitForDone(1500)

    def _cancel_pending(self) -> None:
        self._reset_pending()

    def _reset_pending(self) -> None:
        self.cancel()
        self._enabled = False
        self._perception_enabled = False
        self._consecutive_failures = 0
        self._runtime.reset()

    def _analysis_completed(
        self,
        outcome: _HandAnalysisOutcome,
        generation: int,
    ) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        if not isinstance(outcome, _HandAnalysisOutcome):
            self._record_failure("invalid-outcome")
            return
        self._provider = outcome.provider
        result = outcome.result
        if result.status is not HandLandmarkStatus.OK:
            self._handle_provider_status(result.status)
            return
        self._remember_best_hand(result)
        observed_at = float(self._clock())
        hand_samples = tuple(
            AirHandSample(
                HandSide.LEFT
                if hand.handedness.value == "left"
                else HandSide.RIGHT,
                hand.confidence,
                tuple(
                    AirHandPoint(point.x, point.y, point.z)
                    for point in hand.landmarks
                ),
            )
            for hand in result.hands
            if hand.handedness.value in {"left", "right"}
        )
        self.hand_samples_changed.emit(hand_samples, observed_at)
        lips = self._current_lip_region(observed_at)
        configuration = self._effective_configuration
        try:
            if lips is None:
                runtime_result = self._runtime.update(
                    observed_at,
                    result.hands,
                    configuration,
                )
            else:
                runtime_result = self._runtime.update(
                    observed_at,
                    result.hands,
                    configuration,
                    lips=lips,
                )
        except _TASK_BOUNDARY_ERRORS:
            self._record_failure("runtime-invalid")
            return
        self._consecutive_failures = 0
        self.recognition_changed.emit(runtime_result)
        if runtime_result.decision is None:
            return
        try:
            dispatch = self._dispatcher.dispatch(runtime_result.decision)
        except _TASK_BOUNDARY_ERRORS:
            dispatch = GestureDispatchResult(
                GestureDispatchDisposition.FAILED,
                runtime_result.decision.action,
                "dispatch-boundary-failed",
            )
        self.dispatch_completed.emit(dispatch)

    def _remember_best_hand(self, result: HandLandmarkResult) -> None:
        self._latest_hand = max(
            result.hands,
            key=lambda hand: hand.confidence,
            default=None,
        )
        self._latest_hand_observed_at = (
            float(self._clock()) if self._latest_hand is not None else float("-inf")
        )

    def _current_lip_region(self, observed_at: float) -> LipRegion | None:
        age = observed_at - self._latest_lip_observed_at
        if not 0.0 <= age <= _LIP_REGION_MAXIMUM_AGE_SECONDS:
            self._clear_lip_region()
            return None
        return self._latest_lip_region

    def _canonical_lip_region(self, lips: LipRegion | None) -> LipRegion | None:
        if lips is None or self._mirror is MirrorMode.NATIVE:
            return lips
        return LipRegion(
            NormalizedPoint(1.0 - lips.center.x, lips.center.y),
            lips.width,
            lips.height,
        )

    def _clear_lip_region(self) -> None:
        self._latest_lip_region = None
        self._latest_lip_observed_at = float("-inf")

    def _analysis_failed(self, error_name: str, generation: int) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        self._record_failure(error_name)

    def _handle_provider_status(self, status: HandLandmarkStatus) -> None:
        if status in {HandLandmarkStatus.CANCELLED, HandLandmarkStatus.STALE}:
            return
        if status is HandLandmarkStatus.MODEL_MISSING:
            self._disable_with(GestureControllerStatus.MODEL_MISSING, status.value)
            return
        if status is HandLandmarkStatus.MODEL_LOAD_FAILED:
            self._disable_with(
                GestureControllerStatus.MODEL_LOAD_FAILED,
                status.value,
            )
            return
        self._record_failure(status.value)

    def _record_failure(self, detail_code: str) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures < _FAILURE_LIMIT:
            return
        self._disable_with(
            GestureControllerStatus.INFERENCE_FAILED,
            detail_code,
        )

    def _disable_with(
        self,
        status: GestureControllerStatus,
        detail_code: str,
    ) -> None:
        self._enabled = False
        self._busy = False
        self._runtime.reset()
        if self._provider is not None:
            self._provider.cancel()
        self._set_health(status, detail_code)

    def _set_health(
        self,
        status: GestureControllerStatus,
        detail_code: str = "",
    ) -> GestureControllerHealth:
        self._health = GestureControllerHealth(status, detail_code)
        self.health_changed.emit(self._health)
        return self._health

    def _is_current(self, generation: int) -> bool:
        return (
            self._enabled
            and generation == self._generation
            and self._health.ready
        )
