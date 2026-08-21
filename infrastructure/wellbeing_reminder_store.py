from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from datetime import date, datetime
lazy from typing import Final

lazy from application.wellbeing_reminder import (
    WELLBEING_RULES,
    ReminderResponse,
    WellbeingKind,
)
lazy from domain.performance_preferences import SettingsPort

WELLBEING_STATE_KEY: Final = "wellbeing_reminder_state_v1"
WELLBEING_STATE_FORMAT: Final = "mohan-wellbeing-reminder-state"
WELLBEING_STATE_VERSION: Final = 1
PORTABLE_SETTING_KEYS: Final = (WELLBEING_STATE_KEY,)
_BOUNDARY_ERRORS: Final = (Exception,)
MAX_DAILY_REINFORCEMENTS: Final = 8
MIN_COOLDOWN_SECONDS: Final = 300
MAX_COOLDOWN_SECONDS: Final = 86400


class WellbeingReminderStoreError(RuntimeError):
    """A fixed-detail persistence failure without backend information."""


@dataclass(frozen=True, slots=True)
class WellbeingKindState:
    enabled: bool
    snooze_until: datetime | None
    response: ReminderResponse
    initial_delivered_at: datetime | None
    reinforcement_delivered_at: datetime | None
    daily_reinforcement_count: int
    maximum_daily_reinforcements: int
    same_kind_cooldown_seconds: int
    last_same_kind_reinforcement_at: datetime | None

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("Wellbeing enabled state must be boolean.")
        if not 0 <= self.daily_reinforcement_count <= MAX_DAILY_REINFORCEMENTS:
            raise ValueError("Wellbeing daily count is invalid.")
        if not 1 <= self.maximum_daily_reinforcements <= MAX_DAILY_REINFORCEMENTS:
            raise ValueError("Wellbeing daily budget is invalid.")
        if self.daily_reinforcement_count > self.maximum_daily_reinforcements:
            raise ValueError("Wellbeing daily count exceeds its budget.")
        if not MIN_COOLDOWN_SECONDS <= self.same_kind_cooldown_seconds <= MAX_COOLDOWN_SECONDS:
            raise ValueError("Wellbeing cooldown is invalid.")
        for moment in (
            self.snooze_until,
            self.initial_delivered_at,
            self.reinforcement_delivered_at,
            self.last_same_kind_reinforcement_at,
        ):
            if moment is not None and moment.tzinfo is None:
                raise ValueError("Wellbeing timestamps must be timezone-aware.")
        if (
            self.reinforcement_delivered_at is not None
            and self.initial_delivered_at is None
        ):
            raise ValueError("Wellbeing reinforcement requires an initial reminder.")
        if (
            self.reinforcement_delivered_at is not None
            and self.initial_delivered_at is not None
            and self.reinforcement_delivered_at < self.initial_delivered_at
        ):
            raise ValueError("Wellbeing delivery history is out of order.")


@dataclass(frozen=True, slots=True)
class WellbeingReminderState:
    local_date: date
    kinds: Mapping[WellbeingKind, WellbeingKindState]

    def __post_init__(self) -> None:
        if set(self.kinds) != set(WellbeingKind):
            raise ValueError("Every wellbeing kind requires state.")
        object.__setattr__(self, "kinds", frozendict(self.kinds))

    def for_kind(self, kind: WellbeingKind) -> WellbeingKindState:
        return self.kinds[kind]


def default_wellbeing_state(today: date) -> WellbeingReminderState:
    return WellbeingReminderState(
        today,
        frozendict(
            (
                kind,
                WellbeingKindState(
                    enabled=True,
                    snooze_until=None,
                    response=ReminderResponse.NONE,
                    initial_delivered_at=None,
                    reinforcement_delivered_at=None,
                    daily_reinforcement_count=0,
                    maximum_daily_reinforcements=(
                        WELLBEING_RULES[kind].maximum_daily_reinforcements
                    ),
                    same_kind_cooldown_seconds=int(
                        WELLBEING_RULES[kind].same_kind_cooldown_seconds
                    ),
                    last_same_kind_reinforcement_at=None,
                ),
            )
            for kind in WellbeingKind
        ),
    )


class WellbeingReminderStore[SnapshotT]:
    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self, now: datetime) -> WellbeingReminderState:
        _require_aware(now)
        try:
            raw = self._settings.read(PORTABLE_SETTING_KEYS)
        except _BOUNDARY_ERRORS:
            return default_wellbeing_state(now.date())
        payload = raw.get(WELLBEING_STATE_KEY) if isinstance(raw, Mapping) else None
        state = _decode_state(payload, now.date())
        return _rollover(state, now)

    def save(self, state: WellbeingReminderState) -> None:
        if not isinstance(state, WellbeingReminderState):
            raise WellbeingReminderStoreError("Wellbeing reminder state is invalid.")
        _atomic_write(self._settings, {WELLBEING_STATE_KEY: _encode_state(state)})

    def update_kind(
        self,
        state: WellbeingReminderState,
        kind: WellbeingKind,
        **changes: object,
    ) -> WellbeingReminderState:
        try:
            updated_kind = replace(state.for_kind(kind), **changes)
            kinds = dict(state.kinds)
            kinds[kind] = updated_kind
            return WellbeingReminderState(state.local_date, kinds)
        except KeyError, TypeError, ValueError:
            raise WellbeingReminderStoreError(
                "Wellbeing reminder update is invalid."
            ) from None

    def export_portable(self, now: datetime) -> dict[str, object]:
        return _encode_state(self.load(now))

    def import_portable(
        self, payload: Mapping[str, object], now: datetime
    ) -> WellbeingReminderState:
        _require_aware(now)
        state = _rollover(_decode_state(payload, now.date()), now)
        self.save(state)
        return state


