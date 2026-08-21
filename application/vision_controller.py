from __future__ import annotations

lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol

lazy from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

lazy from application.local_visual_intelligence import (
    LocalFrameAnalysis,
    LocalVisualIntelligencePipeline,
)
lazy from application.multimodal_fusion_hub import FaceMeshFrame
lazy from application.vision_runtime import (
    VisionEnvironmentProbe,
    VisionHealth,
    VisionReadiness,
    bundled_model_directory,
)
lazy from domain.vision_domain import SceneUnderstanding
lazy from infrastructure.face_identity_store import FaceIdentityStore
lazy from infrastructure.opencv_vision import (
    OpenCVFrameEvidence,
    OpenCVVisionProvider,
    VisionModelPaths,
)

MAX_CONSECUTIVE_ANALYSIS_FAILURES = 3

# Providers and protected stores are replaceable external boundaries. They can
# raise implementation-specific Exception subclasses, but process-control
# BaseException subclasses must always propagate.
EXTERNAL_VISION_BOUNDARY_ERRORS = (Exception,)


@dataclass(frozen=True, slots=True)
class _BoundaryResult[ResultT]:
    value: ResultT | None = None
    error_name: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error_name


@dataclass(frozen=True, slots=True)
class _AnalysisBundle:
    evidence: OpenCVFrameEvidence | SceneUnderstanding
    face_mesh: FaceMeshFrame | None = None
    dense_error_name: str = ""


class DenseFaceInference(Protocol):
    frame: FaceMeshFrame


class DenseFaceProvider(Protocol):
    def analyze_face(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
    ) -> DenseFaceInference | None: ...


def _call_external[ResultT](operation: Callable[[], ResultT]) -> _BoundaryResult[ResultT]:
    """Sanitize failures crossing an untrusted provider or protected-store edge."""

    try:
        return _BoundaryResult(value=operation())
    except EXTERNAL_VISION_BOUNDARY_ERRORS as exc:
        return _BoundaryResult(error_name=type(exc).__name__)


class _AnalysisSignals(QObject):
    completed = Signal(object, int)
    failed = Signal(str, int)


class _AnalysisTask(QRunnable):
    def __init__(
        self,
        provider: OpenCVVisionProvider,
        rgb_bytes: bytes,
        width: int,
        height: int,
        generation: int,
        *,
        dense_provider: DenseFaceProvider | None = None,
    ) -> None:
        super().__init__()
        self.signals = _AnalysisSignals()
        self._provider = provider
        self._dense_provider = dense_provider
        self._rgb_bytes = rgb_bytes
        self._width = width
        self._height = height
        self._generation = generation

    def run(self) -> None:
        def analyze() -> OpenCVFrameEvidence | SceneUnderstanding:
            analyze_frame = getattr(self._provider, "analyze_frame", None)
            if callable(analyze_frame):
                return analyze_frame(
                    self._rgb_bytes,
                    self._width,
                    self._height,
                )
            return self._provider.analyze(
                self._rgb_bytes,
                self._width,
                self._height,
            )

        result = _call_external(analyze)
        if not result.succeeded:
            self.signals.failed.emit(result.error_name, self._generation)
            return
        dense_result = (
            _BoundaryResult()
            if self._dense_provider is None
            else _call_external(
                lambda: self._dense_provider.analyze_face(
                    self._rgb_bytes,
                    self._width,
                    self._height,
                )
            )
        )
        face_mesh = (
            dense_result.value.frame
            if dense_result.succeeded and dense_result.value is not None
            else None
        )
        self.signals.completed.emit(
            _AnalysisBundle(
                result.value,
                face_mesh,
                dense_result.error_name,
            ),
            self._generation,
        )


class _EmbeddingTask(QRunnable):
    def __init__(
        self,
        provider: OpenCVVisionProvider,
        rgb_bytes: bytes,
        width: int,
        height: int,
        generation: int,
    ) -> None:
        super().__init__()
        self.signals = _AnalysisSignals()
        self._provider = provider
        self._rgb_bytes = rgb_bytes
        self._width = width
        self._height = height
        self._generation = generation

    def run(self) -> None:
        result = _call_external(
            lambda: self._provider.face_embedding(
                self._rgb_bytes,
                self._width,
                self._height,
            )
        )
        if not result.succeeded:
            self.signals.failed.emit(result.error_name, self._generation)
            return
        self.signals.completed.emit(result.value, self._generation)


