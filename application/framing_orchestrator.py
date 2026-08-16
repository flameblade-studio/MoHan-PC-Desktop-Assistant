from __future__ import annotations

lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from domain.character_framing import (
    CharacterFramingDirector,
    FramingContext,
    FramingDecision,
    FramingMode,
    NormalizedRect,
)
lazy from domain.framing_context_policy import (
    FocusState,
    FramingPolicyContext,
    FramingProposal,
    evaluate_framing_context,
)
lazy from domain.framing_preferences import FramingPreferences, PreferredFraming


class OrchestrationReason(StrEnum):
    POLICY_CANDIDATE = "policy-candidate"
    APPROVED_WELLBEING_CUE = "approved-wellbeing-cue"
    SPECIAL_OCCASION_CANDIDATE = "special-occasion-candidate"
    CLOSE_DISABLED = "close-disabled"
    FULL_BODY_DISABLED = "full-body-disabled"
    FOCUS_PROTECTION = "focus-protection"
    FIXED_PREFERENCE = "fixed-preference"
    ADAPTIVE_DISABLED = "adaptive-disabled"
    REQUIRED_CONTENT_CONTAINMENT = "required-content-containment"
    DIRECTOR_DECISION = "director-decision"


class ApprovedWellbeingPerformance(Protocol):
    event_id: str
    kind: object
    stage: object
    framing: object
    reason_code: str


@dataclass(frozen=True, slots=True)
class SpecialOccasionCandidate:
    event_id: str
    mode: FramingMode
    score: float
    confidence: float
    reason_code: str

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.reason_code.strip():
            raise ValueError("Special-occasion audit fields must not be empty.")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Special-occasion score must be within 0..1.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Special-occasion confidence must be within 0..1.")


@dataclass(frozen=True, slots=True)
class FramingOrchestrationInput:
    policy_context: FramingPolicyContext
    preferences: FramingPreferences
    available_width_px: int
    available_height_px: int
    wellbeing_cue: ApprovedWellbeingPerformance | None = None
    special_occasion: SpecialOccasionCandidate | None = None

    def __post_init__(self) -> None:
        if self.available_width_px <= 0 or self.available_height_px <= 0:
            raise ValueError("Available desktop viewport must be positive.")


@dataclass(frozen=True, slots=True)
class FramingAuditEntry:
    stage: str
    code: str


@dataclass(frozen=True, slots=True)
class OrchestratedFraming:
    decision: FramingDecision
    requested_mode: FramingMode
    candidate_confidence: float
    director_context: FramingContext
    reason_chain: tuple[FramingAuditEntry, ...]


@dataclass(frozen=True, slots=True)
class _Candidate:
    mode: FramingMode
    score: float
    confidence: float
    reasons: tuple[str, ...]
    source: OrchestrationReason


_PREFERRED_MODE = frozendict({
    PreferredFraming.CLOSE: FramingMode.CLOSE,
    PreferredFraming.HALF: FramingMode.HALF,
    PreferredFraming.THREE_QUARTER: FramingMode.THREE_QUARTER,
    PreferredFraming.FULL_BODY: FramingMode.FULL_BODY,
})
_THREE_QUARTER_REQUEST = NormalizedRect(0.10, 0.08, 0.90, 0.74)


