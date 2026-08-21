from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from cloud_scene_interpreter import (
    CloudSceneInterpretation,
    InteractionCandidateKind,
    LocalizedInteractionCandidate,
    SceneFact,
    SceneFactKind,
    SceneFactStatus,
)
lazy from gesture_intent import GestureIntentDecision, GestureState
lazy from local_visual_intelligence import (
    ConservativeDegradation,
    EvidenceAvailability,
    LocalVisualIntelligenceResult,
    PresenceIdentityEvidence,
)
lazy from object_interaction import (
    ObjectInteractionAction,
    ObjectInteractionCandidate,
)
lazy from vision_domain import IdentityObservation, IdentityState, SceneUnderstanding
lazy from visual_context_fusion import (
    FusionDisposition,
    VisualContextFusion,
    VisualContextFusionRequest,
    VisualEvidenceClass,
    VisualEvidenceSource,
)
lazy from visual_social_cues import (
    GazeHeadDirection,
    ObservableFacialCue,
    VisualSocialCueObservation,
)

EXPECTED_OBSERVED_AT = 123.5

OWNER = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.98)

def local_result(
    *,
    observed_at: float = 123.5,
    object_label: str | None = "book",
    object_confidence: float = 0.93,
) -> LocalVisualIntelligenceResult:
    candidate = ObjectInteractionCandidate(
        ObjectInteractionAction.OFFER_OBSERVATION if object_label else ObjectInteractionAction.NONE,
        object_label,
        "looks_like_object" if object_label else None,
        object_confidence if object_label else 0.0,
        1.0 - object_confidence if object_label else 1.0,
        False,
    )
    return LocalVisualIntelligenceResult(
        observed_at,
        PresenceIdentityEvidence(OWNER, None, None),
        EvidenceAvailability.AVAILABLE,
        VisualSocialCueObservation(
            (ObservableFacialCue.SMILE_LIKE,),
            GazeHeadDirection.SCREEN_LIKE,
            0.91,
            0.09,
        ),
        EvidenceAvailability.AVAILABLE,
        GestureIntentDecision(GestureState.IDLE, None, None, 0.0),
        EvidenceAvailability.AVAILABLE,
        candidate,
        False,
        (ConservativeDegradation.HAND_LANDMARK_MODEL_UNAVAILABLE,),
        (),
    )


def cloud(*facts: SceneFact) -> CloudSceneInterpretation:
    candidates = tuple(
        LocalizedInteractionCandidate(
            InteractionCandidateKind.COMMENT,
            f"cloud_scene.observed_{fact.kind.value}",
            (("kind", fact.kind.value), ("label", fact.label)),
            fact.confidence,
        )
        for fact in facts
        if fact.status is SceneFactStatus.OBSERVED
    )
    return CloudSceneInterpretation(
        10,
        SceneUnderstanding(IdentityObservation(IdentityState.UNKNOWN), (), (), ()),
        facts,
        candidates,
        0,
    )


def assert_cloud_identity_payload_cannot_replace_local_identity() -> None:
    fusion = VisualContextFusion()
    generation = fusion.begin_operation()
    untrusted_cloud = CloudSceneInterpretation(
        11,
        SceneUnderstanding(
            IdentityObservation(
                IdentityState.RECOGNIZED,
                "untrusted-cloud-id",
                "Different person",
                1.0,
            ),
            (),
            (),
            (),
        ),
        (),
        (),
        0,
    )
    context = fusion.fuse(
        VisualContextFusionRequest(generation, local_result(), untrusted_cloud)
    )
    assert context.identity is OWNER


def assert_local_identity_is_always_authoritative() -> None:
    fusion = VisualContextFusion()
    generation = fusion.begin_operation()
    context = fusion.fuse(
        VisualContextFusionRequest(
            generation,
            local_result(),
            cloud(
                SceneFact(SceneFactKind.PERSON, "person", SceneFactStatus.OBSERVED, 0.99),
                SceneFact(SceneFactKind.SCENE, "indoor", SceneFactStatus.OBSERVED, 0.90),
            ),
        )
    )
    assert context.identity is OWNER
    assert all(fact.kind != "person" for fact in context.observed)
    assert any(fact.label == "indoor" for fact in context.observed)


