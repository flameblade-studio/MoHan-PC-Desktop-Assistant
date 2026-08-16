from __future__ import annotations

"""Canonical composition owner for the MoHan companion window."""

lazy from PySide6.QtWidgets import QMainWindow

lazy from application.adaptive_character_composition import AdaptiveCharacterFactory
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
    ):
        super().__init__()
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
        self.dashboard = self._create_dashboard(self._gesture_controller)
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
