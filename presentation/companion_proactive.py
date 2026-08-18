from __future__ import annotations

lazy import time
lazy from collections import deque
lazy from collections.abc import Callable

lazy from application.desktop_presence import seconds_since_local_input
lazy from application.multisensory_interaction import (
    MultisensoryInteractionArbiter,
    WelcomeTimingRules,
)
lazy from application.presentation_ports import PresentationDatabasePort
lazy from application.proactive_companion_app_bridge import (
    ProactiveAppEvent,
    ProactiveAppState,
    ProactiveCompanionAppBridge,
)
lazy from application.proactive_companion_composition import (
    create_proactive_companion_bridge,
)
lazy from application.visual_perception import (
    ActivityState,
    PresenceState,
    VisualObservation,
)
lazy from application.wellbeing_app_bridge import ReminderTrigger
lazy from application.wellbeing_app_bridge import SpeakRequest as ProactiveSpeakRequest
lazy from domain.app_profile import personalize_text, profile_setting
lazy from domain.speech_configuration import QueuedSpeech
lazy from domain.time_utils import local_aware_time
lazy from domain.vision_domain import IdentityState

__all__ = ("CompanionProactiveMixin",)

ProactiveCompanionFactory = Callable[
    [
        PresentationDatabasePort,
        Callable[[str, str, str, Callable[[bool], None]], bool],
    ],
    ProactiveCompanionAppBridge,
]


