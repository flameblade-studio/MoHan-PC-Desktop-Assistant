from __future__ import annotations

lazy import hashlib
lazy from dataclasses import dataclass, replace
lazy from datetime import datetime
lazy from enum import StrEnum
lazy from threading import RLock
lazy from typing import Final, Protocol

lazy from application.companion_phrasebook import (
    occasion_phrase_key,
    wellbeing_phrase_key,
)
lazy from application.special_occasion import (
    OccasionContext,
    OccasionCue,
    OccasionKind,
    OccasionResponse,
    OccasionStage,
    SpecialOccasionPolicy,
    active_occasion,
)
lazy from application.wellbeing_reminder import (
    WELLBEING_RULES,
    Eligibility,
    ReminderOccurrence,
    ReminderResponse,
    ReminderStage,
    WellbeingContext,
    WellbeingCue,
    WellbeingKind,
    WellbeingReminderPolicy,
)
lazy from infrastructure.special_occasion_store import SpecialOccasionStore
lazy from infrastructure.wellbeing_reminder_store import WellbeingReminderStore


class RuntimeSource(StrEnum):
    WELLBEING = "wellbeing"
    SPECIAL_OCCASION = "special_occasion"


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class VariationSelector(Protocol):
    def __call__(self, line_key: str, stable_id: str) -> int: ...


@dataclass(frozen=True, slots=True)
class RuntimePolicies:
    """Optional decision strategies kept together at the composition boundary."""

    variation: VariationSelector | None = None
    wellbeing_eligibility: Eligibility | None = None
    occasion_policy: SpecialOccasionPolicy | None = None


# Expected failures from user-replaceable clocks and variation strategies.  A
# programming error outside these boundary failures must remain visible.
_CALLBACK_ERRORS: Final = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True, slots=True)
class RuntimeAttention:
    proactive_enabled: bool
    user_present: bool
    focus_protected: bool = False
    meeting_active: bool = False
    fullscreen_active: bool = False
    speech_active: bool = False
    special_occasions_enabled: bool = True

    def __post_init__(self) -> None:
        values = (
            self.proactive_enabled,
            self.user_present,
            self.focus_protected,
            self.meeting_active,
            self.fullscreen_active,
            self.speech_active,
            self.special_occasions_enabled,
        )
        if any(type(value) is not bool for value in values):
            raise TypeError("Runtime attention values must be boolean.")


@dataclass(frozen=True, slots=True)
class RuntimeCue:
    source: RuntimeSource
    stable_id: str
    line_key: str
    variation_index: int
    cue: WellbeingCue | OccasionCue
    delivery_token: str

    def __post_init__(self) -> None:
        if not self.stable_id or not self.line_key or not self.delivery_token:
            raise ValueError("Runtime cue identifiers cannot be empty.")
        if self.variation_index < 0:
            raise ValueError("Runtime cue variation cannot be negative.")


class WellbeingRuntimeError(RuntimeError):
    """A safe runtime-boundary error without backend or phrase content."""


