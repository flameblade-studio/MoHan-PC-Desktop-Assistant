from __future__ import annotations

lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from enum import StrEnum
lazy from threading import RLock
lazy from typing import Final, Protocol

lazy from application.companion_phrasebook import (
    CompanionPhrasebook,
    public_companion_line,
)
lazy from application.wellbeing_reminder import (
    ReminderOccurrence,
    WellbeingCue,
    WellbeingKind,
)
lazy from application.wellbeing_runtime import RuntimeAttention, RuntimeCue


class ReminderTrigger(StrEnum):
    LUNCH = "lunch"
    DINNER = "dinner"
    OVERWORK = "overwork"
    HYDRATION = "hydration"
    REST = "rest"
    PROLONGED_SITTING = "prolonged_sitting"


class ReminderCommand(StrEnum):
    ACKNOWLEDGE = "acknowledge"
    COMPLETE = "complete"
    SNOOZE = "snooze"
    DISMISS = "dismiss"


MIDNIGHT_COMPLETION_GRACE_SECONDS = 3600.0
TRIGGER_KINDS = frozendict({
    ReminderTrigger.LUNCH: WellbeingKind.MEAL,
    ReminderTrigger.DINNER: WellbeingKind.MEAL,
    ReminderTrigger.OVERWORK: WellbeingKind.PROLONGED_SITTING,
    ReminderTrigger.HYDRATION: WellbeingKind.HYDRATION,
    ReminderTrigger.REST: WellbeingKind.REST,
    ReminderTrigger.PROLONGED_SITTING: WellbeingKind.PROLONGED_SITTING,
})

# Expected failures from a replaceable clock.  Unexpected programming errors
# deliberately remain visible instead of being silently converted.
_CALLBACK_ERRORS: Final = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class WellbeingRuntimePort(Protocol):
    def decide_wellbeing(
        self,
        kind: WellbeingKind,
        attention: RuntimeAttention,
    ) -> RuntimeCue | None: ...

    def record_delivery(self, cue: RuntimeCue, *, succeeded: bool) -> bool: ...

    def acknowledge_wellbeing(self, kind: WellbeingKind) -> None: ...

    def complete_wellbeing(self, kind: WellbeingKind) -> None: ...

    def snooze_wellbeing(self, kind: WellbeingKind, until: datetime) -> None: ...

    def dismiss_wellbeing(self, kind: WellbeingKind) -> None: ...


@dataclass(frozen=True, slots=True)
class SpeakRequest:
    text: str
    source: str
    cue_token: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Speak request text cannot be empty.")
        if not self.source or not self.cue_token:
            raise ValueError("Speak request identifiers cannot be empty.")


@dataclass(frozen=True, slots=True)
class _PendingDelivery:
    request: SpeakRequest
    occurrence: ReminderOccurrence
    cue: RuntimeCue
    created_at: datetime


class WellbeingAppBridgeError(RuntimeError):
    """A safe app-boundary error without phrase or persistence content."""


