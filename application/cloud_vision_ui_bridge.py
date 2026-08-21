from __future__ import annotations

lazy import hashlib
lazy import json
lazy import math
lazy import threading
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    QRunnable,
    QThreadPool,
    Signal,
)
lazy from PySide6.QtGui import QImage

lazy from application.cloud_vision_runtime import (
    CloudVisionFrame,
    CloudVisionResult,
    CloudVisionRuntime,
    CloudVisionStatus,
    CloudVisionTrigger,
    SavedVisionAuthorization,
)
lazy from domain.cloud_scene_interpreter import (
    CloudSceneInterpretation,
    CloudSceneInterpreter,
    MergedSceneUnderstanding,
    SceneFactKind,
)
lazy from domain.contracts import SecretStorePort
lazy from domain.openai_vision_preferences import PREFERENCES_VERSION, VisionDetail
lazy from domain.vision_domain import SceneUnderstanding
lazy from domain.vision_provider_contracts import (
    VisionProviderResult,
    VisionResultStatus,
)
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
)

MIN_ARGUMENT_PAIR_COUNT = 2


@dataclass(frozen=True, slots=True)
class CloudVisionUIResult:
    status: CloudVisionStatus
    interpretation: CloudSceneInterpretation | None = None


class CloudLocalSceneIntegrator:
    """Merge sanitized cloud evidence into the latest typed local scene."""

    def __init__(self, interpreter: CloudSceneInterpreter | None = None) -> None:
        self._interpreter = interpreter or CloudSceneInterpreter()
        self._local_scene: SceneUnderstanding | None = None
        self._local_observed_at = 0.0
        self._last_operation_id = -1

    def observe_local(
        self,
        scene: SceneUnderstanding,
        *,
        observed_at: float,
    ) -> None:
        if not isinstance(scene, SceneUnderstanding):
            raise TypeError("Local scene must be strongly typed.")
        if not math.isfinite(observed_at) or observed_at < self._local_observed_at:
            raise ValueError("Local scene time must be finite and monotonic.")
        self._local_scene = scene
        self._local_observed_at = float(observed_at)

    def merge_cloud(
        self,
        result: CloudVisionUIResult,
    ) -> MergedSceneUnderstanding | None:
        if not isinstance(result, CloudVisionUIResult):
            raise TypeError("Cloud UI result must be strongly typed.")
        cloud = result.interpretation
        if (
            result.status is not CloudVisionStatus.SUCCESS
            or cloud is None
            or self._local_scene is None
            or cloud.operation_id <= self._last_operation_id
        ):
            return None
        merged = self._interpreter.merge(
            self._local_scene,
            local_observed_at=self._local_observed_at,
            cloud=cloud,
        )
        self._last_operation_id = cloud.operation_id
        return merged

    def reset(self) -> None:
        self._local_scene = None
        self._local_observed_at = 0.0
        self._last_operation_id = -1


class SignalPort(Protocol):
    def connect(self, slot: Callable[..., object]) -> object: ...


class CloudVisionServicePort(Protocol):
    result_ready: SignalPort
    busy_changed: SignalPort

    def refresh_authorization(self) -> SavedVisionAuthorization: ...

    def submit_event_rgb(self, rgb: bytes, width: int, height: int) -> bool: ...

    def submit_manual_rgb(self, rgb: bytes, width: int, height: int) -> bool: ...

    def cancel(self) -> None: ...

    def close(self) -> None: ...


class CloudVisionServiceFactoryPort(Protocol):
    def __call__(
        self,
        secret_store: SecretStorePort,
        authorization_source: StoredVisionAuthorizationSource,
    ) -> CloudVisionServicePort: ...


class StoredVisionAuthorizationSource:
    """Expose committed preferences with a stable, content-derived generation."""

    def __init__(self, store: OpenAIVisionPreferencesStore) -> None:
        self._store = store

    def load(self) -> SavedVisionAuthorization:
        preferences = self._store.load()
        payload = self._store.export_portable()
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        generation = int.from_bytes(hashlib.sha256(canonical).digest()[:8], "big")
        return SavedVisionAuthorization(
            preferences,
            PREFERENCES_VERSION,
            generation,
            True,
        )


class _WorkerSignals(QObject):
    done = Signal(object, int)


