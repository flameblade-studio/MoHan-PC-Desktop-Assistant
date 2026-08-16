from __future__ import annotations

lazy import sys
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from typing import Any

lazy from PySide6.QtCore import Signal
lazy from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

lazy from application.cloud_vision_ui_bridge import CloudVisionServiceFactoryPort
lazy from application.companion_phrasebook import (
    PHRASEBOOK_SETTING,
    CompanionPhrasebook,
)
lazy from application.gesture_controller import GestureController
lazy from domain.contracts import SecretStoreFactoryPort
lazy from domain.flagship_safe_intent import FlagshipSafeIntentService
lazy from domain.time_utils import local_aware_time
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStore,
)
lazy from infrastructure.db import StudioDBSettingsPort
lazy from infrastructure.gesture_configuration_store import GestureConfigurationStore
lazy from infrastructure.gesture_template_store import ProtectedGestureTemplateStore
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
)
lazy from infrastructure.platform_contracts import PlatformServicePort
lazy from presentation.flagship.audit import FlagshipAuditMixin
lazy from presentation.flagship.cloud import FlagshipCloudMixin
lazy from presentation.flagship.companion import FlagshipCompanionMixin
lazy from presentation.flagship.gesture_editor import FlagshipGestureEditorMixin
lazy from presentation.flagship.home import FlagshipHomeMixin
lazy from presentation.flagship.lifecycle import FlagshipLifecycleMixin
lazy from presentation.flagship.overview import FlagshipOverviewMixin
lazy from presentation.flagship.planner import FlagshipPlannerMixin
lazy from presentation.flagship.remote import FlagshipRemoteMixin
lazy from presentation.flagship.runtime import FlagshipRuntimeMixin
lazy from presentation.flagship.settings_security import (
    FlagshipSettingsSecurityMixin,
)
lazy from presentation.flagship.shared import (
    GestureRecorderPort,
    UnavailableGestureRecorder,
)
lazy from presentation.flagship.ui_helpers import FlagshipUiHelpersMixin
lazy from presentation.flagship.vision import FlagshipVisionMixin
lazy from presentation.flagship.workflows import FlagshipWorkflowMixin
lazy from presentation.flagship_theme import (
    apply_flagship_theme,
    create_flagship_ornament,
)
lazy from presentation.flagship_ui_localization import FlagshipTranslator

__all__ = ("FlagshipControlCenter",)