class FramingOrchestrator:
    """Apply owner preferences before delegating motion to the framing director."""

    def __init__(self, director: CharacterFramingDirector) -> None:
        self._director = director

    def decide(self, request: FramingOrchestrationInput) -> OrchestratedFraming:
        policy_context = self._policy_context(request)
        candidates = self._candidates(request, policy_context)
        selected, constraints = self._select(candidates, request)
        director_context, containment = self._director_context(
            request,
            selected.mode,
        )
        decision = self._director.decide(director_context)
        chain = (
            FramingAuditEntry("candidate", selected.source.value),
            *(FramingAuditEntry("policy", reason) for reason in selected.reasons),
            *(FramingAuditEntry("preference", reason.value) for reason in constraints),
            *(FramingAuditEntry("containment", reason.value) for reason in containment),
            FramingAuditEntry(
                "director",
                f"{OrchestrationReason.DIRECTOR_DECISION.value}:{decision.reason.value}",
            ),
        )
        return OrchestratedFraming(
            decision=decision,
            requested_mode=selected.mode,
            candidate_confidence=selected.confidence,
            director_context=director_context,
            reason_chain=chain,
        )

    @staticmethod
    def _policy_context(
        request: FramingOrchestrationInput,
    ) -> FramingPolicyContext:
        context = request.policy_context
        preferences = request.preferences
        focus = (
            context.focus_state
            if preferences.focus_protection_enabled
            else FocusState.AVAILABLE
        )
        return replace(
            context,
            focus_state=focus,
            wellbeing_reminder=None,
            close_framing_allowed=(
                context.close_framing_allowed and preferences.allow_close
            ),
        )

    @staticmethod
    def _candidates(
        request: FramingOrchestrationInput,
        context: FramingPolicyContext,
    ) -> tuple[_Candidate, ...]:
        policy = evaluate_framing_context(context)
        candidates = tuple(_from_policy(proposal) for proposal in policy.proposals)
        cue = request.wellbeing_cue
        if cue is not None:
            candidates = (*candidates, _from_wellbeing_cue(cue))
        occasion = request.special_occasion
        if occasion is None:
            return candidates
        return (
            *candidates,
            _Candidate(
                occasion.mode,
                occasion.score,
                occasion.confidence,
                (occasion.reason_code,),
                OrchestrationReason.SPECIAL_OCCASION_CANDIDATE,
            ),
        )

    def _select(
        self,
        candidates: tuple[_Candidate, ...],
        request: FramingOrchestrationInput,
    ) -> tuple[_Candidate, tuple[OrchestrationReason, ...]]:
        preferences = request.preferences
        constraints: list[OrchestrationReason] = []
        allowed = list(candidates)
        if not preferences.allow_close:
            allowed = [item for item in allowed if item.mode is not FramingMode.CLOSE]
            constraints.append(OrchestrationReason.CLOSE_DISABLED)
        if not preferences.allow_full_body:
            allowed = [
                item for item in allowed if item.mode is not FramingMode.FULL_BODY
            ]
            constraints.append(OrchestrationReason.FULL_BODY_DISABLED)
        if (
            preferences.focus_protection_enabled
            and request.policy_context.focus_state is not FocusState.AVAILABLE
        ):
            allowed = [item for item in allowed if item.mode is not FramingMode.CLOSE]
            constraints.append(OrchestrationReason.FOCUS_PROTECTION)

        preferred = _PREFERRED_MODE.get(preferences.preferred_framing)
        if preferred is not None:
            fixed = [item for item in allowed if item.mode is preferred]
            if fixed:
                constraints.append(OrchestrationReason.FIXED_PREFERENCE)
                return _best(fixed), tuple(dict.fromkeys(constraints))
        if not preferences.adaptive_enabled:
            current = [item for item in allowed if item.mode is self._director.mode]
            constraints.append(OrchestrationReason.ADAPTIVE_DISABLED)
            if current:
                return _best(current), tuple(dict.fromkeys(constraints))
        return _best(allowed), tuple(dict.fromkeys(constraints))

    @staticmethod
    def _director_context(
        request: FramingOrchestrationInput,
        requested: FramingMode,
    ) -> tuple[FramingContext, tuple[OrchestrationReason, ...]]:
        source = request.policy_context
        gesture = source.gesture_bounds
        containment_required = bool(
            source.weapon_or_large_prop
            or source.outfit_preview
            or gesture is not None
        )
        synthetic_gesture = (
            _THREE_QUARTER_REQUEST
            if requested is FramingMode.THREE_QUARTER and gesture is None
            else gesture
        )
        force_full = bool(
            source.weapon_or_large_prop
            or source.outfit_preview
            or requested is FramingMode.FULL_BODY
        )
        context = FramingContext(
            available_width_px=request.available_width_px,
            available_height_px=request.available_height_px,
            speech_active=source.speech_active,
            mouth_closed=source.mouth_closed,
            emotion_intensity=(
                max(0.78, source.emotion_intensity)
                if requested is FramingMode.CLOSE
                else 0.0
            ),
            gesture_bounds=synthetic_gesture,
            owner_arrived=False,
            outfit_preview=force_full,
            turning_away=source.angry_back_turn,
            adaptive_enabled=True,
        )
        reasons = (
            (OrchestrationReason.REQUIRED_CONTENT_CONTAINMENT,)
            if containment_required
            else ()
        )
        return context, reasons


def _from_policy(proposal: FramingProposal) -> _Candidate:
    return _Candidate(
        proposal.mode,
        proposal.score,
        proposal.confidence,
        tuple(reason.value for reason in proposal.reasons),
        OrchestrationReason.POLICY_CANDIDATE,
    )


def _from_wellbeing_cue(cue: ApprovedWellbeingPerformance) -> _Candidate:
    event_id = str(cue.event_id).strip()
    reason = str(cue.reason_code).strip()
    kind = _enum_value(cue.kind)
    stage = _enum_value(cue.stage)
    framing = _enum_value(cue.framing)
    if not event_id or not reason or not kind or not stage:
        raise ValueError("Approved wellbeing cue audit fields must not be empty.")
    modes = {
        "half": FramingMode.HALF,
        "close_candidate": FramingMode.CLOSE,
        "three_quarter": FramingMode.THREE_QUARTER,
    }
    try:
        mode = modes[framing]
    except KeyError as error:
        raise ValueError("Approved wellbeing cue framing is unsupported.") from error
    if stage == "initial" and mode is FramingMode.CLOSE:
        raise ValueError("An initial wellbeing cue must never request close framing.")
    return _Candidate(
        mode,
        0.90 if stage == "initial" else 0.98,
        0.94,
        (f"wellbeing:{kind}:{stage}", reason),
        OrchestrationReason.APPROVED_WELLBEING_CUE,
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value)).strip()


def _best(candidates: list[_Candidate] | tuple[_Candidate, ...]) -> _Candidate:
    if not candidates:
        raise ValueError("Framing preferences excluded every candidate.")
    return max(
        candidates,
        key=lambda item: (item.score, item.confidence, -int(item.mode)),
    )
