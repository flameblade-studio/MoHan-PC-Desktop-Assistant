from __future__ import annotations

"""Visual composition and motion behavior for the companion window."""

lazy import contextlib
lazy import math
lazy import time
lazy from pathlib import Path

lazy from PySide6.QtCore import QPoint, QRect, Qt, QTimer
lazy from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPixmap
lazy from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

lazy from application.background_agents import (
    DiagnosticReportWorker,
    ManagerWorkerScheduler,
    VisibleAppWorker,
)
lazy from application.multisensory_interaction import MultisensoryInteractionArbiter
lazy from domain.app_profile import profile_setting, profile_window_title
lazy from domain.companion_animation_contract import (
    CHARACTER_BASE_Y,
    CHARACTER_CANVAS_WIDTH,
    CHARACTER_IMAGE_SIZE,
    ATTENTION_FRAME_INTERVAL_MS,
    CHARACTER_SCALE_DEFAULT,
    CHARACTER_SCALE_MAX,
    CHARACTER_SCALE_MIN,
    EXPRESSION_IMAGE_ASSETS,
    EXPRESSION_POSES,
    IDLE_FRAME_INTERVAL_MS,
    MOTION_FRAME_INTERVAL_MS,
    SPEECH_MOTION_RELEASE_LIMIT,
)
lazy from domain.face_motion import FaceMotionController
lazy from domain.lip_sync import VISEME_CHANGE_TRANSITION_SECONDS, VisemeDynamics
lazy from domain.time_utils import local_wall_time
lazy from presentation.companion_visual_physics import CompanionVisualPhysicsMethods
lazy from presentation.dashboard_dialogs import ClickableLabel
lazy from presentation.presentation_resources import application_icon, resource_path
lazy from presentation.ui_localization import ui_text

__all__ = ("CompanionVisualDynamicsMixin",)

MAX_BUBBLE_LENGTH = 230
GAZE_DISTANCE_THRESHOLD = 1050
MOTION_ZERO_THRESHOLD = 0.015


