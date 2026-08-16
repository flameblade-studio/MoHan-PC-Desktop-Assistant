from __future__ import annotations

lazy from domain.vision_domain import (
    IdentityObservation,
    ObjectDetection,
    SceneUnderstanding,
)


class LocalSceneInterpreter:
    """Infer conservative scene facts from spatially stable local detections."""

    _DRINK_CONTAINERS = frozenset({"bottle", "cup", "wine glass"})
    _READING_OBJECTS = frozenset({"book"})

    def interpret(
        self,
        identity: IdentityObservation,
        detections: tuple[ObjectDetection, ...],
    ) -> SceneUnderstanding:
        labels = {detection.label for detection in detections if detection.confidence >= 0.45}
        activities: list[str] = []
        uncertainty: list[str] = []
        if "person" in labels and labels & self._DRINK_CONTAINERS:
            activities.append("possible_drinking")
            uncertainty.append("drinking_not_confirmed")
        if "person" in labels and labels & self._READING_OBJECTS:
            activities.append("possible_reading")
            uncertainty.append("reading_not_confirmed")
        if "laptop" in labels or "keyboard" in labels:
            activities.append("at_computer")
        return SceneUnderstanding(identity, detections, tuple(activities), tuple(uncertainty))
