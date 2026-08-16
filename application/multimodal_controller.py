from __future__ import annotations

lazy import math
lazy import time
lazy from collections.abc import Callable, Sequence
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

lazy from application.multimodal_fusion_hub import (
    FaceMeshFrame,
    MultimodalFusionHub,
    MultimodalFusionResult,
)
lazy from domain.air_interaction import AirHandSample


class MultimodalControllerStatus(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    BUSY = "busy"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MultimodalControllerHealth:
    status: MultimodalControllerStatus
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.status in {
            MultimodalControllerStatus.READY,
            MultimodalControllerStatus.BUSY,
        }


@dataclass(frozen=True, slots=True)
class _MultimodalRequest:
    observed_at: float
    hands: tuple[AirHandSample, ...]
    face: FaceMeshFrame | None
    audio_samples: tuple[float, ...] | None
    user_speech_text: str
    language: str
    generation: int


class _MultimodalSignals(QObject):
    completed = Signal(object, int)
    failed = Signal(str, int)


class _MultimodalTask(QRunnable):
    def __init__(
        self,
        hub: MultimodalFusionHub,
        request: _MultimodalRequest,
    ) -> None:
        super().__init__()
        self.signals = _MultimodalSignals()
        self._hub = hub
        self._request = request

    def run(self) -> None:
        try:
            result = self._hub.process(
                self._request.observed_at,
                hands=self._request.hands,
                face=self._request.face,
                audio_samples=self._request.audio_samples,
                user_speech_text=self._request.user_speech_text,
                language=self._request.language,
            )
        except Exception as error:
            self.signals.failed.emit(type(error).__name__, self._request.generation)
            return
        self.signals.completed.emit(result, self._request.generation)


class MultimodalController(QObject):
    """Run the local fusion hub off the UI thread with bounded newest-work flow."""

    health_changed = Signal(object)
    result_changed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        hub_factory: Callable[[], MultimodalFusionHub] = MultimodalFusionHub,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(parent)
        if not callable(hub_factory) or not callable(clock):
            raise TypeError("multimodal controller dependencies must be callable")
        self._hub_factory = hub_factory
        self._hub = self._create_hub()
        self._clock = clock
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._enabled = False
        self._busy = False
        self._generation = 0
        self._health = MultimodalControllerHealth(
            MultimodalControllerStatus.DISABLED
        )

    @property
    def health(self) -> MultimodalControllerHealth:
        return self._health

    def configure(self, *, enabled: bool) -> MultimodalControllerHealth:
        if type(enabled) is not bool:
            raise TypeError("multimodal enabled state must be boolean")
        self.cancel()
        self._enabled = enabled
        status = (
            MultimodalControllerStatus.READY
            if enabled
            else MultimodalControllerStatus.DISABLED
        )
        return self._set_health(status)

    def submit(
        self,
        *,
        hands: tuple[AirHandSample, ...] = (),
        face: FaceMeshFrame | None = None,
        audio_samples: Sequence[float] | None = None,
        user_speech_text: str = "",
        language: str = "zh-TW",
        observed_at: float | None = None,
    ) -> None:
        if not self._enabled or self._busy:
            return
        if not isinstance(hands, tuple):
            raise TypeError("multimodal hands must be a tuple")
        if face is not None and not isinstance(face, FaceMeshFrame):
            raise TypeError("multimodal face must be canonical")
        samples = None if audio_samples is None else tuple(float(value) for value in audio_samples)
        if not all(isinstance(hand, AirHandSample) for hand in hands):
            raise TypeError("multimodal hands must contain typed observations")
        if not isinstance(user_speech_text, str) or not isinstance(language, str):
            raise TypeError("multimodal text fields must be strings")
        current_time = self._clock() if observed_at is None else float(observed_at)
        if not math.isfinite(current_time):
            raise ValueError("multimodal observation time must be finite")
        self._busy = True
        self._set_health(MultimodalControllerStatus.BUSY)
        request = _MultimodalRequest(
            current_time,
            hands,
            face,
            samples,
            user_speech_text,
            language,
            self._generation,
        )
        task = _MultimodalTask(self._hub, request)
        task.signals.completed.connect(self._completed)
        task.signals.failed.connect(self._failed)
        self._pool.start(task)

    def cancel(self) -> None:
        self._generation += 1
        self._busy = False
        self._pool.clear()
        # A running QRunnable may still hold the previous hub. Replace the
        # composition-owned hub instead of resetting shared state concurrently.
        self._hub = self._create_hub()
        if self._enabled:
            self._set_health(MultimodalControllerStatus.READY)

    def close(self) -> None:
        self.cancel()
        self._enabled = False
        self._set_health(MultimodalControllerStatus.DISABLED)
        self._pool.waitForDone(1500)

    def _completed(self, result: object, generation: int) -> None:
        if generation != self._generation or not self._enabled:
            return
        self._busy = False
        if not isinstance(result, MultimodalFusionResult):
            self._failed("invalid-result", generation)
            return
        self._set_health(MultimodalControllerStatus.READY)
        self.result_changed.emit(result)

    def _failed(self, error_name: str, generation: int) -> None:
        if generation != self._generation or not self._enabled:
            return
        self._busy = False
        self._set_health(MultimodalControllerStatus.FAILED, error_name)
        self.failed.emit(error_name)

    def _set_health(
        self,
        status: MultimodalControllerStatus,
        detail: str = "",
    ) -> MultimodalControllerHealth:
        self._health = MultimodalControllerHealth(status, detail)
        self.health_changed.emit(self._health)
        return self._health

    def _create_hub(self) -> MultimodalFusionHub:
        hub = self._hub_factory()
        if not isinstance(hub, MultimodalFusionHub):
            raise TypeError("multimodal hub factory must return the canonical hub")
        return hub