def assert_evidence_classes_remain_separate_and_non_executable() -> None:
    fusion = VisualContextFusion()
    generation = fusion.begin_operation()
    context = fusion.fuse(
        VisualContextFusionRequest(
            generation,
            local_result(),
            cloud(
                SceneFact(SceneFactKind.OBJECT, "cup", SceneFactStatus.OBSERVED, 0.90),
                SceneFact(SceneFactKind.ACTIVITY, "possible_reading", SceneFactStatus.INFERRED, 0.88),
                SceneFact(SceneFactKind.SCENE, "outdoor", SceneFactStatus.UNCERTAIN, 0.50),
            ),
        )
    )
    assert context.publishable
    assert all(fact.evidence_class is VisualEvidenceClass.OBSERVED for fact in context.observed)
    assert all(fact.evidence_class is VisualEvidenceClass.INFERRED for fact in context.inferred)
    assert all(fact.evidence_class is VisualEvidenceClass.UNCERTAIN for fact in context.uncertain)
    assert not hasattr(context, "speak")
    assert not hasattr(context, "execute")


def assert_local_equal_or_stronger_object_wins_conflict() -> None:
    fusion = VisualContextFusion()
    generation = fusion.begin_operation()
    context = fusion.fuse(
        VisualContextFusionRequest(
            generation,
            local_result(object_confidence=0.93),
            cloud(SceneFact(SceneFactKind.OBJECT, "book", SceneFactStatus.OBSERVED, 0.93)),
        )
    )
    books = [fact for fact in context.observed if fact.label == "book"]
    assert len(books) == 1
    assert books[0].source is VisualEvidenceSource.LOCAL
    assert context.interaction_candidates == ()


def assert_cancel_reset_and_stale_generations_fail_closed() -> None:
    fusion = VisualContextFusion()
    first = fusion.begin_operation()
    fusion.cancel(first)
    cancelled = fusion.fuse(VisualContextFusionRequest(first, local_result(), cloud()))
    assert cancelled.disposition is FusionDisposition.CANCELLED
    reset_generation = fusion.reset()
    stale = fusion.fuse(VisualContextFusionRequest(first, local_result(), cloud()))
    assert stale.disposition is FusionDisposition.STALE
    current = fusion.fuse(
        VisualContextFusionRequest(reset_generation, local_result(), cloud())
    )
    assert current.disposition is FusionDisposition.FUSED


def assert_deterministic_and_local_timestamp_preserved() -> None:
    request_facts = cloud(
        SceneFact(SceneFactKind.OBJECT, "cup", SceneFactStatus.OBSERVED, 0.90),
        SceneFact(SceneFactKind.SCENE, "indoor", SceneFactStatus.OBSERVED, 0.91),
    )
    first_fusion = VisualContextFusion()
    first_generation = first_fusion.begin_operation()
    first = first_fusion.fuse(
        VisualContextFusionRequest(first_generation, local_result(), request_facts)
    )
    second_fusion = VisualContextFusion()
    second_generation = second_fusion.begin_operation()
    second = second_fusion.fuse(
        VisualContextFusionRequest(second_generation, local_result(), request_facts)
    )
    assert first == second
    assert first.observed_at == EXPECTED_OBSERVED_AT


def run() -> None:
    assert_cloud_identity_payload_cannot_replace_local_identity()
    assert_local_identity_is_always_authoritative()
    assert_evidence_classes_remain_separate_and_non_executable()
    assert_local_equal_or_stronger_object_wins_conflict()
    assert_cancel_reset_and_stale_generations_fail_closed()
    assert_deterministic_and_local_timestamp_preserved()
    print("VISUAL_CONTEXT_FUSION_OK")


if __name__ == "__main__":
    run()
