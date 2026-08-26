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
lazy from domain.sensory_synesthesia import (
    complaint_line as sensory_complaint_line,
    rain_alpha,
    sweat_frequency,
    weather_mood,
)
lazy from domain.somniloquy import random_somniloquy, should_murmur
lazy from domain.speech_configuration import QueuedSpeech
lazy from presentation.companion_speech_queue import enqueue_bounded_speech
lazy from domain.time_utils import local_aware_time

IDLE_SECONDS_THRESHOLD = 120.0
RECOGNIZED_STREAK_THRESHOLD = 3
MAX_TOPIC_LENGTH = 40
VISUAL_MOTION_INTERVAL = 2.0
VISUAL_ARRIVAL_INTERVAL = 90.0
VISUAL_ACTIVITY_ACTIVE_INTERVAL = 10.0 * 60.0
VISUAL_ACTIVITY_BALANCED_INTERVAL = 30.0 * 60.0
SENSORY_COMPLAINT_COOLDOWN_SECONDS = 2.0 * 60.0 * 60.0
SOMNILOQUY_DROWSINESS_THRESHOLD = 0.25
CHRONICLE_RECOLLECTION_IDLE_SECONDS = 120.0
PROJECT_START_DATE = (2026, 7, 28)
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
        queued = QueuedSpeech(
                personalize_text(self.db, text),
                state,
                source="proactive",
                delivery_token=delivery_token,
                completed=completed,
        )
        if not enqueue_bounded_speech(self.speech_queue, queued):
            return False
        self._proactive_speech_completions[delivery_token] = completed
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
        visual_activity: bool = False,
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
            idle_seconds is not None and idle_seconds <= IDLE_SECONDS_THRESHOLD
        )
        require_identity = bool(
            self.db.setting("face_identity_enabled", False)
        )
        recognized = bool(
            camera_enabled
            and presence is PresenceState.PRESENT
            and self._recognized_scene_streak >= RECOGNIZED_STREAK_THRESHOLD
        )
        self._proactive_generation += 1
        proactive_mode = MultisensoryInteractionArbiter._mode_key(
            str(
                self.db.setting(
                    "proactive_interaction_mode",
                    self.db.setting("proactive_mode", "balanced"),
                )
            )
        )
        memory_topics = (
            self._recent_memory_topics()
            if not require_identity or recognized
            else ()
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
            enabled=bool(self.db.setting("proactive_interaction_enabled", True)),
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
            visual_activity=bool(
                visual_activity
                and camera_enabled
                and presence is PresenceState.PRESENT
            ),
            proactive_mode=proactive_mode,
            memory_topics=memory_topics,
        )
        return bridge.dispatch(
            ProactiveAppEvent(state, timer_trigger, scheduled_request)
        )

    def _recent_memory_topics(self, limit: int = 3) -> tuple[str, ...]:
        """Return a few recent memory contents as natural conversation topics."""
        try:
            rows = self.db.list_memories(limit)
        except (AttributeError, LookupError):
            return ()
        topics = []
        for row in rows:
            content = str(row["content"] or "").strip()
            if content and len(content) <= MAX_TOPIC_LENGTH:
                topics.append(content)
        return tuple(topics)

    def _note_human_interaction(self) -> None:
        self.multisensory_arbiter.note_human_interaction()
        affinity = getattr(self, "affinity_state", None)
        if affinity is not None:
            snapshot = affinity.note_interaction()
            self.db.set_setting("affinity_value", snapshot.affinity)
            self.db.set_setting("jealousy_value", snapshot.jealousy)
            self.db.set_setting(
                "affinity_interaction_count", snapshot.interaction_count
            )

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
        # While the companion is speaking, visual presence/motion must not
        # switch the expression state.  A visual-triggered set_state would
        # leave the speaking state, freezing the mouth animation, and the
        # arrival/turn framing would keep rotating the body toward the camera
        # instead of letting the user converse in peace.
        speaking = bool(
            getattr(self, "speech_playing", False)
            or getattr(self, "state", "") == "speaking"
        )
        if not speaking:
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
                and now - getattr(self, "_last_visual_motion_at", 0.0) >= VISUAL_MOTION_INTERVAL
            ):
                self._last_visual_motion_at = now
                self.set_state("happy", source="visual", intensity=0.50)
        arrival = bool(
            observation.presence is PresenceState.PRESENT
            and previous is not PresenceState.PRESENT
            and now - getattr(self, "_last_visual_arrival_at", float("-inf"))
            >= VISUAL_ARRIVAL_INTERVAL
        )
        if arrival:
            self._last_visual_arrival_at = now
        mode = MultisensoryInteractionArbiter._mode_key(
            str(
                self.db.setting(
                    "proactive_interaction_mode",
                    self.db.setting("proactive_mode", "balanced"),
                )
            )
        )
        activity_interval = (
            VISUAL_ACTIVITY_ACTIVE_INTERVAL
            if mode == "active"
            else VISUAL_ACTIVITY_BALANCED_INTERVAL
        )
        activity_prompt = bool(
            not arrival
            and not speaking
            and mode != "quiet"
            and observation.presence is PresenceState.PRESENT
            and observation.activity is ActivityState.ACTIVE
            and now
            - getattr(self, "_last_visual_activity_prompt_at", float("-inf"))
            >= activity_interval
        )
        if activity_prompt:
            self._last_visual_activity_prompt_at = now
        self._dispatch_proactive_companion(
            camera_observation=observation,
            visual_presence_arrival=arrival,
            visual_activity=activity_prompt,
        )

    def _consider_desktop_presence(self) -> None:
        # Time sovereignty: sample the local hour on the existing presence timer
        # so the companion grows drowsy deep into the night without any blocking
        # work on the Qt main thread.
        sovereignty = getattr(self, "time_sovereignty_state", None)
        if sovereignty is not None:
            try:
                local_now = local_aware_time()
                hour = local_now.hour
            except (AttributeError, TypeError, ValueError):
                hour = 0
            sovereignty.update(hour=hour)
            self._drowsy_blink_interval = sovereignty.blink_interval()
        # Wardrobe intuition + satiety: refresh the outfit suggestion and the
        # sluggish-blink interval from the persisted weather and satiety level.
        apply_weather = getattr(self, "_apply_weather_and_satiety", None)
        if apply_weather is not None:
            apply_weather()
        idle_seconds = seconds_since_local_input()
        self._advance_soul_continuity(idle_seconds)
        center = getattr(self.dashboard, "flagship_center", None)
        camera_active = bool(
            center is not None and center.camera_presence.camera is not None
        )
        if camera_active:
            return
        if idle_seconds is None:
            return
        self._dispatch_proactive_companion()

    def _advance_soul_continuity(self, idle_seconds: float | None) -> None:
        """Connect the v4.3 soul modules to the existing one-minute runtime tick."""

        now = local_aware_time()
        start = now.date().replace(
            year=PROJECT_START_DATE[0],
            month=PROJECT_START_DATE[1],
            day=PROJECT_START_DATE[2],
        )
        elapsed_days = max(0, (now.date() - start).days)
        sword = getattr(self, "sword_soul_resonance_state", None)
        if sword is not None:
            sword.update(
                days=float(elapsed_days),
                commits=max(0, int(self.db.setting("sword_soul_commit_count", 0))),
            )
            self._sword_soul_gaze_linger = sword.gaze_linger()

        temperature = float(self.db.setting("weather_temperature_c", 24.0))
        condition = str(self.db.setting("weather_condition", "clear") or "clear")
        sensory = weather_mood(temperature, condition)
        self._sensory_rain_alpha = rain_alpha(sensory)
        self._sensory_sweat_frequency = sweat_frequency(sensory)
        previous = getattr(self, "_sensory_weather_mood", None)
        self._sensory_weather_mood = sensory
        monotonic_now = time.monotonic()
        can_speak = not bool(
            getattr(self, "speech_playing", False)
            or getattr(self, "realtime_mouth_active", False)
        )
        last_weather_line = getattr(
            self, "_last_sensory_weather_line_at", float("-inf")
        )
        if (
            sensory.value != "clear"
            and sensory != previous
            and can_speak
            and monotonic_now - last_weather_line >= SENSORY_COMPLAINT_COOLDOWN_SECONDS
        ):
            line = sensory_complaint_line(
                str(self.db.setting("ui_language", "zh-TW")), sensory
            )
            if line:
                self._last_sensory_weather_line_at = monotonic_now
                self.set_state("gentle_smile_front", source="visual", intensity=0.45)
                self.speak(line, "gentle_smile_front")
                return

        drowsiness = float(
            getattr(getattr(self, "time_sovereignty_state", None), "drowsiness", 0.0)
        )
        if (
            can_speak
            and (idle_seconds or 0.0) >= 10.0 * 60.0
            and drowsiness >= SOMNILOQUY_DROWSINESS_THRESHOLD
            and should_murmur()
        ):
            self.speak(
                random_somniloquy(str(self.db.setting("ui_language", "zh-TW"))),
                "gentle_smile_front",
            )
            return

        # Recall a shared milestone once on each 30-day project anniversary.
        if elapsed_days <= 0 or elapsed_days % 30:
            return
        if int(self.db.setting("chronicle_last_recollection_day", -1)) == elapsed_days:
            return
        chronicle = getattr(self, "shared_chronicle", None)
        if (
            chronicle is None
            or not can_speak
            or (idle_seconds or 0.0) < CHRONICLE_RECOLLECTION_IDLE_SECONDS
        ):
            return
        line = chronicle.recollection(
            str(self.db.setting("ui_language", "zh-TW")), elapsed_days
        )
        if line:
            self.db.set_setting("chronicle_last_recollection_day", elapsed_days)
            self.speak(line, "happy")
