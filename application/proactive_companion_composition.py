from __future__ import annotations

lazy from typing import Protocol

lazy from application.companion_phrasebook import (
    PHRASEBOOK_SETTING,
    CompanionPhrasebook,
)
lazy from application.multisensory_interaction import ProactiveInteraction
lazy from application.outfit_reveal import OutfitRevealCue, OutfitRevealStateStore
lazy from application.proactive_companion_app_bridge import (
    ProactiveCompanionAppBridge,
    SpeechCompletion,
)
lazy from application.proactive_companion_runtime import (
    ApprovedPerformanceCue,
    ProactiveCompanionRuntime,
)
lazy from application.special_occasion import OccasionCue, OccasionExpression
lazy from application.wellbeing_app_bridge import SpeakRequest, WellbeingAppBridge
lazy from application.wellbeing_reminder import ReminderExpression, WellbeingCue
lazy from application.wellbeing_runtime import WellbeingRuntime
lazy from domain.time_utils import local_aware_time
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStore,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.special_occasion_store import SpecialOccasionStore
lazy from infrastructure.wellbeing_reminder_store import WellbeingReminderStore


class SpeechQueue(Protocol):
    def __call__(
        self,
        text: str,
        state: str,
        delivery_token: str,
        completed: SpeechCompletion,
    ) -> bool: ...


class _DatabasePhrasebook:
    def __init__(self, db: StudioDB) -> None:
        self._db = db

    def load(self) -> CompanionPhrasebook:
        return CompanionPhrasebook.from_setting(
            self._db.setting(PHRASEBOOK_SETTING, {})
        )


class _QueuedSpeechPort:
    def __init__(self, enqueue: SpeechQueue) -> None:
        self._enqueue = enqueue

    def submit(
        self,
        request: SpeakRequest,
        performance: ApprovedPerformanceCue,
        *,
        generation: int,
        completed: SpeechCompletion,
    ) -> bool:
        if generation < 0:
            return False
        return self._enqueue(
            request.text,
            _speech_state(performance),
            request.cue_token,
            completed,
        )


def create_proactive_companion_bridge(
    db: StudioDB,
    enqueue: SpeechQueue,
) -> ProactiveCompanionAppBridge:
    """Compose proactive services at one explicit application boundary."""

    settings = StudioDBSettingsPort(db)
    preferences = CompanionProactivityPreferencesStore(settings)
    phrasebook = _DatabasePhrasebook(db)

    def runtime_factory(
        current_phrasebook: CompanionPhrasebook,
    ) -> ProactiveCompanionRuntime:
        wellbeing_runtime = WellbeingRuntime(
            WellbeingReminderStore(settings),
            SpecialOccasionStore(settings),
            clock=local_aware_time,
        )
        wellbeing = WellbeingAppBridge(
            wellbeing_runtime,
            clock=local_aware_time,
        )
        return ProactiveCompanionRuntime(
            wellbeing,
            wellbeing,
            wellbeing_runtime,
            phrasebook=current_phrasebook,
            outfit_reveals=OutfitRevealStateStore(settings),
        )

    return ProactiveCompanionAppBridge(
        runtime_factory,
        preferences,
        phrasebook,
        _QueuedSpeechPort(enqueue),
    )


def _speech_state(performance: ApprovedPerformanceCue) -> str:
    if isinstance(performance, OutfitRevealCue):
        return performance.expression
    if isinstance(performance, ProactiveInteraction):
        return performance.expression
    if isinstance(performance, WellbeingCue):
        return {
            ReminderExpression.GENTLE: "reminder",
            ReminderExpression.CONCERNED: "worried",
            ReminderExpression.RESTRAINED_TSUNDERE: "mock_scold",
            ReminderExpression.QUIETLY_FIRM: "determined_front",
        }[performance.expression]
    if isinstance(performance, OccasionCue):
        return {
            OccasionExpression.QUIETLY_HOPEFUL: "shy_front",
            OccasionExpression.RESTRAINED_SULK: "worried_front",
        }[performance.expression]
    raise TypeError("Unsupported proactive performance cue.")
