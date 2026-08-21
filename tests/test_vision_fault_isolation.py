from __future__ import annotations

lazy import ast
lazy import os
lazy import socket
lazy import sys
lazy from copy import deepcopy
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

lazy from PySide6.QtCore import QCoreApplication
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtTest import QSignalSpy

lazy import camera_presence
lazy from camera_presence import CameraPresenceController
lazy from infrastructure.face_identity_store import FaceIdentityStore
lazy from vision_controller import VisionController
lazy from vision_domain import (
    IdentityObservation,
    IdentityState,
    SceneUnderstanding,
)
lazy from vision_runtime import VisionEnvironmentProbe, VisionReadiness

EXPECTED_CONSECUTIVE_FAILURES = 3

VISION_MODULES = (
    "camera_presence.py",
    "infrastructure/face_identity_store.py",
    "infrastructure/opencv_vision.py",
    "scene_semantics.py",
    "vision_controller.py",
    "vision_domain.py",
    "vision_runtime.py",
    "visual_perception.py",
)
FORBIDDEN_NETWORK_ROOTS = frozenset(
    {
        "aiohttp",
        "ftplib",
        "http",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "websocket",
    }
)
FORBIDDEN_LEGACY_ROOTS = frozenset(
    {
        "ai_client",
        "app",
        "db",
        "realtime_voice",
        "speech",
        "speech_providers",
    }
)


class MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""
        self.saved_values: list[str] = []
        self.clear_count = 0

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value
        self.saved_values.append(value)

    def clear(self) -> None:
        self.value = ""
        self.clear_count += 1


class ImmediatePool:
    def __init__(self) -> None:
        self.started_tasks: list[object] = []
        self.clear_count = 0

    def start(self, task: object) -> None:
        self.started_tasks.append(task)
        task.run()  # type: ignore[attr-defined]

    def clear(self) -> None:
        self.clear_count += 1
        self.started_tasks.clear()

    def waitForDone(self, _milliseconds: int) -> bool:
        return True


class LocalProvider:
    def __init__(self) -> None:
        self.analysis_count = 0

    def analyze(self, rgb_bytes: bytes, width: int, height: int) -> object:
        self.analysis_count += 1
        assert rgb_bytes == b"private-frame"
        assert (width, height) == (2, 2)
        return object()


class MissingCameraDevices:
    @staticmethod
    def videoInputs() -> list[object]:
        return []


class StaticVideoFrame:
    def __init__(self) -> None:
        self._image = QImage(4, 2, QImage.Format_RGB888)
        self._image.fill(QColor("#8090a0"))

    def toImage(self) -> QImage:
        return self._image


def _local_import_roots(filename: str) -> set[str]:
    path = PROJECT / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def assert_disabled_camera_never_creates_inference() -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    provider_creations = 0

    def create_provider() -> LocalProvider:
        nonlocal provider_creations
        provider_creations += 1
        return LocalProvider()

    controller._create_provider = create_provider  # type: ignore[method-assign]
    health = controller.configure(enabled=False, camera_available=True)
    controller.submit_frame(b"private-frame", 2, 2)
    assert health.readiness is VisionReadiness.DISABLED
    assert provider_creations == 0
    assert not controller._busy
    controller.close()


def assert_no_camera_reports_without_crashing() -> None:
    presence = CameraPresenceController(language="zh-TW")
    statuses = QSignalSpy(presence.status_changed)
    with (
        patch.object(camera_presence, "QCamera", object()),
        patch.object(camera_presence, "QMediaDevices", MissingCameraDevices),
    ):
        try:
            presence.start()
        except RuntimeError as exc:
            assert str(exc).strip()
        else:
            raise AssertionError("missing camera must report an explicit error")
    assert presence.camera is None
    assert statuses.count() == 0
    presence.stop()
    assert statuses.count() == 1


def assert_missing_models_fail_closed() -> None:
    fake_cv2 = type(
        "FakeCV2",
        (),
        {"FaceDetectorYN": object(), "FaceRecognizerSF": object()},
    )()
    with TemporaryDirectory() as temporary, patch.dict(
        sys.modules,
        {"cv2": fake_cv2},
    ):
        health = VisionEnvironmentProbe(Path(temporary)).inspect(
            enabled=True,
            camera_available=True,
        )
    assert health.readiness is VisionReadiness.MODEL_MISSING
    assert health.detail.endswith(".onnx")


def assert_three_inference_failures_disable_vision(
    application: QCoreApplication,
) -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    controller._enabled = True
    controller._provider = LocalProvider()  # type: ignore[assignment]
    health_events = QSignalSpy(controller.health_changed)
    for expected_count in (1, 2):
        controller._busy = True
        controller._analysis_failed("RuntimeError", controller._generation)
        assert not controller._busy
        assert controller._enabled
        assert controller._consecutive_analysis_failures == expected_count
        assert health_events.count() == 0
    controller._busy = True
    controller._analysis_failed("RuntimeError", controller._generation)
    application.processEvents()
    assert not controller._busy
    assert not controller._enabled
    assert controller._provider is None
    assert controller._consecutive_analysis_failures == EXPECTED_CONSECUTIVE_FAILURES
    assert health_events.count() == 1
    health = health_events.at(0)[0]
    assert health.readiness is VisionReadiness.RUNTIME_ERROR
    assert health.detail == "RuntimeError"
    controller.close()