class _AnalyzeWorker(QRunnable):
    def __init__(
        self,
        runtime: CloudVisionRuntime,
        frame: CloudVisionFrame,
        generation: int,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._frame = frame
        self._generation = generation
        self.signals = _WorkerSignals()

    def run(self) -> None:
        result = self._runtime.analyze(self._frame)
        self.signals.done.emit(result, self._generation)


class CloudVisionRuntimeService(QObject):
    """Qt lifecycle adapter; frames exist only in memory until analysis ends."""

    result_ready = Signal(object)
    busy_changed = Signal(bool)

    def __init__(
        self,
        runtime: CloudVisionRuntime,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._lock = threading.Lock()
        self._busy = False
        self._closed = False
        self._generation = 0
        self._operation_id = 0
        self._workers: set[_AnalyzeWorker] = set()

    def refresh_authorization(self) -> SavedVisionAuthorization:
        authorization = self._runtime.refresh_saved_authorization()
        if not authorization.enabled:
            self.cancel()
        return authorization

    def submit_rgb_frame(
        self,
        rgb: bytes,
        width: int,
        height: int,
        trigger: CloudVisionTrigger,
    ) -> bool:
        encoded = _encode_rgb_png(rgb, width, height)
        with self._lock:
            if self._closed or self._busy or encoded is None:
                return False
            self._busy = True
            self._operation_id += 1
            operation_id = self._operation_id
            generation = self._generation
        frame = CloudVisionFrame(
            operation_id,
            encoded,
            width,
            height,
            "image/png",
            "Describe only the visible scene and objects relevant to assistance.",
            trigger,
        )
        worker = _AnalyzeWorker(self._runtime, frame, generation)
        with self._lock:
            self._workers.add(worker)
        worker.signals.done.connect(
            lambda result, token, current=worker: self._finished(
                current, result, token
            )
        )
        self.busy_changed.emit(True)
        self._pool.start(worker)
        return True

    def submit_event_rgb(self, rgb: bytes, width: int, height: int) -> bool:
        return self.submit_rgb_frame(
            rgb, width, height, CloudVisionTrigger.EVENT
        )

    def submit_manual_rgb(self, rgb: bytes, width: int, height: int) -> bool:
        return self.submit_rgb_frame(
            rgb, width, height, CloudVisionTrigger.MANUAL
        )

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1
            was_busy = self._busy
            self._busy = False
            self._workers.clear()
        self._runtime.close()
        self._pool.clear()
        if was_busy:
            self.busy_changed.emit(False)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.cancel()
        self._pool.waitForDone(1500)

    def _finished(
        self,
        worker: _AnalyzeWorker,
        result: object,
        generation: int,
    ) -> None:
        with self._lock:
            self._workers.discard(worker)
            if self._closed or generation != self._generation:
                return
            self._busy = False
        self.busy_changed.emit(False)
        safe = _safe_ui_result(result)
        self.result_ready.emit(safe)


def _encode_rgb_png(rgb: bytes, width: int, height: int) -> bytes | None:
    if width <= 0 or height <= 0 or len(rgb) != width * height * 3:
        return None
    image = QImage(rgb, width, height, width * 3, QImage.Format_RGB888).copy()
    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.WriteOnly) or not image.save(buffer, "PNG"):
        return None
    return bytes(data)


def _safe_ui_result(result: object) -> CloudVisionUIResult:
    if not isinstance(result, CloudVisionResult):
        return CloudVisionUIResult(CloudVisionStatus.SERVICE_UNAVAILABLE)
    if not result.succeeded or result.understanding is None:
        return CloudVisionUIResult(result.status)
    interpreted = CloudSceneInterpreter().interpret(
        VisionProviderResult(
            result.operation_id,
            VisionResultStatus("success"),
            "gpt-5.6-luna",
            VisionDetail.AUTO,
            result.understanding,
        )
    )
    return CloudVisionUIResult(
        result.status,
        _suppress_person_facts(interpreted),
    )


def _suppress_person_facts(
    interpretation: CloudSceneInterpretation,
) -> CloudSceneInterpretation:
    facts = tuple(
        fact
        for fact in interpretation.facts
        if fact.kind is not SceneFactKind.PERSON
    )
    removed = len(interpretation.facts) - len(facts)
    if not removed:
        return interpretation
    allowed = {(fact.kind.value, fact.label) for fact in facts}
    candidates = tuple(
        candidate
        for candidate in interpretation.interaction_candidates
        if not candidate.arguments
        or len(candidate.arguments) < MIN_ARGUMENT_PAIR_COUNT
        or (candidate.arguments[0][1], candidate.arguments[1][1]) in allowed
    )
    return CloudSceneInterpretation(
        interpretation.operation_id,
        interpretation.increment,
        facts,
        candidates,
        interpretation.suppressed_claims + removed,
    )
