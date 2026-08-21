from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication
lazy from PySide6.QtTest import QSignalSpy

lazy from gesture_intent import NormalizedPoint
lazy from infrastructure.face_identity_store import FaceIdentityStore
lazy from infrastructure.opencv_vision import OpenCVFrameEvidence
lazy from local_visual_intelligence import (
    ConservativeDegradation,
    EvidenceAvailability,
)
lazy from vision_controller import VisionController, _AnalysisTask
lazy from vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    SceneUnderstanding,
)
lazy from vision_runtime import VisionReadiness

EXPECTED_GENERATION = 7
EXPECTED_CONSECUTIVE_FAILURES = 2


class MemorySecretStore:
    def load(self) -> str:
        return ""

    def save(self, _value: str) -> None:
        pass

    def clear(self) -> None:
        pass


class EmptyIdentities:
    pass


class BrokenProvider:
    def analyze_frame(self, _rgb_bytes: bytes, _width: int, _height: int) -> object:
        raise RuntimeError("camera inference failed")


def local_evidence() -> OpenCVFrameEvidence:
    identity = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.9)
    scene = SceneUnderstanding(identity, (), (), ())
    return OpenCVFrameEvidence(
        scene,
        BoundingBox(20.0, 10.0, 80.0, 90.0),
        (
            NormalizedPoint(0.35, 0.35),
            NormalizedPoint(0.65, 0.35),
            NormalizedPoint(0.50, 0.50),
            NormalizedPoint(0.40, 0.68),
            NormalizedPoint(0.60, 0.68),
        ),
    )


def assert_disabled_and_missing_camera_are_isolated() -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    for enabled, camera_available, expected in (
        (False, False, VisionReadiness.DISABLED),
        (True, False, VisionReadiness.CAMERA_UNAVAILABLE),
    ):
        health = controller.configure(
            enabled=enabled,
            camera_available=camera_available,
        )
        assert health.readiness is expected
        controller.submit_frame(b"", 0, 0)
    controller.close()


def assert_worker_exception_never_escapes(application: QCoreApplication) -> None:
    task = _AnalysisTask(
        BrokenProvider(),  # type: ignore[arg-type]
        b"rgb",
        1,
        1,
        7,
    )
    failures = QSignalSpy(task.signals.failed)
    completions = QSignalSpy(task.signals.completed)
    task.run()
    application.processEvents()
    assert failures.count() == 1
    assert failures.at(0)[-1] == EXPECTED_GENERATION
    assert str(failures.at(0)[0]) == "RuntimeError"
    assert completions.count() == 0


def assert_controller_reports_and_recovers_from_worker_failure(
    application: QCoreApplication,
) -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    health_events = QSignalSpy(controller.health_changed)
    controller._busy = True
    controller._enabled = True
    controller._analysis_failed("RuntimeError", controller._generation)
    application.processEvents()
    assert not controller._busy
    assert health_events.count() == 0
    assert controller._consecutive_analysis_failures == 1
    controller._analysis_failed("RuntimeError", controller._generation)
    application.processEvents()
    assert health_events.count() == 0
    assert controller._consecutive_analysis_failures == EXPECTED_CONSECUTIVE_FAILURES
    controller._analysis_failed("RuntimeError", controller._generation)
    application.processEvents()
    assert health_events.count() == 1
    health = health_events.at(0)[0]
    assert health.readiness is VisionReadiness.RUNTIME_ERROR
    assert health.detail == "RuntimeError"
    assert not controller._enabled
    controller._consecutive_analysis_failures = 2
    controller._enabled = True
    controller._analysis_completed(
        SceneUnderstanding(
            IdentityObservation(IdentityState.NO_FACE),
            (),
            (),
            (),
        ),
        controller._generation,
    )
    application.processEvents()
    assert controller._consecutive_analysis_failures == 0
    controller.close()


def assert_local_pipeline_emits_typed_unknown_degradation_and_keeps_scene(
    application: QCoreApplication,
) -> None:
    now = iter((10.0, 11.0))
    controller = VisionController(
        FaceIdentityStore(MemorySecretStore()),
        clock=lambda: next(now),
        mirrored_input=True,
    )
    controller._enabled = True
    scenes = QSignalSpy(controller.scene_changed)
    intelligence = QSignalSpy(controller.local_intelligence_changed)
    evidence = local_evidence()
    controller._analysis_completed(evidence, controller._generation)
    application.processEvents()
    assert scenes.count() == 1
    assert scenes.at(0)[0] == evidence.scene
    assert intelligence.count() == 1
    result = intelligence.at(0)[0]
    assert result.evidence.face_box == evidence.face_box
    assert result.evidence.sparse_face_landmarks == evidence.sparse_face_landmarks
    assert result.social_availability is EvidenceAvailability.UNKNOWN
    assert result.gesture_availability is EvidenceAvailability.UNKNOWN
    assert ConservativeDegradation.YUNET_FIVE_POINT_INSUFFICIENT in result.degradations
    assert ConservativeDegradation.HAND_LANDMARK_MODEL_UNAVAILABLE in result.degradations

    controller._cancel_pending_work()
    controller._enabled = True
    controller._analysis_completed(evidence, controller._generation - 1)
    application.processEvents()
    assert scenes.count() == 1
    assert intelligence.count() == 1
    controller.close()


def run() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    assert application is not None
    assert_disabled_and_missing_camera_are_isolated()
    assert_worker_exception_never_escapes(application)
    assert_controller_reports_and_recovers_from_worker_failure(application)
    assert_local_pipeline_emits_typed_unknown_degradation_and_keeps_scene(application)


if __name__ == "__main__":
    run()
    print("VISION_CONTROLLER_OK")
