from __future__ import annotations

lazy import sys
lazy import time
lazy from collections import deque
lazy from collections.abc import Callable
lazy from contextlib import suppress
lazy from dataclasses import replace

lazy from PySide6.QtCore import QPoint, Qt, QTimer
lazy from PySide6.QtGui import QImage, QPainter, QPixmap

lazy from application.adaptive_character_composition import (
    DEFAULT_CHARACTER_IMAGE_SIZE as CHARACTER_IMAGE_SIZE,
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
lazy from application.speech_performance import (
    SpeechPerformancePhase,
    SpeechPerformanceTimeline,
)
lazy from domain.affective_state import AffectiveState
lazy from domain.affinity_state import AffinityState
lazy from domain.chronicle import Chronicle, Milestone, MilestoneKind
lazy from domain.companion_animation_contract import EXPRESSION_POSES
lazy from domain.constants import POSE_ATLAS_RELATIVE_ROOT
lazy from domain.emotional_resonance import EmotionalResonanceState
lazy from domain.favor_exclusive import FavorExclusiveState
lazy from domain.personality_state import PersonalityMirrorState
lazy from domain.satiety import SatietyState
lazy from domain.sensory_synesthesia import WeatherMood
lazy from domain.sword_soul_resonance import SwordSoulResonanceState

WAVE_ACKNOWLEDGE_COOLDOWN_SECONDS = 6.0
GAZE_CONFIDENCE_THRESHOLD = 0.35
SMILE_COOLDOWN_SECONDS = 8.0
CHIN_COOLDOWN_SECONDS = 14.0
BROW_COOLDOWN_SECONDS = 16.0
HIGH_FIVE_COOLDOWN_SECONDS = 12.0
PINCH_COOLDOWN_SECONDS = 10.0
lazy from domain.face_motion import FaceMotionController, blend_shyness
lazy from domain.shy_gaze import ShyGazeState
lazy from domain.shyness import ShynessState
lazy from domain.time_sovereignty import TimeSovereigntyState
lazy from domain.wardrobe_intuition import (
    OutfitWeight,
    comfort_verdict,
    complaint_line,
    suggested_weight,
)
lazy from domain.expression_system import (
    DEVOTION_PRIORITY_BONUS,
    FAVOR_DEVOTED_THRESHOLD,
    ExpressionArbiter,
)
lazy from domain.time_utils import local_wall_time
lazy from domain.character_framing import NormalizedRect, PUBLISHABLE_BODY_MODES
lazy from domain.framing_context_policy import (
    EmotionValence,
    FocusState,
    FramingPolicyContext,
)
lazy from domain.constants import DEFAULT_WEATHER_TEMPERATURE_C
lazy from domain.framing_preferences import FramingPreferences
lazy from domain.performance_preferences import PerformancePreferences
lazy from infrastructure.db import StudioDBSettingsPort
lazy from infrastructure.framing_preferences_store import FramingPreferencesStore
lazy from infrastructure.performance_preferences_store import (
    PerformancePreferencesStore,
)
lazy from domain.speech_configuration import (
    DEFAULT_VOICE_VOLUME_PERCENT,
    QueuedSpeech,
)
lazy from domain.speech_providers import create_builtin_speech_registry
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from presentation.performance_composition import create_performance_app_bridge
lazy from presentation.pose_atlas_assets import PoseAtlasAssets
lazy from presentation.presentation_resources import resource_path

__all__ = ("CompanionCoreMixin",)

# Framing modes that publish the v4 full-body photograph.  HALF/CLOSE keep the
# legacy half-body poses (cheek-rest, left-neutral, front-crossed) instead.
_FULL_BODY_MODES = PUBLISHABLE_BODY_MODES


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
        self._adaptive_full_body_active = False
        self._last_atomic_frame = None
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
            composition_factory = lambda stage_frame: create_adaptive_character_composition(
                stage_frame, image_size=CHARACTER_IMAGE_SIZE, framing_style=str(self.db.setting("framing_style", "steady")),
                assets=PoseAtlasAssets(
                    resource_path(POSE_ATLAS_RELATIVE_ROOT), image_size=CHARACTER_IMAGE_SIZE,
                    outfit_overlay=self.presentation_ports.outfit_overlay_factory(on_stale_body_profile=self._on_stale_outfit_pack),
                ),
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
            lambda frame_generation: _current_legacy_character_frame(self, frame_generation),
            self._dispatch_adaptive_character_frame,
        )
        self._publish_adaptive_idle_frame()

    def _on_stale_outfit_pack(self) -> None:
        """The overlay restored the built-in outfit over a generation-1 pack; tell the wardrobe tab once."""
        dashboard = getattr(self, "dashboard", None)
        if dashboard is not None:
            dashboard.set_outfit_generation_status("body-profile-outdated")

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
        # Remember the last atomic frame so the gaze timer can re-compose the
        # full body when the pointer/saccade/shy-aversion moves the eyes without
        # a new speech or behavior event.
        self._last_atomic_frame = atomic_frame
        performance = atomic_frame.performance
        # Speech-activeness comes from the utterance lifecycle, not from the
        # per-frame mouth shape: the coordinator reports mouth_closed=True on
        # every mid-sentence silence viseme, and deriving speech_active from
        # it made the framing oscillate HALF<->THREE_QUARTER on each >1.2s
        # pause (verified by simulation, ruling 2026-08-28).
        phase = getattr(performance, "phase", None)
        speech_active = (
            phase
            in (
                SpeechPerformancePhase.PREPARING,
                SpeechPerformancePhase.SPEAKING,
                SpeechPerformancePhase.PAUSING,
                SpeechPerformancePhase.SETTLING,
            )
            if phase is not None
            else not performance.mouth_closed
        )
        # A pending wardrobe reveal asks the director for a full-body shot so
        # the new outfit/accessory is visible.  Reading the pending-outfit
        # setting here (instead of hard-coding False) lets the director switch
        # to FULL_BODY only while a reveal is actually pending, then return to
        # HALF for ordinary conversation.
        pending_outfit = bool(
            str(self.db.setting("wardrobe_reveal_pending_outfit_id", "") or "").strip()
        )
        hand_action = any(
            not str(value).strip().lower().startswith(("relaxed", "neutral"))
            for value in (
                getattr(performance, "left_hand", "relaxed"),
                getattr(performance, "right_hand", "relaxed"),
            )
        )
        gesture_bounds = (
            NormalizedRect(0.02, 0.0, 0.98, 0.92)
            if hand_action
            else NormalizedRect(0.10, 0.0, 0.90, 0.75)
            if bool(getattr(performance, "gesture_beat", False))
            else None
        )
        affinity = getattr(self, "affinity_state", None)
        intimacy = (
            max(0.0, min(1.0, float(affinity.snapshot().affinity)))
            if affinity is not None
            else 0.5
        )
        policy = FramingPolicyContext(
            away_seconds=0.0,
            returned_to_seat=False,
            intimacy=intimacy,
            emotion_intensity=min(1.0, max(0.0, performance.body_energy)),
            emotion_valence=EmotionValence.NEUTRAL,
            angry_back_turn=str(getattr(performance, "pose", "")).startswith("back-"),
            speech_active=speech_active,
            mouth_closed=performance.mouth_closed,
            gesture_bounds=gesture_bounds,
            weapon_or_large_prop=False,
            outfit_preview=pending_outfit,
            focus_state=FocusState.AVAILABLE,
            proactive_greeting=(
                str(getattr(self, "active_speech_source", "")) == "proactive"
            ),
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
                    self._current_framing_preferences(),
                    composition.assets,
                    v4_enabled=True,
                    face_motion=self._face_motion_with_live_state(),
                )
            )
        except LookupError, RuntimeError, TypeError, ValueError:
            return None
        if decision.should_publish and not decision.used_legacy:
            framing = getattr(decision, "framing", None)
            if framing is not None and framing.mode in _FULL_BODY_MODES:
                # Full-body shots are reserved for gestures, hand actions,
                # accessory reveals, owner arrival and special occasions.  Only
                # these publish the v4 full-body photograph.
                self._publish_adaptive_character_frame(decision.frame)
            else:
                # HALF/CLOSE (idle and speech) keep the legacy half-body poses
                # (cheek-rest, left-neutral, front-crossed).  Do not publish the
                # full-body photograph so the half-body sprites stay in charge.
                self._release_adaptive_full_body()
        return decision

    def _face_motion_with_live_state(self):
        """Return the face-motion frame with live gaze/blink/breath/expression.

        The full-body renderer consumes a single :class:`FaceMotionFrame`, but
        the gaze, blink, breath and expression all live in separate ``self``
        attributes that update on their own timers.  This method stamps the
        current values onto a copy of the frame so the layered renderer sees the
        complete, up-to-date face state on every composition.
        """
        motion = getattr(self, "face_motion_frame", None)
        if motion is None:
            return None
        gaze_x = getattr(self, "gaze_x", 0.0)
        gaze_y = getattr(self, "gaze_y", 0.0)
        blink = getattr(self, "blink_opacity", 0.0)
        breath = getattr(self, "current_breath", 0.0)
        expression = getattr(self, "current_expression", motion.expression)
        # Re-map the expression onto its continuous shape when it changed, so a
        # happy/shy/worried switch actually deforms the brows/blush/eye-smile.
        if expression != motion.expression:
            target = FaceMotionController.neutral(
                str(motion.pose.value),
                expression,
            )
            expression_shape = replace(
                target.expression_shape,
                blink=blink,
            )
        else:
            expression_shape = replace(
                motion.expression_shape,
                blink=blink,
            )
        return replace(
            motion,
            expression=expression,
            expression_shape=expression_shape,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            breath=breath,
        )

    def _refresh_full_body(self) -> None:
        """Re-compose the full body when live state moved without a new event.

        The full-body composition is event-driven, but the gaze, blink, breath
        and expression update on their own timers.  When the full body owns the
        canvas, replay the last atomic frame so the layered renderer re-applies
        the current face state.
        """
        if not getattr(self, "_adaptive_full_body_active", False):
            return
        atomic_frame = getattr(self, "_last_atomic_frame", None)
        if atomic_frame is None:
            return
        self._dispatch_adaptive_character_frame(atomic_frame)

    def _release_adaptive_full_body(self) -> None:
        """Hand the canvas back to the legacy half-body poses."""
        if not getattr(self, "_adaptive_full_body_active", False):
            return
        self._adaptive_full_body_active = False
        # Restore the current half-body expression sprite and let the physics
        # and attention layers re-apply their own visibility rules (instead of
        # blindly showing every overlay).
        expression = self.current_expression
        if expression in self.expression_pixmaps:
            self.character.setPixmap(self.expression_pixmaps[expression])
        self._apply_physics_visibility()
        self._render_attention_layers(force=True)

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
        # The published RGBA already contains the complete photographed body,
        # so the legacy half-body overlays must not be drawn above it.  Leaving
        # the idle physics/attention layers visible stacks a second set of
        # sleeves, hair, ornament and gaze patches over the full-body frame,
        # which is the double-image reported at startup greeting.
        self._adaptive_full_body_active = True
        self._hide_legacy_character_overlays()

    def _hide_legacy_character_overlays(self) -> None:
        """Hide every legacy half-body overlay while the full-body owns the canvas."""

        for attribute in (
            "expression_overlay",
            "sleeve_left_overlay",
            "sleeve_right_overlay",
            "hair_left_overlay",
            "hair_right_overlay",
            "physics_overlay",
            "face_overlay",
            "eye_overlay",
        ):
            overlay = getattr(self, attribute, None)
            if overlay is not None:
                overlay.hide()

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
        """Apply a camera gesture mute for this process only.

        Visual recognition is probabilistic.  It must never rewrite the
        user's persisted global mute preference merely because one camera
        frame looked like the silence gesture.
        """

        dashboard = getattr(self, "dashboard", None)
        if dashboard is None:
            return
        self._gesture_audio_muted = bool(muted)
        self._apply_voice_volume(
            int(
                self.db.setting(
                    "voice_volume_percent", DEFAULT_VOICE_VOLUME_PERCENT
                )
            ),
            bool(self.db.setting("voice_muted", False)) or self._gesture_audio_muted,
        )

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
        if not hasattr(self, "expression_arbiter"):
            return
        try:
            self.set_state("happy", source="conversation", intensity=0.55)
        except AttributeError as exc:
            # A deferred visual startup deliberately does not allocate pose
            # assets. It can still acknowledge a gesture through the status
            # card and voice path, but cannot animate until assets are ready.
            if "physics_expression_poses" not in str(exc):
                raise

    def _on_gesture_recognition(self, result: object) -> None:
        """Answer a waved greeting with an expression and a spoken hello."""

        recognitions = tuple(getattr(result, "recognitions", ()) or ())
        wave_detected = any(
            str(getattr(recognition, "gesture_id", "")) == "wave"
            and bool(getattr(recognition, "triggered", False))
            for recognition in recognitions
        )
        if not wave_detected:
            return
        self._acknowledge_wave()

    def _acknowledge_wave(self) -> None:
        """Acknowledge a recognized wave with a varied, proactive greeting.

        A wave in front of the camera is treated as the user actively seeking
        the companion's attention, so the response is a spoken greeting rather
        than a silent expression.  Greeting lines rotate across a small set of
        variations per language so repeated waves feel like a real exchange
        instead of a canned reply.
        """

        now = time.monotonic()
        if (
            now - getattr(self, "_last_wave_acknowledged_at", float("-inf"))
            < WAVE_ACKNOWLEDGE_COOLDOWN_SECONDS
        ):
            return
        self._last_wave_acknowledged_at = now
        if hasattr(self, "expression_arbiter"):
            try:
                self.set_state("happy", source="visual", intensity=0.6)
            except AttributeError as exc:
                # A deferred visual startup can still acknowledge a wave
                # through the voice path while pose assets are unavailable.
                if "physics_expression_poses" not in str(exc):
                    raise
        language = str(self.db.setting("ui_language", "zh-TW"))
        responses = {
            "zh-TW": (
                "嗨，我在這裡！",
                "主上喚我麼？妾一直都在。",
                "你揮手，妾便來了。",
                "許久不見，近來可好？",
            ),
            "zh-CN": (
                "嗨，我在这里！",
                "主上唤我么？妾一直都在。",
                "你挥手，妾便来了。",
                "许久不见，近来可好？",
            ),
            "en": (
                "Hi there, I'm here!",
                "You called? I have been here all along.",
                "You waved, so here I am.",
                "It has been a while. How have you been?",
            ),
            "ja-JP": (
                "こんにちは、ここにいますよ。",
                "お呼びですか？妾はずっとここに。",
                "手を振ってくれたので、参りました。",
                "お久しぶりです。お元気でしたか？",
            ),
        }
        lines = responses.get(language, responses["zh-TW"])
        index = getattr(self, "_wave_greeting_index", 0)
        self._wave_greeting_index = (index + 1) % len(lines)
        self.speak(lines[index], "happy")

    def _open_dashboard_from_gesture(self) -> None:
        """Open the keyboard conversation surface and acknowledge a wave."""
        self.open_dashboard()
        self._acknowledge_wave()
        # The status card is informative only.  Its transient widget lifecycle
        # must never prevent the real companion from opening the keyboard
        # conversation or answering a recognized wave.
        with suppress(Exception):
            self.dashboard.set_desktop_companion_gesture_status("wave")

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
            int(
                self.db.setting(
                    "voice_volume_percent", DEFAULT_VOICE_VOLUME_PERCENT
                )
            ),
            bool(self.db.setting("voice_muted", False)),
        )
        self.background_scheduler: ManagerWorkerScheduler | None = None
        self.dashboard.settings_saved.connect(self._reload_physics_settings)
        self.dashboard.settings_saved.connect(self._reload_profile)
        self.dashboard.settings_saved.connect(self._reload_background_agents)
        self.dashboard.settings_saved.connect(
            self._reload_proactive_companion_app_bridge
        )
        # Saved welcome/silence thresholds must reach the running arbiter, and
        # the performance/framing preference caches must follow the stores.
        self.dashboard.settings_saved.connect(self._refresh_multisensory_config)
        self.dashboard.settings_saved.connect(self._reload_preference_caches)
        self.proactive_presence_timer = QTimer(self)
        self.proactive_presence_timer.setInterval(60_000)
        self.proactive_presence_timer.timeout.connect(self._consider_desktop_presence)
        self.proactive_presence_timer.start()

    def _reload_preference_caches(self) -> None:
        """Load the typed performance/framing preferences from their stores.

        Domain defaults are deliberately conservative (360°, back views and
        camera-context performances start disabled) and apply whenever the
        user never saved the preferences.
        """
        self._performance_preferences_cache = (
            self._performance_preferences_store.load()
        )
        self._framing_preferences_cache = self._framing_preferences_store.load()

    def _current_performance_preferences(self) -> PerformancePreferences:
        cached = getattr(self, "_performance_preferences_cache", None)
        return cached if cached is not None else PerformancePreferences()

    def _current_framing_preferences(self) -> FramingPreferences:
        cached = getattr(self, "_framing_preferences_cache", None)
        return cached if cached is not None else FramingPreferences()

    def _observe_personality_mirror(self) -> None:
        """Feed the recent conversation window into the personality mirror.

        The mirror reads the full recent dialogue (up to the 1M-token context)
        but reduces it to cheap scalar signals, so it never blocks the UI.
        """
        mirror = getattr(self, "personality_mirror_state", None)
        if mirror is None:
            return
        window = " ".join(
            str(row["content"]) for row in self.db.recent_chat(64)
        )
        mirror.observe_conversation(window)

    def _apply_weather_and_satiety(self) -> None:
        """Drive wardrobe intuition and satiety from the persisted weather.

        The wardrobe runtime writes ``weather_temperature_c`` and
        ``weather_condition`` settings; this method reads them, derives the
        outfit-weight suggestion and comfort verdict, and refreshes the
        satiety-driven blink interval so a hungry companion blinks sluggishly.
        """
        temperature_c = float(
            self.db.setting(
                "weather_temperature_c", DEFAULT_WEATHER_TEMPERATURE_C
            )
        )
        language = str(self.db.setting("ui_language", "zh-TW"))
        # Wardrobe intuition: suggest an outfit weight for the temperature and
        # judge the currently worn weight against it.
        suggested = suggested_weight(temperature_c)
        current_weight = OutfitWeight(
            str(self.db.setting("wardrobe_current_weight", suggested.value))
        )
        verdict = comfort_verdict(temperature_c, current_weight)
        self._wardrobe_suggestion = suggested.value
        self._wardrobe_verdict = verdict.value
        complaint = complaint_line(language, verdict)
        if complaint:
            self._wardrobe_complaint = complaint
        # Satiety: refresh the sluggish-blink interval from the current level.
        satiety = getattr(self, "satiety_state", None)
        if satiety is not None:
            self._satiety_blink_interval = satiety.blink_interval()
            self.db.set_setting("satiety_value", satiety.snapshot())

    def _persist_affection(self) -> None:
        """Write the companion's exclusive-favor coefficients to the dedicated
        ``companion_affection`` table so the expression arbiter can read one
        consistent snapshot (favor, trust, jealousy, satiety, devotion bonus)."""
        favor = getattr(self, "favor_exclusive_state", None)
        satiety = getattr(self, "satiety_state", None)
        affinity = getattr(self, "affinity_state", None)
        favor_score = favor.snapshot() if favor is not None else 0.0
        satiety_level = satiety.snapshot() if satiety is not None else 1.0
        jealousy_meter = (
            affinity.snapshot().jealousy if affinity is not None else 0.0
        )
        trust_level = (
            affinity.snapshot().affinity if affinity is not None else 0.0
        )
        devotion_bonus = (
            DEVOTION_PRIORITY_BONUS
            if favor_score >= FAVOR_DEVOTED_THRESHOLD
            else 0
        )
        self.db.upsert_affection(
            favor_score=favor_score,
            trust_level=trust_level,
            jealousy_meter=jealousy_meter,
            satiety_level=satiety_level,
            devotion_bonus=devotion_bonus,
            last_interaction_ts=local_wall_time().isoformat(timespec="seconds"),
        )

    def _apply_multimodal_result(self, result: object) -> None:
        if not isinstance(result, MultimodalFusionResult):
            return
        now = time.monotonic()
        face = result.face
        if face is not None and face.gaze_confidence >= GAZE_CONFIDENCE_THRESHOLD:
            self._sensory_gaze_target = (
                max(-1.0, min(1.0, -face.gaze_x)),
                max(-1.0, min(1.0, face.gaze_y)),
            )
            self._sensory_gaze_expires_at = now + 0.90
        # Shy gaze aversion: when the user stares at the companion for a
        # sustained stretch, she glances down and away for a few seconds.  The
        # offset is small and downward so it reads as bashful, never an eye-roll.
        # It is kept in a separate field so it never pollutes the raw sensory
        # gaze target; the visual dynamics layer applies it on top.
        shy = getattr(self, "shy_gaze_state", None)
        if shy is not None and face is not None:
            aversion = shy.update(gaze_confidence=face.gaze_confidence, now=now)
            self._shy_gaze_offset = aversion
        # Shyness micro-expression chain: gaze + favor + context drive a
        # continuous shyness level, which is blended into the face-motion frame
        # so the blush/gaze/lip cascade grows on top of the current emotion.
        shyness = getattr(self, "shyness_state", None)
        if shyness is not None and face is not None:
            favor = getattr(self, "favor_exclusive_state", None)
            favor_score = favor.snapshot() if favor is not None else 0.0
            expression = getattr(self, "current_expression", "")
            self._shyness_level = shyness.update(
                gaze_confidence=face.gaze_confidence,
                favor=favor_score,
                expression=expression,
            )
            motion = getattr(self, "face_motion_frame", None)
            if motion is not None:
                self.face_motion_frame = blend_shyness(
                    motion,
                    self._shyness_level,
                )
        if (
            "smile-like" in result.events
            and now - getattr(self, "_last_multimodal_smile_at", 0.0) >= SMILE_COOLDOWN_SECONDS
        ):
            self._last_multimodal_smile_at = now
            self.set_state(
                "gentle_smile_front",
                source="visual",
                intensity=0.35,
            )
        # Mirroring: when the user rests their chin (a thoughtful or tired
        # posture), the companion mirrors a gentle thinking pose instead of
        # staying neutral.  This is a quiet, non-verbal act of empathy that
        # makes the companion feel present without interrupting.
        if (
            "resting-chin" in result.events
            and now - getattr(self, "_last_multimodal_chin_at", 0.0) >= CHIN_COOLDOWN_SECONDS
        ):
            self._last_multimodal_chin_at = now
            self.set_state(
                "thinking_front",
                source="visual",
                intensity=0.30,
            )
        # Mirroring: a furrowed brow (brow tension) is met with a gentle,
        # concerned expression rather than a neutral face.  This is a quiet
        # non-verbal acknowledgment that the companion notices the user's
        # tension without interrupting.
        if (
            "brow-tension-like" in result.events
            and now - getattr(self, "_last_multimodal_brow_at", 0.0) >= BROW_COOLDOWN_SECONDS
        ):
            self._last_multimodal_brow_at = now
            self.set_state(
                "worried_front",
                source="visual",
                intensity=0.30,
            )
        # Crimson Flame resonance: a furrowed brow (brow tension) feeds a smooth
        # resonance level that shortens the idle breathing period and quickens
        # the blink rate, so the companion's body mirrors the user's agitation.
        # The typing-rate input is left at zero here because keystroke sampling
        # belongs to a separate background slot; brow tension alone is enough to
        # drive the resonance without blocking the Qt main thread.
        resonance = getattr(self, "emotional_resonance_state", None)
        if resonance is not None and face is not None:
            resonance.update(
                brow_tension=face.brow_tension,
                typing_rate_kps=0.0,
                now=now,
            )
            self._resonance_breath_period = resonance.breath_period()
        if (
            "high-five" in result.events
            and now - getattr(self, "_last_multimodal_high_five_at", 0.0) >= HIGH_FIVE_COOLDOWN_SECONDS
        ):
            self._last_multimodal_high_five_at = now
            self.set_state("happy", source="visual", intensity=0.75)
            # A palm-up high-five is a cross-dimensional hand-hold: a warm
            # gesture that spikes affection.
            affinity = getattr(self, "affinity_state", None)
            if affinity is not None:
                snapshot = affinity.note_affection_boost()
                self.db.set_setting("affinity_value", snapshot.affinity)
                self.db.set_setting("jealousy_value", snapshot.jealousy)
                self.db.set_setting(
                    "affinity_interaction_count", snapshot.interaction_count
                )
            favor = getattr(self, "favor_exclusive_state", None)
            if favor is not None:
                self.db.set_setting("favor_value", favor.note_gesture())
            self._persist_affection()
            language = str(self.db.setting("ui_language", "zh-TW"))
            responses = {
                "zh-TW": "擊掌！今日也配合得很好。",
                "zh-CN": "击掌！今天也配合得很好。",
                "en": "High five! We worked well together today.",
                "ja-JP": "ハイタッチ！今日も息がぴったりですね。",
            }
            self.speak(responses.get(language, responses["zh-TW"]), "happy")
        # Cross-dimensional feeding: a pinch gesture released near the companion
        # reads as the user offering her a treat.  She opens her lips, smiles,
        # and her affection spikes.
        if (
            "pinch" in result.events
            and now - getattr(self, "_last_multimodal_pinch_at", 0.0) >= PINCH_COOLDOWN_SECONDS
        ):
            self._last_multimodal_pinch_at = now
            self.set_state("happy", source="visual", intensity=0.65)
            affinity = getattr(self, "affinity_state", None)
            if affinity is not None:
                snapshot = affinity.note_affection_boost()
                self.db.set_setting("affinity_value", snapshot.affinity)
                self.db.set_setting("jealousy_value", snapshot.jealousy)
                self.db.set_setting(
                    "affinity_interaction_count", snapshot.interaction_count
                )
            favor = getattr(self, "favor_exclusive_state", None)
            if favor is not None:
                self.db.set_setting("favor_value", favor.note_gesture())
            self._persist_affection()
            language = str(self.db.setting("ui_language", "zh-TW"))
            responses = {
                "zh-TW": "主上餵妾的……妾、妾便收下了。",
                "zh-CN": "主上喂妾的……妾、妾便收下了。",
                "en": "A treat from you… I shall accept it.",
                "ja-JP": "主上から頂いたもの……妾、頂戴いたします。",
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
        # Camera gestures may temporarily silence this process, but never
        # persist a global mute preference across application restarts.
        self._gesture_audio_muted = False
        self.state = "idle"
        self.expression_generation = 0
        self.expression_arbiter = ExpressionArbiter(
            set(EXPRESSION_POSES) | {"idle", "speaking"}
        )
        self.affective_state = AffectiveState()
        self.affinity_state = AffinityState(
            affinity=float(self.db.setting("affinity_value", 0.0)),
            jealousy=float(self.db.setting("jealousy_value", 0.0)),
            interaction_count=int(self.db.setting("affinity_interaction_count", 0)),
        )
        self.shy_gaze_state = ShyGazeState()
        self._shy_gaze_offset: tuple[float, float] | None = None
        self._shy_gaze_offset_current: tuple[float, float] = (0.0, 0.0)
        self.shyness_state = ShynessState()
        self._shyness_level = 0.0
        self.emotional_resonance_state = EmotionalResonanceState()
        self._resonance_breath_period = 72.0
        self.time_sovereignty_state = TimeSovereigntyState()
        self.sword_soul_resonance_state = SwordSoulResonanceState()
        self.shared_chronicle = Chronicle(
            (
                Milestone(MilestoneKind.FIRST_RELEASE, 20),
            )
        )
        self._sword_soul_gaze_linger = 0.0
        self._sensory_weather_mood = WeatherMood.CLEAR
        self._sensory_rain_alpha = 0.0
        self._sensory_sweat_frequency = 0.0
        self._drowsy_blink_interval: float | None = None
        self._satiety_blink_interval: float | None = None
        self._wardrobe_suggestion: str = "moderate"
        self._wardrobe_verdict: str = "comfortable"
        self._wardrobe_complaint: str = ""
        self.personality_mirror_state = PersonalityMirrorState()
        self.satiety_state = SatietyState(
            satiety=float(self.db.setting("satiety_value", 1.0)),
        )
        self.favor_exclusive_state = FavorExclusiveState(
            favor=float(self.db.setting("favor_value", 0.0)),
        )
        self.active_ai_wait_generation = 0
        self.active_ai_wait_expression = ""
        self.speech_queue: deque[QueuedSpeech] = deque()
        self.speech_playing = False
        self.active_speech_text = ""
        self.active_speech_engine = ""
        self.active_speech_source = ""
        self.active_speech_delivery_token = ""
        self.speech_playback_generation = 0
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
        # Typed preference stores are the single source of truth for the
        # performance and framing preferences (domain defaults apply when the
        # user never saved them).  The caches refresh on every settings save.
        settings_port = StudioDBSettingsPort(self.db)
        self._performance_preferences_store = PerformancePreferencesStore(
            settings_port
        )
        self._framing_preferences_store = FramingPreferencesStore(settings_port)
        self._reload_preference_caches()
        self._latest_visual_scene = None
        self._recognized_scene_streak = 0
        self._last_wave_acknowledged_at = float("-inf")
        self._multisensory_variation_index = int(
            self.db.setting("multisensory_variation_index", 0)
        )
