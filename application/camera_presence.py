from __future__ import annotations

lazy import time
lazy from dataclasses import dataclass, replace

lazy from PySide6.QtCore import QObject, Qt, Signal
lazy from PySide6.QtGui import QImage

lazy from application.visual_perception import (
    LocalVisualAnalyzer,
    PresenceState,
    VisualObservation,
)
lazy from domain.service_status_localization import ServiceStatus, service_status

try:
    from PySide6.QtMultimedia import (
        QCamera,
        QMediaCaptureSession,
        QMediaDevices,
        QVideoFrame,
        QVideoSink,
    )
except ImportError:  # packaged editions can omit QtMultimedia
    QCamera = None

ABSENT_STREAK_THRESHOLD = 6
GESTURE_SAMPLE_INTERVAL = 0.1


@dataclass(slots=True)
class PresenceDebouncer:
    """Keep brief camera dropouts from becoming false leave/return cycles."""

    dropout_grace_seconds: float = 5.0
    _stable: PresenceState = PresenceState.UNKNOWN
    _away_candidate_since: float | None = None

    def __post_init__(self) -> None:
        if self.dropout_grace_seconds < 0.0:
            raise ValueError("Presence dropout grace must not be negative.")

    def stabilize(self, observation: VisualObservation) -> VisualObservation:
        presence = observation.presence
        if presence is PresenceState.PRESENT:
            self._stable = PresenceState.PRESENT
            self._away_candidate_since = None
            return observation
        if self._stable is not PresenceState.PRESENT:
            self._stable = presence
            return observation
        if self._away_candidate_since is None:
            self._away_candidate_since = observation.observed_at
        elapsed = observation.observed_at - self._away_candidate_since
        if elapsed < self.dropout_grace_seconds:
            return replace(observation, presence=PresenceState.PRESENT)
        self._stable = presence
        self._away_candidate_since = None
        return observation

    def reset(self) -> None:
        self._stable = PresenceState.UNKNOWN
        self._away_candidate_since = None


