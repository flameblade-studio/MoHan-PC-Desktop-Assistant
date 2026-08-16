from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from functools import partial
lazy from typing import Protocol

lazy from application.gesture_action_router import (
    GestureActionDecision,
    GestureActionSafety,
)
lazy from domain.gesture_configuration import GestureAction


class GestureActionPort(Protocol):
    """Small application boundary for already-authorized gesture actions."""

    def show_control_center(self) -> None: ...

    def hide_control_center(self) -> None: ...

    def set_audio_muted(self, muted: bool) -> None: ...

    def stop_current_speech(self) -> None: ...

    def toggle_listening(self) -> None: ...

    def set_realtime_enabled(self, enabled: bool) -> None: ...

    def set_interaction_mode(self, mode: str) -> None: ...

    def acknowledge_positive(self) -> None: ...

    def submit_safe_text_command(self, command: str) -> None: ...


class GestureDispatchDisposition(StrEnum):
    EXECUTED = "executed"
    IGNORED = "ignored"
    CONFIRMATION_REQUIRED = "confirmation-required"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class GestureDispatchResult:
    disposition: GestureDispatchDisposition
    action: GestureAction
    reason_code: str

    @property
    def executed(self) -> bool:
        return self.disposition is GestureDispatchDisposition.EXECUTED


GestureAuthorizer = Callable[[GestureActionDecision], bool]


class GestureActionDispatcher:
    """Execute one routed intent without weakening existing policy boundaries."""

    def __init__(
        self,
        actions: GestureActionPort,
        *,
        authorize: GestureAuthorizer | None = None,
    ) -> None:
        self._actions = actions
        self._authorize = authorize
        self._executors: frozendict[GestureAction, Callable[[], None]] = frozendict({
            GestureAction.SHOW_DASHBOARD: actions.show_control_center,
            GestureAction.HIDE_DASHBOARD: actions.hide_control_center,
            GestureAction.MUTE_AUDIO: partial(actions.set_audio_muted, True),
            GestureAction.UNMUTE_AUDIO: partial(actions.set_audio_muted, False),
            GestureAction.STOP_SPEECH: actions.stop_current_speech,
            GestureAction.TOGGLE_LISTENING: actions.toggle_listening,
            GestureAction.START_REALTIME: partial(
                actions.set_realtime_enabled,
                True,
            ),
            GestureAction.STOP_REALTIME: partial(
                actions.set_realtime_enabled,
                False,
            ),
            GestureAction.WORK_MODE: partial(
                actions.set_interaction_mode,
                "work",
            ),
            GestureAction.COMPANION_MODE: partial(
                actions.set_interaction_mode,
                "companion",
            ),
            GestureAction.DO_NOT_DISTURB_MODE: partial(
                actions.set_interaction_mode,
                "do-not-disturb",
            ),
            GestureAction.POSITIVE_ACKNOWLEDGEMENT: actions.acknowledge_positive,
        })

    def dispatch(self, decision: GestureActionDecision) -> GestureDispatchResult:
        if not isinstance(decision, GestureActionDecision):
            raise TypeError("Gesture dispatch requires a routed decision.")
        if not decision.executable:
            return GestureDispatchResult(
                GestureDispatchDisposition.IGNORED,
                decision.action,
                decision.disposition.value,
            )
        authorization = self._authorize_if_required(decision)
        if authorization is not None:
            return authorization
        try:
            self._execute(decision)
        except Exception:  # noqa: BLE001 - external application boundary
            return GestureDispatchResult(
                GestureDispatchDisposition.FAILED,
                decision.action,
                "action-boundary-failed",
            )
        return GestureDispatchResult(
            GestureDispatchDisposition.EXECUTED,
            decision.action,
            "executed",
        )

    def _authorize_if_required(
        self,
        decision: GestureActionDecision,
    ) -> GestureDispatchResult | None:
        if decision.safety not in {
            GestureActionSafety.DEVICE_ACCESS,
            GestureActionSafety.CLOUD_SESSION,
        }:
            return None
        if self._authorize is None:
            return GestureDispatchResult(
                GestureDispatchDisposition.CONFIRMATION_REQUIRED,
                decision.action,
                "authorization-unavailable",
            )
        try:
            allowed = self._authorize(decision)
        except Exception:  # noqa: BLE001 - external authorization boundary
            return GestureDispatchResult(
                GestureDispatchDisposition.FAILED,
                decision.action,
                "authorization-boundary-failed",
            )
        if allowed is not True:
            return GestureDispatchResult(
                GestureDispatchDisposition.DENIED,
                decision.action,
                "authorization-denied",
            )
        return None

    def _execute(self, decision: GestureActionDecision) -> None:
        if decision.action is GestureAction.CUSTOM_COMMAND:
            self._actions.submit_safe_text_command(decision.command_text)
            return
        executor = self._executors.get(decision.action)
        if executor is None:
            raise ValueError("Gesture action is not executable.")
        executor()
