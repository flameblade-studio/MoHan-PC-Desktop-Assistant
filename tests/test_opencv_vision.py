from __future__ import annotations

lazy import sys
lazy from importlib.metadata import version
lazy from pathlib import Path
lazy from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import cv2
lazy import numpy as np

lazy from domain.gesture_intent import NormalizedPoint
lazy from infrastructure.opencv_vision import (
    NanoDetDecoder,
    OpenCVDependencyError,
    load_opencv_runtime,
    yunet_single_face_geometry,
)

CONFIDENCE_THRESHOLD = 0.9
IMAGE_WIDTH = 832
IMAGE_HEIGHT = 624
LANDMARK_COUNT = 5


def assert_required_opencv_runtime_is_installed() -> None:
    assert version("opencv-python") == "5.0.0.93"
    assert cv2.__version__ == "5.0.0"
    assert hasattr(cv2, "FaceDetectorYN")
    assert hasattr(cv2, "FaceRecognizerSF")
    runtime = load_opencv_runtime()
    assert runtime.cv2 is cv2
    assert runtime.numpy is np


def assert_dependency_gate_fails_clearly() -> None:
    def missing_importer(name: str) -> object:
        if name == "cv2":
            raise ModuleNotFoundError("No module named 'cv2'", name="cv2")
        return np

    try:
        load_opencv_runtime(missing_importer)
    except OpenCVDependencyError as exc:
        assert "pinned runtime dependencies" in str(exc)
        assert isinstance(exc.__cause__, ModuleNotFoundError)
    else:
        raise AssertionError("missing cv2 must fail at the OpenCV adapter boundary")

    incomplete_cv2 = SimpleNamespace(dnn=SimpleNamespace(readNet=object()))

    def incomplete_importer(name: str) -> object:
        return incomplete_cv2 if name == "cv2" else np

    try:
        load_opencv_runtime(incomplete_importer)
    except OpenCVDependencyError as exc:
        assert "FaceDetectorYN" in str(exc)
        assert "dnn.NMSBoxes" in str(exc)
    else:
        raise AssertionError("incomplete cv2 must fail before model loading")


def outputs(*, malformed: bool = False, non_finite: bool = False) -> tuple[object, ...]:
    counts = (2704, 676, 169)
    classes = [np.zeros((1, count, 80), dtype=np.float32) for count in counts]
    boxes = [np.zeros((1, count, 32), dtype=np.float32) for count in counts]
    classes[0][0, 0, 39] = 0.92
    if non_finite:
        boxes[0][0, 0, 0] = np.nan
    if malformed:
        boxes[-1] = np.zeros((1, counts[-1], 16), dtype=np.float32)
    # The official model returns all class layers first and all box layers last.
    return (*classes, *boxes)


def assert_official_layout_decodes() -> None:
    detections = NanoDetDecoder(cv2, np).decode(outputs(), 832, 624)
    assert len(detections) == 1
    detection = detections[0]
    assert detection.label == "bottle"
    assert detection.confidence > CONFIDENCE_THRESHOLD
    assert 0 <= detection.box.left < detection.box.right <= IMAGE_WIDTH
    assert 0 <= detection.box.top < detection.box.bottom <= IMAGE_HEIGHT


def assert_unknown_layout_fails_closed() -> None:
    decoder = NanoDetDecoder(cv2, np)
    for bad_outputs in (outputs(malformed=True), outputs()[:-1]):
        try:
            decoder.decode(bad_outputs, 640, 480)
        except ValueError as exc:
            assert "NanoDet output" in str(exc)
        else:
            raise AssertionError("unknown NanoDet output must fail closed")
    try:
        decoder.decode(outputs(), 0, 480)
    except ValueError as exc:
        assert "dimensions" in str(exc)
    else:
        raise AssertionError("invalid source dimensions must be rejected")


def assert_non_finite_output_fails_closed() -> None:
    try:
        NanoDetDecoder(cv2, np).decode(outputs(non_finite=True), 640, 480)
    except ValueError as exc:
        assert "non-finite" in str(exc)
    else:
        raise AssertionError("non-finite inference output must be rejected")


def assert_yunet_single_face_geometry_is_typed_and_normalized() -> None:
    face = np.array(
        [
            64.0,
            48.0,
            128.0,
            96.0,
            96.0,
            72.0,
            160.0,
            72.0,
            128.0,
            96.0,
            104.0,
            120.0,
            152.0,
            120.0,
            0.95,
        ],
        dtype=np.float32,
    )
    box, landmarks = yunet_single_face_geometry(face, 256, 192)
    assert (box.left, box.top, box.right, box.bottom) == (64.0, 48.0, 192.0, 144.0)
    assert len(landmarks) == LANDMARK_COUNT
    assert landmarks[0] == NormalizedPoint(0.375, 0.375)
    assert landmarks[-1] == NormalizedPoint(0.59375, 0.625)
    for invalid in (face[:13], np.full(15, np.nan, dtype=np.float32)):
        try:
            yunet_single_face_geometry(invalid, 256, 192)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid YuNet evidence must fail closed")


def run() -> None:
    assert_required_opencv_runtime_is_installed()
    assert_dependency_gate_fails_clearly()
    assert_official_layout_decodes()
    assert_unknown_layout_fails_closed()
    assert_non_finite_output_fails_closed()
    assert_yunet_single_face_geometry_is_typed_and_normalized()


if __name__ == "__main__":
    run()
    print("OPENCV_VISION_OK")
