from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from gesture_intent import (
    GestureIntent,
    GestureState,
    HandLandmarks,
    HandSide,
    LipRegion,
    NormalizedPoint,
)
lazy from local_visual_intelligence import (
    ConservativeDegradation,
    DenseFacialEvidence,
    EvidenceAvailability,
    IntelligenceComponent,
    LocalFrameAnalysis,
    LocalVisualIntelligencePipeline,
)
lazy from object_interaction import ObjectInteractionAction, ObjectSemanticScope
lazy from vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    ObjectDetection,
    SceneUnderstanding,
)
lazy from visual_social_cues import (
    FacialCueMeasurements,
    GazeHeadDirection,
    ObservableFacialCue,
)

IDENTITY = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.94)
FACE_BOX = BoundingBox(0.2, 0.1, 0.8, 0.9)
SPARSE = tuple(
    NormalizedPoint(0.35 + index * 0.07, 0.4 + (index % 2) * 0.08)
    for index in range(5)
)
LIPS = LipRegion(NormalizedPoint(0.5, 0.45), 0.12, 0.08)


def scene(*objects: ObjectDetection) -> SceneUnderstanding:
    return SceneUnderstanding(IDENTITY, tuple(objects), (), ())


def detection(label: str, confidence: float = 0.9) -> ObjectDetection:
    return ObjectDetection(label, confidence, BoundingBox(0.1, 0.1, 0.4, 0.5))


