from __future__ import annotations

lazy import queue
lazy from pathlib import Path
lazy from typing import Any

lazy from PySide6.QtCore import QThreadPool, QTimer
lazy from PySide6.QtWidgets import QApplication, QComboBox

lazy from application.camera_presence import CameraPresenceController
lazy from application.cloud_vision_ui_bridge import (
    CloudVisionServicePort,
    StoredVisionAuthorizationSource,
)
lazy from application.flagship_action_runtime import ActionExecutor
lazy from application.multimodal_controller import MultimodalController
lazy from application.multimodal_fusion_hub import FaceMeshFrame
lazy from application.vision_controller import VisionController
lazy from domain.air_interaction import AirHandSample
lazy from domain.cloud_scene_interpreter import CloudSceneInterpreter
lazy from domain.contracts import SecretStoreFactoryPort
lazy from domain.flagship_action_models import ActionRequest, ActionResult
lazy from domain.flagship_action_policy import PolicyEngine
lazy from domain.vision_domain import SceneUnderstanding
lazy from infrastructure.face_identity_store import FaceIdentityStore
lazy from infrastructure.flagship_windows_toolbox import WindowsToolbox
lazy from infrastructure.platform_contracts import PlatformServicePort
lazy from infrastructure.platform_services import current_platform_services
lazy from infrastructure.secret_store import platform_secret_store_factory
lazy from infrastructure.windows_tools import WindowTools
lazy from integrations.ai_client import ActionPlannerWorker
lazy from integrations.remote_control import RemoteControlServer
lazy from presentation.flagship.cloud_health import CloudHealthWorker

__all__ = ("FlagshipRuntimeMixin",)


