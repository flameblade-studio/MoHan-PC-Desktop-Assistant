from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.vision_domain import ObjectDetection, SceneUnderstanding

MIN_CONFIDENCE_THRESHOLD = 0.5


class ObjectInteractionAction(StrEnum):
    NONE = "none"
    OFFER_OBSERVATION = "offer-observation"
    ASK_LOOKUP_CONSENT = "ask-lookup-consent"


class ObjectSemanticScope(StrEnum):
    GENERAL = "general"
    EXACT_TITLE_BRAND_OR_CONTENT = "exact-title-brand-or-content"


@dataclass(frozen=True, slots=True)
class ObjectInteractionRequest:
    scene: SceneUnderstanding
    semantic_scope: ObjectSemanticScope = ObjectSemanticScope.GENERAL
    lookup_requested: bool = False
    privacy_allows_cloud_offer: bool = False


@dataclass(frozen=True, slots=True)
class ObjectInteractionCandidate:
    action: ObjectInteractionAction
    object_label: str | None
    wording_key: str | None
    confidence: float
    uncertainty: float
    requires_cloud_semantics: bool

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in (self.confidence, self.uncertainty)
        ):
            raise ValueError("Object confidence and uncertainty must be normalized.")


_NATURAL_OBJECTS = frozenset(
    {"book", "bottle", "cup", "laptop", "keyboard", "cell phone", "clock"}
)


def propose_object_interaction(
    request: ObjectInteractionRequest,
    *,
    confidence_threshold: float = 0.72,
) -> ObjectInteractionCandidate:
    """Offer a hedged local observation or consent request; never perform lookup."""

    if not math.isfinite(confidence_threshold) or not MIN_CONFIDENCE_THRESHOLD <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be finite and conservative.")
    detection = _best_supported_detection(request.scene.objects)
    if detection is None or detection.confidence < confidence_threshold:
        return _none()
    if request.semantic_scope is ObjectSemanticScope.EXACT_TITLE_BRAND_OR_CONTENT:
        if request.lookup_requested and request.privacy_allows_cloud_offer:
            return ObjectInteractionCandidate(
                ObjectInteractionAction.ASK_LOOKUP_CONSENT,
                detection.label,
                "ask_lookup_consent",
                detection.confidence,
                1.0 - detection.confidence,
                True,
            )
        return ObjectInteractionCandidate(
            ObjectInteractionAction.NONE,
            detection.label,
            None,
            detection.confidence,
            1.0 - detection.confidence,
            True,
        )
    return ObjectInteractionCandidate(
        ObjectInteractionAction.OFFER_OBSERVATION,
        detection.label,
        "looks_like_object",
        detection.confidence,
        1.0 - detection.confidence,
        False,
    )


def _best_supported_detection(
    detections: tuple[ObjectDetection, ...],
) -> ObjectDetection | None:
    for detection in detections:
        if (
            not detection.label.strip()
            or not math.isfinite(detection.confidence)
            or not 0.0 <= detection.confidence <= 1.0
        ):
            raise ValueError("Object detections must have a label and normalized confidence.")
    supported = (
        detection
        for detection in detections
        if detection.label.strip().casefold() in _NATURAL_OBJECTS
    )
    return max(supported, key=lambda detection: detection.confidence, default=None)


def _none() -> ObjectInteractionCandidate:
    return ObjectInteractionCandidate(
        ObjectInteractionAction.NONE,
        None,
        None,
        0.0,
        1.0,
        False,
    )