def _rollover(state: WellbeingReminderState, now: datetime) -> WellbeingReminderState:
    if state.local_date == now.date():
        return state
    kinds = {}
    for kind, item in state.kinds.items():
        kinds[kind] = replace(
            item,
            snooze_until=(
                item.snooze_until
                if item.snooze_until is not None and item.snooze_until > now
                else None
            ),
            response=ReminderResponse.NONE,
            initial_delivered_at=None,
            reinforcement_delivered_at=None,
            daily_reinforcement_count=0,
        )
    return WellbeingReminderState(now.date(), kinds)


def _encode_state(state: WellbeingReminderState) -> dict[str, object]:
    return {
        "format": WELLBEING_STATE_FORMAT,
        "version": WELLBEING_STATE_VERSION,
        "local_date": state.local_date.isoformat(),
        "kinds": {
            kind.value: {
                "enabled": item.enabled,
                "snooze_until": _iso(item.snooze_until),
                "response": item.response.value,
                "initial_delivered_at": _iso(item.initial_delivered_at),
                "reinforcement_delivered_at": _iso(item.reinforcement_delivered_at),
                "daily_reinforcement_count": item.daily_reinforcement_count,
                "maximum_daily_reinforcements": (item.maximum_daily_reinforcements),
                "same_kind_cooldown_seconds": item.same_kind_cooldown_seconds,
                "last_same_kind_reinforcement_at": _iso(
                    item.last_same_kind_reinforcement_at
                ),
            }
            for kind, item in state.kinds.items()
        },
    }


def _decode_state(payload: object, today: date) -> WellbeingReminderState:
    defaults = default_wellbeing_state(today)
    if not isinstance(payload, Mapping):
        return defaults
    version = payload.get("version")
    if (
        payload.get("format") != WELLBEING_STATE_FORMAT
        or type(version) is not int
        or version != WELLBEING_STATE_VERSION
    ):
        return defaults
    try:
        stored_date = date.fromisoformat(str(payload.get("local_date", "")))
    except ValueError:
        return defaults
    raw_kinds = payload.get("kinds")
    if not isinstance(raw_kinds, Mapping):
        return defaults
    kinds = {
        kind: _decode_kind(raw_kinds.get(kind.value), defaults.for_kind(kind))
        for kind in WellbeingKind
    }
    return WellbeingReminderState(stored_date, kinds)


def _decode_kind(raw: object, default: WellbeingKindState) -> WellbeingKindState:
    if not isinstance(raw, Mapping):
        return default
    try:
        response = ReminderResponse(raw.get("response", ReminderResponse.NONE))
        candidate = WellbeingKindState(
            enabled=raw.get("enabled"),
            snooze_until=_datetime(raw.get("snooze_until")),
            response=response,
            initial_delivered_at=_datetime(raw.get("initial_delivered_at")),
            reinforcement_delivered_at=_datetime(raw.get("reinforcement_delivered_at")),
            daily_reinforcement_count=raw.get("daily_reinforcement_count"),
            maximum_daily_reinforcements=raw.get("maximum_daily_reinforcements"),
            same_kind_cooldown_seconds=raw.get("same_kind_cooldown_seconds"),
            last_same_kind_reinforcement_at=_datetime(
                raw.get("last_same_kind_reinforcement_at")
            ),
        )
    except TypeError, ValueError:
        return default
    return candidate


def _datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError
    return moment


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _require_aware(now: datetime) -> None:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise WellbeingReminderStoreError("Current wellbeing time is invalid.")


def _atomic_write[SnapshotT](
    settings: SettingsPort[SnapshotT],
    values: Mapping[str, object],
) -> None:
    try:
        before = settings.snapshot(PORTABLE_SETTING_KEYS)
    except _BOUNDARY_ERRORS:
        raise WellbeingReminderStoreError(
            "Wellbeing reminder state could not be snapshotted."
        ) from None
    try:
        settings.write(values)
    except _BOUNDARY_ERRORS:
        try:
            settings.restore(before)
        except _BOUNDARY_ERRORS:
            raise WellbeingReminderStoreError(
                "Wellbeing reminder persistence failed and rollback was incomplete."
            ) from None
        raise WellbeingReminderStoreError(
            "Wellbeing reminder persistence failed; previous values were restored."
        ) from None
