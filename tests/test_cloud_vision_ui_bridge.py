from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy import threading
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from time import monotonic

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QObject, Signal
lazy from PySide6.QtWidgets import QApplication

lazy from domain.cloud_scene_interpreter import CloudSceneInterpretation
lazy from application.cloud_vision_runtime import (
    CloudVisionResult,
    CloudVisionStatus,
    SavedVisionAuthorization,
)
lazy from application.cloud_vision_ui_bridge import (
    CloudVisionRuntimeService,
    CloudVisionUIResult,
    _safe_ui_result,
)
lazy from domain.vision_provider_contracts import (
    ClaimStatus,
    VisualClaim,
    VisualUnderstanding,
)
lazy from presentation.flagship_ui import ControlCenterDependencies, FlagshipControlCenter
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
)
lazy from domain.openai_vision_preferences import (
    PREFERENCES_VERSION,
    OpenAIVisionPreferences,
)
lazy from domain.vision_domain import IdentityObservation, IdentityState, SceneUnderstanding

EXPECTED_OPERATION_ID = 8
PAIR_LENGTH = 2


class FakeRuntime:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.frames: list[object] = []
        self.close_calls = 0
        self.authorization = SavedVisionAuthorization(
            OpenAIVisionPreferences(enabled=True, cloud_vision_enabled=True),
            PREFERENCES_VERSION,
            1,
        )

    def refresh_saved_authorization(self) -> SavedVisionAuthorization:
        return self.authorization

    def analyze(self, frame: object) -> CloudVisionResult:
        self.frames.append(frame)
        self.started.set()
        self.release.wait(2.0)
        return CloudVisionResult(frame.operation_id, CloudVisionStatus.SUCCESS, 1)

    def close(self) -> None:
        self.close_calls += 1
        self.release.set()


class StickyRuntime(FakeRuntime):
    def close(self) -> None:
        self.close_calls += 1


class FakeService(QObject):
    result_ready = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, source: object) -> None:
        super().__init__()
        self.source = source
        self.refreshes: list[object] = []
        self.event_frames: list[tuple[bytes, int, int]] = []
        self.manual_frames: list[tuple[bytes, int, int]] = []
        self.cancel_calls = 0
        self.close_calls = 0

    def refresh_authorization(self):
        authorization = self.source.load()
        self.refreshes.append(authorization)
        return authorization

    def submit_event_rgb(self, rgb: bytes, width: int, height: int) -> bool:
        if not self.source.load().enabled:
            return False
        self.event_frames.append((rgb, width, height))
        return True

    def submit_manual_rgb(self, rgb: bytes, width: int, height: int) -> bool:
        if not self.source.load().enabled:
            return False
        self.manual_frames.append((rgb, width, height))
        return True

    def cancel(self) -> None:
        self.cancel_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class Factory:
    def __init__(self) -> None:
        self.service: FakeService | None = None
        self.secret_store: object | None = None

    def __call__(self, secret_store: object, source: object) -> FakeService:
        self.secret_store = secret_store
        self.service = FakeService(source)
        return self.service


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return
    raise AssertionError("Qt condition timed out")


def assert_runtime_service_single_inflight_and_cancel() -> None:
    runtime = FakeRuntime()
    service = CloudVisionRuntimeService(runtime)
    try:
        rgb = bytes([20, 30, 40] * 4)
        assert service.submit_event_rgb(rgb, 2, 2) is True
        assert runtime.started.wait(1.0)
        assert service.submit_event_rgb(rgb, 2, 2) is False
        service.cancel()
        _wait_until(lambda: runtime.close_calls >= 1)
        assert len(runtime.frames) == 1
        assert "image_bytes" not in repr(runtime.frames[0])
    finally:
        service.close()


def assert_repeated_cancel_keeps_worker_tracking_bounded() -> None:
    runtime = StickyRuntime()
    service = CloudVisionRuntimeService(runtime)
    rgb = bytes([20, 30, 40] * 4)
    try:
        assert service.submit_event_rgb(rgb, 2, 2)
        assert runtime.started.wait(1.0)
        for _index in range(1_000):
            service.cancel()
            assert len(service._workers) <= 1
            assert service.submit_event_rgb(rgb, 2, 2)
        service.cancel()
        assert len(service._workers) <= 1
    finally:
        runtime.release.set()
        service.close()


def assert_safe_ui_result_contains_typed_sanitized_interpretation() -> None:
    understanding = VisualUnderstanding(
        "A person is reading beside a laptop.",
        (
            VisualClaim(
                "A person is visible beside a laptop.",
                ClaimStatus.OBSERVED,
                0.96,
                "Visible pixels show a person and laptop.",
            ),
            VisualClaim(
                "The person is named Alice.",
                ClaimStatus.OBSERVED,
                0.99,
                "A name may be visible.",
            ),
        ),
        (),
    )
    safe = _safe_ui_result(
        CloudVisionResult(8, CloudVisionStatus.SUCCESS, 1, understanding)
    )
    assert isinstance(safe, CloudVisionUIResult)
    assert isinstance(safe.interpretation, CloudSceneInterpretation)
    assert safe.interpretation.operation_id == EXPECTED_OPERATION_ID
    assert safe.interpretation.suppressed_claims == PAIR_LENGTH
    assert all(fact.label != "person" for fact in safe.interpretation.facts)
    assert "Alice" not in repr(safe)
    failed = _safe_ui_result(
        CloudVisionResult(9, CloudVisionStatus.STALE, 1)
    )
    assert failed.interpretation is None