class CameraPresenceController(QObject):
    """Local-only coarse presence detection. Frames are never persisted."""

    presence_changed = Signal(bool)
    status_changed = Signal(str)
    vision_frame_ready = Signal(bytes, int, int)
    gesture_frame_ready = Signal(bytes, int, int)
    visual_observation = Signal(object)

    def __init__(
        self,
        parent=None,
        *,
        language: str = "zh-TW",
        clock=time.monotonic,
    ):
        super().__init__(parent)
        self.language = language
        self._clock = clock
        self.camera = None
        self.session = None
        self.sink = None
        self._analyzer = LocalVisualAnalyzer()
        self._presence_debouncer = PresenceDebouncer()
        self._present = False
        self._last_sample = 0.0
        self._last_vision_sample = 0.0
        self._last_gesture_sample = 0.0
        self._gesture_sampling_enabled = False
        self._active = False
        # Idle throttling: when no presence has been observed for a sustained
        # period, the sampling interval grows to save CPU and power.  Presence
        # returns to the normal cadence as soon as motion is detected again.
        self._idle_sample_interval = 0.45
        self._last_presence_at: float | None = None
        self._absent_streak = 0

    @staticmethod
    def available() -> bool:
        return QCamera is not None and bool(QMediaDevices.videoInputs())

    def start(self, device_index: int = 0) -> None:
        if QCamera is None:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.CAMERA_COMPONENT_UNAVAILABLE,
                )
            )
        devices = QMediaDevices.videoInputs()
        if not devices:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.CAMERA_NOT_FOUND,
                )
            )
        if self.camera is not None:
            return
        index = max(0, min(int(device_index), len(devices) - 1))
        self.camera = QCamera(devices[index])
        self.session = QMediaCaptureSession()
        self.sink = QVideoSink()
        self.session.setCamera(self.camera)
        self.session.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self._frame)
        self.camera.errorOccurred.connect(self._camera_error)
        self.status_changed.emit(
            service_status(
                self.language,
                ServiceStatus.CAMERA_STARTING,
            )
        )
        self._active = True
        self.camera.start()
        self.status_changed.emit(
            service_status(
                self.language,
                ServiceStatus.CAMERA_ACTIVE,
                device=devices[index].description(),
            )
        )

    def stop(self) -> None:
        self._active = False
        if self.camera is not None:
            self.camera.stop()
        self.camera = None
        self.session = None
        self.sink = None
        self._analyzer.reset()
        self._presence_debouncer.reset()
        self._last_sample = 0.0
        self._last_vision_sample = 0.0
        self._last_gesture_sample = 0.0
        if self._present:
            self._present = False
            self.presence_changed.emit(False)
        self.status_changed.emit(
            service_status(
                self.language,
                ServiceStatus.CAMERA_CLOSED,
            )
        )

    def configure_gesture_sampling(self, enabled: bool) -> None:
        """Enable transient gesture frames without starting another camera loop."""

        if type(enabled) is not bool:
            raise TypeError("Gesture sampling state must be boolean.")
        self._gesture_sampling_enabled = enabled
        self._last_gesture_sample = 0.0

    def _frame(self, frame: QVideoFrame) -> None:
        if not self._active:
            return
        now = self._clock()
        image = frame.toImage()
        if image.isNull():
            return
        self._emit_due_rgb_frames(image, now)
        if now - self._last_sample < self._idle_sample_interval:
            return
        self._last_sample = now
        image = image.scaled(24, 18)
        sample: list[int] = []
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                sample.append(
                    (color.red() * 3 + color.green() * 6 + color.blue()) // 10
                )
        observation = self._presence_debouncer.stabilize(
            self._analyzer.analyze(sample, observed_at=now)
        )
        self.visual_observation.emit(observation)
        present = observation.presence is PresenceState.PRESENT
        if present != self._present:
            self._present = present
            self.presence_changed.emit(present)
        # Grow the sampling interval only after a sustained absence (several
        # consecutive absent observations), and snap back to the normal cadence
        # the moment presence is detected.  A single absent frame never widens
        # the interval, so the deterministic sampling-rate contract is kept.
        if present:
            self._last_presence_at = now
            self._absent_streak = 0
            self._idle_sample_interval = 0.45
        else:
            self._absent_streak += 1
            if self._absent_streak >= ABSENT_STREAK_THRESHOLD:
                self._idle_sample_interval = min(2.0, 0.45 + self._absent_streak * 0.05)

    def _emit_due_rgb_frames(self, image: QImage, now: float) -> None:
        gesture_due = bool(
            self._gesture_sampling_enabled
            and now - self._last_gesture_sample >= GESTURE_SAMPLE_INTERVAL
        )
        vision_due = now - self._last_vision_sample >= 1.0
        if gesture_due or vision_due:
            raw, width, height = _transient_rgb_frame(image)
        else:
            raw, width, height = b"", 0, 0
        if vision_due:
            self._last_vision_sample = now
            if raw:
                self.vision_frame_ready.emit(raw, width, height)
        if gesture_due:
            self._last_gesture_sample = now
            if raw:
                self.gesture_frame_ready.emit(raw, width, height)

    def close(self) -> None:
        self.stop()

    def _camera_error(self, _error, message: str) -> None:
        self._active = False
        self._last_gesture_sample = 0.0
        self.status_changed.emit(
            service_status(
                self.language,
                ServiceStatus.CAMERA_ERROR,
                detail=message,
            )
        )


def _transient_rgb_frame(image: QImage) -> tuple[bytes, int, int]:
    rgb = image.convertToFormat(QImage.Format_RGB888).scaled(
        640,
        480,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    width = rgb.width()
    height = rgb.height()
    if rgb.bytesPerLine() != width * 3:
        return b"", 0, 0
    byte_count = rgb.bytesPerLine() * height
    return bytes(rgb.constBits()[:byte_count]), width, height
