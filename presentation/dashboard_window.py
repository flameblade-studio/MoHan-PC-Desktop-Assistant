from __future__ import annotations

lazy from PySide6.QtCore import Signal
lazy from PySide6.QtWidgets import QDialog, QLayout, QVBoxLayout

lazy from application.gesture_controller import GestureController
lazy from application.presentation_ports import PresentationDatabasePort
lazy from application.theme_pack_service import ThemePackService
lazy from domain.theme_pack import ThemePack, build_stylesheet
lazy from domain.theme_session import ThemeResolution, ThemeSession
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_conversation import DashboardConversationMixin
lazy from presentation.dashboard_platforms import DashboardPlatformMixin
lazy from presentation.dashboard_settings import DashboardSettingsMixin
lazy from presentation.dashboard_shell import DashboardShellMixin
lazy from presentation.dashboard_today_memory import DashboardTodayMemoryMixin
lazy from presentation.dashboard_voice import DashboardVoiceMixin
lazy from presentation.dashboard_wardrobe_preferences import (
    DashboardWardrobePreferencesMixin,
)
lazy from presentation.flagship_theme import apply_flagship_theme

__all__ = ("Dashboard",)


class Dashboard(
    DashboardWardrobePreferencesMixin,
    DashboardShellMixin,
    DashboardSettingsMixin,
    DashboardVoiceMixin,
    DashboardConversationMixin,
    DashboardTodayMemoryMixin,
    DashboardPlatformMixin,
    QDialog,
):
    speak_requested = Signal(str, str)
    voice_preview_requested = Signal()
    realtime_toggle_requested = Signal(bool)
    realtime_voice_changed = Signal(str)
    realtime_output_mode_changed = Signal(str)
    realtime_output_settings_changed = Signal()
    state_requested = Signal(str)
    ai_wait_expression_requested = Signal(int, str, float)
    ai_wait_expression_finished = Signal(int)
    work_changed = Signal()
    settings_saved = Signal()
    volume_changed = Signal(int, bool)
    visibility_changed = Signal(bool)
    topmost_mode_changed = Signal(str)
    character_scale_preview = Signal(int)
    visual_observation_changed = Signal(object)
    visual_scene_changed = Signal(object)
    multimodal_result_changed = Signal(object)
    human_interaction = Signal()
    outfit_generation_requested = Signal()

    def __init__(
        self,
        db: PresentationDatabasePort,
        dependencies: DashboardDependencies,
        parent=None,
        *,
        gesture_controller: GestureController | None = None,
    ):
        super().__init__(parent)
        self.gesture_controller = gesture_controller
        self._initialize_dashboard_state(db, dependencies)
        self._initialize_theme_support()
        self._settings_draft_snapshot = self.db.settings_snapshot()
        self._configure_dashboard_window()
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SetNoConstraint)
        start_button, stop_button = self._build_dashboard_header(root)
        self._mount_dashboard_tabs(root)
        self._mount_global_settings_actions(root)
        self._connect_dashboard_signals(
            start_button,
            stop_button,
        )
        self._start_dashboard_timer()
        self.refresh_all()
        self._disable_implicit_default_buttons()
        self._apply_profile_texts()
        apply_flagship_theme(
            self,
            high_contrast=bool(
                self.db.setting("flagship_high_contrast", False)
            ),
            scale=float(self.db.setting("flagship_ui_scale", 1.0)),
        )
        self._apply_theme_resolution(self.theme_session.last_resolution)
        self._enforce_readable_combo_popups()
        self.apply_chat_zoom(self.chat_zoom_percent, persist=False)

    def _initialize_theme_support(self) -> None:
        self.theme_pack_service = ThemePackService(
            self.db.path.parent / "themes"
        )
        persisted = str(self.db.setting("active_theme_id", "builtin"))
        self.theme_session = ThemeSession(
            persisted,
            resolve=self.theme_pack_service.resolve,
            preview=self._apply_theme_resolution,
            commit=self._commit_theme,
        )

    def _commit_theme(self, theme_id: str) -> None:
        self.theme_pack_service.activate(theme_id)
        self.db.set_setting("active_theme_id", theme_id)

    def _apply_theme_resolution(self, resolution: ThemeResolution) -> None:
        apply_flagship_theme(
            self,
            high_contrast=bool(
                self.db.setting("flagship_high_contrast", False)
            ),
            scale=float(self.db.setting("flagship_ui_scale", 1.0)),
        )
        if resolution.resolved_id == "builtin":
            self._enforce_readable_combo_popups()
            if hasattr(self, "chat"):
                self.apply_chat_zoom(self.chat_zoom_percent, persist=False)
            return
        theme = resolution.payload
        if not isinstance(theme, ThemePack):
            raise TypeError("Resolved theme payload must be a theme pack.")
        stylesheet = self.styleSheet() + build_stylesheet(theme)
        background = self.theme_pack_service.background_path(theme.theme_id)
        if background is not None:
            normalized = background.as_posix().replace("'", "\\'")
            stylesheet += (
                "QWidget[mohanFlagshipTheme='true']{"
                f"border-image:url('{normalized}') 0 0 0 0 stretch stretch;"
                "}"
            )
        self.setStyleSheet(stylesheet)
        self._enforce_readable_combo_popups()
        if hasattr(self, "chat"):
            self.apply_chat_zoom(self.chat_zoom_percent, persist=False)

    def closeEvent(self, event) -> None:
        """Stop dashboard-owned callbacks before its database can be closed."""

        timer = getattr(self, "timer", None)
        if timer is not None:
            timer.stop()
        front_raise_timer = getattr(self, "front_raise_timer", None)
        if front_raise_timer is not None:
            front_raise_timer.stop()
        super().closeEvent(event)
