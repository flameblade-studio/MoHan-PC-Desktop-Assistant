from __future__ import annotations

lazy import ast
lazy import os
lazy import sys
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

lazy import pytest
lazy from PySide6.QtCore import QObject, QTimer, Signal
lazy from PySide6.QtWidgets import QApplication, QLabel, QPushButton

lazy from application.presentation_ports import PresentationPorts
lazy from dashboard_composition import DashboardDependencies
lazy from dashboard_window import Dashboard
lazy from flagship_ui import FlagshipControlCenter
lazy from flagship_ui_localization import FlagshipTranslator
lazy from gesture_action_dispatcher import (
    GestureDispatchDisposition,
    GestureDispatchResult,
)
lazy from gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionSafety,
)
lazy from gesture_configuration import GestureAction, GestureConfiguration
lazy from gesture_controller import (
    GestureController,
    GestureControllerHealth,
    GestureControllerStatus,
)
lazy from gesture_runtime import GestureRuntimeResult
lazy from infrastructure.db import StudioDB
lazy from infrastructure.face_identity_store import FaceIdentityStore
lazy from infrastructure.hand_landmark_provider import (
    HandLandmarkResult,
    HandLandmarkStatus,
)
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from vision_controller import VisionController
lazy from vision_runtime import VisionHealth, VisionReadiness

SENSITIVE_PATH = r"C:\Users\USERNAME\secret-models\mohan.onnx"
FRAME = b"\x00\x00\x00"
EXPECTED_PROVIDER_CALLS = 3
EXPECTED_RUNTIME_CALLS = 5
READY_DECISION = GestureActionDecision(
    GestureActionDisposition.READY,
    "open-palm",
    GestureAction.SHOW_DASHBOARD,
    GestureActionSafety.LOCAL_REVERSIBLE,
)


@pytest.fixture(scope="module", autouse=True)
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class OfflineListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def toggle_listening(self) -> None:
        return None


class OfflinePlatformServices:
    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=("portable-zip",),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(
            root / "data",
            root / "config",
            root / "cache",
        )

    def set_autostart(self, *_args: object, **_kwargs: object) -> None:
        return None

    def open_path(self, _path: Path) -> None:
        raise AssertionError("Failure isolation must not invoke the operating system.")


class OfflineVoiceCatalog:
    def windows_voices(self) -> list[tuple[str, str]]:
        return []


class ImmediatePool:
    def start(self, task: object) -> None:
        task.run()  # type: ignore[attr-defined]

    def clear(self) -> None:
        return None

    def waitForDone(self, _milliseconds: int) -> bool:
        return True


class SequenceProvider:
    def __init__(self, statuses: tuple[HandLandmarkStatus, ...]) -> None:
        self._statuses = list(statuses)
        self.calls = 0
        self.cancel_calls = 0

    def analyze(
        self,
        _rgb_bytes: bytes,
        _width: int,
        _height: int,
        *,
        mirror: object,
    ) -> HandLandmarkResult:
        assert mirror is not None
        self.calls += 1
        status = self._statuses.pop(0) if self._statuses else HandLandmarkStatus.OK
        return HandLandmarkResult(status, self.calls)

    def cancel(self) -> None:
        self.cancel_calls += 1