class FlagshipRuntimeMixin:
    def _initialize_services(
        self,
        db,
        data_path: Path,
        platform_services: PlatformServicePort | None,
        secret_store_factory: SecretStoreFactoryPort | None,
    ) -> None:
        self.db = db
        self.data_path = data_path
        self.platform_services = platform_services or current_platform_services()
        self.secret_store_factory = (
            secret_store_factory
            or platform_secret_store_factory(self.platform_services)
        )
        self.ha_secret = self.secret_store_factory(
            data_path / "home-assistant-token.dpapi",
            "MoHan Home Assistant token",
        )
        self.openai_secret = self.secret_store_factory(
            data_path / "openai-key.dpapi",
            "MoHan OpenAI API key",
        )
        self.face_identity_secret = self.secret_store_factory(
            data_path / "face-identities.dpapi",
            "MoHan local face identity templates",
        )
        self.gesture_template_secret = self.secret_store_factory(
            data_path / "gesture-templates.dpapi",
            "MoHan local gesture skeleton templates",
        )

    def _initialize_runtime_state(self) -> None:
        # 工作執行緒限制為三個，避免背景 AI 與雲端工作阻塞桌面互動。
        # Gmail 等連接器仍由個別工作項目管理逾時與錯誤。
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)
        self.planner_busy = False
        self._planner_worker: ActionPlannerWorker | None = None
        self._planner_generation = 0
        self.planner_timeout = QTimer(self)
        self.planner_timeout.setSingleShot(True)
        self.planner_timeout.setInterval(50_000)
        self.planner_timeout.timeout.connect(self._planner_timed_out)
        self._cloud_test_generation = 0
        self._cloud_scene_interpreter = CloudSceneInterpreter()
        self._latest_local_scene: SceneUnderstanding | None = None
        self._latest_local_scene_observed_at = 0.0
        self._latest_cloud_operation_id = -1
        self._cloud_test_worker: CloudHealthWorker | None = None
        self.cloud_test_timeout = QTimer(self)
        self.cloud_test_timeout.setSingleShot(True)
        self.cloud_test_timeout.setInterval(35_000)
        self.cloud_test_timeout.timeout.connect(self._cloud_test_timed_out)
        self.camera_restore_timer = QTimer(self)
        self.camera_restore_timer.setSingleShot(True)
        self.camera_restore_timer.timeout.connect(
            self._restore_camera_if_enabled
        )
        self.remote_server: RemoteControlServer | None = None
        self.camera_presence = CameraPresenceController(
            self,
            language=self.language,
        )
        self.camera_presence.visual_observation.connect(
            self.visual_observation_changed.emit
        )
        self.camera_presence.status_changed.connect(self._camera_status_changed)
        self.camera_presence.presence_changed.connect(self._presence_changed)
        self.face_identities = FaceIdentityStore(self.face_identity_secret)
        self.vision_controller = VisionController(
            self.face_identities,
            self,
            dense_provider_factory=self._dense_face_provider_factory,
        )
        self.multimodal_controller = MultimodalController(self)
        self._latest_multimodal_face: tuple[FaceMeshFrame, float] | None = None
        self._latest_multimodal_hands: tuple[
            tuple[AirHandSample, ...],
            float,
        ] | None = None
        self.camera_presence.vision_frame_ready.connect(
            self.vision_controller.submit_frame
        )
        self.vision_controller.face_mesh_changed.connect(
            self._multimodal_face_changed
        )
        self.vision_controller.face_mesh_health_changed.connect(
            self._face_mesh_health_changed
        )
        self.multimodal_controller.result_changed.connect(
            self.multimodal_result_changed.emit
        )
        self.camera_presence.vision_frame_ready.connect(
            self._submit_cloud_vision_event_frame
        )
        if self._gesture_controller is not None:
            self.camera_presence.gesture_frame_ready.connect(
                self._gesture_controller.submit_frame
            )
            self.vision_controller.lip_region_changed.connect(
                self._gesture_controller.set_lip_region
            )
            self._gesture_controller.health_changed.connect(
                self._gesture_health_changed
            )
            self._gesture_controller.hand_samples_changed.connect(
                self._multimodal_hands_changed
            )
            self._gesture_controller.dispatch_completed.connect(
                self._gesture_dispatch_completed
            )
        self.vision_controller.health_changed.connect(self._vision_health_changed)
        self.vision_controller.scene_changed.connect(self._vision_scene_changed)
        self.vision_controller.enrollment_progress.connect(
            self._enrollment_progress
        )
        self.vision_controller.enrollment_completed.connect(
            self._enrollment_completed
        )
        self.vision_controller.enrollment_failed.connect(self._enrollment_failed)
        self._screen_cache = b""
        self._closed = False
        self._remote_status_cache: dict[str, Any] = {
            "assistant": str(self.db.setting("assistant_name", "墨寒")),
            "status": "starting",
        }
        self._remote_commands: queue.Queue[tuple[str, str]] = queue.Queue()
        self._permission_controls: dict[str, QComboBox] = {}
        self._configure_executor()

    def _multimodal_face_changed(
        self,
        face: FaceMeshFrame,
        observed_at: float,
    ) -> None:
        self._latest_multimodal_face = (face, observed_at)
        self._submit_multimodal_observation(observed_at)

    def _multimodal_hands_changed(
        self,
        hands: tuple[AirHandSample, ...],
        observed_at: float,
    ) -> None:
        self._latest_multimodal_hands = (hands, observed_at)
        face_is_recent = (
            self._latest_multimodal_face is not None
            and abs(observed_at - self._latest_multimodal_face[1]) <= 0.75
        )
        if not face_is_recent:
            self._submit_multimodal_observation(observed_at)

    def _submit_multimodal_observation(self, observed_at: float) -> None:
        face = None
        if self._latest_multimodal_face is not None:
            candidate, candidate_time = self._latest_multimodal_face
            if abs(observed_at - candidate_time) <= 0.75:
                face = candidate
        hands: tuple[AirHandSample, ...] = ()
        if self._latest_multimodal_hands is not None:
            candidate_hands, candidate_time = self._latest_multimodal_hands
            if abs(observed_at - candidate_time) <= 0.75:
                hands = candidate_hands
        self.multimodal_controller.submit(
            hands=hands,
            face=face,
            language=self.language,
            observed_at=observed_at,
        )

    def _initialize_cloud_vision_service(self) -> None:
        self.cloud_vision_service: CloudVisionServicePort | None = None
        factory = self._cloud_vision_service_factory
        if factory is None:
            self._refresh_openai_vision_status(self.openai_vision_store.load())
            return
        try:
            service = factory(
                self.openai_secret,
                StoredVisionAuthorizationSource(self.openai_vision_store),
            )
            service.result_ready.connect(self._cloud_vision_result)
            service.busy_changed.connect(self._cloud_vision_busy_changed)
            self.cloud_vision_service = service
            authorization = service.refresh_authorization()
            self._refresh_openai_vision_status(authorization.preferences)
        except (OSError, RuntimeError, TypeError, ValueError):
            self.cloud_vision_service = None
            self.openai_vision_status.setText(
                self._t("● 雲端視覺服務目前無法使用")
            )

    def _start_control_center_timers(self) -> None:
        self.remote_poll = QTimer(self)
        self.remote_poll.timeout.connect(self._drain_remote_commands)
        self.remote_poll.start(250)
        self.screen_timer = QTimer(self)
        self.screen_timer.timeout.connect(self._refresh_screen_cache)
        self.screen_timer.start(2000)
        self.workflow_timer = QTimer(self)
        self.workflow_timer.timeout.connect(self.run_due_workflows)
        self.workflow_timer.start(30000)

    def _configure_executor(self) -> None:
        permissions = self.db.setting("flagship_permissions", {})
        protected = [
            str(Path.home() / ".ssh"),
            str(Path.home() / ".gnupg"),
            str(Path.home() / "AppData"),
        ]
        if self.platform_services.capabilities.platform_id in {
            "macos",
            "linux",
        }:
            protected.extend(
                str(path)
                for path in (
                    self.platform_services.paths.data,
                    self.platform_services.paths.config,
                    self.platform_services.paths.cache,
                )
            )
        self.policy = PolicyEngine(permissions, protected_paths=protected)
        self.executor = ActionExecutor(
            self.policy,
            confirm=self._confirm_action,
            audit=self.db.audit_event,
        )
        allowed_folders = [
            str(row["target_value"]) for row in self.db.allowed_targets("folder")
        ]
        allowed_apps = {
            str(row["display_name"]): str(row["target_value"])
            for row in self.db.allowed_targets("app")
        }
        allowed_websites = [
            str(row["target_value"]) for row in self.db.allowed_targets("web")
        ]
        self.toolbox = WindowsToolbox(
            allowed_folders=allowed_folders,
            allowed_apps=allowed_apps,
            allowed_websites=allowed_websites,
            platform_services=self.platform_services,
        )
        self.toolbox.register_with(self.executor)
        self.window_tools = WindowTools()
        self.window_tools.register_with(self.executor)
        self.executor.register("clipboard_read", self._clipboard_read)
        self.executor.register("clipboard_write", self._clipboard_write)
        self.executor.register("read_status", self._action_read_status)
        self._register_home_tools()
        self._register_cloud_tools()

    def _action_read_status(self, request: ActionRequest) -> ActionResult:
        return ActionResult(
            request.request_id,
            True,
            self._t("已整理目前工作狀態"),
            self._remote_status_payload(),
        )

    def _clipboard_read(self, request: ActionRequest) -> ActionResult:
        text = QApplication.clipboard().text()
        return ActionResult(
            request.request_id,
            True,
            self._t("已讀取剪貼簿文字"),
            {"text": text[:100000]},
        )

    def _clipboard_write(self, request: ActionRequest) -> ActionResult:
        text = str(request.arguments.get("text", ""))
        if len(text) > 100000:
            raise ValueError(self._t("剪貼簿文字不可超過 100,000 字"))
        QApplication.clipboard().setText(text)
        return ActionResult(
            request.request_id,
            True,
            self._t("已寫入剪貼簿"),
        )
