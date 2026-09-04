from __future__ import annotations

"""Canonical composition owner for the MoHan companion window."""

lazy from PySide6.QtWidgets import QMainWindow

lazy from application.adaptive_character_composition import AdaptiveCharacterFactory
lazy from application.self_generating_wardrobe import FashionTrendScoutFactory
lazy from presentation.autonomous_outfit_generation_controller import (
    AutonomousOutfitGenerationController,
)
lazy from application.gesture_action_dispatcher import GestureActionDispatcher
lazy from application.gesture_controller import GestureController
lazy from application.presentation_ports import default_data_dir
lazy from application.service_container import (
    CompanionServices,
    create_default_services,
)
lazy from presentation.companion_core import CompanionCoreMixin
lazy from presentation.companion_face_animation import CompanionFaceAnimationMixin
lazy from presentation.companion_platform import CompanionPlatformMixin
lazy from presentation.companion_proactive import (
    CompanionProactiveMixin,
    ProactiveCompanionFactory,
)
lazy from presentation.companion_speech_runtime import CompanionSpeechRuntimeMixin
lazy from presentation.companion_visual_dynamics import CompanionVisualDynamicsMixin
lazy from presentation.lingxiao_fonts import register_bundled_fonts
lazy from presentation.presentation_resources import resource_path

__all__ = ("CompanionWindow",)


class CompanionWindow(
    CompanionCoreMixin,
    CompanionProactiveMixin,
    CompanionVisualDynamicsMixin,
    CompanionFaceAnimationMixin,
    CompanionSpeechRuntimeMixin,
    CompanionPlatformMixin,
    QMainWindow,
):
    """Compose the companion's independent behavior owners."""

    # These are independent injected composition boundaries, not one coupled
    # parameter bundle; keeping them named makes isolated regression tests clear.
    def __init__(
        self,
        startup_speech: bool = True,
        services: CompanionServices | None = None,
        defer_visual_startup: bool = False,
        *,
        adaptive_character_factory: AdaptiveCharacterFactory | None = None,
        adaptive_character_enabled: bool | None = None,
        proactive_companion_factory: ProactiveCompanionFactory | None = None,
        fashion_trend_scout_factory: FashionTrendScoutFactory | None = None,
    ):
        super().__init__()
        register_bundled_fonts()
        runtime_services = services or create_default_services(
            default_data_dir(),
            resource_path("voice_listener.ps1"),
            self,
        )
        self._initialize_runtime_services(runtime_services)
        self._run_first_run_wizard_if_needed(startup_speech)
        self._gesture_application = self._create_gesture_application()
        self._gesture_controller = GestureController(
            GestureActionDispatcher(
                self._gesture_application,
                authorize=self._authorize_gesture_action,
            )
        )
        self._gesture_controller.recognition_changed.connect(
            self._on_gesture_recognition
        )
        self.dashboard = self._create_dashboard(self._gesture_controller)
        self._autonomous_outfit_generation = AutonomousOutfitGenerationController(
            db=self.db,
            secret_store=self.secret_store,
            project_root=resource_path("."),
            trend_scout_factory=fashion_trend_scout_factory,
            parent=self,
        )
        self.dashboard.outfit_generation_requested.connect(
            lambda: self._autonomous_outfit_generation.request_generation(
                explicit=True
            )
        )
        self._autonomous_outfit_generation.status_changed.connect(
            self.dashboard.set_outfit_generation_status
        )
        # 緊急停止原本只發訊號、沒有任何接收者：換裝批次跑在另一個執行緒池，
        # 使用者按下停手之後剩餘視角仍會逐張呼叫付費 API，而介面已經宣告
        # 「所有工具與遠端連線均已中止」。這條接線是那句話成立的前提。
        # flagship_center 由 dashboard 的設定分頁建立，未必存在，故防禦性取用。
        flagship_center = getattr(self.dashboard, "flagship_center", None)
        if flagship_center is not None:
            flagship_center.emergency_stop_requested.connect(
                self._autonomous_outfit_generation.abort
            )
        self._autonomous_outfit_generation.start()
        self._connect_dashboard_signals()
        self._connect_speech_service_signals()
        self._initialize_companion_state(startup_speech)
        self._initialize_proactive_companion_app_bridge(
            proactive_companion_factory
        )
        self._configure_character_window()
        self._initialize_motion_state()
        self._build_ui(defer_visual_assets=defer_visual_startup)
        self._initialize_adaptive_character_composition(
            adaptive_character_factory,
            adaptive_character_enabled,
        )
        self._reload_background_agents()
        self._apply_character_scale(
            self.character_scale_percent,
            preserve_anchor=False,
        )
        self._position_corner()
        if not defer_visual_startup:
            self._finish_visual_startup()
