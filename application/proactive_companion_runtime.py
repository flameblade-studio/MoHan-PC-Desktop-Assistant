from __future__ import annotations

lazy import hashlib
lazy from dataclasses import dataclass
lazy from datetime import date, datetime, timedelta
lazy from enum import IntEnum, StrEnum
lazy from typing import Protocol

lazy from application.companion_phrasebook import (
    CompanionPhrasebook,
    public_companion_line,
)
lazy from application.multisensory_interaction import (
    InteractionKind,
    InteractionTextContext,
    MultisensoryInteractionArbiter,
    ProactiveInteraction,
    WelcomeStyle,
    interaction_text,
)
lazy from application.outfit_reveal import (
    OutfitRevealContext,
    OutfitRevealCue,
    OutfitRevealStateStore,
    decide_outfit_reveal,
)
lazy from application.special_occasion import OccasionCue, OccasionKind, OccasionStage
lazy from application.wellbeing_app_bridge import ReminderTrigger, SpeakRequest
lazy from application.wellbeing_reminder import WellbeingCue, WellbeingKind
lazy from application.wellbeing_runtime import RuntimeAttention, RuntimeCue

MIN_ABSENCE_SECONDS = 60.0
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)

type ApprovedPerformanceCue = (
    WellbeingCue | OccasionCue | ProactiveInteraction | OutfitRevealCue
)

_PENDING_DELIVERY_TIMEOUT = timedelta(minutes=5)


class ProactiveSource(StrEnum):
    SCHEDULED = "scheduled"
    SPECIAL_OCCASION = "special_occasion"
    WELLBEING = "wellbeing"
    RETURN = "return"
    CHECK_IN = "check_in"
    WARDROBE = "wardrobe"
    VISUAL_PRESENCE = "visual_presence"
    VISUAL_ACTIVITY = "visual_activity"


class CandidatePriority(IntEnum):
    SCHEDULED = 110
    OCCASION_GRUMBLE = 100
    BIRTHDAY_HINT = 95
    OCCASION_HINT = 90
    MEAL = 80
    HYDRATION = 70
    REST = 60
    PROLONGED_SITTING = 50
    WARDROBE_REVEAL = 45
    LONG_RETURN = 40
    BRIEF_RETURN = 30
    VISUAL_PRESENCE = 35
    VISUAL_ACTIVITY = 25
    CHECK_IN = 20


@dataclass(frozen=True, slots=True)
class NormalizedCompanionEnvironment:
    now: datetime
    user_present: bool
    absence_duration_seconds: float
    focus_active: bool
    meeting_active: bool
    fullscreen_active: bool
    seconds_since_user_interaction: float
    reminder_trigger: ReminderTrigger | None
    language: str
    user_title: str
    scheduled_request: SpeakRequest | None = None
    speech_active: bool = False
    pending_outfit_id: str = ""
    user_looking: bool = False
    visual_presence_arrival: bool = False
    visual_activity: bool = False
    proactive_mode: str = "balanced"
    memory_topics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.now.tzinfo is None:
            raise ValueError("Companion environment time must be timezone-aware.")
        if self.absence_duration_seconds < 0.0:
            raise ValueError("Absence duration must not be negative.")
        if self.seconds_since_user_interaction < 0.0:
            raise ValueError("User interaction age must not be negative.")
        if not self.language.strip() or not self.user_title.strip():
            raise ValueError("Companion language and user title must not be empty.")


@dataclass(frozen=True, slots=True)
class ProactiveCompanionRequest:
    speak: SpeakRequest
    performance: ApprovedPerformanceCue
    source: ProactiveSource
    priority: CandidatePriority
    delivery_token: str


class WellbeingAppPort(Protocol):
    def request(
        self,
        trigger: ReminderTrigger | str,
        *,
        attention: RuntimeAttention,
        language: str,
        phrasebook: CompanionPhrasebook | None = None,
        enabled: bool = True,
    ) -> SpeakRequest | None: ...

    def report_spoken(self, cue_token: str, *, succeeded: bool) -> bool: ...