class CompanionVisualDynamicsMixin:
    """Own the companion window's visual construction and motion dynamics."""

    _build_physics_overlay_widgets = (
        CompanionVisualPhysicsMethods._build_physics_overlay_widgets
    )
    _initialize_physics_animation = (
        CompanionVisualPhysicsMethods._initialize_physics_animation
    )
    _physics_enabled = CompanionVisualPhysicsMethods._physics_enabled
    _reload_physics_settings = CompanionVisualPhysicsMethods._reload_physics_settings
    _apply_physics_visibility = CompanionVisualPhysicsMethods._apply_physics_visibility
    _build_physics_layers = CompanionVisualPhysicsMethods._build_physics_layers
    _reset_physics_dynamics = CompanionVisualPhysicsMethods._reset_physics_dynamics
    _ornament_anchors = staticmethod(CompanionVisualPhysicsMethods._ornament_anchors)
    _hair_anchors = staticmethod(CompanionVisualPhysicsMethods._hair_anchors)
    _sleeve_anchors = staticmethod(CompanionVisualPhysicsMethods._sleeve_anchors)
    _load_physics_sources = CompanionVisualPhysicsMethods._load_physics_sources
    _scaled_expression_asset = staticmethod(
        CompanionVisualPhysicsMethods._scaled_expression_asset
    )
    _physics_expression_pose_map = (
        CompanionVisualPhysicsMethods._physics_expression_pose_map
    )
    _register_expression_pose_frames = (
        CompanionVisualPhysicsMethods._register_expression_pose_frames
    )
    _hair_texture_only = staticmethod(CompanionVisualPhysicsMethods._hair_texture_only)
    _sleeve_texture_only = staticmethod(
        CompanionVisualPhysicsMethods._sleeve_texture_only
    )
    _update_physics_pose = CompanionVisualPhysicsMethods._update_physics_pose
    _physics_tick = CompanionVisualPhysicsMethods._physics_tick
    _render_sleeve_layers = CompanionVisualPhysicsMethods._render_sleeve_layers
    _render_hair_layers = CompanionVisualPhysicsMethods._render_hair_layers
    _render_physics_layer = CompanionVisualPhysicsMethods._render_physics_layer

    def _configure_character_window(self) -> None:
        self.setWindowTitle(profile_window_title(self.db))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # Keep every native MoHan window on the same icon contract. Windows
        # can use this hidden tool window while resolving the taskbar group.
        self.setWindowIcon(application_icon())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.character_topmost_active = True
        self.character_behind_hwnd = 0
        self._smart_overlap_hwnd = 0

    def _initialize_motion_state(self) -> None:
        self.character_base_x = 2
        self.character_base_y = CHARACTER_BASE_Y
        self.motion_base_x = 0
        self.motion_base_y = self.character_base_y
        self.ambient_motion_x = 0.0
        self.ambient_motion_y = 0.0
        self.ambient_motion_target_x = 0.0
        self.ambient_motion_target_y = 0.0
        self.speech_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self.last_composed_body_position: tuple[int, int] | None = None
        saved_scale = int(
            self.db.setting(
                "character_scale_percent",
                CHARACTER_SCALE_DEFAULT,
            )
        )
        self.character_scale_percent = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, saved_scale),
        )
        self.character_scale = self.character_scale_percent / 100.0
        self.setFixedSize(
            CHARACTER_CANVAS_WIDTH,
            CHARACTER_BASE_Y + CHARACTER_IMAGE_SIZE,
        )

    def _finish_visual_startup(self) -> None:
        if self._visual_startup_complete:
            return
        self._load_expression_assets()
        self._build_physics_layers()
        self._build_attention_layers()
        self._build_mouth_frames()
        self._update_physics_pose("idle")
        self._apply_physics_visibility()
        self._render_attention_layers(force=True)
        self._setup_timers()
        self._setup_tray()
        self._visual_startup_complete = True
        if self._startup_speech_requested:
            if not bool(self.db.setting("onboarding_complete", False)):
                # First awakening: a quiet, fateful greeting for the very first
                # launch, echoing the "accidental birth" of the companion.
                self.speak(
                    f"妾……終於能與{profile_setting(self.db, 'user_title')}相見了。"
                    "自赤焰劍中醒來，往後便由妾伴您左右。",
                    "gentle_smile_front",
                )
            else:
                self.speak(
                    f"妾已就位。{profile_setting(self.db, 'user_title')}點妾，"
                    "便可展開今日卷冊。",
                    "idle",
                )

    def complete_deferred_startup(self) -> None:
        """Finish heavy visual preparation after the first window paint."""
        if self._closing or self._visual_startup_complete:
            return
        self._finish_visual_startup()
        self.dashboard.update_panel.start_automatic_check()

    def _load_expression_assets(self) -> None:
        for expression in EXPRESSION_IMAGE_ASSETS:
            if expression in self.expression_pixmaps:
                continue
            pix = QPixmap(str(resource_path(f"assets/expressions/{expression}.png")))
            self.expression_pixmaps[expression] = pix.scaled(
                465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

    def _build_ui(self, defer_visual_assets: bool = False) -> None:
        root = QWidget()
        root.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(root)
        self._build_speech_bubble(root)
        self._build_character_widget(root, defer_visual_assets)
        self._build_expression_overlay(root)
        self._build_physics_overlay_widgets(root)
        self._build_attention_overlay_widgets(root)
        self.bubble.raise_()
        self.bubble.hide()

    def _build_speech_bubble(self, root: QWidget) -> None:
        self.bubble = QFrame(root)
        self.bubble.setObjectName("speechBubble")
        self.bubble.setGeometry(18, 8, 430, 96)
        self.bubble.setStyleSheet(
            "QFrame#speechBubble{background:rgba(15,29,40,225);"
            "border:1px solid #5b9bb8;border-radius:18px;}"
        )
        layout = QVBoxLayout(self.bubble)
        self.bubble_name = QLabel(profile_setting(self.db, "assistant_name"))
        self.bubble_name.setStyleSheet("color:#8fc9e0;font-size:11px;")
        self.bubble_text = QLabel()
        self.bubble_text.setWordWrap(True)
        self.bubble_text.setMaximumWidth(390)
        self.bubble_text.setStyleSheet("color:#f3f8fa;font-size:14px;")
        layout.addWidget(self.bubble_name)
        layout.addWidget(self.bubble_text, 1)

    def _build_character_widget(
        self,
        root: QWidget,
        defer_visual_assets: bool,
    ) -> None:
        self.character = ClickableLabel(root)
        self.expression_pixmaps: dict[str, QPixmap] = {}
        initial_assets = ("idle",) if defer_visual_assets else EXPRESSION_IMAGE_ASSETS
        for expression in initial_assets:
            source = QPixmap(str(resource_path(f"assets/expressions/{expression}.png")))
            self.expression_pixmaps[expression] = source.scaled(
                465,
                465,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        self.safe_layer_rendering = True
        self.conservative_idle = True
        self.physics_features = {
            key: bool(self.db.setting(key, True))
            for key in (
                "physics_sleeves",
                "physics_hair",
                "physics_ornament",
                "physics_eye_tracking",
                "physics_face_parallax",
            )
        }
        self.current_expression = "idle"
        self.character.setPixmap(self.expression_pixmaps["idle"])
        self.character.setScaledContents(True)
        self.character.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        self.character.setGeometry(
            self.character_base_x,
            self.character_base_y,
            CHARACTER_IMAGE_SIZE,
            CHARACTER_IMAGE_SIZE,
        )
        self.character.clicked.connect(self._character_clicked)
        self.character.drag_started.connect(self._begin_character_drag)
        self.character.drag_moved.connect(self._move_character_drag)
        self.character.drag_finished.connect(self._finish_character_drag)

    def _build_expression_overlay(self, root: QWidget) -> None:
        self.expression_overlay = QLabel(root)
        self._configure_character_overlay(self.expression_overlay)
        self.expression_overlay.hide()
        self.character_opacity = QGraphicsOpacityEffect(self.character)
        self.character.setGraphicsEffect(self.character_opacity)
        self.character_opacity.setOpacity(1.0)
        self.overlay_opacity = QGraphicsOpacityEffect(self.expression_overlay)
        self.expression_overlay.setGraphicsEffect(self.overlay_opacity)
        self.overlay_opacity.setOpacity(0.0)

    def _build_attention_overlay_widgets(self, root: QWidget) -> None:
        self.face_overlay = QLabel(root)
        self.eye_overlay = QLabel(root)
        for overlay in (self.face_overlay, self.eye_overlay):
            self._configure_character_overlay(overlay)
            overlay.hide()

    def _configure_character_overlay(self, overlay: QLabel) -> None:
        overlay.setScaledContents(True)
        overlay.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        overlay.setGeometry(self.character.geometry())
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)

    def _position_corner(self) -> None:
        # Anchor to the screen that currently contains the companion, so a
        # multi-display setup keeps the character on the display the user
        # dragged it to instead of snapping back to the primary screen.
        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        available = screen.availableGeometry()
        self.move(
            available.right() - self.width() - 8,
            available.bottom() - self.height() + 1,
        )

    def _apply_character_scale(
        self,
        percent: int,
        preserve_anchor: bool = True,
    ) -> None:
        percent = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, int(percent)),
        )
        previous_bottom_right = (
            self.frameGeometry().bottomRight() if preserve_anchor else None
        )
        self.character_scale_percent = percent
        self.character_scale = percent / 100.0
        display_size = max(
            1,
            round(CHARACTER_IMAGE_SIZE * self.character_scale),
        )
        window_width = max(
            CHARACTER_CANVAS_WIDTH,
            display_size + 5,
        )
        window_height = CHARACTER_BASE_Y + display_size
        self.setFixedSize(window_width, window_height)
        self.character_base_x = (window_width - display_size) // 2
        character_geometry = QRect(
            self.character_base_x,
            self.character_base_y,
            display_size,
            display_size,
        )
        for layer in (
            self.character,
            self.expression_overlay,
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
            self.face_overlay,
            self.eye_overlay,
        ):
            layer.setGeometry(character_geometry)
        self.bubble.move(
            max(8, (window_width - self.bubble.width()) // 2),
            8,
        )
        self._position_character_layers(
            getattr(self, "motion_base_x", 0),
            getattr(
                self,
                "motion_base_y",
                self.character_base_y,
            ),
        )
        if previous_bottom_right is not None:
            proposed = QPoint(
                previous_bottom_right.x() - self.width() + 1,
                previous_bottom_right.y() - self.height() + 1,
            )
            screen = QApplication.screenAt(previous_bottom_right)
            if screen is None:
                screen = QApplication.primaryScreen()
            available = screen.availableGeometry()
            proposed.setX(
                max(
                    available.left(),
                    min(
                        proposed.x(),
                        available.right() - self.width() + 1,
                    ),
                )
            )
            proposed.setY(
                max(
                    available.top(),
                    min(
                        proposed.y(),
                        available.bottom() - self.height() + 1,
                    ),
                )
            )
            self.move(proposed)

    def _hide_bubble_unless_speaking(self) -> None:
        """Hide the bubble after a delay; a late timer must survive teardown."""
        if getattr(self, "_closing", False) or self.speech_playing:
            return
        with contextlib.suppress(RuntimeError):
            self.bubble.hide()

    def _show_bubble(self, text: str) -> None:
        normalized = text.strip()
        if len(normalized) > MAX_BUBBLE_LENGTH:
            display = normalized[:227].rstrip() + ui_text(
                profile_setting(self.db, "ui_language"),
                "bubble_full_content",
                "…\n（完整內容請見對話頁）",
            )
        else:
            display = normalized
        self.bubble_text.setText(display)
        text_height = (
            self.bubble_text
            .fontMetrics()
            .boundingRect(
                QRect(0, 0, 390, 1200),
                Qt.TextWordWrap,
                display,
            )
            .height()
        )
        bubble_height = max(96, min(202, text_height + 48))
        self.bubble.setGeometry(
            max(8, (self.width() - 430) // 2),
            8,
            430,
            bubble_height,
        )
        self.bubble.show()
        self.bubble.raise_()

    def _setup_timers(self) -> None:
        self._initialize_idle_animation()
        self._initialize_mouth_animation_state()
        self._initialize_mouth_timers()
        self._initialize_physics_animation()
        self._initialize_motion_attention()
        self._initialize_service_timers()

    def _initialize_idle_animation(self) -> None:
        self.idle_phase = 0
        self.idle_pose = "front"
        self._set_expression(self._idle_expression(), fade=False)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._idle_tick)
        self.idle_timer.start(IDLE_FRAME_INTERVAL_MS)
        self.pose_timer = QTimer(self)
        self.pose_timer.setSingleShot(True)
        self.pose_timer.timeout.connect(self._rotate_idle_pose)
        self._schedule_pose_change()
        self.blink_timer = QTimer(self)
        self.blink_timer.setSingleShot(True)
        self.blink_timer.timeout.connect(self._blink)
        self._schedule_blink()
        self.gaze_timer = QTimer(self)
        self.gaze_timer.setSingleShot(True)
        self.gaze_timer.timeout.connect(self._start_attention_glance)
        self._schedule_attention_glance()
        self.ambient_timer = QTimer(self)
        self.ambient_timer.setSingleShot(True)
        self.ambient_timer.timeout.connect(self._show_ambient_expression)
        self._schedule_ambient_expression()

    def _initialize_mouth_animation_state(self) -> None:
        self.face_motion_controller = FaceMotionController()
        self.face_motion_frame = self.face_motion_controller.neutral(
            getattr(self, "idle_pose", "front"),
            "idle_front",
        )
        self.face_renderer = self.presentation_ports.face_renderer_factory()
        self.mouth_open = False
        self.mouth_frame_index = 0
        self.idle_blinking = False
        self.speech_blinking = False
        self.blink_opacity = 0.0
        self.blink_restore_pixmap = QPixmap()
        self.speech_blink_restore_pixmap = QPixmap()
        self.speech_visual_pixmap = QPixmap()
        self.blink_generation = 0
        self.audio_driven_mouth = False
        self.mouth_closing = False
        self.viseme_dynamics = VisemeDynamics()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.speech_motion_release_attempts = 0
        self.realtime_motion_release_attempts = 0
        self.after_speech_state = "idle"
        self.speech_closed_expression = "idle"
        self.speech_mid_expression = "mouth_mid"
        self.speech_open_expression = "speaking"
        self.speech_current_expression = "idle"
        self.speech_pose_suffix = "_front"
        self.speech_gesture_expression: str | None = None
        self.realtime_mouth_active = False
        self.mouth_transition_from = QPixmap()
        self.mouth_transition_to = QPixmap()
        self.mouth_transition_started = 0.0
        self.mouth_transition_duration = VISEME_CHANGE_TRANSITION_SECONDS
        self.realtime_after_speech_state = "idle"

    def _initialize_mouth_timers(self) -> None:
        self.mouth_timer = QTimer(self)
        self.mouth_timer.setSingleShot(True)
        self.mouth_timer.timeout.connect(self._mouth_tick)
        self.mouth_visual_timer = QTimer(self)
        self.mouth_visual_timer.setInterval(MOTION_FRAME_INTERVAL_MS)
        self.mouth_visual_timer.timeout.connect(self._render_audio_mouth_transition)
        self.speech_finish_timer = QTimer(self)
        self.speech_finish_timer.setSingleShot(True)
        self.speech_finish_timer.timeout.connect(self._complete_speech_audio_finished)
        self.realtime_finish_timer = QTimer(self)
        self.realtime_finish_timer.setSingleShot(True)
        self.realtime_finish_timer.timeout.connect(
            self._complete_realtime_speaking_stop
        )
        self.expression_return_timer = QTimer(self)
        self.expression_return_timer.setSingleShot(True)
        self.expression_return_timer.timeout.connect(self._release_scheduled_expression)
        self.scheduled_expression_state = ""
        self.scheduled_expression_generation = 0

    def _initialize_motion_attention(self) -> None:
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.gaze_target_x = 0.0
        self.gaze_target_y = 0.0
        self._sensory_gaze_target: tuple[float, float] | None = None
        self._sensory_gaze_expires_at = 0.0
        # A natural saccade: the eyes briefly drift to a random nearby point
        # and return, instead of staying locked on the cursor.  This mirrors
        # how a real person's gaze wanders during idle conversation.
        self._saccade_active = False
        self._saccade_target_x = 0.0
        self._saccade_target_y = 0.0
        self._saccade_expires_at = 0.0
        self.saccade_timer = QTimer(self)
        self.saccade_timer.setSingleShot(True)
        self.saccade_timer.timeout.connect(self._start_saccade)
        self._schedule_saccade()
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(MOTION_FRAME_INTERVAL_MS)
        self.motion_timer.timeout.connect(self._motion_tick)
        self.motion_timer.start()
        self.attention_pose = ""
        self.attention_timer = QTimer(self)
        self.attention_timer.timeout.connect(self._attention_tick)
        self.attention_timer.start(ATTENTION_FRAME_INTERVAL_MS)

    def _initialize_service_timers(self) -> None:
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(20_000)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.dashboard.refresh_work_time)
        self.clock_timer.start(1_000)
        self.topmost_timer = QTimer(self)
        self.topmost_timer.setInterval(100)
        self.topmost_timer.timeout.connect(self._topmost_policy_tick)
        self.topmost_timer.start()
        self.background_agent_timer = QTimer(self)
        self.background_agent_timer.setInterval(1_000)
        self.background_agent_timer.timeout.connect(self._background_agent_tick)
        self.background_agent_timer.start()

    def _idle_tick(self) -> None:
        if self.state != "idle":
            return
        self._ensure_idle_mouth_closed()
        self.idle_phase = (self.idle_phase + 1) % 720
        # Crimson Flame resonance: the breathing period shortens smoothly when
        # the user is agitated (furrowed brow), so the companion's body mirrors
        # the user's tension.  The period is eased by the resonance state, never
        # snapped, so the transition stays smooth frame to frame.
        breath_period = getattr(self, "_resonance_breath_period", 72.0)
        breath = (math.sin(self.idle_phase * math.tau / breath_period) + 1.0) / 2.0
        # Speech volume and idle breathing share one continuous body layer.
        # Ease between them so the first idle frame cannot snap the sleeves
        # and hair after the final spoken viseme.
        self.current_breath += (breath - self.current_breath) * 0.22
        sway = math.sin(self.idle_phase * math.tau / 210.0)
        self.ambient_motion_target_y = breath * 2.0
        self.ambient_motion_target_x = sway * 0.7

    def _reload_profile(self) -> None:
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self.dashboard.apply_profile_from_database()
        self.bubble_name.setText(self.dashboard.assistant_name)
        if hasattr(self, "tray"):
            self.tray.setToolTip(title)

    def _reload_background_agents(self) -> None:
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is not None:
            scheduler.close()
        self.background_scheduler = None
        if not bool(self.db.setting("background_assistant_enabled", False)):
            return
        proactive_mode = MultisensoryInteractionArbiter._mode_key(
            str(
                self.db.setting(
                    "proactive_interaction_mode",
                    self.db.setting("proactive_mode", "balanced"),
                )
            )
        )
        watched_names = [
            name.strip()[:80]
            for name in str(
                self.db.setting(
                    "background_watch_apps",
                    "Visual Studio Code,GitHub Desktop",
                )
            ).split(",")
            if name.strip()
        ][:12]
        workers = []
        if watched_names and proactive_mode != "quiet":
            workers.append(
                VisibleAppWorker(
                    self.presentation_ports.visible_windows,
                    {name: (name,) for name in watched_names},
                )
            )
        report_text = str(self.db.setting("background_diagnostic_report", "")).strip()
        if report_text:
            report_path = Path(report_text)
            workers.append(DiagnosticReportWorker(lambda path=report_path: path))
        if not workers:
            return
        event_cooldown = (
            1_800.0
            if proactive_mode == "quiet"
            else 300.0
            if proactive_mode == "active"
            else 900.0
        )
        self.background_scheduler = ManagerWorkerScheduler(
            workers,
            max_workers=2,
            event_cooldown_seconds=event_cooldown,
            global_cooldown_seconds=max(180.0, event_cooldown / 3),
        )

    def _background_agent_tick(self) -> None:
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is None or self._closing:
            return
        scheduler.tick()
        quiet = (
            self.dashboard.mode in {"勿擾", "會議", "離席", "休眠"}
            or self.state != "idle"
            or self.speech_playing
            or self.realtime_mouth_active
        )
        for observation in scheduler.drain(now=local_wall_time(), quiet=quiet):
            if not self.set_state(
                observation.expression,
                source="ambient",
                intensity=0.28,
            ):
                continue
            self._show_bubble(observation.message)
            self._schedule_return_to_idle(2_800, observation.expression)
            QTimer.singleShot(3_400, self._hide_bubble_unless_speaking)

    def _build_attention_layers(self) -> None:
        self.face_sources = {}
        self.eye_sources = {}
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            self.face_sources[pose] = QPixmap(
                str(resource_path(f"assets/expressions/v120_face{suffix}.png"))
            ).scaled(465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.eye_sources[pose] = QPixmap(
                str(resource_path(f"assets/expressions/v120_eyes{suffix}.png"))
            ).scaled(465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _render_attention_layers(self, force: bool = False) -> None:
        if not hasattr(self, "face_overlay"):
            return
        render_base = self._render_base_expression()
        pose = self.physics_expression_poses.get(
            render_base,
            getattr(self, "idle_pose", "front"),
        )
        eye_expression = getattr(self, "current_expression", "")
        render_state = (
            pose,
            eye_expression,
            round(getattr(self, "gaze_x", 0.0), 2),
            round(getattr(self, "gaze_y", 0.0), 2),
        )
        if not force and render_state == getattr(self, "attention_render_state", None):
            return
        self.attention_pose = pose
        self.attention_render_state = render_state
        face_source = self.expression_face_sources.get(
            render_base,
            self.face_sources[pose],
        )
        eye_source = getattr(self, "expression_eye_sources", {}).get(
            render_base,
            self.eye_sources[pose],
        )
        gaze_x = getattr(self, "gaze_x", 0.0)
        gaze_y = getattr(self, "gaze_y", 0.0)
        face_rendered = QPixmap(face_source.size())
        face_rendered.fill(Qt.transparent)
        face_painter = QPainter(face_rendered)
        face_painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # Never translate a photographed face patch over the base portrait.
        # Even a sub-pixel offset creates a visible duplicate lip/eyelid seam.
        # Face parallax is represented by a gaze-dependent, alpha-clipped
        # lighting shift instead; the facial geometry remains registered.
        face_painter.drawPixmap(0, 0, face_source)
        face_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        face_light = QLinearGradient(
            115 + gaze_x * 18,
            105 + gaze_y * 9,
            345 + gaze_x * 18,
            315 + gaze_y * 9,
        )
        face_light.setColorAt(0.0, QColor(175, 215, 235, 0))
        face_light.setColorAt(
            0.48,
            QColor(225, 242, 250, 7 + round(abs(gaze_x) * 3)),
        )
        face_light.setColorAt(
            1.0,
            QColor(20, 38, 58, 5 + round(abs(gaze_y) * 2)),
        )
        face_painter.fillRect(face_rendered.rect(), face_light)
        face_painter.end()
        eye_rendered = QPixmap(eye_source.size())
        eye_rendered.fill(Qt.transparent)
        # Do not paint synthetic catchlights or move a photographed eye patch.
        # Both approaches introduce white specks or duplicated eyelid edges.
        # Mouse attention is expressed through the registered face lighting
        # and body micro-turn below, leaving the canonical eye art untouched.
        self.face_overlay.setPixmap(face_rendered)
        self.eye_overlay.setPixmap(eye_rendered)

    def _attention_tick(self) -> None:
        if getattr(self, "pose_transition_active", False):
            self.face_overlay.hide()
            self.eye_overlay.hide()
            return
        full_body = getattr(self, "_adaptive_full_body_active", False)
        active = (
            self.state in {"idle", "speaking"}
            or self._render_base_expression() in EXPRESSION_POSES
        )
        sensory_target = getattr(self, "_sensory_gaze_target", None)
        sensory_active = (
            active
            and sensory_target is not None
            and time.monotonic()
            <= getattr(self, "_sensory_gaze_expires_at", 0.0)
        )
        if sensory_active:
            self.gaze_target_x, self.gaze_target_y = sensory_target
            # Shy gaze aversion: apply a small, downward offset on top of the
            # sensory gaze target so the companion glances away bashfully when
            # the user stares.  The offset is eased toward its target with a
            # lerp so the look-away reads as a shy glance, never a sudden snap.
            shy_offset = getattr(self, "_shy_gaze_offset", None)
            if shy_offset is not None:
                current = getattr(self, "_shy_gaze_offset_current", (0.0, 0.0))
                eased_x = current[0] + (shy_offset[0] - current[0]) * 0.18
                eased_y = current[1] + (shy_offset[1] - current[1]) * 0.18
                self._shy_gaze_offset_current = (eased_x, eased_y)
                self.gaze_target_x = max(
                    -1.0, min(1.0, self.gaze_target_x + eased_x)
                )
                self.gaze_target_y = max(
                    -1.0, min(1.0, self.gaze_target_y + eased_y)
                )
            else:
                self._shy_gaze_offset_current = (0.0, 0.0)
        elif getattr(self, "_saccade_active", False):
            # A brief saccade overrides cursor tracking so the eyes drift to a
            # nearby point and return, instead of staying locked on the mouse.
            if time.monotonic() <= self._saccade_expires_at:
                self.gaze_target_x = self._saccade_target_x
                self.gaze_target_y = self._saccade_target_y
            else:
                self._saccade_active = False
                self.gaze_target_x = 0.0
                self.gaze_target_y = 0.0
        elif active:
            face_center = self.mapToGlobal(
                QPoint(
                    self.character_base_x + round(235 * self.character_scale),
                    self.character_base_y + round(165 * self.character_scale),
                )
            )
            cursor = QCursor.pos()
            delta_x = cursor.x() - face_center.x()
            delta_y = cursor.y() - face_center.y()
            distance = math.hypot(delta_x, delta_y)
            if distance <= GAZE_DISTANCE_THRESHOLD:
                distance_weight = max(0.0, 1.0 - max(0.0, distance - 720) / 330)
                self.gaze_target_x = (
                    max(
                        -1.0,
                        min(1.0, delta_x / 520.0),
                    )
                    * distance_weight
                )
                self.gaze_target_y = (
                    max(
                        -1.0,
                        min(1.0, delta_y / 360.0),
                    )
                    * distance_weight
                )
            else:
                self.gaze_target_x = 0.0
                self.gaze_target_y = 0.0
        else:
            self.gaze_target_x = 0.0
            self.gaze_target_y = 0.0
        # Sword-soul awakening lets her gaze linger instead of snapping back
        # with the same mechanical timing forever.  The bounded reduction is
        # subtle (0.15 -> 0.10) and therefore cannot stall pointer tracking.
        linger = max(0.0, min(1.0, float(
            getattr(self, "_sword_soul_gaze_linger", 0.0)
        )))
        smoothing = (0.15 - 0.05 * linger) if active else 0.22
        self.gaze_x += (self.gaze_target_x - self.gaze_x) * smoothing
        self.gaze_y += (self.gaze_target_y - self.gaze_y) * smoothing
        if full_body:
            # The full-body frame owns the canvas and renders its own eyes from
            # the gaze vector computed above.  Keep the legacy gaze/lighting
            # patches hidden, but re-compose the full body so the iris layers
            # track the pointer, saccade and shy look-away.
            self.face_overlay.hide()
            self.eye_overlay.hide()
            self._refresh_full_body()
            return
        if not active:
            self.face_overlay.hide()
            self.eye_overlay.hide()
            return
        self._render_attention_layers()
        self._compose_character_position()
        expression_dynamic = (
            self._render_base_expression() in self.physics_expression_poses
            and self.expression_overlay.isHidden()
        )
        self.face_overlay.setVisible(
            expression_dynamic and self._physics_enabled("physics_face_parallax")
        )
        # Speech and blink frames already contain the photographed eyes.
        # Keeping the gaze patch out of that path prevents duplicate eyelid
        # seams and white specks while preserving idle eye tracking.
        show_eye_layer = (
            expression_dynamic
            and self.state != "speaking"
            and not getattr(self, "idle_blinking", False)
            and not self.speech_blinking
            and self._physics_enabled("physics_eye_tracking")
        )
        self.eye_overlay.setVisible(show_eye_layer)
        if expression_dynamic:
            self.face_overlay.raise_()
        if show_eye_layer:
            self.eye_overlay.raise_()
        self.bubble.raise_()

    def _motion_tick(self) -> None:
        """Blend every motion source before moving any visible layer.

        Idle breathing, speech emphasis and emotional gestures used to write
        the character position independently.  Their timers could therefore
        pull the body between different coordinates on adjacent frames.  Each
        source now owns only its target offset and this compositor is the sole
        place that moves the complete layered character.
        """
        if self.state != "idle":
            self.ambient_motion_target_x = 0.0
            self.ambient_motion_target_y = 0.0
        if self.state != "speaking":
            self.speech_motion_target_y = 0.0
        self.ambient_motion_x += (
            self.ambient_motion_target_x - self.ambient_motion_x
        ) * 0.20
        self.ambient_motion_y += (
            self.ambient_motion_target_y - self.ambient_motion_y
        ) * 0.20
        self.speech_motion_y += (
            self.speech_motion_target_y - self.speech_motion_y
        ) * 0.34
        for attribute in (
            "ambient_motion_x",
            "ambient_motion_y",
            "speech_motion_y",
        ):
            value = getattr(self, attribute)
            if abs(value) < MOTION_ZERO_THRESHOLD:
                setattr(self, attribute, 0.0)
        self._compose_character_position()

    def _begin_speech_motion_release(self) -> None:
        """Release the final spoken head lift while the mouth closes."""
        if self.audio_driven_mouth:
            self.mouth_closing = True
        self.head_motion_y = 0.0
        self.speech_motion_target_y = 0.0

    def _wait_for_speech_motion_release(
        self,
        timer: QTimer,
        attempts_attribute: str,
    ) -> bool:
        """Delay state hand-off until speech motion is visually centred."""
        scale = getattr(self, "character_scale", 1.0)
        if round(self.speech_motion_y * scale) == 0:
            setattr(self, attempts_attribute, 0)
            self._finish_speech_motion_release()
            return False
        attempts = int(getattr(self, attempts_attribute, 0)) + 1
        if attempts >= SPEECH_MOTION_RELEASE_LIMIT:
            setattr(self, attempts_attribute, 0)
            self._finish_speech_motion_release()
            return False
        setattr(self, attempts_attribute, attempts)
        timer.start(MOTION_FRAME_INTERVAL_MS)
        return True

    def _finish_speech_motion_release(self) -> None:
        """Transfer visual ownership without changing the composed pixel."""
        if not self.speech_motion_y:
            return
        self.ambient_motion_y += self.speech_motion_y
        self.speech_motion_y = 0.0
        self._compose_character_position()

    def _compose_character_position(self) -> None:
        scale = getattr(self, "character_scale", 1.0)
        tracked_gaze_x = (
            getattr(self, "gaze_x", 0.0)
            if self._physics_enabled("physics_eye_tracking")
            else 0.0
        )
        body_turn_x = round(tracked_gaze_x * 1.6 * scale)
        composed_x = self.ambient_motion_x + self.gesture_motion_x
        composed_y = (
            self.ambient_motion_y + self.speech_motion_y + self.gesture_motion_y
        )
        self.motion_base_x = round(composed_x)
        self.motion_base_y = self.character_base_y + round(composed_y)
        body_x = self.character_base_x + round(composed_x * scale) + body_turn_x
        body_y = self.character_base_y + round(composed_y * scale)
        position = (body_x, body_y)
        if position == self.last_composed_body_position:
            return
        for layer in (
            self.character,
            self.expression_overlay,
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
        ):
            layer.move(body_x, body_y)
        if hasattr(self, "face_overlay"):
            self.face_overlay.move(body_x, body_y)
            self.eye_overlay.move(body_x, body_y)
        self.last_composed_body_position = position

    def _position_character_layers(self, base_x: int, base_y: int) -> None:
        """Compatibility entry point for direct positioning and old tests."""
        self.ambient_motion_x = float(base_x)
        self.ambient_motion_y = float(base_y - self.character_base_y)
        self.ambient_motion_target_x = self.ambient_motion_x
        self.ambient_motion_target_y = self.ambient_motion_y
        self.last_composed_body_position = None
        self._compose_character_position()
