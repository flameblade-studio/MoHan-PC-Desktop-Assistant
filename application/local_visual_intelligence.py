from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from application.object_interaction import (
    ObjectInteractionAction,
    ObjectInteractionCandidate,
    ObjectInteractionRequest,
    ObjectSemanticScope,
    propose_object_interaction,
)
lazy from domain.air_interaction import AirInteractionEvent
lazy from application.visual_social_cues import (
    FacialCueMeasurements,
    GazeHeadDirection,
    ObservableFacialCue,
    VisualSocialCueObservation,
    observe_social_cues,
)
lazy from domain.gesture_intent import (
    GestureFrame,
    GestureIntentDecision,
    GestureState,
    HandLandmarks,
    LipRegion,
    NormalizedPoint,
    SilenceGestureDetector,
)
lazy from domain.vision_domain import (
    BoundingBox,
    IdentityObservation,
    SceneUnderstanding,
)


class EvidenceAvailability(StrEnum):
    AVAILABLE = "available"
    UNKNOWN = "unknown"
    FAILED = "failed"


class ConservativeDegradation(StrEnum):
    YUNET_FIVE_POINT_INSUFFICIENT = "yunet-five-point-insufficient"
    DENSE_FACE_ANALYSIS_UNAVAILABLE = "dense-face-analysis-unavailable"
    HAND_LANDMARK_MODEL_UNAVAILABLE = "hand-landmark-model-unavailable"
    OPTIONAL_COMPONENT_FAILED = "optional-component-failed"


class IntelligenceComponent(StrEnum):
    SOCIAL_CUES = "social-cues"
    GESTURE_INTENT = "gesture-intent"
    OBJECT_INTERACTION = "object-interaction"


@dataclass(frozen=True, slots=True)
class ComponentFailure:
    component: IntelligenceComponent
    error_type: str
    message: str

    def __post_init__(self) -> None:
        if not self.error_type or not self.message:
            raise ValueError("Component failures must remain observable.")


@dataclass(frozen=True, slots=True)
class PresenceIdentityEvidence:
    """Evidence passed through unchanged from the local OpenCV boundary."""

    identity: IdentityObservation
    face_box: BoundingBox | None
    sparse_face_landmarks: tuple[NormalizedPoint, ...] | None

    def __post_init__(self) -> None:
        landmarks = self.sparse_face_landmarks
        if landmarks is not None and len(landmarks) != 5:
            raise ValueError("YuNet sparse face evidence must contain five points.")


@dataclass(frozen=True, slots=True)
class DenseFacialEvidence:
    landmarks: tuple[NormalizedPoint, ...]
    measurements: FacialCueMeasurements
    lips: LipRegion | None = None

    def __post_init__(self) -> None:
        if len(self.landmarks) < 20:
            raise ValueError("Dense facial evidence requires at least 20 landmarks.")


@dataclass(frozen=True, slots=True)
class LocalFrameAnalysis:
    observed_at: float
    scene: SceneUnderstanding
    face_box: BoundingBox | None = None
    sparse_face_landmarks: tuple[NormalizedPoint, ...] | None = None
    dense_face: DenseFacialEvidence | None = None
    hands: tuple[HandLandmarks, ...] | None = None
    semantic_scope: ObjectSemanticScope = ObjectSemanticScope.GENERAL
    lookup_requested: bool = False
    privacy_allows_cloud_offer: bool = False
    air_interaction: AirInteractionEvent | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.observed_at):
            raise ValueError("Local frame time must be finite.")
        if self.sparse_face_landmarks is not None and len(self.sparse_face_landmarks) != 5:
            raise ValueError("Sparse face analysis must contain exactly five points.")
        if self.hands is not None and len({hand.side for hand in self.hands}) != len(self.hands):
            raise ValueError("A local frame cannot contain duplicate hand sides.")
        if self.air_interaction is not None and not isinstance(
            self.air_interaction,
            AirInteractionEvent,
        ):
            raise TypeError("Local air interaction evidence must be canonical.")


@dataclass(frozen=True, slots=True)
class LocalVisualIntelligenceResult:
    observed_at: float
    evidence: PresenceIdentityEvidence
    social_availability: EvidenceAvailability
    social_cues: VisualSocialCueObservation
    gesture_availability: EvidenceAvailability
    gesture: GestureIntentDecision
    object_availability: EvidenceAvailability
    object_interaction: ObjectInteractionCandidate
    cloud_semantics_needed: bool
    degradations: tuple[ConservativeDegradation, ...]
    failures: tuple[ComponentFailure, ...]
    air_interaction: AirInteractionEvent | None = None