class PassiveRuntime:
    def update(
        self,
        observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        return GestureRuntimeResult(observed_at, ())

    def cancel(self) -> None:
        return None

    def reset(self) -> None:
        return None


class DecisionRuntime(PassiveRuntime):
    def update(
        self,
        observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        return GestureRuntimeResult(observed_at, (), READY_DECISION)


class SensitiveRuntimeFailure(Exception):
    pass


class FailingRuntime(PassiveRuntime):
    def __init__(self) -> None:
        self.calls = 0

    def update(
        self,
        _observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        self.calls += 1
        raise SensitiveRuntimeFailure(SENSITIVE_PATH)


class SequencedRuntime(PassiveRuntime):
    def __init__(self, failures: tuple[bool, ...]) -> None:
        self._failures = list(failures)
        self.calls = 0

    def update(
        self,
        observed_at: float,
        _hands: tuple[object, ...],
        _configuration: GestureConfiguration,
    ) -> GestureRuntimeResult:
        self.calls += 1
        should_fail = self._failures.pop(0) if self._failures else False
        if should_fail:
            raise SensitiveRuntimeFailure(SENSITIVE_PATH)
        return GestureRuntimeResult(observed_at, ())


class PassiveDispatcher:
    def dispatch(self, decision: object) -> GestureDispatchResult:
        assert isinstance(decision, GestureActionDecision)
        return GestureDispatchResult(
            GestureDispatchDisposition.EXECUTED,
            decision.action,
            "executed",
        )


class SensitiveDispatchFailure(Exception):
    pass


class FailingDispatcher:
    def __init__(self) -> None:
        self.calls = 0

    def dispatch(self, _decision: object) -> GestureDispatchResult:
        self.calls += 1
        raise SensitiveDispatchFailure(SENSITIVE_PATH)


def _gesture_controller(
    provider: SequenceProvider,
    *,
    runtime: PassiveRuntime | None = None,
    dispatcher: PassiveDispatcher | FailingDispatcher | None = None,
) -> GestureController:
    controller = GestureController(
        dispatcher or PassiveDispatcher(),
        provider_factory=lambda: provider,
        runtime=runtime or PassiveRuntime(),
    )
    controller._pool = ImmediatePool()  # type: ignore[assignment]
    health = controller.configure(
        GestureConfiguration(enabled=True),
        camera_available=True,
    )
    assert health.status is GestureControllerStatus.READY
    return controller


def _submit(controller: GestureController, application: QApplication) -> None:
    controller.submit_frame(FRAME, 1, 1)
    application.processEvents()


def test_missing_models_disable_only_gesture_sampling(tmp_path: Path) -> None:
    controller = GestureController(
        PassiveDispatcher(),
        model_directory=tmp_path,
    )
    health = controller.configure(
        GestureConfiguration(enabled=True),
        camera_available=True,
    )
    try:
        assert health.status is GestureControllerStatus.MODEL_MISSING
        assert not health.ready
        assert not controller.sampling_enabled
        assert all(
            path.name
            in {
                "palm_detection_mediapipe_2023feb.onnx",
                "handpose_estimation_mediapipe_2023feb.onnx",
            }
            for path in controller._models.missing
        )
    finally:
        controller.close()


def test_model_load_failure_disables_only_gesture_sampling(
    application: QApplication,
) -> None:
    provider = SequenceProvider((HandLandmarkStatus.MODEL_LOAD_FAILED,))
    controller = _gesture_controller(provider)
    try:
        _submit(controller, application)
        assert controller.health.status is GestureControllerStatus.MODEL_LOAD_FAILED
        assert not controller.sampling_enabled
        assert provider.cancel_calls == 1
    finally:
        controller.close()


def test_three_inference_failures_disable_only_gesture_sampling(
    application: QApplication,
) -> None:
    provider = SequenceProvider((HandLandmarkStatus.INFERENCE_FAILED,) * 3)
    controller = _gesture_controller(provider)
    try:
        for expected_failures in (1, 2):
            _submit(controller, application)
            assert controller.sampling_enabled
            assert controller._consecutive_failures == expected_failures
        _submit(controller, application)
        assert controller.health.status is GestureControllerStatus.INFERENCE_FAILED
        assert (
            controller.health.detail_code == HandLandmarkStatus.INFERENCE_FAILED.value
        )
        assert not controller.sampling_enabled
        assert provider.calls == EXPECTED_PROVIDER_CALLS
    finally:
        controller.close()


def test_runtime_exception_is_sanitized_and_disables_only_gestures(
    application: QApplication,
) -> None:
    provider = SequenceProvider((HandLandmarkStatus.OK,) * 3)
    runtime = FailingRuntime()
    controller = _gesture_controller(provider, runtime=runtime)
    try:
        for expected_failures in (1, 2):
            _submit(controller, application)
            assert controller.sampling_enabled
            assert controller._consecutive_failures == expected_failures
        _submit(controller, application)
        assert controller.health.status is GestureControllerStatus.INFERENCE_FAILED
        assert controller.health.detail_code == "runtime-invalid"
        assert SENSITIVE_PATH not in controller.health.detail_code
        assert not controller.sampling_enabled
        assert runtime.calls == EXPECTED_PROVIDER_CALLS
    finally:
        controller.close()


def test_successful_runtime_update_resets_the_consecutive_failure_streak(
    application: QApplication,
) -> None:
    provider = SequenceProvider((HandLandmarkStatus.OK,) * 5)
    runtime = SequencedRuntime((True, False, True, True, True))
    controller = _gesture_controller(provider, runtime=runtime)
    try:
        _submit(controller, application)
        assert controller._consecutive_failures == 1

        _submit(controller, application)
        assert controller._consecutive_failures == 0
        assert controller.sampling_enabled

        for expected_failures in (1, 2):
            _submit(controller, application)
            assert controller._consecutive_failures == expected_failures
            assert controller.sampling_enabled

        _submit(controller, application)
        assert controller.health.status is GestureControllerStatus.INFERENCE_FAILED
        assert controller.health.detail_code == "runtime-invalid"
        assert not controller.sampling_enabled
        assert runtime.calls == EXPECTED_RUNTIME_CALLS
    finally:
        controller.close()


def test_dispatcher_exception_fails_one_action_without_disabling_gestures(
    application: QApplication,
) -> None:
    provider = SequenceProvider((HandLandmarkStatus.OK,))
    dispatcher = FailingDispatcher()
    controller = _gesture_controller(
        provider,
        runtime=DecisionRuntime(),
        dispatcher=dispatcher,
    )
    results: list[GestureDispatchResult] = []
    controller.dispatch_completed.connect(results.append)
    try:
        _submit(controller, application)
        assert controller.sampling_enabled
        assert controller.health.status is GestureControllerStatus.READY
        assert dispatcher.calls == 1
        assert len(results) == 1
        assert results[0].disposition is GestureDispatchDisposition.FAILED
        assert results[0].reason_code == "dispatch-boundary-failed"
        assert SENSITIVE_PATH not in results[0].reason_code
    finally:
        controller.close()


def test_camera_off_keeps_gesture_and_vision_inactive() -> None:
    gesture = GestureController(
        PassiveDispatcher(),
        provider_factory=lambda: SequenceProvider((HandLandmarkStatus.OK,)),
    )
    vision = VisionController(FaceIdentityStore(MemorySecretStore()))
    try:
        gesture_health = gesture.configure(
            GestureConfiguration(enabled=True),
            camera_available=False,
        )
        vision_health = vision.configure(enabled=True, camera_available=False)
        gesture.submit_frame(FRAME, 1, 1)
        vision.submit_frame(FRAME, 1, 1)
        assert gesture_health.status is GestureControllerStatus.CAMERA_UNAVAILABLE
        assert not gesture.sampling_enabled
        assert vision_health.readiness is VisionReadiness.CAMERA_UNAVAILABLE
        assert not vision_health.ready
        assert not vision._enabled
        assert not vision._busy
    finally:
        gesture.close()
        vision.close()


class SensitiveVisionFailure(Exception):
    pass


def test_vision_controller_failure_disables_only_vision(
    application: QApplication,
) -> None:
    controller = VisionController(FaceIdentityStore(MemorySecretStore()))
    controller._enabled = True
    health_events: list[VisionHealth] = []
    controller.health_changed.connect(health_events.append)

    def fail_provider_creation() -> object:
        raise SensitiveVisionFailure(SENSITIVE_PATH)

    controller._create_provider = fail_provider_creation  # type: ignore[method-assign]
    try:
        controller.submit_frame(FRAME, 1, 1)
        application.processEvents()
        assert not controller._enabled
        assert not controller._busy
        assert len(health_events) == 1
        assert health_events[0].readiness is VisionReadiness.RUNTIME_ERROR
        assert health_events[0].detail == "SensitiveVisionFailure"
        assert SENSITIVE_PATH not in health_events[0].detail
    finally:
        controller.close()


class AuditRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def audit_event(self, event_type: str, payload: object) -> None:
        self.events.append((event_type, payload))


class FailureStatusSurface:
    _gesture_health_changed = FlagshipControlCenter._gesture_health_changed
    _gesture_dispatch_completed = FlagshipControlCenter._gesture_dispatch_completed
    _vision_health_changed = FlagshipControlCenter._vision_health_changed

    def __init__(self, language: str) -> None:
        self._translator = FlagshipTranslator(language)
        self.language = self._translator.language
        self._closed = False
        self.db = AuditRecorder()
        self.gesture_record_status = QLabel("__gesture_status_unchanged__")
        self.gesture_record_button = QPushButton()
        self.camera_status = QLabel("__vision_status_unchanged__")

    def _t(self, source: str, /, **values: object) -> str:
        return self._translator.text(source, **values)

    def _selected_gesture(self) -> None:
        return None


@pytest.mark.parametrize("language", ("zh-TW", "zh-CN", "en", "ja-JP"))
def test_failure_states_are_visible_in_four_languages_without_sensitive_paths(
    language: str,
) -> None:
    surface = FailureStatusSurface(language)
    translator = FlagshipTranslator(language)
    gesture_states = (
        (
            GestureControllerHealth(
                GestureControllerStatus.CAMERA_UNAVAILABLE,
                SENSITIVE_PATH,
            ),
            "攝影機尚未就緒，手勢互動保持停用。",
        ),
        (
            GestureControllerHealth(
                GestureControllerStatus.MODEL_MISSING,
                SENSITIVE_PATH,
            ),
            "手部模型缺失，手勢互動保持停用。",
        ),
        (
            GestureControllerHealth(
                GestureControllerStatus.MODEL_LOAD_FAILED,
                SENSITIVE_PATH,
            ),
            "手部模型無法載入，手勢互動保持停用。",
        ),
        (
            GestureControllerHealth(
                GestureControllerStatus.INFERENCE_FAILED,
                SENSITIVE_PATH,
            ),
            "手勢辨識連續失敗，已安全停用。",
        ),
    )
    for health, source in gesture_states:
        surface._gesture_health_changed(health)
        rendered = surface.gesture_record_status.text()
        assert rendered == translator.text(source)
        assert SENSITIVE_PATH not in rendered

    surface._gesture_dispatch_completed(
        GestureDispatchResult(
            GestureDispatchDisposition.FAILED,
            GestureAction.SHOW_DASHBOARD,
            "dispatch-boundary-failed",
        )
    )
    dispatch_text = surface.gesture_record_status.text()
    assert dispatch_text == translator.text("手勢動作執行失敗，未變更其他功能。")
    assert SENSITIVE_PATH not in dispatch_text

    expected_vision_texts = {
        "zh-TW": {
            VisionReadiness.READY: "靈視環境已就緒",
            VisionReadiness.DISABLED: "本機視覺感知已停用。",
            VisionReadiness.CAMERA_UNAVAILABLE: (
                "攝影機尚未就緒，本機視覺感知保持停用。"
            ),
            VisionReadiness.ENGINE_UNAVAILABLE: (
                "本機視覺引擎無法使用，視覺感知保持停用。"
            ),
            VisionReadiness.MODEL_MISSING: (
                "本機視覺模型缺失，視覺感知保持停用。"
            ),
            VisionReadiness.MODEL_UNTRUSTED: (
                "本機視覺模型未通過完整性驗證，視覺感知保持停用。"
            ),
            VisionReadiness.RUNTIME_ERROR: (
                "本機視覺分析失敗，已安全停用；其他功能不受影響。"
            ),
        },
        "zh-CN": {
            VisionReadiness.READY: "灵视环境已就绪",
            VisionReadiness.DISABLED: "本地视觉感知已停用。",
            VisionReadiness.CAMERA_UNAVAILABLE: (
                "摄像头尚未就绪，本地视觉感知保持停用。"
            ),
            VisionReadiness.ENGINE_UNAVAILABLE: (
                "本地视觉引擎不可用，视觉感知保持停用。"
            ),
            VisionReadiness.MODEL_MISSING: (
                "本地视觉模型缺失，视觉感知保持停用。"
            ),
            VisionReadiness.MODEL_UNTRUSTED: (
                "本地视觉模型未通过完整性验证，视觉感知保持停用。"
            ),
            VisionReadiness.RUNTIME_ERROR: (
                "本地视觉分析失败，已安全停用；其他功能不受影响。"
            ),
        },
        "en": {
            VisionReadiness.READY: "Vision is ready",
            VisionReadiness.DISABLED: "Local visual perception is disabled.",
            VisionReadiness.CAMERA_UNAVAILABLE: (
                "The camera is not ready, so local visual perception remains disabled."
            ),
            VisionReadiness.ENGINE_UNAVAILABLE: (
                "The local vision engine is unavailable, so visual perception "
                "remains disabled."
            ),
            VisionReadiness.MODEL_MISSING: (
                "Local vision models are missing, so visual perception remains "
                "disabled."
            ),
            VisionReadiness.MODEL_UNTRUSTED: (
                "Local vision models failed integrity verification, so visual "
                "perception remains disabled."
            ),
            VisionReadiness.RUNTIME_ERROR: (
                "Local vision analysis failed and was safely disabled; other "
                "features are unaffected."
            ),
        },
        "ja-JP": {
            VisionReadiness.READY: "視覚認識の準備ができました",
            VisionReadiness.DISABLED: "ローカル視覚認識は無効です。",
            VisionReadiness.CAMERA_UNAVAILABLE: (
                "カメラの準備ができていないため、ローカル視覚認識は無効のままです。"
            ),
            VisionReadiness.ENGINE_UNAVAILABLE: (
                "ローカル視覚エンジンを利用できないため、視覚認識は無効のままです。"
            ),
            VisionReadiness.MODEL_MISSING: (
                "ローカル視覚モデルがないため、視覚認識は無効のままです。"
            ),
            VisionReadiness.MODEL_UNTRUSTED: (
                "ローカル視覚モデルが整合性検証に合格しなかったため、"
                "視覚認識は無効のままです。"
            ),
            VisionReadiness.RUNTIME_ERROR: (
                "ローカル視覚解析に失敗したため安全に無効化しました。"
                "その他の機能には影響しません。"
            ),
        },
    }[language]
    for readiness, expected_text in expected_vision_texts.items():
        surface.camera_status.setText("__vision_status_unchanged__")
        surface._vision_health_changed(VisionHealth(readiness, SENSITIVE_PATH))
        vision_text = surface.camera_status.text()
        assert vision_text == expected_text
        assert SENSITIVE_PATH not in vision_text
        assert "private-owner" not in vision_text


def _dashboard_dependencies(root: Path) -> DashboardDependencies:
    secret = MemorySecretStore()
    unavailable = lambda *_args, **_kwargs: None
    return DashboardDependencies(
        listener=OfflineListener(),
        secret_store=secret,
        azure_secret_store=secret,
        azure_hd_secret_store=secret,
        secret_store_factory=lambda *_args: MemorySecretStore(),
        platform_services=OfflinePlatformServices(root),
        presentation_ports=PresentationPorts(
            ai_worker_factory=unavailable,
            voice_catalog=OfflineVoiceCatalog(),
            profile_manager_factory=unavailable,
            update_manager_factory=unavailable,
            portable_secret_binder=unavailable,
            autostart_configurator=unavailable,
            validate_face_assets=lambda _path: (),
            face_renderer_factory=unavailable,
            visible_windows=list,
        ),
    )


def _assert_dashboard_services_remain_available(
    dashboard: Dashboard,
    label: str,
) -> None:
    application = QApplication.instance()
    assert application is not None
    center = dashboard.flagship_center
    voice_events: list[str] = []
    realtime_events: list[bool] = []
    dashboard.voice_preview_requested.connect(lambda: voice_events.append(label))
    dashboard.realtime_toggle_requested.connect(realtime_events.append)
    dashboard.voice_preview_button.click()
    dashboard.realtime_btn.blockSignals(True)
    dashboard.realtime_btn.setChecked(False)
    dashboard.realtime_btn.blockSignals(False)
    dashboard.realtime_btn.click()
    application.processEvents()
    assert voice_events == [label]
    assert realtime_events[-1:] == [True]
    assert dashboard.isEnabled()
    assert dashboard.voice_preview_button.isEnabled()
    assert dashboard.realtime_btn.isEnabled()
    assert dashboard.save_settings_button.isEnabled()
    next_value = not center.companion_enabled.isChecked()
    center.companion_enabled.setChecked(next_value)
    assert center.save_draft_settings()
    assert bool(center.db.setting("proactive_interaction_enabled")) is next_value
    assert not center._closed


def test_each_optional_failure_leaves_dashboard_voice_realtime_and_settings_alive(
    tmp_path: Path,
) -> None:
    application = QApplication.instance()
    assert application is not None
    db = StudioDB(tmp_path / "failure-isolation.db")
    db.set_setting("onboarding_complete", True)
    with patch.object(QTimer, "start", return_value=None):
        dashboard = Dashboard(db, _dashboard_dependencies(tmp_path))
    dashboard.show()
    application.processEvents()
    center = dashboard.flagship_center
    events: tuple[tuple[str, Callable[[], None]], ...] = (
        (
            "model-missing",
            lambda: center._gesture_health_changed(
                GestureControllerHealth(GestureControllerStatus.MODEL_MISSING)
            ),
        ),
        (
            "model-load-failed",
            lambda: center._gesture_health_changed(
                GestureControllerHealth(GestureControllerStatus.MODEL_LOAD_FAILED)
            ),
        ),
        (
            "three-inference-failures",
            lambda: center._gesture_health_changed(
                GestureControllerHealth(GestureControllerStatus.INFERENCE_FAILED)
            ),
        ),
        (
            "runtime-exception",
            lambda: center._gesture_health_changed(
                GestureControllerHealth(
                    GestureControllerStatus.INFERENCE_FAILED,
                    "runtime-invalid",
                )
            ),
        ),
        (
            "dispatcher-exception",
            lambda: center._gesture_dispatch_completed(
                GestureDispatchResult(
                    GestureDispatchDisposition.FAILED,
                    GestureAction.SHOW_DASHBOARD,
                    "dispatch-boundary-failed",
                )
            ),
        ),
        (
            "camera-off",
            lambda: (
                center._gesture_health_changed(
                    GestureControllerHealth(GestureControllerStatus.CAMERA_UNAVAILABLE)
                ),
                center._vision_health_changed(
                    VisionHealth(VisionReadiness.CAMERA_UNAVAILABLE)
                ),
            ),
        ),
        (
            "vision-controller-failure",
            lambda: center._vision_health_changed(
                VisionHealth(VisionReadiness.RUNTIME_ERROR, SENSITIVE_PATH)
            ),
        ),
    )
    try:
        for label, emit_failure in events:
            emit_failure()
            _assert_dashboard_services_remain_available(dashboard, label)
        center.close_services()
        center.close_services()
        assert center._closed
    finally:
        center.close_services()
        dashboard.close()
        dashboard.deleteLater()
        application.processEvents()
        db.close()


def test_optional_controllers_do_not_import_unrelated_application_features() -> None:
    forbidden_roots = {
        "app",
        "db",
        "flagship_ui",
        "realtime_voice",
        "speech",
    }
    for filename in ("gesture_controller.py", "vision_controller.py"):
        tree = ast.parse((PROJECT_ROOT / filename).read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        assert not roots & forbidden_roots, (filename, roots & forbidden_roots)