class WellbeingRuntime:
    """Coordinate policy decisions and persist only confirmed deliveries."""

    def __init__(
        self,
        wellbeing_store: WellbeingReminderStore,
        occasion_store: SpecialOccasionStore,
        *,
        clock: Clock,
        policies: RuntimePolicies | None = None,
    ) -> None:
        resolved_policies = policies or RuntimePolicies()
        if not isinstance(resolved_policies, RuntimePolicies):
            raise TypeError("Runtime policies are invalid.")
        self._wellbeing_store = wellbeing_store
        self._occasion_store = occasion_store
        self._clock = clock
        self._variation = resolved_policies.variation or stable_variation_index
        self._wellbeing_eligibility = resolved_policies.wellbeing_eligibility
        self._occasion_policy = (
            resolved_policies.occasion_policy or SpecialOccasionPolicy()
        )
        self._lock = RLock()

    def decide_wellbeing(
        self,
        kind: WellbeingKind,
        attention: RuntimeAttention,
    ) -> RuntimeCue | None:
        with self._lock:
            now = self._now()
            state = self._wellbeing_store.load(now)
            item = state.for_kind(kind)
            if item.snooze_until is not None:
                if item.snooze_until > now:
                    return None
                state = self._wellbeing_store.update_kind(
                    state,
                    kind,
                    snooze_until=None,
                    response=ReminderResponse.NONE,
                )
                self._wellbeing_store.save(state)
                item = state.for_kind(kind)
            event_id = _wellbeing_event_id(now, kind)
            context = WellbeingContext(
                local_now=now,
                occurrence=ReminderOccurrence(
                    event_id=event_id,
                    kind=kind,
                    initial_delivered_at=item.initial_delivered_at,
                    response=item.response,
                    reinforcement_delivered_at=item.reinforcement_delivered_at,
                ),
                kind_enabled=item.enabled,
                proactive_enabled=attention.proactive_enabled,
                user_present=attention.user_present,
                focus_protected=attention.focus_protected,
                meeting_active=attention.meeting_active,
                fullscreen_active=attention.fullscreen_active,
                speech_active=attention.speech_active,
                daily_reinforcement_count=item.daily_reinforcement_count,
                last_same_kind_reinforcement_at=(item.last_same_kind_reinforcement_at),
            )
            rules = dict(WELLBEING_RULES)
            base_rule = rules[kind]
            rules[kind] = replace(
                base_rule,
                maximum_daily_reinforcements=(item.maximum_daily_reinforcements),
                same_kind_cooldown_seconds=max(
                    float(item.same_kind_cooldown_seconds),
                    base_rule.reinforcement_delay_seconds,
                ),
            )
            cue = WellbeingReminderPolicy(
                rules=rules,
                eligibility=self._wellbeing_eligibility,
            ).decide(context)
            if cue is None:
                return None
            line_key = wellbeing_phrase_key(cue.kind, cue.stage)
            return self._runtime_cue(
                RuntimeSource.WELLBEING,
                event_id,
                line_key,
                cue,
            )

    def decide_special_occasion(
        self,
        attention: RuntimeAttention,
    ) -> RuntimeCue | None:
        with self._lock:
            now = self._now()
            state = self._occasion_store.load(now)
            occasion = active_occasion(now)
            if occasion is None:
                return None
            active = occasion.kind
            item = state.occasions[active]
            delivered = set()
            if item.hint_delivered_at is not None:
                delivered.add(OccasionStage.SUBTLE_HINT)
            if item.grumble_delivered_at is not None:
                delivered.add(OccasionStage.RESTRAINED_GRUMBLE)
            cue = self._occasion_policy.decide(
                OccasionContext(
                    local_now=now,
                    user_present=attention.user_present,
                    proactive_enabled=attention.proactive_enabled,
                    special_occasions_enabled=(
                        attention.special_occasions_enabled and item.enabled
                    ),
                    focus_protected=attention.focus_protected,
                    meeting_active=attention.meeting_active,
                    fullscreen_active=attention.fullscreen_active,
                    speech_active=attention.speech_active,
                    response=item.response,
                    delivered_stages=frozenset(delivered),
                    first_hint_at=item.hint_delivered_at,
                )
            )
            if cue is None:
                return None
            stable_id = _occasion_event_id(now, cue.kind)
            line_key = occasion_phrase_key(cue.kind, cue.stage)
            return self._runtime_cue(
                RuntimeSource.SPECIAL_OCCASION,
                stable_id,
                line_key,
                cue,
            )

    def record_delivery(self, runtime_cue: RuntimeCue, *, succeeded: bool) -> bool:
        if type(succeeded) is not bool:
            raise WellbeingRuntimeError("Delivery result must be boolean.")
        if not succeeded:
            return False
        with self._lock:
            now = self._now()
            self._validate_runtime_cue(runtime_cue)
            if runtime_cue.source is RuntimeSource.WELLBEING:
                return self._record_wellbeing(runtime_cue, now)
            if runtime_cue.source is RuntimeSource.SPECIAL_OCCASION:
                return self._record_occasion(runtime_cue, now)
            raise WellbeingRuntimeError("Runtime cue source is invalid.")

    def acknowledge_wellbeing(self, kind: WellbeingKind) -> None:
        self._respond_wellbeing(kind, ReminderResponse.ACKNOWLEDGED)

    def complete_wellbeing(self, kind: WellbeingKind) -> None:
        self._respond_wellbeing(kind, ReminderResponse.COMPLETED)

    def dismiss_wellbeing(self, kind: WellbeingKind) -> None:
        self._respond_wellbeing(kind, ReminderResponse.DISMISSED)

    def snooze_wellbeing(self, kind: WellbeingKind, until: datetime) -> None:
        with self._lock:
            now = self._now()
            if not isinstance(until, datetime) or until.tzinfo is None or until <= now:
                raise WellbeingRuntimeError("Snooze deadline must be in the future.")
            state = self._wellbeing_store.load(now)
            updated = self._wellbeing_store.update_kind(
                state,
                kind,
                snooze_until=until,
                response=ReminderResponse.SNOOZED,
            )
            self._wellbeing_store.save(updated)

    def acknowledge_special_occasion(self, kind: OccasionKind) -> None:
        self._respond_occasion(kind, OccasionResponse.ACKNOWLEDGED)

    def complete_special_occasion(self, kind: OccasionKind) -> None:
        self._respond_occasion(kind, OccasionResponse.CELEBRATED)

    def snooze_special_occasion(self, kind: OccasionKind) -> None:
        self._respond_occasion(kind, OccasionResponse.SNOOZED)

    def dismiss_special_occasion(self, kind: OccasionKind) -> None:
        self._respond_occasion(kind, OccasionResponse.DISMISSED)

    def _runtime_cue(
        self,
        source: RuntimeSource,
        stable_id: str,
        line_key: str,
        cue: WellbeingCue | OccasionCue,
    ) -> RuntimeCue:
        try:
            variation = self._variation(line_key, stable_id)
        except _CALLBACK_ERRORS:
            raise WellbeingRuntimeError("Cue variation selection failed.") from None
        if type(variation) is not int or variation < 0:
            raise WellbeingRuntimeError("Cue variation selection is invalid.")
        token = _delivery_token(source, stable_id, line_key, variation)
        return RuntimeCue(source, stable_id, line_key, variation, cue, token)

    def _record_wellbeing(self, runtime_cue: RuntimeCue, now: datetime) -> bool:
        cue = runtime_cue.cue
        if not isinstance(cue, WellbeingCue):
            raise WellbeingRuntimeError("Wellbeing cue type is invalid.")
        if runtime_cue.stable_id != _wellbeing_event_id(now, cue.kind):
            return False
        state = self._wellbeing_store.load(now)
        item = state.for_kind(cue.kind)
        if item.response is not ReminderResponse.NONE:
            return False
        if cue.stage is ReminderStage.INITIAL:
            if item.initial_delivered_at is not None:
                return False
            updated = self._wellbeing_store.update_kind(
                state, cue.kind, initial_delivered_at=now
            )
        elif cue.stage is ReminderStage.RESTRAINED_REINFORCEMENT:
            if (
                item.initial_delivered_at is None
                or item.reinforcement_delivered_at is not None
                or item.daily_reinforcement_count >= item.maximum_daily_reinforcements
            ):
                return False
            updated = self._wellbeing_store.update_kind(
                state,
                cue.kind,
                reinforcement_delivered_at=now,
                daily_reinforcement_count=item.daily_reinforcement_count + 1,
                last_same_kind_reinforcement_at=now,
            )
        else:
            raise WellbeingRuntimeError("Wellbeing cue stage is invalid.")
        self._wellbeing_store.save(updated)
        return True

    def _record_occasion(self, runtime_cue: RuntimeCue, now: datetime) -> bool:
        cue = runtime_cue.cue
        if not isinstance(cue, OccasionCue):
            raise WellbeingRuntimeError("Special occasion cue type is invalid.")
        if runtime_cue.stable_id != _occasion_event_id(now, cue.kind):
            return False
        state = self._occasion_store.load(now)
        item = state.occasions[cue.kind]
        if item.response is not OccasionResponse.NONE:
            return False
        if cue.stage is OccasionStage.SUBTLE_HINT:
            if item.hint_delivered_at is not None:
                return False
            updated = self._occasion_store.update_occasion(
                state, cue.kind, hint_delivered_at=now
            )
        elif cue.stage is OccasionStage.RESTRAINED_GRUMBLE:
            if item.hint_delivered_at is None or item.grumble_delivered_at is not None:
                return False
            updated = self._occasion_store.update_occasion(
                state, cue.kind, grumble_delivered_at=now
            )
        else:
            raise WellbeingRuntimeError("Special occasion cue stage is invalid.")
        self._occasion_store.save(updated)
        return True

    def _respond_wellbeing(
        self, kind: WellbeingKind, response: ReminderResponse
    ) -> None:
        with self._lock:
            now = self._now()
            state = self._wellbeing_store.load(now)
            updated = self._wellbeing_store.update_kind(
                state, kind, response=response, snooze_until=None
            )
            self._wellbeing_store.save(updated)

    def _respond_occasion(self, kind: OccasionKind, response: OccasionResponse) -> None:
        with self._lock:
            now = self._now()
            state = self._occasion_store.load(now)
            updated = self._occasion_store.update_occasion(
                state, kind, response=response
            )
            self._occasion_store.save(updated)

    def _validate_runtime_cue(self, runtime_cue: RuntimeCue) -> None:
        if not isinstance(runtime_cue, RuntimeCue):
            raise WellbeingRuntimeError("Runtime cue is invalid.")
        if runtime_cue.source is RuntimeSource.WELLBEING:
            cue = runtime_cue.cue
            if not isinstance(cue, WellbeingCue) or runtime_cue.line_key != (
                wellbeing_phrase_key(cue.kind, cue.stage)
            ):
                raise WellbeingRuntimeError("Runtime cue integrity validation failed.")
        elif runtime_cue.source is RuntimeSource.SPECIAL_OCCASION:
            cue = runtime_cue.cue
            if not isinstance(cue, OccasionCue) or runtime_cue.line_key != (
                occasion_phrase_key(cue.kind, cue.stage)
            ):
                raise WellbeingRuntimeError("Runtime cue integrity validation failed.")
        else:
            raise WellbeingRuntimeError("Runtime cue source is invalid.")
        expected = _delivery_token(
            runtime_cue.source,
            runtime_cue.stable_id,
            runtime_cue.line_key,
            runtime_cue.variation_index,
        )
        if runtime_cue.delivery_token != expected:
            raise WellbeingRuntimeError("Runtime cue integrity validation failed.")

    def _now(self) -> datetime:
        try:
            now = self._clock()
        except _CALLBACK_ERRORS:
            raise WellbeingRuntimeError("Runtime clock failed.") from None
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise WellbeingRuntimeError("Runtime clock must be timezone-aware.")
        return now


def stable_variation_index(line_key: str, stable_id: str) -> int:
    digest = hashlib.blake2s(
        f"mohan-runtime-v1\0{line_key}\0{stable_id}".encode(),
        digest_size=4,
    ).digest()
    return int.from_bytes(digest, "big")


def _wellbeing_event_id(now: datetime, kind: WellbeingKind) -> str:
    return f"{now.date().isoformat()}:{kind.value}"


def _occasion_event_id(now: datetime, kind: OccasionKind) -> str:
    return f"{now.date().isoformat()}:{kind.value}"


def _delivery_token(
    source: RuntimeSource,
    stable_id: str,
    line_key: str,
    variation_index: int,
) -> str:
    return hashlib.sha256(
        f"{source.value}\0{stable_id}\0{line_key}\0{variation_index}".encode()
    ).hexdigest()
