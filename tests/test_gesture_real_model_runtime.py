from __future__ import annotations

lazy import ast
lazy import os
lazy import socket
lazy import sys
lazy import time
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE_PACKAGES = PROJECT / ".venv315" / "Lib" / "site-packages"
if WORKSPACE_PACKAGES.is_dir():
    sys.path.insert(0, str(WORKSPACE_PACKAGES))
sys.path.insert(0, str(PROJECT))

lazy import cv2
lazy import numpy as np
lazy from PySide6.QtCore import QCoreApplication

lazy from application.gesture_action_router import GestureActionDecision
lazy from domain.gesture_configuration import GestureConfiguration
lazy from application.gesture_controller import GestureController, GestureControllerStatus
lazy from application.gesture_runtime import GestureRuntimeResult
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkProvider,
    HandLandmarkStatus,
    HandModelPaths,
)

MODEL_ROOT = PROJECT / "assets" / "vision-models"
MODELS = HandModelPaths(
    MODEL_ROOT / "palm_detection_mediapipe_2023feb.onnx",
    MODEL_ROOT / "handpose_estimation_mediapipe_2023feb.onnx",
)
WIDTH = 320
HEIGHT = 240
MAX_SUBMIT_FRAME_SECONDS = 0.10


class Runtime:
    def __init__(self) -> None:
        self.calls = 0

    def update(self, observed_at, hands, configuration) -> GestureRuntimeResult:
        self.calls += 1
        assert hands == ()
        assert configuration.enabled
        return GestureRuntimeResult(observed_at, ())

    def cancel(self) -> None:
        pass

    def reset(self) -> None:
        pass


class Dispatcher:
    def __init__(self) -> None:
        self.decisions: list[GestureActionDecision] = []

    def dispatch(self, decision: GestureActionDecision) -> object:
        self.decisions.append(decision)
        return object()


def blank_frame() -> bytes:
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8).tobytes()


def test_real_models_load_and_blank_frame_is_safe_no_hand() -> None:
    assert MODELS.missing == ()
    palm_net = cv2.dnn.readNet(str(MODELS.palm_detection))
    hand_net = cv2.dnn.readNet(str(MODELS.hand_pose))
    assert palm_net is not None and hand_net is not None

    frame = blank_frame()
    provider = HandLandmarkProvider(MODELS)
    result = provider.analyze(frame, WIDTH, HEIGHT)
    assert result.status is HandLandmarkStatus.OK
    assert result.hands == ()
    assert not hasattr(provider, "_frame")
    assert frame not in _object_values(provider)


def test_real_provider_controller_is_nonblocking_and_no_hand_stays_ready() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    runtime = Runtime()
    dispatcher = Dispatcher()
    controller = GestureController(
        dispatcher,
        model_directory=MODEL_ROOT,
        provider_factory=lambda: HandLandmarkProvider(MODELS),
        runtime=runtime,
    )
    health = controller.configure(
        GestureConfiguration(enabled=True),
        camera_available=True,
    )
    assert health.status is GestureControllerStatus.READY
    frame = blank_frame()
    started = time.monotonic()
    controller.submit_frame(frame, WIDTH, HEIGHT)
    assert time.monotonic() - started < MAX_SUBMIT_FRAME_SECONDS
    deadline = time.monotonic() + 5.0
    while runtime.calls == 0 and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert runtime.calls == 1
    assert controller.health.status is GestureControllerStatus.READY
    assert controller.sampling_enabled
    assert dispatcher.decisions == []
    assert frame not in _object_values(controller)
    controller.close()


def test_hand_runtime_modules_have_no_network_imports_or_frame_writes() -> None:
    forbidden_network = {"aiohttp", "httpx", "requests", "socket", "urllib"}
    forbidden_writes = {"imwrite", "VideoWriter", "write_bytes"}
    for name in (
        "infrastructure/hand_landmark_provider.py",
        "application/gesture_controller.py",
        "application/gesture_runtime.py",
    ):
        source = (PROJECT / name).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=name)
        imported = {
            *(
                alias.name.split(".", 1)[0]
                for alias in node.names
            )
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        }
        imported.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert imported.isdisjoint(forbidden_network)
        assert all(marker not in source for marker in forbidden_writes)
    assert socket.getdefaulttimeout() is None


def _object_values(value: object) -> tuple[object, ...]:
    try:
        return tuple(vars(value).values())
    except TypeError:
        return ()


def run() -> None:
    test_real_models_load_and_blank_frame_is_safe_no_hand()
    test_real_provider_controller_is_nonblocking_and_no_hand_stays_ready()
    test_hand_runtime_modules_have_no_network_imports_or_frame_writes()
    print("GESTURE_REAL_MODEL_RUNTIME_OK")


if __name__ == "__main__":
    run()
