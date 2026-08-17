from __future__ import annotations

lazy import sys
lazy import time
lazy from collections import deque
lazy from collections.abc import Callable
lazy from contextlib import suppress

lazy from PySide6.QtCore import QPoint, Qt, QTimer
lazy from PySide6.QtGui import QImage, QPainter, QPixmap

lazy from application.adaptive_character_composition import (
    DEFAULT_CHARACTER_IMAGE_SIZE as CHARACTER_IMAGE_SIZE,
)
lazy from application.adaptive_character_composition import (
    AdaptiveCharacterComposition,
    AdaptiveCharacterFactory,
    create_adaptive_character_composition,
)
lazy from application.adaptive_character_runtime import AdaptiveCharacterRequest
lazy from application.background_agents import ManagerWorkerScheduler
lazy from application.body_pose_renderer import BodyPoseFrame
lazy from application.character_framing_app_bridge import AppFramingState
lazy from application.gesture_action_router import GestureActionDecision
lazy from application.gesture_application_adapter import (
    GestureApplicationAdapter,
    GestureApplicationCallbacks,
)
lazy from application.gesture_controller import GestureController
lazy from application.multimodal_fusion_hub import MultimodalFusionResult
lazy from application.presentation_ports import fallback_platform_services
lazy from application.service_container import CompanionServices
lazy from application.speech_performance import SpeechPerformanceTimeline
lazy from domain.companion_animation_contract import EXPRESSION_POSES
lazy from domain.expression_system import ExpressionArbiter
lazy from domain.framing_context_policy import (
    EmotionValence,
    FocusState,
    FramingPolicyContext,
)
lazy from domain.framing_preferences import FramingPreferences
lazy from domain.speech_configuration import QueuedSpeech
lazy from domain.speech_providers import create_builtin_speech_registry
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from presentation.performance_composition import create_performance_app_bridge
lazy from presentation.pose_atlas_assets import PoseAtlasAssets
lazy from presentation.presentation_resources import resource_path

__all__ = ("CompanionCoreMixin",)


