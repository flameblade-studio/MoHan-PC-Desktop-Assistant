from __future__ import annotations

lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from application.framing_orchestrator import (
    ApprovedWellbeingPerformance,
    FramingAuditEntry,
    FramingOrchestrationInput,
    OrchestratedFraming,
    SpecialOccasionCandidate,
)
lazy from domain.character_framing import FramingMode, NormalizedRect
lazy from domain.framing_context_policy import FramingPolicyContext
lazy from domain.framing_preferences import FramingPreferences


class FramingBridgeDisposition(StrEnum):
    BYPASSED = "bypassed"
    STALE = "stale"
    DUPLICATE = "duplicate"
    FALLBACK = "fallback"
    EMITTED = "emitted"


@dataclass(frozen=True, slots=True)
class AppFramingState:
    generation: int
    policy_context: FramingPolicyContext
    available_width_px: int
    available_height_px: int
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Framing generation must not be negative.")
        if self.available_width_px <= 0 or self.available_height_px <= 0:
            raise ValueError("Available desktop viewport must be positive.")


@dataclass(frozen=True, slots=True)
class FramingBridgeInput:
    state: AppFramingState
    preferences: FramingPreferences
    approved_wellbeing_cue: ApprovedWellbeingPerformance | None = None
    special_occasion: SpecialOccasionCandidate | None = None


@dataclass(frozen=True, slots=True)
class AtomicFramingCommand:
    generation: int
    mode: FramingMode
    crop: NormalizedRect
    transition_ms: int
    reason_chain: tuple[FramingAuditEntry, ...]

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Framing command generation must not be negative.")
        if self.transition_ms < 0:
            raise ValueError("Framing transition must not be negative.")
        if not self.reason_chain:
            raise ValueError("Framing command requires an audit reason chain.")


@dataclass(frozen=True, slots=True)
class FramingBridgeResult:
    disposition: FramingBridgeDisposition
    command: AtomicFramingCommand | None


class FramingOrchestrationPort(Protocol):
    def decide(self, request: FramingOrchestrationInput) -> OrchestratedFraming: ...


class CharacterFramingAppBridge:
    """One narrow, atomic boundary for app-level adaptive framing."""

    def __init__(self, orchestrator: FramingOrchestrationPort) -> None:
        self._orchestrator = orchestrator
        self._generation = -1
        self._last_input: FramingBridgeInput | None = None
        self._last_command_signature: tuple[object, ...] | None = None
        self._last_good: AtomicFramingCommand | None = None

    @property
    def last_known_good(self) -> AtomicFramingCommand | None:
        return self._last_good

    def dispatch(self, value: FramingBridgeInput) -> FramingBridgeResult:
        state = value.state
        if not state.enabled:
            return FramingBridgeResult(FramingBridgeDisposition.BYPASSED, None)
        if state.generation < self._generation:
            return FramingBridgeResult(FramingBridgeDisposition.STALE, None)
        if value == self._last_input:
            return FramingBridgeResult(FramingBridgeDisposition.DUPLICATE, None)

        request = FramingOrchestrationInput(
            policy_context=state.policy_context,
            preferences=value.preferences,
            available_width_px=state.available_width_px,
            available_height_px=state.available_height_px,
            wellbeing_cue=value.approved_wellbeing_cue,
            special_occasion=value.special_occasion,
        )
        try:
            framing = self._orchestrator.decide(request)
            command = _command(state.generation, framing)
        except (LookupError, RuntimeError, TypeError, ValueError):
            return FramingBridgeResult(
                FramingBridgeDisposition.FALLBACK,
                self._last_good,
            )

        signature = _command_signature(command)
        if signature == self._last_command_signature:
            self._generation = max(self._generation, state.generation)
            self._last_input = value
            return FramingBridgeResult(FramingBridgeDisposition.DUPLICATE, None)

        self._generation = max(self._generation, state.generation)
        self._last_input = value
        self._last_command_signature = signature
        self._last_good = command
        return FramingBridgeResult(FramingBridgeDisposition.EMITTED, command)


def _command(
    generation: int,
    framing: OrchestratedFraming,
) -> AtomicFramingCommand:
    decision = framing.decision
    return AtomicFramingCommand(
        generation,
        decision.mode,
        decision.crop,
        decision.transition_ms,
        framing.reason_chain,
    )


def _command_signature(command: AtomicFramingCommand) -> tuple[object, ...]:
    return (
        command.mode,
        command.crop,
        command.transition_ms,
        command.reason_chain,
    )
