from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtTest import QSignalSpy

lazy from camera_presence import CameraPresenceController

EXPECTED_GESTURE_COUNT = 5
EXPECTED_SCENE_COUNT = 2
EXPECTED_OBSERVATION_COUNT = 3


class VideoFrame:
    def __init__(self, *, valid: bool = True) -> None:
        if valid:
            self._image = QImage(4, 2, QImage.Format_RGB888)
            self._image.fill(QColor("#8090a0"))
        else:
            self._image = QImage()

    def toImage(self) -> QImage:
        return self._image


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def assert_default_off_and_independent_sampling_rates() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    clock = Clock()
    controller = CameraPresenceController(clock=clock)
    controller._active = True
    gestures = QSignalSpy(controller.gesture_frame_ready)
    scenes = QSignalSpy(controller.vision_frame_ready)
    observations = QSignalSpy(controller.visual_observation)
    frame = VideoFrame()

    clock.now = 10.0
    controller._frame(frame)  # type: ignore[arg-type]
    application.processEvents()
    assert gestures.count() == 0
    assert scenes.count() == 1
    assert observations.count() == 1

    controller.configure_gesture_sampling(True)
    for moment in (10.01, 10.05, 10.12, 10.23, 10.46, 11.01):
        clock.now = moment
        controller._frame(frame)  # type: ignore[arg-type]
    application.processEvents()
    assert gestures.count() == EXPECTED_GESTURE_COUNT
    assert scenes.count() == EXPECTED_SCENE_COUNT
    assert observations.count() == EXPECTED_OBSERVATION_COUNT
    payload, width, height = gestures.at(0)
    assert isinstance(payload, bytes) and payload
    assert width > 0 and height > 0


def assert_disable_stop_fault_and_invalid_frames_fail_closed() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    clock = Clock()
    controller = CameraPresenceController(clock=clock)
    controller._active = True
    controller.configure_gesture_sampling(True)
    gestures = QSignalSpy(controller.gesture_frame_ready)

    clock.now = 20.0
    controller._frame(VideoFrame(valid=False))  # type: ignore[arg-type]
    controller.configure_gesture_sampling(False)
    clock.now = 20.2
    controller._frame(VideoFrame())  # type: ignore[arg-type]
    controller.configure_gesture_sampling(True)
    controller._camera_error(None, "temporary camera failure")
    clock.now = 20.4
    controller._frame(VideoFrame())  # type: ignore[arg-type]
    controller.stop()
    clock.now = 20.6
    controller._frame(VideoFrame())  # type: ignore[arg-type]
    application.processEvents()
    assert gestures.count() == 0

    try:
        controller.configure_gesture_sampling(1)  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("Non-boolean gesture sampling state was accepted.")


def run() -> None:
    assert_default_off_and_independent_sampling_rates()
    assert_disable_stop_fault_and_invalid_frames_fail_closed()
    print("CAMERA_GESTURE_FRAMES_OK")


if __name__ == "__main__":
    run()