class CompanionProactiveMixin:
    def _initialize_proactive_companion_app_bridge(
        self,
        factory: ProactiveCompanionFactory | None,
    ) -> None:
        self._proactive_generation = 0
        self._latest_visual_observation: VisualObservation | None = None
        self._camera_away_started_at: float | None = None
        selected_factory = factory or create_proactive_companion_bridge
        self._proactive_companion_factory = selected_factory
        try:
            self._proactive_companion_bridge = selected_factory(
                self.db,
                self._enqueue_proactive_speech,
            )
        except (LookupError, RuntimeError, TypeError, ValueError):
            self._proactive_companion_bridge = None

    def _reload_proactive_companion_app_bridge(self) -> None:
        factory = getattr(self, "_proactive_companion_factory", None)
        if factory is None or self._closing:
            return
        self._close_proactive_companion_app_bridge()
        self._initialize_proactive_companion_app_bridge(factory)

    def _enqueue_proactive_speech(
        self,
        text: str,
        state: str,
        delivery_token: str,
        completed: Callable[[bool], None],
    ) -> bool:
        if self._closing or not text.strip() or not delivery_token:
            return False
        if delivery_token in self._proactive_speech_completions:
            return False
        self._proactive_speech_completions[delivery_token] = completed
        self.speech_queue.append(
            QueuedSpeech(
                personalize_text(self.db, text),
                state,
                source="proactive",
                delivery_token=delivery_token,
                completed=completed,
            )
        )
        self._start_next_speech()
        return True

    def _complete_proactive_companion_speech(self, succeeded: bool) -> None:
        token = self.active_speech_delivery_token
        if not token:
            return
        self.active_speech_delivery_token = ""
        completed = self._proactive_speech_completions.pop(token, None)
        if completed is not None:
            completed(bool(succeeded))

    def _close_proactive_companion_app_bridge(self) -> None:
        bridge = getattr(self, "_proactive_companion_bridge", None)
        self._proactive_companion_bridge = None
        if bridge is not None:
            bridge.close()
        self.active_speech_delivery_token = ""
        self.speech_queue = deque(
            queued
            for queued in self.speech_queue
            if not queued.delivery_token
        )
        self._proactive_speech_completions.clear()

    def _dispatch_proactive_companion(
        self,
        timer_trigger: ReminderTrigger | None = None,
        scheduled_request: ProactiveSpeakRequest | None = None,
        camera_observation: VisualObservation | None = None,
        visual_presence_arrival: bool = False,
    ):
        bridge = getattr(self, "_proactive_companion_bridge", None)
        if bridge is None or self._closing:
            return None
        if camera_observation is not None:
            self._latest_visual_observation = camera_observation
        observation = self._latest_visual_observation
        center = getattr(self.dashboard, "flagship_center", None)
        camera_enabled = bool(
            center is not None and center.camera_presence.camera is not None
        )
        presence = (
            observation.presence
            if camera_enabled and observation is not None
            else PresenceState.UNKNOWN
        )
        monotonic_now = time.monotonic()
        if (
            camera_enabled
            and presence is PresenceState.AWAY
            and self._camera_away_started_at is None
        ):
            self._camera_away_started_at = monotonic_now
        absence_seconds = (
            max(0.0, monotonic_now - self._camera_away_started_at)
            if self._camera_away_started_at is not None
            else 0.0
        )
        if camera_enabled and presence is PresenceState.PRESENT:
            self._camera_away_started_at = None
        idle_seconds = seconds_since_local_input()
        session_user_active = bool(
            idle_seconds is not None and idle_seconds <= 120.0
        )
        require_identity = bool(
            self.db.setting("face_identity_enabled", False)
        )
        recognized = bool(
            camera_enabled
            and presence is PresenceState.PRESENT
            and self._recognized_scene_streak >= 3
        )
        self._proactive_generation += 1
        proactive_mode = MultisensoryInteractionArbiter._mode_key(
            str(self.db.setting("proactive_mode", "平衡（推薦）"))
        )
        state = ProactiveAppState(
            generation=self._proactive_generation,
            now=local_aware_time(),
            language=profile_setting(self.db, "ui_language"),
            user_title=profile_setting(self.db, "user_title"),
            session_user_active=session_user_active,
            camera_enabled=camera_enabled,
            camera_presence=presence,
            camera_absence_seconds=absence_seconds,
            recognized_user=recognized,
            focus_active=False,
            meeting_active=False,
            fullscreen_active=False,
            speech_active=bool(
                self.speech_playing
                or getattr(self, "realtime_mouth_active", False)
                or getattr(self.realtime, "running", False)
                or getattr(self.listener, "is_recording", False)
            ),
            seconds_since_user_interaction=max(0.0, idle_seconds or 0.0),
            enabled=bool(
                self.db.setting("proactive_interaction_enabled", True)
                and (
                    timer_trigger is not None
                    or scheduled_request is not None
                    or not require_identity
                    or recognized
                    or not camera_enabled
                )
            ),
            pending_outfit_id=str(
                self.db.setting("wardrobe_reveal_pending_outfit_id", "")
                or ""
            ),
            user_looking=bool(
                recognized or (not camera_enabled and session_user_active)
            ),
            visual_presence_arrival=bool(
                visual_presence_arrival
                and camera_enabled
                and presence is PresenceState.PRESENT
            ),
            proactive_mode=proactive_mode,
        )
        return bridge.dispatch(
            ProactiveAppEvent(state, timer_trigger, scheduled_request)
        )

    def _note_human_interaction(self) -> None:
        self.multisensory_arbiter.note_human_interaction()

    def _current_multisensory_config(self) -> tuple[float, float, float, float]:
        return (
            float(
                self.db.setting("multisensory_welcome_minimum_seconds", 60)
            ),
            float(
                self.db.setting(
                    "multisensory_welcome_brief_max_seconds", 30 * 60
                )
            ),
            float(
                self.db.setting(
                    "multisensory_welcome_long_seconds", 4 * 60 * 60
                )
            ),
            float(
                self.db.setting(
                    "multisensory_conversation_silence_seconds", 45 * 60
                )
            ),
        )

    @staticmethod
    def _new_multisensory_arbiter(
        config: tuple[float, float, float, float],
    ) -> MultisensoryInteractionArbiter:
        minimum, brief, long_away, conversation = config
        try:
            timing = WelcomeTimingRules(minimum, brief, long_away)
        except ValueError:
            timing = WelcomeTimingRules()
        return MultisensoryInteractionArbiter(
            timing=timing,
            conversation_silence_seconds=conversation,
        )

    def _refresh_multisensory_config(self) -> None:
        current = self._current_multisensory_config()
        if current == self._multisensory_config:
            return
        self._multisensory_config = current
        self.multisensory_arbiter = self._new_multisensory_arbiter(current)

    def _remember_visual_scene(self, scene) -> None:
        self._latest_visual_scene = scene
        identity = getattr(scene, "identity", None)
        if getattr(identity, "state", None) is IdentityState.RECOGNIZED:
            self._recognized_scene_streak += 1
        else:
            self._recognized_scene_streak = 0

    def _consider_visual_interaction(self, observation) -> None:
        if not isinstance(observation, VisualObservation):
            return
        now = time.monotonic()
        previous = getattr(
            self,
            "_desktop_visual_presence",
            PresenceState.UNKNOWN,
        )
        self._desktop_visual_presence = observation.presence
        self.dashboard.set_desktop_companion_visual_status(
            "present"
            if observation.presence is PresenceState.PRESENT
            else "away"
            if observation.presence is PresenceState.AWAY
            else "unknown",
            active=observation.activity is ActivityState.ACTIVE,
        )
        if observation.presence is PresenceState.PRESENT:
            self.set_state(
                "gentle_smile_front",
                source="visual",
                intensity=0.35,
            )
            if previous is not PresenceState.PRESENT:
                self.set_state("happy", source="visual", intensity=0.50)
        if (
            observation.activity is ActivityState.ACTIVE
            and now - getattr(self, "_last_visual_motion_at", 0.0) >= 2.0
        ):
            self._last_visual_motion_at = now
            self.set_state("happy", source="visual", intensity=0.50)
        arrival = bool(
            observation.presence is PresenceState.PRESENT
            and previous is not PresenceState.PRESENT
            and now - getattr(self, "_last_visual_arrival_at", float("-inf"))
            >= 90.0
        )
        if arrival:
            self._last_visual_arrival_at = now
        self._dispatch_proactive_companion(
            camera_observation=observation,
            visual_presence_arrival=arrival,
        )

    def _consider_desktop_presence(self) -> None:
        center = getattr(self.dashboard, "flagship_center", None)
        camera_active = bool(
            center is not None and center.camera_presence.camera is not None
        )
        if camera_active:
            return
        idle_seconds = seconds_since_local_input()
        if idle_seconds is None:
            return
        self._dispatch_proactive_companion()