class ApprovedWellbeingCuePort(Protocol):
    def approved_cue(self, cue_token: str) -> WellbeingCue | None: ...


class SpecialOccasionServicePort(Protocol):
    def decide_special_occasion(
        self,
        attention: RuntimeAttention,
    ) -> RuntimeCue | None: ...

    def record_delivery(self, cue: RuntimeCue, *, succeeded: bool) -> bool: ...


@dataclass(frozen=True, slots=True)
class _Candidate:
    request: ProactiveCompanionRequest
    commit_payload: object


@dataclass(frozen=True, slots=True)
class _PendingCandidate:
    candidate: _Candidate
    expires_at: datetime


class ProactiveCompanionRuntime:
    """Choose one approved proactive interaction and commit only after speech."""

    def __init__(
        self,
        wellbeing: WellbeingAppPort,
        wellbeing_cues: ApprovedWellbeingCuePort,
        occasions: SpecialOccasionServicePort,
        *,
        phrasebook: CompanionPhrasebook | None = None,
        outfit_reveals: OutfitRevealStateStore | None = None,
    ) -> None:
        self._wellbeing = wellbeing
        self._wellbeing_cues = wellbeing_cues
        self._occasions = occasions
        self._phrasebook = phrasebook
        self._outfit_reveals = outfit_reveals
        self._pending: dict[str, _PendingCandidate] = {}
        self._pending_signatures: set[tuple[object, ...]] = set()
        self._delivered_date: date | None = None
        self._delivered_count = 0
        self._delivered_signatures: set[tuple[object, ...]] = set()

    def propose(
        self,
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> ProactiveCompanionRequest | None:
        self._rollover(environment.now)
        self._expire_pending(environment.now)
        if not self._may_interrupt(environment, preferences):
            return None
        if self._pending:
            return None
        if self._delivered_count >= preferences.daily_limit:
            return None
        candidates = tuple(
            candidate
            for candidate in (
                self._scheduled_candidate(environment),
                self._occasion_candidate(environment, preferences),
                self._wellbeing_candidate(environment, preferences),
                self._wardrobe_candidate(environment),
                self._visual_presence_candidate(environment),
                self._visual_activity_candidate(environment),
                self._return_candidate(environment, preferences),
                self._check_in_candidate(environment),
            )
            if candidate is not None
        )
        if (
            MultisensoryInteractionArbiter._mode_key(environment.proactive_mode)
            == "quiet"
        ):
            candidates = tuple(
                candidate
                for candidate in candidates
                if candidate.request.source
                in {ProactiveSource.SCHEDULED, ProactiveSource.WELLBEING}
            )
        available = tuple(
            item
            for item in candidates
            if _signature(item.request) not in self._pending_signatures
            and _signature(item.request) not in self._delivered_signatures
        )
        if not available:
            self._release_unselected(candidates, None)
            return None
        selected = max(available, key=lambda item: int(item.request.priority))
        self._release_unselected(candidates, selected)
        token = selected.request.delivery_token
        self._pending[token] = _PendingCandidate(
            selected,
            environment.now + _PENDING_DELIVERY_TIMEOUT,
        )
        self._pending_signatures.add(_signature(selected.request))
        return selected.request

    def _wardrobe_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
    ) -> _Candidate | None:
        outfit_id = environment.pending_outfit_id.strip()
        if not outfit_id or self._outfit_reveals is None:
            return None
        cue = decide_outfit_reveal(
            OutfitRevealContext(
                outfit_id=outfit_id,
                first_reveal_pending=True,
                user_present=environment.user_present,
                user_looking=environment.user_looking,
                speech_busy=environment.speech_active,
                do_not_disturb=(
                    environment.focus_active
                    or environment.meeting_active
                    or environment.fullscreen_active
                ),
            )
        )
        if cue is None:
            return None
        text = public_companion_line(
            environment.language,
            cue.phrase_key,
            phrasebook=self._phrasebook,
        )
        if not text:
            return None
        token = hashlib.sha256(
            f"wardrobe-reveal\0{outfit_id}".encode()
        ).hexdigest()
        return _Candidate(
            ProactiveCompanionRequest(
                SpeakRequest(text, ProactiveSource.WARDROBE.value, token),
                cue,
                ProactiveSource.WARDROBE,
                CandidatePriority.WARDROBE_REVEAL,
                token,
            ),
            outfit_id,
        )

    def report_spoken(self, delivery_token: str, *, succeeded: bool) -> bool:
        if not delivery_token or type(succeeded) is not bool:
            raise ValueError("Proactive delivery result is invalid.")
        pending = self._pending.pop(delivery_token, None)
        if pending is None:
            return False
        candidate = pending.candidate
        signature = _signature(candidate.request)
        self._pending_signatures.discard(signature)
        committed = self._commit(candidate, succeeded=succeeded)
        if not committed:
            return False
        self._delivered_count += 1
        self._delivered_signatures.add(signature)
        return True

    @staticmethod
    def _may_interrupt(
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> bool:
        return bool(
            preferences.enabled
            and environment.user_present
            and not environment.speech_active
            and not (
                preferences.focus_protection_enabled and environment.focus_active
            )
            and not (
                preferences.meeting_protection_enabled and environment.meeting_active
            )
            and not (
                preferences.fullscreen_protection_enabled
                and environment.fullscreen_active
            )
        )

    def _occasion_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> _Candidate | None:
        if not preferences.special_occasions_enabled:
            return None
        attention = _attention(environment, preferences)
        runtime_cue = self._occasions.decide_special_occasion(attention)
        if runtime_cue is None or not isinstance(runtime_cue.cue, OccasionCue):
            return None
        cue = runtime_cue.cue
        if cue.kind is OccasionKind.MOHAN_BIRTHDAY and not preferences.birthday_enabled:
            return None
        text = public_companion_line(
            environment.language,
            runtime_cue.line_key,
            variation_index=runtime_cue.variation_index,
            phrasebook=self._phrasebook,
        )
        if not text:
            return None
        priority = (
            CandidatePriority.OCCASION_GRUMBLE
            if cue.stage is OccasionStage.RESTRAINED_GRUMBLE
            else CandidatePriority.BIRTHDAY_HINT
            if cue.kind is OccasionKind.MOHAN_BIRTHDAY
            else CandidatePriority.OCCASION_HINT
        )
        speak = SpeakRequest(text, ProactiveSource.SPECIAL_OCCASION.value, runtime_cue.delivery_token)
        return _Candidate(
            ProactiveCompanionRequest(
                speak,
                cue,
                ProactiveSource.SPECIAL_OCCASION,
                priority,
                runtime_cue.delivery_token,
            ),
            runtime_cue,
        )

    @staticmethod
    def _scheduled_candidate(
        environment: NormalizedCompanionEnvironment,
    ) -> _Candidate | None:
        request = environment.scheduled_request
        if request is None:
            return None
        interaction = ProactiveInteraction(
            InteractionKind.GENTLE_CHECK_IN,
            "reminder",
        )
        return _Candidate(
            ProactiveCompanionRequest(
                request,
                interaction,
                ProactiveSource.SCHEDULED,
                CandidatePriority.SCHEDULED,
                request.cue_token,
            ),
            request.cue_token,
        )

    def _wellbeing_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> _Candidate | None:
        trigger = environment.reminder_trigger
        if trigger is None or not _trigger_enabled(trigger, preferences):
            return None
        request = self._wellbeing.request(
            trigger,
            attention=_attention(environment, preferences),
            language=environment.language,
            phrasebook=self._phrasebook,
            enabled=True,
        )
        if request is None:
            return None
        cue = self._wellbeing_cues.approved_cue(request.cue_token)
        if cue is None:
            self._wellbeing.report_spoken(request.cue_token, succeeded=False)
            return None
        priority = {
            WellbeingKind.MEAL: CandidatePriority.MEAL,
            WellbeingKind.HYDRATION: CandidatePriority.HYDRATION,
            WellbeingKind.REST: CandidatePriority.REST,
            WellbeingKind.PROLONGED_SITTING: CandidatePriority.PROLONGED_SITTING,
        }[cue.kind]
        return _Candidate(
            ProactiveCompanionRequest(
                request,
                cue,
                ProactiveSource.WELLBEING,
                priority,
                request.cue_token,
            ),
            request.cue_token,
        )

    def _return_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
        preferences: CompanionProactivityPreferences,
    ) -> _Candidate | None:
        away = environment.absence_duration_seconds
        if away < MIN_ABSENCE_SECONDS:
            return None
        if away >= preferences.long_wait_seconds:
            style = WelcomeStyle.CEREMONIAL
            priority = CandidatePriority.LONG_RETURN
        elif away <= preferences.brief_absence_seconds:
            style = WelcomeStyle.WARM
            priority = CandidatePriority.BRIEF_RETURN
        else:
            style = WelcomeStyle.GENERAL
            priority = CandidatePriority.BRIEF_RETURN
        interaction = ProactiveInteraction(
            InteractionKind.WELCOME_BACK,
            "neutral",
            style,
        )
        return self._local_candidate(environment, interaction, priority)

    def _visual_presence_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
    ) -> _Candidate | None:
        """Acknowledge a newly seen person through the normal speech boundary."""

        if not environment.visual_presence_arrival:
            return None
        return self._local_candidate(
            environment,
            ProactiveInteraction(
                InteractionKind.WELCOME_BACK,
                "happy",
                WelcomeStyle.WARM,
            ),
            CandidatePriority.VISUAL_PRESENCE,
            source=ProactiveSource.VISUAL_PRESENCE,
        )

    def _visual_activity_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
    ) -> _Candidate | None:
        """Warmly acknowledge visible activity without claiming identity."""

        if not environment.visual_activity:
            return None
        interaction = ProactiveInteraction(
            InteractionKind.GENTLE_CHECK_IN,
            "happy",
        )
        variation = _visual_activity_variation(environment.now)
        text = _visual_activity_text(
            environment.language,
            environment.user_title,
            variation,
        )
        if not text:
            return None
        token = _visual_activity_token(environment.now, variation)
        return _Candidate(
            ProactiveCompanionRequest(
                SpeakRequest(text, ProactiveSource.VISUAL_ACTIVITY.value, token),
                interaction,
                ProactiveSource.VISUAL_ACTIVITY,
                CandidatePriority.VISUAL_ACTIVITY,
                token,
            ),
            token,
        )

    def _check_in_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
    ) -> _Candidate | None:
        threshold = _check_in_threshold(environment.proactive_mode)
        if threshold is None:
            return None
        if environment.seconds_since_user_interaction < threshold:
            return None
        interaction = ProactiveInteraction(
            InteractionKind.GENTLE_CHECK_IN,
            "gentle",
        )
        # Natural topic: when a recent memory topic is available, weave it
        # into the check-in so the companion recalls the user's life instead
        # of repeating a canned greeting.
        if environment.memory_topics:
            topic = environment.memory_topics[0]
            text = _memory_check_in_text(environment.language, environment.user_title, topic)
            if text:
                token = _local_token(environment.now, interaction, 0)
                speak = SpeakRequest(text, ProactiveSource.CHECK_IN.value, token)
                return _Candidate(
                    ProactiveCompanionRequest(
                        speak,
                        interaction,
                        ProactiveSource.CHECK_IN,
                        CandidatePriority.CHECK_IN,
                        token,
                    ),
                    token,
                )
        return self._local_candidate(
            environment,
            interaction,
            CandidatePriority.CHECK_IN,
        )

    def _local_candidate(
        self,
        environment: NormalizedCompanionEnvironment,
        interaction: ProactiveInteraction,
        priority: CandidatePriority,
        *,
        source: ProactiveSource | None = None,
    ) -> _Candidate | None:
        variation = _stable_variation(environment.now, interaction)
        text = interaction_text(
            environment.language,
            interaction,
            InteractionTextContext(
                user_title=environment.user_title,
                wall_time=environment.now,
                custom_welcome=(
                    self._phrasebook.welcomes if self._phrasebook else None
                ),
                custom_check_ins=(
                    self._phrasebook.check_ins if self._phrasebook else None
                ),
                variation_index=variation,
            ),
        )
        if not text:
            return None
        token = _local_token(environment.now, interaction, variation)
        source = source or (
            ProactiveSource.RETURN
            if interaction.kind is InteractionKind.WELCOME_BACK
            else ProactiveSource.CHECK_IN
        )
        speak = SpeakRequest(text, source.value, token)
        return _Candidate(
            ProactiveCompanionRequest(speak, interaction, source, priority, token),
            token,
        )

    def _commit(self, candidate: _Candidate, *, succeeded: bool) -> bool:
        source = candidate.request.source
        if source is ProactiveSource.WELLBEING:
            return self._wellbeing.report_spoken(
                str(candidate.commit_payload),
                succeeded=succeeded,
            )
        if source is ProactiveSource.SPECIAL_OCCASION:
            runtime_cue = candidate.commit_payload
            if not isinstance(runtime_cue, RuntimeCue):
                return False
            return self._occasions.record_delivery(runtime_cue, succeeded=succeeded)
        if source is ProactiveSource.WARDROBE:
            if self._outfit_reveals is None:
                return False
            return self._outfit_reveals.record_reveal(
                str(candidate.commit_payload),
                succeeded=succeeded,
            )
        return succeeded

    def _release_unselected(
        self,
        candidates: tuple[_Candidate, ...],
        selected: _Candidate | None,
    ) -> None:
        for candidate in candidates:
            if (
                candidate is not selected
                and candidate.request.source is ProactiveSource.WELLBEING
            ):
                self._wellbeing.report_spoken(
                    str(candidate.commit_payload),
                    succeeded=False,
                )

    def _expire_pending(self, now: datetime) -> None:
        expired = tuple(
            token
            for token, pending in self._pending.items()
            if pending.expires_at <= now
        )
        for token in expired:
            self._release_pending(token)

    def _release_pending(self, delivery_token: str) -> None:
        pending = self._pending.pop(delivery_token, None)
        if pending is None:
            return
        candidate = pending.candidate
        self._pending_signatures.discard(_signature(candidate.request))
        self._commit(candidate, succeeded=False)

    def _release_all_pending(self) -> None:
        for token in tuple(self._pending):
            self._release_pending(token)

    def _rollover(self, now: datetime) -> None:
        today = now.date()
        if self._delivered_date == today:
            return
        self._release_all_pending()
        self._delivered_date = today
        self._delivered_count = 0
        self._delivered_signatures.clear()


