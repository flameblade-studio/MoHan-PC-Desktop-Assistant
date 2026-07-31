from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal

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


class CameraPresenceController(QObject):
    """Local-only coarse presence detection. Frames are never persisted."""

    presence_changed = Signal(bool)
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera = None
        self.session = None
        self.sink = None
        self._previous: list[int] | None = None
        self._last_motion = 0.0
        self._present = False
        self._last_sample = 0.0

    @staticmethod
    def available() -> bool:
        return QCamera is not None and bool(QMediaDevices.videoInputs())

    def start(self, device_index: int = 0) -> None:
        if QCamera is None:
            raise RuntimeError("此封裝未包含 QtMultimedia 攝影機元件")
        devices = QMediaDevices.videoInputs()
        if not devices:
            raise RuntimeError("找不到可用攝影機")
        if self.camera is not None:
            return
        index = max(0, min(int(device_index), len(devices) - 1))
        self.camera = QCamera(devices[index])
        self.session = QMediaCaptureSession()
        self.sink = QVideoSink()
        self.session.setCamera(self.camera)
        self.session.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self._frame)
        self.camera.errorOccurred.connect(
            lambda _error, message: self.status_changed.emit(
                f"攝影機錯誤：{message}"
            )
        )
        self.camera.start()
        self.status_changed.emit(
            f"攝影機使用中：{devices[index].description()}（僅本機在場偵測）"
        )

    def stop(self) -> None:
        if self.camera is not None:
            self.camera.stop()
        self.camera = None
        self.session = None
        self.sink = None
        self._previous = None
        self._last_motion = 0.0
        if self._present:
            self._present = False
            self.presence_changed.emit(False)
        self.status_changed.emit("攝影機已關閉")

    def _frame(self, frame: "QVideoFrame") -> None:
        now = time.monotonic()
        if now - self._last_sample < 0.45:
            return
        self._last_sample = now
        image = frame.toImage()
        if image.isNull():
            return
        image = image.scaled(24, 18)
        sample: list[int] = []
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                sample.append(
                    (color.red() * 3 + color.green() * 6 + color.blue()) // 10
                )
        brightness = sum(sample) / max(1, len(sample))
        if self._previous is not None:
            difference = sum(
                abs(current - previous)
                for current, previous in zip(sample, self._previous)
            ) / max(1, len(sample))
            if difference >= 5.5 and brightness >= 8:
                self._last_motion = now
        self._previous = sample
        # Stay present for 45 seconds after meaningful local movement. This is
        # intentionally not identity recognition and stores no camera frame.
        present = brightness >= 8 and now - self._last_motion <= 45.0
        if present != self._present:
            self._present = present
            self.presence_changed.emit(present)

    def close(self) -> None:
        self.stop()