def test_successful_cloud_continuation_resolves_status_from_true_owner() -> None:
    """Guard the import order that exposed a Python 3.15rc1 lazy proxy."""

    source = """
import application.cloud_vision_ui_bridge as bridge

class FakeResult:
    operation_id = 7
    status = "success"
    succeeded = True
    understanding = object()

class FakeDetail:
    AUTO = "auto"

class FakeInterpreter:
    def interpret(self, value):
        assert value[1].value == "success"
        return "interpreted"

bridge.CloudVisionResult = FakeResult
bridge.VisionProviderResult = lambda *values: values
bridge.VisionDetail = FakeDetail
bridge.CloudSceneInterpreter = FakeInterpreter
bridge._suppress_person_facts = lambda value: value

result = bridge._safe_ui_result(FakeResult())
assert result.interpretation == "interpreted"
"""
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHON_JIT": "1", "QT_QPA_PLATFORM": "offscreen"},
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr


def assert_control_center_merges_cloud_into_latest_local_scene(root: Path) -> None:
    db = StudioDB(root / "mohan-merge.db")
    store = OpenAIVisionPreferencesStore(StudioDBSettingsPort(db))
    factory = Factory()
    center = FlagshipControlCenter(
        db,
        root,
        dependencies=ControlCenterDependencies(
            openai_vision_store=store,
            openai_vision_key_available=lambda: True,
            cloud_vision_service_factory=factory,
        ),
    )
    emitted: list[SceneUnderstanding] = []
    center.visual_scene_changed.connect(emitted.append)
    owner = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.98)
    local = SceneUnderstanding(owner, (), ("at_computer",), ())
    center._vision_scene_changed(local)
    try:
        understanding = VisualUnderstanding(
            "A person may be reading.",
            (
                VisualClaim(
                    "The person may be reading a book.",
                    ClaimStatus.INFERRED,
                    0.91,
                    "A book-like object is visible.",
                ),
            ),
            (),
        )
        result = _safe_ui_result(
            CloudVisionResult(11, CloudVisionStatus.SUCCESS, 1, understanding)
        )
        center._cloud_vision_result(result)
        assert len(emitted) == PAIR_LENGTH
        merged = emitted[-1]
        assert merged.identity is owner
        assert merged.activities == ("at_computer", "possible_reading")
        center._cloud_vision_result(result)
        center._cloud_vision_result(
            CloudVisionUIResult(CloudVisionStatus.CANCELLED)
        )
        assert len(emitted) == PAIR_LENGTH
        assert not hasattr(result, "speak")
        assert not hasattr(result, "execute")
    finally:
        center.close_services()
        db.close()


def assert_control_center_saved_lifecycle(root: Path) -> None:
    db = StudioDB(root / "mohan.db")
    store = OpenAIVisionPreferencesStore(StudioDBSettingsPort(db))
    factory = Factory()
    center = FlagshipControlCenter(
        db,
        root,
        dependencies=ControlCenterDependencies(
            openai_vision_store=store,
            openai_vision_key_available=lambda: True,
            cloud_vision_service_factory=factory,
        ),
    )
    service = factory.service
    assert service is not None
    try:
        rgb = bytes([1, 2, 3] * 4)
        center.openai_vision_enabled.setChecked(True)
        center.openai_cloud_vision_enabled.setChecked(True)
        center.camera_presence.vision_frame_ready.emit(rgb, 2, 2)
        assert service.event_frames == []
        assert service.refreshes[-1].enabled is False

        center.save_draft_settings()
        assert service.refreshes[-1].enabled is True
        center.camera_presence.vision_frame_ready.emit(rgb, 2, 2)
        assert service.event_frames == [(rgb, 2, 2)]

        center.camera_enabled.setChecked(False)
        center.apply_camera_settings()
        assert service.cancel_calls == 1
        center.stop_openai_vision_immediately()
        assert service.cancel_calls == PAIR_LENGTH
        assert store.load().enabled is False
    finally:
        center.close_services()
        assert service.close_calls == 1
        db.close()


def run() -> None:
    QApplication.instance() or QApplication([])
    assert_runtime_service_single_inflight_and_cancel()
    assert_repeated_cancel_keeps_worker_tracking_bounded()
    assert_safe_ui_result_contains_typed_sanitized_interpretation()
    test_successful_cloud_continuation_resolves_status_from_true_owner()
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        assert_control_center_saved_lifecycle(Path(temp))
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        assert_control_center_merges_cloud_into_latest_local_scene(Path(temp))
    print("CLOUD_VISION_UI_BRIDGE_OK")


if __name__ == "__main__":
    run()