def _attention(
    environment: NormalizedCompanionEnvironment,
    preferences: CompanionProactivityPreferences,
) -> RuntimeAttention:
    return RuntimeAttention(
        proactive_enabled=preferences.enabled,
        user_present=environment.user_present,
        focus_protected=environment.focus_active,
        meeting_active=environment.meeting_active,
        fullscreen_active=environment.fullscreen_active,
        speech_active=environment.speech_active,
        special_occasions_enabled=preferences.special_occasions_enabled,
    )


def _trigger_enabled(
    trigger: ReminderTrigger,
    preferences: CompanionProactivityPreferences,
) -> bool:
    return {
        ReminderTrigger.LUNCH: preferences.meal_enabled,
        ReminderTrigger.DINNER: preferences.meal_enabled,
        ReminderTrigger.HYDRATION: preferences.hydration_enabled,
        ReminderTrigger.REST: preferences.rest_enabled,
        ReminderTrigger.OVERWORK: preferences.prolonged_sitting_enabled,
        ReminderTrigger.PROLONGED_SITTING: preferences.prolonged_sitting_enabled,
    }[trigger]


def _check_in_threshold(mode: str) -> float | None:
    key = MultisensoryInteractionArbiter._mode_key(mode)
    if key == "quiet":
        return None
    if key == "active":
        return 15.0 * 60.0
    return 45.0 * 60.0


