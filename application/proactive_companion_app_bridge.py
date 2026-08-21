from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from datetime import datetime, timedelta
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from application.companion_phrasebook import CompanionPhrasebook
lazy from application.proactive_companion_runtime import (
    ApprovedPerformanceCue,
    NormalizedCompanionEnvironment,
    ProactiveCompanionRequest,
)
lazy from application.visual_perception import PresenceState
lazy from application.wellbeing_app_bridge import ReminderTrigger, SpeakRequest
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)

_PENDING_SPEECH_TIMEOUT = timedelta(minutes=5)


class ProactiveAppDisposition(StrEnum):
    SUBMITTED = "submitted"
    BYPASSED = "bypassed"
    STALE = "stale"
    DUPLICATE = "duplicate"
    CLOSED = "closed"
    LKG = "last-known-good"


@dataclass(frozen=True, slots=True)
class ProactiveAppState:
    generation: int
    now: datetime
    language: str
    user_title: str
    session_user_active: bool
    camera_enabled: bool
    camera_presence: PresenceState = PresenceState.UNKNOWN
    camera_absence_seconds: float = 0.0
    recognized_user: bool = False
    focus_active: bool = False
    meeting_active: bool = False
    fullscreen_active: bool = False
    speech_active: bool = False
    seconds_since_user_interaction: float = 0.0
    enabled: bool = True
    pending_outfit_id: str = ""
    user_looking: bool = False
    visual_presence_arrival: bool = False
    visual_activity: bool = False
    proactive_mode: str = "balanced"
    memory_topics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Proactive app generation must not be negative.")
        if self.now.tzinfo is None:
            raise ValueError("Proactive app time must be timezone-aware.")
        if self.camera_absence_seconds < 0.0:
            raise ValueError("Camera absence duration must not be negative.")
        if self.seconds_since_user_interaction < 0.0:
            raise ValueError("User interaction age must not be negative.")
        if not self.language.strip() or not self.user_title.strip():
            raise ValueError("App language and user title must not be empty.")
        if self.recognized_user and (
            not self.camera_enabled
            or self.camera_presence is not PresenceState.PRESENT
        ):
            raise ValueError("Recognition requires an enabled camera and presence.")
        if self.visual_presence_arrival and (
            not self.camera_enabled
            or self.camera_presence is not PresenceState.PRESENT
        ):
            raise ValueError("Visual arrival requires an enabled camera and presence.")
        if self.visual_activity and (
            not self.camera_enabled
            or self.camera_presence is not PresenceState.PRESENT
        ):
            raise ValueError("Visual activity requires an enabled camera and presence.")


@dataclass(frozen=True, slots=True)
class ProactiveAppEvent:
    state: ProactiveAppState
    timer_trigger: ReminderTrigger | None = None
    scheduled_request: SpeakRequest | None = None

    def __post_init__(self) -> None:
        if self.timer_trigger is not None and self.scheduled_request is not None:
            raise ValueError("A proactive event cannot contain two timer requests.")


@dataclass(frozen=True, slots=True)
class ProactiveAppResult:
    disposition: ProactiveAppDisposition
    request: ProactiveCompanionRequest | None