def dense(*, lips: LipRegion | None = LIPS) -> DenseFacialEvidence:
    landmarks = tuple(
        NormalizedPoint(0.2 + (index % 5) * 0.1, 0.2 + (index // 5) * 0.1)
        for index in range(20)
    )
    return DenseFacialEvidence(
        landmarks,
        FacialCueMeasurements(smile_like=0.88, screen_alignment=0.83),
        lips,
    )


def silence_hand(side: HandSide, *, mirrored: bool = False) -> HandLandmarks:
    points = [NormalizedPoint(0.5, 0.82) for _ in range(21)]
    points[6] = NormalizedPoint(0.5, 0.59)
    points[8] = NormalizedPoint(0.5, 0.46)
    for pip, tip in ((10, 12), (14, 16), (18, 20)):
        points[pip] = NormalizedPoint(0.52, 0.68)
        points[tip] = NormalizedPoint(0.51, 0.74)
    if mirrored:
        points = [NormalizedPoint(1.0 - point.x, point.y) for point in points]
    return HandLandmarks(side, tuple(points))


def frame(
    at: float,
    *,
    face: DenseFacialEvidence | None = None,
    hands: tuple[HandLandmarks, ...] | None = None,
    objects: tuple[ObjectDetection, ...] = (),
) -> LocalFrameAnalysis:
    return LocalFrameAnalysis(
        at,
        scene(*objects),
        FACE_BOX,
        SPARSE,
        face,
        hands,
    )


def exact_object_frame(
    at: float,
    *,
    lookup: bool = False,
    privacy: bool = False,
) -> LocalFrameAnalysis:
    return LocalFrameAnalysis(
        at,
        scene(detection("book")),
        FACE_BOX,
        SPARSE,
        semantic_scope=ObjectSemanticScope.EXACT_TITLE_BRAND_OR_CONTENT,
        lookup_requested=lookup,
        privacy_allows_cloud_offer=privacy,
    )


def assert_yunet_five_points_degrade_without_inventing_social_or_hand_data() -> None:
    pipeline = LocalVisualIntelligencePipeline()
    result = pipeline.analyze(frame(0.0, objects=(detection("book"),)))
    assert result.evidence.identity is IDENTITY
    assert result.evidence.face_box is FACE_BOX
    assert result.evidence.sparse_face_landmarks is SPARSE
    assert result.social_availability is EvidenceAvailability.UNKNOWN
    assert result.social_cues.facial_cues == (ObservableFacialCue.UNKNOWN,)
    assert result.social_cues.gaze_head_direction is GazeHeadDirection.UNKNOWN
    assert result.gesture_availability is EvidenceAvailability.UNKNOWN
    assert result.gesture.intent is None
    assert ConservativeDegradation.YUNET_FIVE_POINT_INSUFFICIENT in result.degradations
    assert ConservativeDegradation.HAND_LANDMARK_MODEL_UNAVAILABLE in result.degradations
    assert result.object_interaction.action is ObjectInteractionAction.OFFER_OBSERVATION


def assert_full_local_evidence_produces_one_immutable_result() -> None:
    pipeline = LocalVisualIntelligencePipeline(
        minimum_gesture_frames=3,
        minimum_gesture_duration=0.2,
    )
    right = silence_hand(HandSide.RIGHT)
    first = pipeline.analyze(frame(1.0, face=dense(), hands=(right,)))
    second = pipeline.analyze(frame(1.1, face=dense(), hands=(right,)))
    final = pipeline.analyze(frame(1.21, face=dense(), hands=(right,)))
    assert first.social_cues.facial_cues == (ObservableFacialCue.SMILE_LIKE,)
    assert first.social_cues.gaze_head_direction is GazeHeadDirection.SCREEN_LIKE
    assert second.gesture.state is GestureState.CANDIDATE
    assert final.gesture.intent is GestureIntent.SILENCE_REQUEST
    assert final.gesture_availability is EvidenceAvailability.AVAILABLE
    try:
        final.cloud_semantics_needed = True
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("Pipeline result must be immutable.")


def assert_mirror_setting_is_geometry_only_and_supports_both_hands() -> None:
    for side in HandSide:
        pipeline = LocalVisualIntelligencePipeline(
            mirrored_input=True,
            minimum_gesture_frames=2,
            minimum_gesture_duration=0.1,
        )
        observed = silence_hand(side, mirrored=True)
        pipeline.analyze(frame(2.0, face=dense(), hands=(observed,)))
        result = pipeline.analyze(frame(2.11, face=dense(), hands=(observed,)))
        assert result.gesture.intent is GestureIntent.SILENCE_REQUEST
        assert result.gesture.hand is side


def assert_reset_cancel_and_monotonic_time_are_explicit() -> None:
    pipeline = LocalVisualIntelligencePipeline(
        minimum_gesture_frames=2,
        minimum_gesture_duration=0.1,
    )
    hand = silence_hand(HandSide.LEFT)
    pipeline.analyze(frame(3.0, face=dense(), hands=(hand,)))
    pipeline.cancel()
    after_cancel = pipeline.analyze(frame(3.1, face=dense(), hands=(hand,)))
    assert after_cancel.gesture.state is GestureState.CANDIDATE
    pipeline.reset()
    reset = pipeline.analyze(frame(0.0, face=dense(), hands=(hand,)))
    assert reset.gesture.state is GestureState.CANDIDATE
    try:
        pipeline.analyze(frame(-0.1, face=dense(), hands=(hand,)))
    except ValueError:
        pass
    else:
        raise AssertionError("Time reversal must fail explicitly.")


def assert_object_privacy_boundary_is_preserved() -> None:
    pipeline = LocalVisualIntelligencePipeline()
    exact = pipeline.analyze(exact_object_frame(4.0))
    assert exact.object_interaction.action is ObjectInteractionAction.NONE
    assert exact.cloud_semantics_needed
    consent = pipeline.analyze(exact_object_frame(4.1, lookup=True, privacy=True))
    assert consent.object_interaction.action is ObjectInteractionAction.ASK_LOOKUP_CONSENT
    assert consent.cloud_semantics_needed


def assert_optional_component_errors_are_isolated_but_visible() -> None:
    pipeline = LocalVisualIntelligencePipeline()
    invalid = detection("book", float("nan"))
    result = pipeline.analyze(frame(5.0, objects=(invalid,)))
    assert result.evidence.identity is IDENTITY
    assert result.object_availability is EvidenceAvailability.FAILED
    assert result.object_interaction.action is ObjectInteractionAction.NONE
    assert result.failures[0].component is IntelligenceComponent.OBJECT_INTERACTION
    assert result.failures[0].error_type == "ValueError"
    assert ConservativeDegradation.OPTIONAL_COMPONENT_FAILED in result.degradations


def run() -> None:
    assert_yunet_five_points_degrade_without_inventing_social_or_hand_data()
    assert_full_local_evidence_produces_one_immutable_result()
    assert_mirror_setting_is_geometry_only_and_supports_both_hands()
    assert_reset_cancel_and_monotonic_time_are_explicit()
    assert_object_privacy_boundary_is_preserved()
    assert_optional_component_errors_are_isolated_but_visible()
    print("LOCAL_VISUAL_INTELLIGENCE_OK")


if __name__ == "__main__":
    run()