def _memory_check_in_text(language: str, user_title: str, topic: str) -> str:
    """Weave a remembered topic into a natural check-in line."""
    topic = str(topic).strip()
    if not topic:
        return ""
    locale = str(language).strip().lower()
    if locale.startswith(("zh-cn", "zh-hans")):
        return f"{user_title}，之前您提到「{topic}」，后来如何了？"
    if locale.startswith("en"):
        return f"{user_title}, you mentioned \"{topic}\" earlier — how did that go?"
    if locale.startswith("ja"):
        return f"{user_title}、以前「{topic}」とおっしゃっていましたが、その後いかがですか？"
    return f"{user_title}，之前你提到「{topic}」，後來如何了？"


def _visual_activity_variation(now: datetime) -> int:
    payload = f"mohan-visual-activity-v1\0{now.date()}\0{now.hour // 2}"
    return int.from_bytes(
        hashlib.blake2s(payload.encode(), digest_size=2).digest(),
        "big",
    )


def _visual_activity_token(now: datetime, variation: int) -> str:
    bucket = int(now.timestamp()) // (10 * 60)
    payload = f"visual-activity\0{bucket}\0{variation}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _visual_activity_text(language: str, user_title: str, variation: int) -> str:
    locale = str(language).strip().lower()
    lines = (
        (
            f"看見您在這裡，墨寒很安心，{user_title}。",
            f"{user_title}，墨寒有留意到您。今天還順利嗎？",
            f"您一動，墨寒就注意到了。想和我說說話嗎，{user_title}？",
        )
        if not locale.startswith(("zh-cn", "zh-hans", "en", "ja"))
        else (
            f"看见您在这里，墨寒很安心，{user_title}。",
            f"{user_title}，墨寒有留意到您。今天还顺利吗？",
            f"您一动，墨寒就注意到了。想和我说说话吗，{user_title}？",
        )
        if locale.startswith(("zh-cn", "zh-hans"))
        else (
            f"I am glad to see you here, {user_title}.",
            f"I noticed you, {user_title}. Is everything going well today?",
            f"You caught my attention, {user_title}. Would you like to talk?",
        )
        if locale.startswith("en")
        else (
            f"ここにいらっしゃるのが見えて、安心しました、{user_title}。",
            f"{user_title}、ちゃんと気づいていますよ。今日は順調ですか？",
            f"動かれたので気づきました、{user_title}。少しお話ししませんか？",
        )
    )
    return lines[variation % len(lines)]


def _signature(request: ProactiveCompanionRequest) -> tuple[object, ...]:
    return request.source, request.speak.source, request.delivery_token


def _stable_variation(
    now: datetime,
    interaction: ProactiveInteraction,
) -> int:
    payload = f"mohan-proactive-v1\0{now.date()}\0{interaction.kind.value}\0{interaction.style.value}"
    return int.from_bytes(hashlib.blake2s(payload.encode(), digest_size=4).digest(), "big")


def _local_token(
    now: datetime,
    interaction: ProactiveInteraction,
    variation: int,
) -> str:
    payload = f"{now.date()}\0{interaction.kind.value}\0{interaction.style.value}\0{variation}"
    return hashlib.sha256(payload.encode()).hexdigest()