class ProactiveRuntimePort(Protocol):
    def propose(
        self,
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> ProactiveCompanionRequest | None: ...

    def report_spoken(self, delivery_token: str, *, succeeded: bool) -> bool: ...


class ProactivityPreferencesPort(Protocol):
    def load(self) -> CompanionProactivityPreferences: ...


class PhrasebookPort(Protocol):
    def load(self) -> CompanionPhrasebook: ...


SpeechCompletion = Callable[[bool], None]


class SpeechSubmitPort(Protocol):
    def submit(
        self,
        request: SpeakRequest,
        performance: ApprovedPerformanceCue,
        *,
        generation: int,
        completed: SpeechCompletion,
    ) -> bool: ...


class RuntimeFactory(Protocol):
    def __call__(self, phrasebook: CompanionPhrasebook) -> ProactiveRuntimePort: ...


@dataclass(slots=True)
class _PendingSpeech:
    generation: int
    submitted_at: datetime
    request: ProactiveCompanionRequest
    completed: bool = False


class ProactiveCompanionAppBridge:
    """Normalize app state and submit one approved request to the speech port."""

    def __init__(
        self,
        runtime_factory: RuntimeFactory,
        preferences: ProactivityPreferencesPort,
        phrasebook: PhrasebookPort,
        speech: SpeechSubmitPort,
    ) -> None:
        self._preferences = preferences
        self._phrasebook = phrasebook
        self._speech = speech
        self._runtime = runtime_factory(phrasebook.load())
        self._seen_generation = -1
        self._submission_generation = -1
        self._closed = False
        self._last_signature: tuple[object, ...] | None = None
        self._last_good: ProactiveCompanionRequest | None = None
        self._pending: dict[str, _PendingSpeech] = {}

    @property
    def last_known_good(self) -> ProactiveCompanionRequest | None:
        return self._last_good

    def dispatch(self, event: ProactiveAppEvent) -> ProactiveAppResult:
        self._expire_pending(event.state.now)
        signature, terminal = self._preflight(event)
        if terminal is not None:
            return terminal
        state = event.state
        if self._has_pending_generation(state.generation):
            return self._result(ProactiveAppDisposition.DUPLICATE)
        return self._dispatch_new(event, signature)

    def _dispatch_new(
        self,
        event: ProactiveAppEvent,
        signature: tuple[object, ...],
    ) -> ProactiveAppResult:
        state = event.state
        try:
            preferences = self._preferences.load()
            request = self._runtime.propose(
                _environment(event),
                preferences,
            )
        except (LookupError, RuntimeError, TypeError, ValueError):
            return self._result(ProactiveAppDisposition.LKG, last_good=True)
        self._seen_generation = max(self._seen_generation, state.generation)
        self._last_signature = signature
        if request is None:
            return self._result(ProactiveAppDisposition.BYPASSED)
        self._retire_superseded(state.generation)
        if self._pending:
            self._runtime.report_spoken(
                request.delivery_token,
                succeeded=False,
            )
            return self._result(ProactiveAppDisposition.DUPLICATE)

        self._submission_generation = max(
            self._submission_generation,
            state.generation,
        )
        pending = _PendingSpeech(state.generation, state.now, request)
        self._pending[request.delivery_token] = pending
        submitted = self._submit(pending)
        if not submitted:
            self._finish(request.delivery_token, succeeded=False)
            return self._result(ProactiveAppDisposition.LKG, last_good=True)
        self._last_good = request
        return ProactiveAppResult(ProactiveAppDisposition.SUBMITTED, request)

    def _has_pending_generation(self, generation: int) -> bool:
        return any(
            pending.generation == generation
            for pending in self._pending.values()
        )

    def _result(
        self,
        disposition: ProactiveAppDisposition,
        *,
        last_good: bool = False,
    ) -> ProactiveAppResult:
        return ProactiveAppResult(
            disposition,
            self._last_good if last_good else None,
        )

    def _preflight(
        self,
        event: ProactiveAppEvent,
    ) -> tuple[tuple[object, ...], ProactiveAppResult | None]:
        state = event.state
        signature = _event_signature(event)
        disposition = (
            ProactiveAppDisposition.CLOSED
            if self._closed
            else ProactiveAppDisposition.BYPASSED
            if not state.enabled
            else ProactiveAppDisposition.STALE
            if state.generation < self._seen_generation
            else ProactiveAppDisposition.DUPLICATE
            if signature == self._last_signature
            else None
        )
        terminal = (
            ProactiveAppResult(disposition, None)
            if disposition is not None
            else None
        )
        return signature, terminal

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for token in tuple(self._pending):
            self._finish(token, succeeded=False)

    def _submit(self, pending: _PendingSpeech) -> bool:
        request = pending.request

        def completed(succeeded: bool) -> None:
            self._finish(request.delivery_token, succeeded=succeeded)

        try:
            return bool(
                self._speech.submit(
                    request.speak,
                    request.performance,
                    generation=pending.generation,
                    completed=completed,
                )
            )
        except (RuntimeError, TypeError, ValueError):
            return False

    def _expire_pending(self, now: datetime) -> None:
        for token, pending in tuple(self._pending.items()):
            if pending.submitted_at + _PENDING_SPEECH_TIMEOUT <= now:
                self._finish(token, succeeded=False)

    def _retire_superseded(self, generation: int) -> None:
        for token, pending in tuple(self._pending.items()):
            if pending.generation < generation:
                self._finish(token, succeeded=False)

    def _finish(self, delivery_token: str, *, succeeded: bool) -> None:
        pending = self._pending.pop(delivery_token, None)
        if pending is None or pending.completed:
            return
        pending.completed = True
        valid = bool(
            succeeded
            and not self._closed
            and pending.generation >= self._submission_generation
        )
        self._runtime.report_spoken(delivery_token, succeeded=valid)


def _environment(event: ProactiveAppEvent) -> NormalizedCompanionEnvironment:
    state = event.state
    visual_presence = bool(
        state.camera_enabled
        and state.camera_presence is PresenceState.PRESENT
    )
    timer_event = bool(
        event.timer_trigger is not None or event.scheduled_request is not None
    )
    user_present = (
        state.session_user_active
        if timer_event
        else visual_presence
        if state.camera_enabled
        else state.session_user_active
    )
    absence = state.camera_absence_seconds if state.camera_enabled else 0.0
    return NormalizedCompanionEnvironment(
        now=state.now,
        user_present=user_present,
        absence_duration_seconds=absence,
        focus_active=state.focus_active,
        meeting_active=state.meeting_active,
        fullscreen_active=state.fullscreen_active,
        seconds_since_user_interaction=state.seconds_since_user_interaction,
        reminder_trigger=event.timer_trigger,
        scheduled_request=event.scheduled_request,
        language=state.language,
        user_title=state.user_title,
        speech_active=state.speech_active,
        pending_outfit_id=state.pending_outfit_id,
        user_looking=state.user_looking,
        visual_presence_arrival=state.visual_presence_arrival,
        visual_activity=state.visual_activity,
        proactive_mode=state.proactive_mode,
        memory_topics=state.memory_topics,
    )


def _event_signature(event: ProactiveAppEvent) -> tuple[object, ...]:
    state = event.state
    return (
        state.generation,
        state.now,
        state.session_user_active,
        state.camera_enabled,
        state.camera_presence,
        state.camera_absence_seconds,
        state.recognized_user,
        state.focus_active,
        state.meeting_active,
        state.fullscreen_active,
        state.speech_active,
        state.seconds_since_user_interaction,
        state.pending_outfit_id,
        state.user_looking,
        state.visual_presence_arrival,
        state.visual_activity,
        state.proactive_mode,
        state.memory_topics,
        event.timer_trigger,
        (
            event.scheduled_request.cue_token
            if event.scheduled_request is not None
            else None
        ),
    )
