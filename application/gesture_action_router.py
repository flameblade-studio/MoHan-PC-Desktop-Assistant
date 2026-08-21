from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.gesture_configuration import (
    GestureAction,
    GestureConfiguration,
    GestureSource,
)

MIN_CONFIDENCE_THRESHOLD = 0.5


class GestureActionDisposition(StrEnum):
    READY = "ready"
    DISABLED = "disabled"
    UNKNOWN_GESTURE = "unknown-gesture"
    LOW_CONFIDENCE = "low-confidence"
    COOLDOWN = "cooldown"
    NO_ACTION = "no-action"


class GestureActionSafety(StrEnum):
    LOCAL_REVERSIBLE = "local-reversible"
    DEVICE_ACCESS = "device-access"
    CLOUD_SESSION = "cloud-session"
    POLICY_ROUTED = "policy-routed"


_ACTION_SAFETY = frozendict({
    GestureAction.SHOW_DASHBOARD: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.HIDE_DASHBOARD: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.MUTE_AUDIO: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.UNMUTE_AUDIO: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.STOP_SPEECH: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.TOGGLE_LISTENING: GestureActionSafety.DEVICE_ACCESS,
    GestureAction.START_REALTIME: GestureActionSafety.CLOUD_SESSION,
    GestureAction.STOP_REALTIME: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.WORK_MODE: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.COMPANION_MODE: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.DO_NOT_DISTURB_MODE: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.POSITIVE_ACKNOWLEDGEMENT: GestureActionSafety.LOCAL_REVERSIBLE,
    GestureAction.CUSTOM_COMMAND: GestureActionSafety.POLICY_ROUTED,
})


@dataclass(frozen=True, slots=True)
class GestureTrigger:
    gesture_id: str
    confidence: float
    observed_at: float

    def __post_init__(self) -> None:
        if not self.gesture_id.strip():
            raise ValueError("Gesture trigger identifier must not be empty.")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Gesture trigger confidence must be normalized.")
        if not math.isfinite(self.observed_at):
            raise ValueError("Gesture trigger time must be finite.")


@dataclass(frozen=True, slots=True)
class GestureActionDecision:
    disposition: GestureActionDisposition
    gesture_id: str
    action: GestureAction = GestureAction.NONE
    safety: GestureActionSafety | None = None
    command_text: str = ""
    source: GestureSource | None = None

    @property
    def executable(self) -> bool:
        return self.disposition is GestureActionDisposition.READY

    @property
    def requires_policy_pipeline(self) -> bool:
        return self.safety is GestureActionSafety.POLICY_ROUTED

    @property
    def requires_explicit_runtime_confirmation(self) -> bool:
        return self.safety in {
            GestureActionSafety.DEVICE_ACCESS,
            GestureActionSafety.CLOUD_SESSION,
        }


class GestureActionRouter:
    """Translate debounced recognition into intent without executing anything."""

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.78,
        cooldown_seconds: float = 2.0,
    ) -> None:
        if not math.isfinite(confidence_threshold) or not MIN_CONFIDENCE_THRESHOLD <= confidence_threshold <= 1.0:
            raise ValueError("Gesture action confidence threshold is invalid.")
        if not math.isfinite(cooldown_seconds) or cooldown_seconds < 0.0:
            raise ValueError("Gesture action cooldown is invalid.")
        self._confidence_threshold = confidence_threshold
        self._cooldown_seconds = cooldown_seconds
        self._last_triggered_at: dict[str, float] = {}
        self._last_observed_at = -math.inf

    def route(
        self,
        trigger: GestureTrigger,
        configuration: GestureConfiguration,
    ) -> GestureActionDecision:
        if trigger.observed_at < self._last_observed_at:
            raise ValueError("Gesture triggers must be time ordered.")
        self._last_observed_at = trigger.observed_at
        if not configuration.enabled:
            return self._blocked(trigger, GestureActionDisposition.DISABLED)
        try:
            definition = configuration.definition(trigger.gesture_id)
        except KeyError:
            return self._blocked(trigger, GestureActionDisposition.UNKNOWN_GESTURE)
        blocked = self._definition_block(
            trigger,
            enabled=definition.enabled,
        )
        if blocked is not None:
            return blocked
        binding = definition.binding
        if binding.action is GestureAction.NONE:
            return GestureActionDecision(
                GestureActionDisposition.NO_ACTION,
                trigger.gesture_id,
                source=definition.source,
            )
        safety = _ACTION_SAFETY[binding.action]
        self._last_triggered_at[trigger.gesture_id] = trigger.observed_at
        return GestureActionDecision(
            GestureActionDisposition.READY,
            trigger.gesture_id,
            binding.action,
            safety,
            binding.custom_command,
            definition.source,
        )

    def _definition_block(
        self,
        trigger: GestureTrigger,
        *,
        enabled: bool,
    ) -> GestureActionDecision | None:
        disposition = None
        if not enabled:
            disposition = GestureActionDisposition.DISABLED
        elif trigger.confidence < self._confidence_threshold:
            disposition = GestureActionDisposition.LOW_CONFIDENCE
        else:
            previous = self._last_triggered_at.get(trigger.gesture_id, -math.inf)
            if trigger.observed_at - previous < self._cooldown_seconds:
                disposition = GestureActionDisposition.COOLDOWN
        return self._blocked(trigger, disposition) if disposition is not None else None

    def reset(self) -> None:
        self._last_triggered_at.clear()
        self._last_observed_at = -math.inf

    @staticmethod
    def _blocked(
        trigger: GestureTrigger,
        disposition: GestureActionDisposition,
    ) -> GestureActionDecision:
        return GestureActionDecision(disposition, trigger.gesture_id)