class WellbeingAppBridge:
    """Translate app triggers into side-effect-free speech requests."""

    def __init__(self, runtime: WellbeingRuntimePort, *, clock: Clock) -> None:
        self._runtime = runtime
        self._clock = clock
        self._pending: dict[str, _PendingDelivery] = {}
        self._pending_event_ids: set[str] = set()
        self._lock = RLock()

    def request(
        self,
        trigger: ReminderTrigger | str,
        *,
        attention: RuntimeAttention,
        language: str,
        phrasebook: CompanionPhrasebook | None = None,
        enabled: bool = True,
    ) -> SpeakRequest | None:
        normalized = _trigger(trigger)
        if type(enabled) is not bool:
            raise WellbeingAppBridgeError("Reminder enabled state must be boolean.")
        if not enabled:
            return None
        with self._lock:
            now = self._now()
            self._discard_stale(now)
            occurrence = normalize_occurrence(normalized, now)
            if occurrence.event_id in self._pending_event_ids:
                return None
            cue = self._runtime.decide_wellbeing(occurrence.kind, attention)
            if cue is None:
                return None
            if cue.delivery_token in self._pending:
                return None
            text = public_companion_line(
                language,
                cue.line_key,
                variation_index=cue.variation_index,
                phrasebook=phrasebook,
            )
            if not text.strip():
                return None
            request = SpeakRequest(text, normalized.value, cue.delivery_token)
            pending = _PendingDelivery(request, occurrence, cue, now)
            self._pending[request.cue_token] = pending
            self._pending_event_ids.add(occurrence.event_id)
            return request

    def report_spoken(self, cue_token: str, *, succeeded: bool) -> bool:
        if not isinstance(cue_token, str) or not cue_token:
            raise WellbeingAppBridgeError("Cue token is invalid.")
        if type(succeeded) is not bool:
            raise WellbeingAppBridgeError("Spoken result must be boolean.")
        with self._lock:
            now = self._now()
            pending = self._pending.pop(cue_token, None)
            if pending is None:
                return False
            self._pending_event_ids.discard(pending.occurrence.event_id)
            # A cue decided at 23:59 legitimately finishes playing after
            # midnight.  Rejecting on a bare date mismatch dropped those
            # deliveries from the record and allowed a duplicate nag the
            # next morning; accept any completion within one hour of the
            # date change instead.
            same_day = pending.created_at.date() == now.date()
            crossed_midnight = (
                not same_day
                and (now - pending.created_at).total_seconds()
                <= MIDNIGHT_COMPLETION_GRACE_SECONDS
            )
            if not (same_day or crossed_midnight):
                return False
            if not succeeded:
                self._runtime.record_delivery(pending.cue, succeeded=False)
                return False
            return self._runtime.record_delivery(pending.cue, succeeded=True)

    def approved_cue(self, cue_token: str) -> WellbeingCue | None:
        """Return only the policy-approved cue associated with a pending request."""

        if not isinstance(cue_token, str) or not cue_token:
            return None
        with self._lock:
            pending = self._pending.get(cue_token)
            if pending is None or not isinstance(pending.cue.cue, WellbeingCue):
                return None
            return pending.cue.cue

    def command(
        self,
        trigger: ReminderTrigger | str,
        command: ReminderCommand | str,
        *,
        snooze_until: datetime | None = None,
        enabled: bool = True,
    ) -> None:
        normalized = _trigger(trigger)
        normalized_command = _command(command)
        if type(enabled) is not bool:
            raise WellbeingAppBridgeError("Reminder enabled state must be boolean.")
        if not enabled:
            return
        kind = TRIGGER_KINDS[normalized]
        if normalized_command is ReminderCommand.ACKNOWLEDGE:
            self._runtime.acknowledge_wellbeing(kind)
        elif normalized_command is ReminderCommand.COMPLETE:
            self._runtime.complete_wellbeing(kind)
        elif normalized_command is ReminderCommand.DISMISS:
            self._runtime.dismiss_wellbeing(kind)
        elif normalized_command is ReminderCommand.SNOOZE:
            if snooze_until is None:
                raise WellbeingAppBridgeError("Snooze requires a deadline.")
            self._runtime.snooze_wellbeing(kind, snooze_until)
        else:
            raise WellbeingAppBridgeError("Reminder command is invalid.")

    def _discard_stale(self, now: datetime) -> None:
        stale = tuple(
            token
            for token, pending in self._pending.items()
            if pending.created_at.date() != now.date()
        )
        for token in stale:
            pending = self._pending.pop(token)
            self._pending_event_ids.discard(pending.occurrence.event_id)

    def _now(self) -> datetime:
        try:
            now = self._clock()
        except _CALLBACK_ERRORS:
            raise WellbeingAppBridgeError("Reminder bridge clock failed.") from None
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise WellbeingAppBridgeError(
                "Reminder bridge clock must be timezone-aware."
            )
        return now


def normalize_occurrence(
    trigger: ReminderTrigger | str,
    now: datetime,
) -> ReminderOccurrence:
    normalized = _trigger(trigger)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise WellbeingAppBridgeError("Occurrence time must be timezone-aware.")
    return ReminderOccurrence(
        event_id=f"{now.date().isoformat()}:{normalized.value}",
        kind=TRIGGER_KINDS[normalized],
    )


def _trigger(value: ReminderTrigger | str) -> ReminderTrigger:
    try:
        return value if isinstance(value, ReminderTrigger) else ReminderTrigger(value)
    except TypeError, ValueError:
        raise WellbeingAppBridgeError("Reminder trigger is invalid.") from None


def _command(value: ReminderCommand | str) -> ReminderCommand:
    try:
        return value if isinstance(value, ReminderCommand) else ReminderCommand(value)
    except TypeError, ValueError:
        raise WellbeingAppBridgeError("Reminder command is invalid.") from None
