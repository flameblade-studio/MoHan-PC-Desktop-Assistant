from __future__ import annotations

lazy import math
lazy import threading
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from application.local_visual_intelligence import (
    EvidenceAvailability,
    LocalVisualIntelligenceResult,
)
lazy from application.object_interaction import ObjectInteractionAction
lazy from application.visual_social_cues import (
    GazeHeadDirection,
    ObservableFacialCue,
)
lazy from domain.cloud_scene_interpreter import (
    CloudSceneInterpretation,
    LocalizedInteractionCandidate,
    SceneFact,
    SceneFactKind,
    SceneFactStatus,
)
lazy from domain.gesture_intent import GestureState
lazy from domain.vision_domain import IdentityObservation


class FusionDisposition(StrEnum):
    FUSED = "fused"
    CANCELLED = "cancelled"
    STALE = "stale"
    INVALID = "invalid"


class VisualEvidenceClass(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class VisualEvidenceSource(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(frozen=True, slots=True)
class FusedVisualFact:
    kind: str
    label: str
    evidence_class: VisualEvidenceClass
    confidence: float
    source: VisualEvidenceSource

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.label.strip():
            raise ValueError("Fused visual facts require stable semantic codes.")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Fused visual confidence must be normalized.")


@dataclass(frozen=True, slots=True)
class VisualContextFusionRequest:
    generation: int
    local: LocalVisualIntelligenceResult
    cloud: CloudSceneInterpretation

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("Fusion generation must not be negative.")
        if not isinstance(self.local, LocalVisualIntelligenceResult):
            raise TypeError("Fusion requires a typed local visual result.")
        if not isinstance(self.cloud, CloudSceneInterpretation):
            raise TypeError("Fusion requires a typed safe cloud interpretation.")


@dataclass(frozen=True, slots=True)
class FusedVisualContext:
    generation: int
    disposition: FusionDisposition
    observed_at: float
    identity: IdentityObservation
    observed: tuple[FusedVisualFact, ...]
    inferred: tuple[FusedVisualFact, ...]
    uncertain: tuple[FusedVisualFact, ...]
    interaction_candidates: tuple[LocalizedInteractionCandidate, ...]

    @property
    def publishable(self) -> bool:
        return self.disposition is FusionDisposition.FUSED


class VisualContextFusion:
    """Fuse local and safe cloud semantics without speech or action authority."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._generation = 0
        self._cancelled_generation: int | None = None

    def begin_operation(self) -> int:
        with self._lock:
            self._generation += 1
            self._cancelled_generation = None
            return self._generation

    def cancel(self, generation: int) -> None:
        if generation < 0:
            return
        with self._lock:
            if generation == self._generation:
                self._cancelled_generation = generation

    def reset(self) -> int:
        with self._lock:
            self._generation += 1
            self._cancelled_generation = None
            return self._generation

    def fuse(self, request: VisualContextFusionRequest) -> FusedVisualContext:
        state = self._operation_state(request.generation)
        if state is not None:
            return _empty_context(request, state)
        local_facts = _local_facts(request.local)
        cloud_facts = _eligible_cloud_facts(request.cloud.facts, local_facts)
        state = self._operation_state(request.generation)
        if state is not None:
            return _empty_context(request, state)
        facts = _deterministic_facts((*local_facts, *cloud_facts))
        return FusedVisualContext(
            request.generation,
            FusionDisposition.FUSED,
            request.local.observed_at,
            request.local.evidence.identity,
            tuple(fact for fact in facts if fact.evidence_class is VisualEvidenceClass.OBSERVED),
            tuple(fact for fact in facts if fact.evidence_class is VisualEvidenceClass.INFERRED),
            tuple(fact for fact in facts if fact.evidence_class is VisualEvidenceClass.UNCERTAIN),
            _safe_candidates(request.cloud.interaction_candidates, cloud_facts),
        )

    def _operation_state(self, generation: int) -> FusionDisposition | None:
        with self._lock:
            if generation == self._cancelled_generation:
                return FusionDisposition.CANCELLED
            if generation != self._generation:
                return FusionDisposition.STALE
        return None


def _local_facts(result: LocalVisualIntelligenceResult) -> tuple[FusedVisualFact, ...]:
    facts: list[FusedVisualFact] = []
    if result.social_availability is EvidenceAvailability.AVAILABLE:
        facts.extend(
            _local_observation("social_cue", cue.value, result.social_cues.confidence)
            for cue in result.social_cues.facial_cues
            if cue is not ObservableFacialCue.UNKNOWN
        )
        direction = result.social_cues.gaze_head_direction
        if direction is not GazeHeadDirection.UNKNOWN:
            facts.append(_local_observation("gaze_direction", direction.value, result.social_cues.confidence))
    if (
        result.gesture_availability is EvidenceAvailability.AVAILABLE
        and result.gesture.state is GestureState.TRIGGERED
        and result.gesture.intent is not None
    ):
        facts.append(_local_observation("gesture", result.gesture.intent.value, result.gesture.confidence))
    if result.air_interaction is not None:
        facts.append(
            _local_observation(
                "air_interaction",
                result.air_interaction.kind.value,
                result.air_interaction.confidence,
            )
        )
    candidate = result.object_interaction
    if (
        result.object_availability is EvidenceAvailability.AVAILABLE
        and candidate.object_label
        and candidate.action is not ObjectInteractionAction.NONE
    ):
        facts.append(_local_observation("object", candidate.object_label, candidate.confidence))
    facts.extend(
            FusedVisualFact(
                "local_evidence",
                degradation.value,
                VisualEvidenceClass.UNCERTAIN,
                0.0,
                VisualEvidenceSource.LOCAL,
            )
            for degradation in result.degradations
    )
    return tuple(facts)


def _local_observation(kind: str, label: str, confidence: float) -> FusedVisualFact:
    return FusedVisualFact(
        kind,
        label,
        VisualEvidenceClass.OBSERVED,
        confidence,
        VisualEvidenceSource.LOCAL,
    )


def _eligible_cloud_facts(
    cloud_facts: tuple[SceneFact, ...],
    local_facts: tuple[FusedVisualFact, ...],
) -> tuple[FusedVisualFact, ...]:
    local_strength = {
        (fact.kind, fact.label.casefold()): fact.confidence
        for fact in local_facts
        if fact.evidence_class is VisualEvidenceClass.OBSERVED
    }
    accepted: list[FusedVisualFact] = []
    for fact in cloud_facts:
        if fact.kind is SceneFactKind.PERSON:
            continue
        converted = _cloud_fact(fact)
        local_confidence = local_strength.get(
            (converted.kind, converted.label.casefold()),
            -1.0,
        )
        if local_confidence >= converted.confidence:
            continue
        accepted.append(converted)
    return tuple(accepted)


def _cloud_fact(fact: SceneFact) -> FusedVisualFact:
    evidence_class = {
        SceneFactStatus.OBSERVED: VisualEvidenceClass.OBSERVED,
        SceneFactStatus.INFERRED: VisualEvidenceClass.INFERRED,
        SceneFactStatus.UNCERTAIN: VisualEvidenceClass.UNCERTAIN,
    }[fact.status]
    return FusedVisualFact(
        fact.kind.value,
        fact.label,
        evidence_class,
        fact.confidence,
        VisualEvidenceSource.CLOUD,
    )


def _deterministic_facts(
    facts: tuple[FusedVisualFact, ...],
) -> tuple[FusedVisualFact, ...]:
    strongest: dict[tuple[str, str, VisualEvidenceClass], FusedVisualFact] = {}
    for fact in facts:
        key = (fact.kind, fact.label.casefold(), fact.evidence_class)
        current = strongest.get(key)
        if current is None or _fact_priority(fact) > _fact_priority(current):
            strongest[key] = fact
    return tuple(
        sorted(
            strongest.values(),
            key=lambda fact: (
                fact.evidence_class.value,
                fact.kind,
                fact.label.casefold(),
                fact.source.value,
            ),
        )
    )


def _fact_priority(fact: FusedVisualFact) -> tuple[int, float]:
    return (1 if fact.source is VisualEvidenceSource.LOCAL else 0, fact.confidence)


def _safe_candidates(
    candidates: tuple[LocalizedInteractionCandidate, ...],
    cloud_facts: tuple[FusedVisualFact, ...],
) -> tuple[LocalizedInteractionCandidate, ...]:
    allowed = {(fact.kind, fact.label) for fact in cloud_facts}
    return tuple(
        candidate
        for candidate in candidates
        if candidate.requires_user_action
        or _candidate_signature(candidate) in allowed
    )


def _candidate_signature(
    candidate: LocalizedInteractionCandidate,
) -> tuple[str, str] | None:
    arguments = dict(candidate.arguments)
    kind = arguments.get("kind")
    label = arguments.get("label")
    return (kind, label) if kind and label else None


def _empty_context(
    request: VisualContextFusionRequest,
    disposition: FusionDisposition,
) -> FusedVisualContext:
    return FusedVisualContext(
        request.generation,
        disposition,
        request.local.observed_at,
        request.local.evidence.identity,
        (),
        (),
        (),
        (),
    )