def assert_stop_clears_enrollment_and_work() -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    pool = ImmediatePool()
    controller._pool = pool  # type: ignore[assignment]
    controller._enabled = True
    controller._busy = True
    controller._provider = LocalProvider()  # type: ignore[assignment]
    controller._enrollment_name = "private identity"
    controller._enrollment_samples.extend(((0.1, 0.2), (0.2, 0.3)))
    controller.stop()
    assert not controller._enabled
    assert not controller._busy
    assert controller._provider is None
    assert controller._enrollment_name == ""
    assert controller._enrollment_samples == []
    assert pool.clear_count == 1
    assert pool.started_tasks == []


def assert_stop_ignores_late_inference_completion(
    application: QCoreApplication,
) -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    scene_events = QSignalSpy(controller.scene_changed)
    health_events = QSignalSpy(controller.health_changed)
    enrollment_events = QSignalSpy(controller.enrollment_completed)
    enrollment_failures = QSignalSpy(controller.enrollment_failed)
    late_scene = SceneUnderstanding(
        IdentityObservation(IdentityState.UNKNOWN),
        (),
        (),
        (),
    )
    controller._enabled = True
    controller._busy = True
    controller.stop()
    stopped_generation = controller._generation - 1
    controller._analysis_completed(late_scene, stopped_generation)
    controller._analysis_failed("RuntimeError", stopped_generation)
    controller._embedding_completed((0.1, 0.2), stopped_generation)
    controller._embedding_failed("RuntimeError", stopped_generation)
    application.processEvents()
    assert scene_events.count() == 0
    assert health_events.count() == 0
    assert enrollment_events.count() == 0
    assert enrollment_failures.count() == 0
    assert controller._consecutive_analysis_failures == 0


def assert_stopped_camera_drops_late_frames(
    application: QCoreApplication,
) -> None:
    presence = CameraPresenceController()
    inference_frames = QSignalSpy(presence.vision_frame_ready)
    observations = QSignalSpy(presence.visual_observation)
    presence.stop()
    presence._last_sample = -10.0
    presence._last_vision_sample = -10.0
    presence._frame(StaticVideoFrame())  # type: ignore[arg-type]
    application.processEvents()
    assert inference_frames.count() == 0
    assert observations.count() == 0


def assert_raw_frames_are_transient_and_never_persisted(
    application: QCoreApplication,
) -> None:
    secret_store = MemorySecretStore()
    controller = VisionController(FaceIdentityStore(secret_store))
    pool = ImmediatePool()
    provider = LocalProvider()
    controller._pool = pool  # type: ignore[assignment]
    controller._provider = provider  # type: ignore[assignment]
    controller._enabled = True
    with TemporaryDirectory() as temporary:
        before = tuple(Path(temporary).iterdir())
        controller.submit_frame(b"private-frame", 2, 2)
        application.processEvents()
        controller.stop()
        after = tuple(Path(temporary).iterdir())
    assert provider.analysis_count == 1
    assert before == after == ()
    assert secret_store.saved_values == []
    assert all(
        value != b"private-frame"
        for value in vars(controller).values()
    )


def assert_visual_pipeline_has_no_network_path(
    application: QCoreApplication,
) -> None:
    for filename in VISION_MODULES:
        roots = _local_import_roots(filename)
        assert not roots & FORBIDDEN_NETWORK_ROOTS, (
            filename,
            roots & FORBIDDEN_NETWORK_ROOTS,
        )

    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    pool = ImmediatePool()
    provider = LocalProvider()
    controller._pool = pool  # type: ignore[assignment]
    controller._provider = provider  # type: ignore[assignment]
    controller._enabled = True
    with patch.object(
        socket,
        "socket",
        side_effect=AssertionError("vision must not open a network socket"),
    ):
        controller.submit_frame(b"private-frame", 2, 2)
        application.processEvents()
    assert provider.analysis_count == 1
    controller.stop()


def assert_legacy_voice_and_chat_settings_are_unrelated() -> None:
    settings = {
        "voice_engine": "openai-speech",
        "tts_voice": "coral",
        "realtime_voice": "shimmer",
        "chat_zoom_percent": 130,
        "persona_prompt": "private persona",
    }
    expected = deepcopy(settings)
    for filename in VISION_MODULES:
        roots = _local_import_roots(filename)
        assert not roots & FORBIDDEN_LEGACY_ROOTS, (
            filename,
            roots & FORBIDDEN_LEGACY_ROOTS,
        )
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    controller.configure(enabled=False, camera_available=False)
    controller.stop()
    assert settings == expected


def run() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    assert application is not None
    checks = (
        ("disabled camera creates no inference", assert_disabled_camera_never_creates_inference),
        ("missing camera reports safely", assert_no_camera_reports_without_crashing),
        ("missing models fail closed", assert_missing_models_fail_closed),
        (
            "three failures disable vision",
            lambda: assert_three_inference_failures_disable_vision(application),
        ),
        ("stop clears enrollment and work", assert_stop_clears_enrollment_and_work),
        (
            "stop ignores late inference completion",
            lambda: assert_stop_ignores_late_inference_completion(application),
        ),
        (
            "stopped camera drops late frames",
            lambda: assert_stopped_camera_drops_late_frames(application),
        ),
        (
            "raw frames remain transient",
            lambda: assert_raw_frames_are_transient_and_never_persisted(application),
        ),
        (
            "visual pipeline has no network path",
            lambda: assert_visual_pipeline_has_no_network_path(application),
        ),
        (
            "legacy voice and chat settings are unrelated",
            assert_legacy_voice_and_chat_settings_are_unrelated,
        ),
    )
    failures: list[AssertionError] = []
    for description, check in checks:
        try:
            check()
        except AssertionError as exc:
            exc.add_note(description)
            failures.append(exc)
    if failures:
        raise ExceptionGroup("vision fault-isolation contract failures", failures)
    print("VISION_FAULT_ISOLATION_OK")


if __name__ == "__main__":
    run()