class FlagshipControlCenter(
    FlagshipRuntimeMixin,
    FlagshipPlannerMixin,
    FlagshipCloudMixin,
    FlagshipHomeMixin,
    FlagshipRemoteMixin,
    FlagshipCompanionMixin,
    FlagshipGestureEditorMixin,
    FlagshipVisionMixin,
    FlagshipSettingsSecurityMixin,
    FlagshipUiHelpersMixin,
    FlagshipOverviewMixin,
    FlagshipWorkflowMixin,
    FlagshipAuditMixin,
    FlagshipLifecycleMixin,
    QWidget,
):
    speak_requested = Signal(str, str)
    remote_command_received = Signal(str)
    emergency_stop_requested = Signal()
    visual_scene_changed = Signal(object)
    visual_observation_changed = Signal(object)
    multimodal_result_changed = Signal(object)
    openai_vision_authorization_changed = Signal(object)
    openai_vision_stop_requested = Signal()

    def __init__(  # noqa: PLR0913 -- stable API keeps dependencies explicit
        self,
        db,
        data_path: Path,
        parent=None,
        *,
        platform_services: PlatformServicePort | None = None,
        secret_store_factory: SecretStoreFactoryPort | None = None,
        proactivity_store: CompanionProactivityPreferencesStore | None = None,
        openai_vision_store: OpenAIVisionPreferencesStore | None = None,
        gesture_store: GestureConfigurationStore | None = None,
        gesture_recorder: GestureRecorderPort | None = None,
        gesture_controller: GestureController | None = None,
        openai_vision_key_available: Callable[[], bool] | None = None,
        cloud_vision_service_factory: CloudVisionServiceFactoryPort | None = None,
        dense_face_provider_factory: Callable[[], object] | None = None,
        language: str = "zh-TW",
    ):
        """Build the center with an explicit, backward-compatible language."""
        super().__init__(parent)
        self._translator = _active_translator_factory()(language)
        self.language = self._translator.language
        self._safe_intents = FlagshipSafeIntentService(
            translate=self._t,
            clock=local_aware_time,
        )
        self._initialize_services(
            db,
            data_path,
            platform_services,
            secret_store_factory,
        )
        self.proactivity_store = proactivity_store or (
            CompanionProactivityPreferencesStore(StudioDBSettingsPort(db))
        )
        self._proactivity_draft = self.proactivity_store.begin_edit()
        self.gesture_store = gesture_store or GestureConfigurationStore(
            StudioDBSettingsPort(db),
            ProtectedGestureTemplateStore(self.gesture_template_secret),
        )
        self._gesture_draft = self.gesture_store.begin_edit()
        self._gesture_controller = gesture_controller
        self._gesture_recorder = (
            gesture_recorder
            or gesture_controller
            or UnavailableGestureRecorder()
        )
        self.openai_vision_store = openai_vision_store or (
            OpenAIVisionPreferencesStore(StudioDBSettingsPort(db))
        )
        self._openai_vision_draft = self.openai_vision_store.begin_edit()
        self._openai_vision_key_probe = openai_vision_key_available
        self._cloud_vision_service_factory = cloud_vision_service_factory
        self._dense_face_provider_factory = dense_face_provider_factory
        self._phrasebook_draft = CompanionPhrasebook.from_setting(
            self.db.setting(PHRASEBOOK_SETTING, {})
        )
        self._initialize_runtime_state()
        self._build_control_center_ui()
        self._initialize_cloud_vision_service()
        self._start_control_center_timers()
        self.camera_restore_timer.start(0)

    def _t(self, source: str, /, **values: Any) -> str:
        return self._translator.text(source, **values)

    def _system_text(self, message: str) -> str:
        return self._translator.system_message(message)

    def _build_control_center_ui(self) -> None:
        root = QVBoxLayout(self)
        ornament_row = QHBoxLayout()
        ornament_row.addStretch(1)
        ornament_row.addWidget(create_flagship_ornament(self, size=72))
        root.addLayout(ornament_row)
        emergency = QPushButton(self._t("緊急停止所有工具與遠端操作（Esc）"))
        emergency.setStyleSheet(
            "QPushButton{background:#772f3a;color:white;font-weight:bold;"
            "padding:10px;border-radius:8px;}"
        )
        emergency.clicked.connect(self.emergency_stop)
        root.addWidget(emergency)
        self.tabs = QTabWidget()
        for page, label in (
            (self._overview_tab(), "任務中心"),
            (self._workflow_tab(), "工作流程"),
            (self._cloud_tab(), "雲端連接器"),
            (self._home_tab(), "智慧家庭"),
            (self._remote_tab(), "遠端與隱私"),
            (self._companion_tab(), "陪伴與關心"),
            (self._security_tab(), "安全權限"),
            (self._audit_tab(), "稽核紀錄"),
        ):
            self.tabs.addTab(page, self._t(label))
        root.addWidget(self.tabs, 1)
        apply_flagship_theme(
            self,
            high_contrast=bool(
                self.db.setting("flagship_high_contrast", False)
            ),
            scale=float(self.db.setting("flagship_ui_scale", 1.0)),
        )


def _active_translator_factory() -> Callable[[str], object]:
    """Honor the legacy module's patch point without depending on that module."""
    compatibility = sys.modules.get("flagship_ui")
    return getattr(compatibility, "FlagshipTranslator", FlagshipTranslator)