def _current_legacy_character_frame(window: object, generation: int) -> BodyPoseFrame:
    """Snapshot the proven renderer for the adaptive fallback boundary."""

    size = CHARACTER_IMAGE_SIZE
    canvas = QImage(size, size, QImage.Format_RGBA8888)
    canvas.fill(Qt.transparent)
    pixmap = window.character.pixmap()
    if pixmap is not None and not pixmap.isNull():
        image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        image = image.scaled(
            size,
            size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        painter = QPainter(canvas)
        painter.drawImage(
            (size - image.width()) // 2,
            (size - image.height()) // 2,
            image,
        )
        painter.end()
    return BodyPoseFrame(
        size,
        size,
        bytes(canvas.constBits()),
        generation,
        ("legacy-current",),
        ("legacy-current",),
        False,
    )


class CompanionCoreMixin:
    """Compose the companion's core services, state, and application bridges."""

    def _initialize_adaptive_character_composition(
        self,
        factory: AdaptiveCharacterFactory | None,
        enabled: bool | None,
    ) -> None:
        """Open the v4 composition gate without touching legacy rendering."""

        self._adaptive_character_composition: AdaptiveCharacterComposition | None = None
        self._performance_app_bridge = None
        self._adaptive_character_generation = 0
        self._staged_adaptive_frame = None
        selected = (
            bool(self.db.setting("adaptive_character_v4_enabled", True))
            if enabled is None
            else bool(enabled)
        )
        self._adaptive_character_enabled = selected
        if not selected:
            return
        composition_factory = factory
        if composition_factory is None:
            composition_factory = lambda stage_frame: (
                create_adaptive_character_composition(
                    stage_frame,
                    image_size=CHARACTER_IMAGE_SIZE,
                    assets=PoseAtlasAssets(
                        resource_path("assets/pose-atlas/v4"),
                        image_size=CHARACTER_IMAGE_SIZE,
                    ),
                )
            )
        try:
            composition = composition_factory(self._stage_adaptive_character_frame)
            generation = composition.runtime.begin_operation()
        except ImportError, LookupError, RuntimeError, TypeError, ValueError:
            self._adaptive_character_enabled = False
            return
        self._adaptive_character_composition = composition
        self._adaptive_character_generation = generation
        self._performance_app_bridge = create_performance_app_bridge(
            lambda frame_generation: _current_legacy_character_frame(
                self,
                frame_generation,
            ),
            self._dispatch_adaptive_character_frame,
        )
        self._publish_adaptive_idle_frame()

    def _publish_adaptive_idle_frame(self) -> None:
        """Publish a complete PoseAtlas body before the first spoken reply."""
        try:
            prepared = self.speech_performance.prepare("desktop-idle")
            self._record_speech_performance(prepared)
            generation = prepared[0].generation
            self._record_speech_performance(
                self.speech_performance.final_audio(generation=generation)
            )
            self._record_speech_performance(
                self.speech_performance.mouth_closed(generation=generation)
            )
        except LookupError, RuntimeError, TypeError, ValueError:
            # The proven legacy surface remains available if an optional v4
            # frame cannot be assembled during startup.
            return

    def _stage_adaptive_character_frame(self, frame: object) -> None:
        """Hold adapter output until the atomic coordinator approves publish."""

        self._staged_adaptive_frame = frame

    def _dispatch_adaptive_character_frame(
        self,
        atomic_frame: object,
    ) -> object | None:
        """Composition entrypoint used by the provider-neutral performance bridge."""

        composition = self._adaptive_character_composition
        if not self._adaptive_character_enabled or composition is None or self._closing:
            return None
        performance = atomic_frame.performance
        speech_active = not performance.mouth_closed
        policy = FramingPolicyContext(
            away_seconds=0.0,
            returned_to_seat=False,
            intimacy=0.5,
            emotion_intensity=min(1.0, max(0.0, performance.body_energy)),
            emotion_valence=EmotionValence.NEUTRAL,
            angry_back_turn=performance.pose.startswith("back-"),
            speech_active=speech_active,
            mouth_closed=performance.mouth_closed,
            gesture_bounds=None,
            weapon_or_large_prop=False,
            outfit_preview=False,
            focus_state=FocusState.AVAILABLE,
            proactive_greeting=False,
            close_framing_allowed=True,
        )
        framing_state = AppFramingState(
            performance.behavior_generation,
            policy,
            max(1, self.character.width()),
            max(1, self.character.height()),
            True,
        )
        try:
            decision = composition.runtime.dispatch(
                AdaptiveCharacterRequest(
                    self._adaptive_character_generation,
                    atomic_frame,
                    framing_state,
                    FramingPreferences(),
                    composition.assets,
                    v4_enabled=True,
                )
            )
        except LookupError, RuntimeError, TypeError, ValueError:
            return None
        if decision.should_publish and not decision.used_legacy:
            self._publish_adaptive_character_frame(decision.frame)
        return decision

    def _publish_adaptive_character_frame(self, frame: object) -> None:
        """Publish approved RGBA without resizing the character widget."""

        if frame is not self._staged_adaptive_frame:
            return
        expected = frame.width * frame.height * 4
        if len(frame.rgba) != expected:
            return
        image = QImage(
            frame.rgba,
            frame.width,
            frame.height,
            frame.width * 4,
            QImage.Format_RGBA8888,
        ).copy()
        self.character.setPixmap(QPixmap.fromImage(image))
        self._staged_adaptive_frame = None

    def _cancel_adaptive_character_composition(self) -> None:
        """Close the active v4 generation without disturbing legacy shutdown."""

        composition = getattr(self, "_adaptive_character_composition", None)
        generation = getattr(self, "_adaptive_character_generation", 0)
        self._adaptive_character_composition = None
        self._staged_adaptive_frame = None
        if composition is None or generation <= 0:
            return
        with suppress(LookupError, RuntimeError, TypeError, ValueError):
            composition.runtime.cancel(generation)

    def _initialize_runtime_services(
        self,
        services: CompanionServices,
    ) -> None:
        self.db = services.db
        self.platform_services = (
            services.platform_services or fallback_platform_services()
        )
        self.presentation_ports = services.presentation_ports
        if self.presentation_ports is None:
            raise ValueError("Companion requires injected presentation ports.")
        self.backup_manager = services.backup_manager
        self.secret_store = services.secret_store
        self.azure_secret_store = services.azure_secret_store
        self.azure_hd_secret_store = services.azure_hd_secret_store
        self.secret_store_factory = services.secret_store_factory
        self.cloud_vision_service_factory = services.cloud_vision_service_factory
        self.dense_face_provider_factory = services.dense_face_provider_factory
        self.tts = services.local_tts
        self.cloud_tts = services.cloud_tts
        self.azure_tts = services.azure_speech
        self.azure_hd_tts = services.azure_hd_speech
        self.speech_providers = (
            services.speech_providers
            or create_builtin_speech_registry(
                self.tts,
                self.cloud_tts,
                self.azure_tts,
                self.azure_hd_tts,
            )
        )
        self.realtime = services.realtime
        self.realtime_speech_output = services.realtime_speech_output
        self.listener = services.listener

    def _run_first_run_wizard_if_needed(
        self,
        startup_speech: bool,
    ) -> None:
        should_run = (
            startup_speech
            and "--smoke-auto-exit" not in sys.argv
            and not bool(self.db.setting("onboarding_complete", False))
        )
        if should_run:
            FirstRunWizard(
                self.db,
                platform_services=self.platform_services,
            ).exec()

    def _create_dashboard(
        self,
        gesture_controller: GestureController | None = None,
    ) -> Dashboard:
        return Dashboard(
            self.db,
            DashboardDependencies(
                listener=self.listener,
                secret_store=self.secret_store,
                azure_secret_store=self.azure_secret_store,
                azure_hd_secret_store=self.azure_hd_secret_store,
                azure_speech=self.azure_tts,
                azure_hd_speech=self.azure_hd_tts,
                secret_store_factory=self.secret_store_factory,
                platform_services=self.platform_services,
                cloud_vision_service_factory=(self.cloud_vision_service_factory),
                dense_face_provider_factory=self.dense_face_provider_factory,
                presentation_ports=self.presentation_ports,
            ),
            gesture_controller=gesture_controller,
        )

    def _create_gesture_application(self) -> GestureApplicationAdapter:
        """Bind hand gestures to existing user-visible application paths."""

        return GestureApplicationAdapter(
            GestureApplicationCallbacks(
                show_control_center=self._open_dashboard_from_gesture,
                hide_control_center=self.dashboard_hide_if_available,
                set_audio_muted=self._set_gesture_audio_muted,
                stop_current_speech=self._stop_current_speech_from_gesture,
                toggle_listening=self.listener.toggle_listening,
                set_realtime_enabled=self.toggle_realtime,
                set_interaction_mode=self._set_gesture_interaction_mode,
                acknowledge_positive=self._acknowledge_gesture,
                submit_safe_text_command=self._submit_gesture_text_command,
            )
        )

    def _authorize_gesture_action(self, decision: GestureActionDecision) -> bool:
        """Reuse the control center's persisted permission and audit boundary."""

        dashboard = getattr(self, "dashboard", None)
        center = getattr(dashboard, "flagship_center", None)
        authorize = getattr(center, "authorize_gesture_action", None)
        return bool(authorize(decision)) if callable(authorize) else False

    def dashboard_hide_if_available(self) -> None:
        dashboard = getattr(self, "dashboard", None)
        if dashboard is not None:
            dashboard.hide()

    def _set_gesture_audio_muted(self, muted: bool) -> None:
        dashboard = getattr(self, "dashboard", None)
        if dashboard is None:
            return
        dashboard.voice_muted.setChecked(bool(muted))

    def _stop_current_speech_from_gesture(self) -> None:
        for engine in (
            self.tts,
            self.cloud_tts,
            self.azure_tts,
            self.azure_hd_tts,
        ):
            stop = getattr(engine, "stop", None)
            if callable(stop):
                stop()
        self._stop_realtime_output()
        self.speech_queue.clear()
        if self.speech_playing:
            self._complete_proactive_companion_speech(False)
            self._stop_mouth_animation()
            self.speech_playing = False
            self.active_speech_text = ""
            self.active_speech_engine = ""
            self.set_state("idle", source="conversation", force=True)

    def _set_gesture_interaction_mode(self, mode: str) -> None:
        canonical = {
            "work": "工作",
            "companion": "陪伴",
            "do-not-disturb": "勿擾",
        }[mode]
        dashboard = getattr(self, "dashboard", None)
        if dashboard is None:
            return
        index = dashboard.mode_combo.findData(canonical)
        if index >= 0:
            dashboard.mode_combo.setCurrentIndex(index)

    def _acknowledge_gesture(self) -> None:
        if hasattr(self, "expression_arbiter"):
            self.set_state("happy", source="conversation", intensity=0.55)

    def _open_dashboard_from_gesture(self) -> None:
        """Open the keyboard conversation surface and acknowledge a wave."""
        self.open_dashboard()
        self._acknowledge_gesture()
        language = str(self.db.setting("ui_language", "zh-TW"))
        responses = {
            "zh-TW": "主上，妾在。可以直接在控制台輸入想說的話。",
            "zh-CN": "主上，妾在。可以直接在控制台输入想说的话。",
            "en": "I am here. You can type to me directly in the control center.",
            "ja-JP": "ここにいます。コントロールセンターから直接入力してください。",
        }
        self.speak(responses.get(language, responses["zh-TW"]), "happy")

    def _submit_gesture_text_command(self, command: str) -> None:
        dashboard = getattr(self, "dashboard", None)
        if dashboard is None:
            return
        dashboard._input_source = "gesture"
        dashboard.chat_input.setText(command)
        dashboard.send_chat()

    def _connect_dashboard_signals(self) -> None:
        self.dashboard.speak_requested.connect(self.speak)
        self.dashboard.voice_preview_requested.connect(self.preview_voice)
        self.dashboard.realtime_toggle_requested.connect(self.toggle_realtime)
        self.dashboard.realtime_voice_changed.connect(self._apply_realtime_voice_change)
        self.dashboard.realtime_output_mode_changed.connect(
            self._apply_realtime_voice_change
        )
        self.dashboard.realtime_output_settings_changed.connect(
            self._refresh_realtime_output_settings
        )
        self.dashboard.volume_changed.connect(self._apply_voice_volume)
        self.dashboard.visibility_changed.connect(self._dashboard_visibility_changed)
        self.dashboard.topmost_mode_changed.connect(
            lambda _mode: self._topmost_policy_tick()
        )
        self.dashboard.character_scale_preview.connect(self._apply_character_scale)
        self.dashboard.state_requested.connect(self.set_state)
        self.dashboard.ai_wait_expression_requested.connect(
            self._start_ai_wait_expression
        )
        self.dashboard.ai_wait_expression_finished.connect(
            self._finish_ai_wait_expression
        )
        self.dashboard.visual_observation_changed.connect(
            self._consider_visual_interaction
        )
        self.dashboard.visual_scene_changed.connect(self._remember_visual_scene)
        self.dashboard.multimodal_result_changed.connect(
            self._apply_multimodal_result
        )
        self.dashboard.human_interaction.connect(self._note_human_interaction)
        self._apply_voice_volume(
            int(self.db.setting("voice_volume_percent", 125)),
            bool(self.db.setting("voice_muted", False)),
        )
        self.background_scheduler: ManagerWorkerScheduler | None = None
        self.dashboard.settings_saved.connect(self._reload_physics_settings)
        self.dashboard.settings_saved.connect(self._reload_profile)
        self.dashboard.settings_saved.connect(self._reload_background_agents)
        self.dashboard.settings_saved.connect(
            self._reload_proactive_companion_app_bridge
        )
        self.proactive_presence_timer = QTimer(self)
        self.proactive_presence_timer.setInterval(60_000)
        self.proactive_presence_timer.timeout.connect(self._consider_desktop_presence)
        self.proactive_presence_timer.start()

    def _apply_multimodal_result(self, result: object) -> None:
        if not isinstance(result, MultimodalFusionResult):
            return
        now = time.monotonic()
        face = result.face
        if face is not None and face.gaze_confidence >= 0.35:
            self._sensory_gaze_target = (
                max(-1.0, min(1.0, -face.gaze_x)),
                max(-1.0, min(1.0, face.gaze_y)),
            )
            self._sensory_gaze_expires_at = now + 0.90
        if (
            "smile-like" in result.events
            and now - getattr(self, "_last_multimodal_smile_at", 0.0) >= 8.0
        ):
            self._last_multimodal_smile_at = now
            self.set_state(
                "gentle_smile_front",
                source="visual",
                intensity=0.35,
            )
        if (
            "high-five" in result.events
            and now - getattr(self, "_last_multimodal_high_five_at", 0.0) >= 12.0
        ):
            self._last_multimodal_high_five_at = now
            self.set_state("happy", source="visual", intensity=0.75)
            language = str(self.db.setting("ui_language", "zh-TW"))
            responses = {
                "zh-TW": "擊掌！今日也配合得很好。",
                "zh-CN": "击掌！今天也配合得很好。",
                "en": "High five! We worked well together today.",
                "ja-JP": "ハイタッチ！今日も息がぴったりですね。",
            }
            self.speak(responses.get(language, responses["zh-TW"]), "happy")

    def _connect_speech_service_signals(self) -> None:
        self.tts.finished.connect(self._speech_audio_finished)
        self.tts.failed.connect(self._windows_voice_failed)
        self.tts.viseme_cue.connect(self._audio_viseme_cue)
        self.cloud_tts.finished.connect(self._speech_audio_finished)
        self.cloud_tts.failed.connect(self._cloud_voice_failed)
        self.cloud_tts.viseme_cue.connect(self._audio_viseme_cue)
        if self.azure_tts is not None:
            self.azure_tts.finished.connect(self._speech_audio_finished)
            self.azure_tts.failed.connect(self._azure_voice_failed)
            self.azure_tts.viseme_cue.connect(self._audio_viseme_cue)
        if self.azure_hd_tts is not None:
            self.azure_hd_tts.finished.connect(self._speech_audio_finished)
            self.azure_hd_tts.failed.connect(self._azure_hd_voice_failed)
            self.azure_hd_tts.viseme_cue.connect(self._audio_viseme_cue)
        self.realtime.status_changed.connect(self._realtime_status)
        self.realtime.user_transcript.connect(self._realtime_user_text)
        self.realtime.assistant_transcript.connect(self._realtime_assistant_text)
        self.realtime.speaking_changed.connect(self._realtime_speaking)
        self.realtime.viseme_cue.connect(self._audio_viseme_cue)
        self.realtime.failed.connect(self._realtime_failed)
        if self.realtime_speech_output is not None:
            self.realtime.output_text_started.connect(
                self.realtime_speech_output.begin_response
            )
            self.realtime.output_text_delta.connect(
                self.realtime_speech_output.add_text
            )
            self.realtime.output_text_done.connect(
                self.realtime_speech_output.finish_response
            )
            self.realtime.output_interrupted.connect(self.realtime_speech_output.cancel)
            self.realtime_speech_output.speaking_changed.connect(
                self._realtime_speaking
            )
            self.realtime_speech_output.playback_guard_changed.connect(
                self.realtime.set_external_playback_active
            )
            self.realtime_speech_output.viseme_cue.connect(self._audio_viseme_cue)
            self.realtime_speech_output.status_changed.connect(self._realtime_status)
            self.realtime_speech_output.failed.connect(self._realtime_failed)

    def _initialize_companion_state(self, startup_speech: bool) -> None:
        self.state = "idle"
        self.expression_generation = 0
        self.expression_arbiter = ExpressionArbiter(
            set(EXPRESSION_POSES) | {"idle", "speaking"}
        )
        self.active_ai_wait_generation = 0
        self.active_ai_wait_expression = ""
        self.speech_queue: deque[QueuedSpeech] = deque()
        self.speech_playing = False
        self.active_speech_text = ""
        self.active_speech_engine = ""
        self.active_speech_source = ""
        self.active_speech_delivery_token = ""
        self._proactive_speech_completions: dict[str, Callable[[bool], None]] = {}
        self.speech_performance = SpeechPerformanceTimeline()
        self.last_speech_performance_event = None
        self.last_speech_performance_directive = None
        self.cloud_fallback_active = False
        self.speech_fallback_attempts: set[str] = set()
        self.drag_offset: QPoint | None = None
        self.last_overwork_notice = ""
        self._startup_speech_requested = startup_speech
        self._visual_startup_complete = False
        self._closing = False
        self._multisensory_config = self._current_multisensory_config()
        self.multisensory_arbiter = self._new_multisensory_arbiter(
            self._multisensory_config
        )
        self._latest_visual_scene = None
        self._recognized_scene_streak = 0
        self._multisensory_variation_index = int(
            self.db.setting("multisensory_variation_index", 0)
        )
