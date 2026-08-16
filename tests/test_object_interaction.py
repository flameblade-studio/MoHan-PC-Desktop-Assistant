from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from object_interaction import (
    ObjectInteractionAction,
    ObjectInteractionRequest,
    ObjectSemanticScope,
    propose_object_interaction,
)
lazy from vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    ObjectDetection,
    SceneUnderstanding,
)


def scene(label: str, confidence: float) -> SceneUnderstanding:
    detection = ObjectDetection(label, confidence, BoundingBox(0.1, 0.1, 0.5, 0.5))
    return SceneUnderstanding(
        IdentityObservation(IdentityState.UNKNOWN),
        (detection,),
        (),
        (),
    )


def assert_supported_object_is_hedged_and_local() -> None:
    result = propose_object_interaction(ObjectInteractionRequest(scene("book", 0.91)))
    assert result.action is ObjectInteractionAction.OFFER_OBSERVATION
    assert result.object_label == "book"
    assert result.wording_key == "looks_like_object"
    assert not result.requires_cloud_semantics


def assert_low_confidence_and_unknown_objects_stay_silent() -> None:
    low = propose_object_interaction(ObjectInteractionRequest(scene("book", 0.60)))
    unknown = propose_object_interaction(ObjectInteractionRequest(scene("artifact", 0.99)))
    assert low.action is ObjectInteractionAction.NONE
    assert unknown.action is ObjectInteractionAction.NONE
    assert low.wording_key is None and unknown.wording_key is None


def assert_exact_semantics_require_cloud_and_explicit_consent_offer() -> None:
    exact = ObjectInteractionRequest(
        scene("book", 0.93),
        ObjectSemanticScope.EXACT_TITLE_BRAND_OR_CONTENT,
    )
    blocked = propose_object_interaction(exact)
    assert blocked.action is ObjectInteractionAction.NONE
    assert blocked.requires_cloud_semantics
    requested_without_privacy = propose_object_interaction(
        ObjectInteractionRequest(
            exact.scene,
            exact.semantic_scope,
            lookup_requested=True,
            privacy_allows_cloud_offer=False,
        )
    )
    assert requested_without_privacy.action is ObjectInteractionAction.NONE
    consent = propose_object_interaction(
        ObjectInteractionRequest(
            exact.scene,
            exact.semantic_scope,
            lookup_requested=True,
            privacy_allows_cloud_offer=True,
        )
    )
    assert consent.action is ObjectInteractionAction.ASK_LOOKUP_CONSENT
    assert consent.wording_key == "ask_lookup_consent"
    assert consent.requires_cloud_semantics


def assert_invalid_detection_is_not_silently_accepted() -> None:
    for confidence in (-0.1, 1.1, float("nan")):
        try:
            propose_object_interaction(
                ObjectInteractionRequest(scene("book", confidence))
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid detection confidence must be rejected.")


def run() -> None:
    assert_supported_object_is_hedged_and_local()
    assert_low_confidence_and_unknown_objects_stay_silent()
    assert_exact_semantics_require_cloud_and_explicit_consent_offer()
    assert_invalid_detection_is_not_silently_accepted()
    print("OBJECT_INTERACTION_OK")


if __name__ == "__main__":
    run()
