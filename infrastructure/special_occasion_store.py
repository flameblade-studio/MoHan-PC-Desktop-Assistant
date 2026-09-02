from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from datetime import date, datetime
lazy from typing import Final

lazy from application.special_occasion import OccasionKind, OccasionResponse
lazy from domain.performance_preferences import SettingsPort

SPECIAL_OCCASION_STATE_KEY: Final = "special_occasion_state_v1"
SPECIAL_OCCASION_STATE_FORMAT: Final = "mohan-special-occasion-state"
SPECIAL_OCCASION_STATE_VERSION: Final = 1
PORTABLE_SETTING_KEYS: Final = (SPECIAL_OCCASION_STATE_KEY,)
_BOUNDARY_ERRORS: Final = (Exception,)


class SpecialOccasionStoreError(RuntimeError):
    """A fixed-detail persistence failure without backend information."""


@dataclass(frozen=True, slots=True)
class OccasionState:
    enabled: bool = True
    hint_delivered_at: datetime | None = None
    grumble_delivered_at: datetime | None = None
    response: OccasionResponse = OccasionResponse.NONE

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("Special occasion enabled state must be boolean.")
        for moment in (self.hint_delivered_at, self.grumble_delivered_at):
            if moment is not None and moment.tzinfo is None:
                raise ValueError("Special occasion timestamps must be timezone-aware.")
        if self.grumble_delivered_at is not None and self.hint_delivered_at is None:
            raise ValueError("A special occasion cannot grumble before its hint.")


@dataclass(frozen=True, slots=True)
class SpecialOccasionState:
    local_date: date
    occasions: Mapping[OccasionKind, OccasionState]

    def __post_init__(self) -> None:
        if set(self.occasions) != set(OccasionKind):
            raise ValueError("Every special occasion requires state.")
        object.__setattr__(self, "occasions", frozendict(self.occasions))


def default_special_occasion_state(today: date) -> SpecialOccasionState:
    return SpecialOccasionState(
        today,
        frozendict((kind, OccasionState()) for kind in OccasionKind),
    )


class SpecialOccasionStore[SnapshotT]:
    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self, now: datetime) -> SpecialOccasionState:
        _require_aware(now)
        try:
            raw = self._settings.read(PORTABLE_SETTING_KEYS)
        except _BOUNDARY_ERRORS:
        # 後端讀不到不是「從未保存」：回預設值會讓排程端把已送達的提醒再送一次，
        # 偏好編輯器也會拿預設值開啟、一存就覆蓋掉原有設定。寫入路徑早就拋
        # 型別化錯誤，讀取路徑比照。
            raise SpecialOccasionStoreError(
                "Special occasion state could not be read."
            ) from None
        payload = (
            raw.get(SPECIAL_OCCASION_STATE_KEY) if isinstance(raw, Mapping) else None
        )
        state = _decode_state(payload, now.date())
        return _rollover(state, now)

    def save(self, state: SpecialOccasionState) -> None:
        if not isinstance(state, SpecialOccasionState):
            raise SpecialOccasionStoreError("Special occasion state is invalid.")
        _atomic_write(
            self._settings, {SPECIAL_OCCASION_STATE_KEY: _encode_state(state)}
        )

    def update_occasion(
        self,
        state: SpecialOccasionState,
        kind: OccasionKind,
        **changes: object,
    ) -> SpecialOccasionState:
        try:
            occasions = dict(state.occasions)
            occasions[kind] = replace(occasions[kind], **changes)
            return SpecialOccasionState(state.local_date, occasions)
        except KeyError, TypeError, ValueError:
            raise SpecialOccasionStoreError(
                "Special occasion update is invalid."
            ) from None

    def export_portable(self, now: datetime) -> dict[str, object]:
        return _encode_state(self.load(now))

    def import_portable(
        self, payload: Mapping[str, object], now: datetime
    ) -> SpecialOccasionState:
        _require_aware(now)
        decoded = _decode_state(payload, now.date())
        state = _rollover(decoded, now)
        self.save(state)
        return state


def _rollover(
    state: SpecialOccasionState,
    now: datetime,
) -> SpecialOccasionState:
    if state.local_date == now.date():
        return state
    return SpecialOccasionState(
        now.date(),
        frozendict(
            (kind, OccasionState(enabled=item.enabled))
            for kind, item in state.occasions.items()
        ),
    )


def _encode_state(state: SpecialOccasionState) -> dict[str, object]:
    return {
        "format": SPECIAL_OCCASION_STATE_FORMAT,
        "version": SPECIAL_OCCASION_STATE_VERSION,
        "local_date": state.local_date.isoformat(),
        "occasions": {
            kind.value: {
                "enabled": item.enabled,
                "hint_delivered_at": _iso(item.hint_delivered_at),
                "grumble_delivered_at": _iso(item.grumble_delivered_at),
                "response": item.response.value,
            }
            for kind, item in state.occasions.items()
        },
    }


def _decode_state(payload: object, today: date) -> SpecialOccasionState:
    defaults = default_special_occasion_state(today)
    if not isinstance(payload, Mapping):
        return defaults
    version = payload.get("version")
    if (
        payload.get("format") != SPECIAL_OCCASION_STATE_FORMAT
        or type(version) is not int
        or version != SPECIAL_OCCASION_STATE_VERSION
    ):
        return defaults
    try:
        stored_date = date.fromisoformat(str(payload.get("local_date", "")))
    except ValueError:
        return defaults
    raw = payload.get("occasions")
    if not isinstance(raw, Mapping):
        return defaults
    occasions = {
        kind: _decode_occasion(raw.get(kind.value), defaults.occasions[kind])
        for kind in OccasionKind
    }
    return SpecialOccasionState(stored_date, occasions)


def _decode_occasion(raw: object, default: OccasionState) -> OccasionState:
    if not isinstance(raw, Mapping):
        return default
    try:
        return OccasionState(
            enabled=raw.get("enabled"),
            hint_delivered_at=_datetime(raw.get("hint_delivered_at")),
            grumble_delivered_at=_datetime(raw.get("grumble_delivered_at")),
            response=OccasionResponse(raw.get("response", OccasionResponse.NONE)),
        )
    except TypeError, ValueError:
        return default


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
        raise SpecialOccasionStoreError("Current special occasion time is invalid.")


def _atomic_write[SnapshotT](
    settings: SettingsPort[SnapshotT],
    values: Mapping[str, object],
) -> None:
    try:
        before = settings.snapshot(PORTABLE_SETTING_KEYS)
    except _BOUNDARY_ERRORS:
        raise SpecialOccasionStoreError(
            "Special occasion state could not be snapshotted."
        ) from None
    try:
        settings.write(values)
    except _BOUNDARY_ERRORS:
        try:
            settings.restore(before)
        except _BOUNDARY_ERRORS:
            raise SpecialOccasionStoreError(
                "Special occasion persistence failed and rollback was incomplete."
            ) from None
        raise SpecialOccasionStoreError(
            "Special occasion persistence failed; previous values were restored."
        ) from None