class VisionController(QObject):
    """Isolate optional visual inference from every existing MoHan feature."""

    health_changed = Signal(object)
    scene_changed = Signal(object)
    local_intelligence_changed = Signal(object)
    face_mesh_changed = Signal(object, float)
    face_mesh_health_changed = Signal(bool, str)
    lip_region_changed = Signal(object, float)
    enrollment_progress = Signal(int, int)
    enrollment_completed = Signal(str)
    enrollment_failed = Signal(str)

    def __init__(
        self,
        identities: FaceIdentityStore,
        parent: QObject | None = None,
        *,
        model_directory: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
        mirrored_input: bool = False,
        dense_provider_factory: Callable[[], DenseFaceProvider] | None = None,
    ) -> None:
        super().__init__(parent)
        self._identities = identities
        self._model_directory = model_directory or bundled_model_directory()
        self._probe = VisionEnvironmentProbe(self._model_directory)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._provider: OpenCVVisionProvider | None = None
        self._dense_provider: DenseFaceProvider | None = None
        self._dense_provider_factory = dense_provider_factory
        self._dense_provider_unavailable = False
        self._clock = clock
        self._local_pipeline = LocalVisualIntelligencePipeline(
            mirrored_input=mirrored_input
        )
        self._enabled = False
        self._busy = False
        self._enrollment_name = ""
        self._enrollment_samples: list[tuple[float, ...]] = []
        self._required_enrollment_samples = 5
        self._consecutive_analysis_failures = 0
        self._generation = 0

    def configure(self, *, enabled: bool, camera_available: bool) -> VisionHealth:
        self._cancel_pending_work()
        self._dense_provider_unavailable = False
        health = self._probe.inspect(
            enabled=enabled,
            camera_available=camera_available,
        )
        self._enabled = health.ready
        if not health.ready:
            self._provider = None
            self._dense_provider = None
        self.health_changed.emit(health)
        return health

    def submit_frame(self, rgb_bytes: bytes, width: int, height: int) -> None:
        if not self._enabled or self._busy:
            return
        provider_result = _call_external(
            lambda: self._provider or self._create_provider()
        )
        if not provider_result.succeeded or provider_result.value is None:
            self._enabled = False
            self.health_changed.emit(
                VisionHealth(
                    VisionReadiness.RUNTIME_ERROR,
                    provider_result.error_name or "RuntimeError",
                )
            )
            return
        provider = provider_result.value
        self._provider = provider
        dense_provider = self._dense_provider
        if (
            dense_provider is None
            and self._dense_provider_factory is not None
            and not self._dense_provider_unavailable
        ):
            dense_result = _call_external(self._create_dense_provider)
            if dense_result.succeeded:
                dense_provider = dense_result.value
                self._dense_provider = dense_provider
                self.face_mesh_health_changed.emit(True, "")
            else:
                self._dense_provider_unavailable = True
                self.face_mesh_health_changed.emit(
                    False,
                    dense_result.error_name or "RuntimeError",
                )
        self._busy = True
        generation = self._generation
        if self._enrollment_name:
            task = _EmbeddingTask(
                provider,
                rgb_bytes,
                width,
                height,
                generation,
            )
            task.signals.completed.connect(self._embedding_completed)
            task.signals.failed.connect(self._embedding_failed)
            self._pool.start(task)
            return
        task = _AnalysisTask(
            provider,
            rgb_bytes,
            width,
            height,
            generation,
            dense_provider=dense_provider,
        )
        task.signals.completed.connect(self._analysis_completed)
        task.signals.failed.connect(self._analysis_failed)
        self._pool.start(task)

    def begin_enrollment(self, display_name: str) -> None:
        if not self._enabled:
            raise RuntimeError("vision is not ready")
        name = display_name.strip()
        if not name:
            raise ValueError("display name must not be empty")
        self._enrollment_name = name
        self._enrollment_samples.clear()
        self.enrollment_progress.emit(0, self._required_enrollment_samples)

    def cancel_enrollment(self) -> None:
        self._enrollment_name = ""
        self._enrollment_samples.clear()

    def stop(self) -> None:
        self._enabled = False
        self._provider = None
        self._dense_provider = None
        self._cancel_pending_work()

    def close(self) -> None:
        self.stop()
        self._pool.waitForDone(1500)

    def _create_provider(self) -> OpenCVVisionProvider:
        root = self._model_directory
        return OpenCVVisionProvider(
            VisionModelPaths(
                root / "face_detection_yunet_2023mar.onnx",
                root / "face_recognition_sface_2021dec.onnx",
                root / "object_detection_nanodet_2022nov.onnx",
            ),
            self._identities,
        )

    def _create_dense_provider(self) -> DenseFaceProvider:
        if self._dense_provider_factory is None:
            raise RuntimeError("Dense face provider is not configured.")
        return self._dense_provider_factory()

    def _cancel_pending_work(self) -> None:
        self._generation += 1
        self._busy = False
        self._consecutive_analysis_failures = 0
        self._pool.clear()
        self._local_pipeline.reset()
        self.cancel_enrollment()

    def _is_current(self, generation: int) -> bool:
        return self._enabled and generation == self._generation

    def _analysis_completed(
        self,
        evidence: _AnalysisBundle | OpenCVFrameEvidence | SceneUnderstanding,
        generation: int,
    ) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        self._consecutive_analysis_failures = 0
        if isinstance(evidence, _AnalysisBundle):
            if evidence.face_mesh is not None:
                self.face_mesh_changed.emit(evidence.face_mesh, float(self._clock()))
            if evidence.dense_error_name:
                self.face_mesh_health_changed.emit(
                    False,
                    evidence.dense_error_name,
                )
            evidence = evidence.evidence
        if isinstance(evidence, SceneUnderstanding):
            self.scene_changed.emit(evidence)
            return
        if not isinstance(evidence, OpenCVFrameEvidence):
            self._analysis_failed("TypeError", generation)
            return
        observed_at = float(self._clock())
        try:
            result = self._local_pipeline.analyze(
                LocalFrameAnalysis(
                    observed_at=observed_at,
                    scene=evidence.scene,
                    face_box=evidence.face_box,
                    sparse_face_landmarks=evidence.sparse_face_landmarks,
                )
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            self._analysis_failed(type(exc).__name__, generation)
            return
        self.scene_changed.emit(evidence.scene)
        self.lip_region_changed.emit(evidence.lip_region, observed_at)
        self.local_intelligence_changed.emit(result)

    def _analysis_failed(self, error_name: str, generation: int) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        self._consecutive_analysis_failures += 1
        if self._consecutive_analysis_failures < MAX_CONSECUTIVE_ANALYSIS_FAILURES:
            return
        self._enabled = False
        self._provider = None
        self.health_changed.emit(
            VisionHealth(VisionReadiness.RUNTIME_ERROR, error_name)
        )

    def _embedding_completed(self, embedding: object, generation: int) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        if not self._enrollment_name:
            return
        if not isinstance(embedding, tuple) or not embedding:
            self.enrollment_failed.emit("exactly_one_face_required")
            return
        self._enrollment_samples.append(embedding)
        count = len(self._enrollment_samples)
        self.enrollment_progress.emit(count, self._required_enrollment_samples)
        if count < self._required_enrollment_samples:
            return
        name = self._enrollment_name
        enrollment = _call_external(
            lambda: self._identities.enroll(
                name,
                tuple(self._enrollment_samples),
            )
        )
        if not enrollment.succeeded:
            self.cancel_enrollment()
            self.enrollment_failed.emit(enrollment.error_name)
            return
        self.cancel_enrollment()
        self.enrollment_completed.emit(name)

    def _embedding_failed(self, error_name: str, generation: int) -> None:
        if not self._is_current(generation):
            return
        self._busy = False
        self.enrollment_failed.emit(error_name)