class LocalVisualIntelligencePipeline:
    """Coordinate local evidence without camera, UI, storage, network, or control."""

    def __init__(
        self,
        *,
        mirrored_input: bool = False,
        minimum_gesture_frames: int = 3,
        minimum_gesture_duration: float = 0.20,
        gesture_cooldown: float = 2.0,
    ) -> None:
        self._mirrored_input = bool(mirrored_input)
        self._gesture_settings = (
            minimum_gesture_frames,
            minimum_gesture_duration,
            gesture_cooldown,
        )
        self._gesture = self._new_gesture_detector()
        self._last_time = -math.inf

    def analyze(self, frame: LocalFrameAnalysis) -> LocalVisualIntelligenceResult:
        if frame.observed_at < self._last_time:
            raise ValueError("Local visual frames must use monotonic time order.")
        self._last_time = frame.observed_at
        evidence = PresenceIdentityEvidence(
            frame.scene.identity,
            frame.face_box,
            frame.sparse_face_landmarks,
        )
        degradations: list[ConservativeDegradation] = []
        failures: list[ComponentFailure] = []
        social_availability, social = self._social(frame, degradations, failures)
        gesture_availability, gesture = self._gesture_result(
            frame,
            degradations,
            failures,
        )
        object_availability, object_candidate = self._object(frame, failures)
        if failures:
            degradations.append(ConservativeDegradation.OPTIONAL_COMPONENT_FAILED)
        return LocalVisualIntelligenceResult(
            frame.observed_at,
            evidence,
            social_availability,
            social,
            gesture_availability,
            gesture,
            object_availability,
            object_candidate,
            object_candidate.requires_cloud_semantics,
            tuple(dict.fromkeys(degradations)),
            tuple(failures),
            frame.air_interaction,
        )

    def cancel(self) -> None:
        self._gesture.cancel()

    def reset(self) -> None:
        self._gesture = self._new_gesture_detector()
        self._last_time = -math.inf

    def _new_gesture_detector(self) -> SilenceGestureDetector:
        frames, duration, cooldown = self._gesture_settings
        return SilenceGestureDetector(
            minimum_frames=frames,
            minimum_duration=duration,
            cooldown=cooldown,
        )

    def _social(
        self,
        frame: LocalFrameAnalysis,
        degradations: list[ConservativeDegradation],
        failures: list[ComponentFailure],
    ) -> tuple[EvidenceAvailability, VisualSocialCueObservation]:
        if frame.dense_face is None:
            degradations.append(
                ConservativeDegradation.YUNET_FIVE_POINT_INSUFFICIENT
                if frame.sparse_face_landmarks is not None
                else ConservativeDegradation.DENSE_FACE_ANALYSIS_UNAVAILABLE
            )
            return EvidenceAvailability.UNKNOWN, _unknown_social()
        try:
            return (
                EvidenceAvailability.AVAILABLE,
                observe_social_cues(frame.dense_face.measurements),
            )
        except (TypeError, ValueError) as error:
            failures.append(_failure(IntelligenceComponent.SOCIAL_CUES, error))
            return EvidenceAvailability.FAILED, _unknown_social()

    def _gesture_result(
        self,
        frame: LocalFrameAnalysis,
        degradations: list[ConservativeDegradation],
        failures: list[ComponentFailure],
    ) -> tuple[EvidenceAvailability, GestureIntentDecision]:
        if frame.hands is None:
            self._gesture.cancel()
            degradations.append(ConservativeDegradation.HAND_LANDMARK_MODEL_UNAVAILABLE)
            return EvidenceAvailability.UNKNOWN, _unknown_gesture()
        lips = frame.dense_face.lips if frame.dense_face is not None else None
        if lips is None:
            self._gesture.cancel()
            degradations.append(ConservativeDegradation.DENSE_FACE_ANALYSIS_UNAVAILABLE)
            return EvidenceAvailability.UNKNOWN, _unknown_gesture()
        try:
            canonical_lips, canonical_hands = self._canonical_geometry(lips, frame.hands)
            decision = self._gesture.update(
                GestureFrame(
                    frame.observed_at,
                    canonical_lips,
                    canonical_hands,
                    tracking_valid=True,
                )
            )
            return EvidenceAvailability.AVAILABLE, decision
        except (RuntimeError, TypeError, ValueError) as error:
            self._gesture.cancel()
            failures.append(_failure(IntelligenceComponent.GESTURE_INTENT, error))
            return EvidenceAvailability.FAILED, _unknown_gesture()

    def _object(
        self,
        frame: LocalFrameAnalysis,
        failures: list[ComponentFailure],
    ) -> tuple[EvidenceAvailability, ObjectInteractionCandidate]:
        try:
            candidate = propose_object_interaction(
                ObjectInteractionRequest(
                    frame.scene,
                    frame.semantic_scope,
                    frame.lookup_requested,
                    frame.privacy_allows_cloud_offer,
                )
            )
            return EvidenceAvailability.AVAILABLE, candidate
        except (TypeError, ValueError) as error:
            failures.append(_failure(IntelligenceComponent.OBJECT_INTERACTION, error))
            return EvidenceAvailability.FAILED, _unknown_object()

    def _canonical_geometry(
        self,
        lips: LipRegion,
        hands: tuple[HandLandmarks, ...],
    ) -> tuple[LipRegion, tuple[HandLandmarks, ...]]:
        if not self._mirrored_input:
            return lips, hands

        def point(value: NormalizedPoint) -> NormalizedPoint:
            return NormalizedPoint(1.0 - value.x, value.y)

        return (
            LipRegion(point(lips.center), lips.width, lips.height),
            tuple(
                HandLandmarks(hand.side, tuple(point(value) for value in hand.points))
                for hand in hands
            ),
        )


def _unknown_social() -> VisualSocialCueObservation:
    return VisualSocialCueObservation(
        (ObservableFacialCue.UNKNOWN,),
        GazeHeadDirection.UNKNOWN,
        0.0,
        1.0,
    )


def _unknown_gesture() -> GestureIntentDecision:
    return GestureIntentDecision(GestureState.IDLE, None, None, 0.0)


def _unknown_object() -> ObjectInteractionCandidate:
    return ObjectInteractionCandidate(
        ObjectInteractionAction.NONE,
        None,
        None,
        0.0,
        1.0,
        False,
    )


def _failure(component: IntelligenceComponent, error: Exception) -> ComponentFailure:
    message = str(error).strip() or "unspecified optional component failure"
    return ComponentFailure(component, type(error).__name__, message)
