from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from cloud_scene_interpreter import (
    CloudSceneInterpreter,
    InteractionCandidateKind,
    SceneFactKind,
    SceneFactStatus,
)
lazy from integrations.openai_vision_provider import (
    ClaimStatus,
    VisionDetail,
    VisionProviderResult,
    VisionResultStatus,
    VisualClaim,
    VisualUnderstanding,
)
lazy from vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    ObjectDetection,
    SceneUnderstanding,
)

EXPECTED_SUPPRESSED_CLAIMS = 5
EXPECTED_OBSERVED_AT = 1234.5


def claim(
    text: str,
    status: ClaimStatus,
    confidence: float,
    evidence: str = "Visible pixels support this description.",
) -> VisualClaim:
    return VisualClaim(text, status, confidence, evidence)


def result(*claims: VisualClaim) -> VisionProviderResult:
    return VisionProviderResult(
        7,
        VisionResultStatus.SUCCESS,
        "gpt-5.6-luna",
        VisionDetail.AUTO,
        VisualUnderstanding("Scene summary.", claims, ()),
    )


def assert_observation_inference_and_uncertainty_are_separate() -> None:
    interpreted = CloudSceneInterpreter().interpret(
        result(
            claim("A person is visible near a laptop.", ClaimStatus.OBSERVED, 0.94),
            claim("The person may be reading a book.", ClaimStatus.INFERRED, 0.88),
            claim("A cup might be present.", ClaimStatus.UNCERTAIN, 0.99),
        )
    )
    assert {(fact.kind, fact.status) for fact in interpreted.facts} == {
        (SceneFactKind.PERSON, SceneFactStatus.OBSERVED),
        (SceneFactKind.ACTIVITY, SceneFactStatus.INFERRED),
    }
    assert interpreted.increment.activities == ("possible_reading",)
    assert interpreted.increment.uncertainty == (
        "cloud_possible_reading_not_confirmed",
    )
    assert all(
        candidate.text_key.startswith("cloud_scene.")
        for candidate in interpreted.interaction_candidates
    )
    assert all(not hasattr(candidate, "speak") for candidate in interpreted.interaction_candidates)


def assert_low_confidence_and_sensitive_exact_claims_are_suppressed() -> None:
    interpreted = CloudSceneInterpreter().interpret(
        result(
            claim("A laptop is visible.", ClaimStatus.OBSERVED, 0.74),
            claim("The person is named Alice.", ClaimStatus.OBSERVED, 0.99),
            claim('The book title is “Secret History”.', ClaimStatus.OBSERVED, 0.99),
            claim("The phone brand may be ExampleCorp.", ClaimStatus.INFERRED, 0.99),
            claim("手機品牌可能是範例公司。", ClaimStatus.INFERRED, 0.99),
        )
    )
    assert interpreted.facts == ()
    assert interpreted.increment.objects == ()
    assert interpreted.suppressed_claims == EXPECTED_SUPPRESSED_CLAIMS
    offers = [
        candidate
        for candidate in interpreted.interaction_candidates
        if candidate.kind is InteractionCandidateKind.OFFER_LOOKUP
    ]
    assert len(offers) == 1
    assert offers[0].requires_user_action
    assert "Secret History" not in repr(interpreted)
    assert "ExampleCorp" not in repr(interpreted)
    assert "範例公司" not in repr(interpreted)
    assert all(fact.kind is not SceneFactKind.PERSON for fact in interpreted.facts)


def assert_local_verified_identity_timestamp_and_evidence_win() -> None:
    owner = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.97)
    local_laptop = ObjectDetection(
        "laptop",
        0.96,
        BoundingBox(10, 10, 100, 100),
    )
    local = SceneUnderstanding(owner, (local_laptop,), ("at_computer",), ())
    cloud = CloudSceneInterpreter().interpret(
        result(
            claim("A laptop is visible.", ClaimStatus.OBSERVED, 0.90),
            claim("A person is visible.", ClaimStatus.OBSERVED, 0.95),
        )
    )
    merged = CloudSceneInterpreter().merge(
        local,
        local_observed_at=EXPECTED_OBSERVED_AT,
        cloud=cloud,
    )
    assert merged.scene.identity is owner
    assert merged.scene.objects == (local_laptop,)
    assert merged.observed_at == EXPECTED_OBSERVED_AT
    assert all(fact.label != "laptop" for fact in merged.cloud_facts)
    assert merged.scene.activities == ("at_computer",)


def assert_unknown_or_failed_input_degrades_safely() -> None:
    interpreter = CloudSceneInterpreter()
    failed = VisionProviderResult(
        8,
        VisionResultStatus.NETWORK_UNAVAILABLE,
        "gpt-5.6-luna",
        VisionDetail.AUTO,
    )
    for value in (failed, {"operation_id": 99, "future": "unknown"}, None):
        interpreted = interpreter.interpret(value)
        assert interpreted.facts == ()
        assert interpreted.interaction_candidates == ()
        assert interpreted.increment.identity.state is IdentityState.UNKNOWN
        assert interpreted.increment.activities == ()


def assert_deterministic_deduplication() -> None:
    repeated = result(
        claim("A book is visible.", ClaimStatus.OBSERVED, 0.91),
        claim("A book is visible.", ClaimStatus.OBSERVED, 0.91),
    )
    first = CloudSceneInterpreter().interpret(repeated)
    second = CloudSceneInterpreter().interpret(repeated)
    assert first == second
    assert len(first.facts) == 1
    assert first.facts[0].label == "book"


def run() -> None:
    assert_observation_inference_and_uncertainty_are_separate()
    assert_low_confidence_and_sensitive_exact_claims_are_suppressed()
    assert_local_verified_identity_timestamp_and_evidence_win()
    assert_unknown_or_failed_input_degrades_safely()
    assert_deterministic_deduplication()
    print("CLOUD_SCENE_INTERPRETER_OK")


if __name__ == "__main__":
    run()
