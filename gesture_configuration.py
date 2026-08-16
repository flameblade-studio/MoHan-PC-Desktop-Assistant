"""Compatibility facade for domain gesture configuration."""

from __future__ import annotations

from domain.gesture_configuration import (
    BUILTIN_GESTURE_LABELS,
    DEFAULT_GESTURE_BINDINGS,
    GESTURE_ACTION_LABELS,
    GESTURE_CONFIGURATION_FORMAT,
    GESTURE_CONFIGURATION_VERSION,
    LANDMARKS_PER_HAND,
    MAX_CUSTOM_GESTURES,
    MAX_SAMPLES_PER_GESTURE,
    GestureAction,
    GestureBinding,
    GestureConfiguration,
    GestureDefinition,
    GestureLandmark,
    GestureSample,
    GestureSource,
    LocalizedLabel,
    default_gesture_definitions,
    export_gesture_configuration,
    import_gesture_configuration,
)

__all__ = (
    "BUILTIN_GESTURE_LABELS",
    "DEFAULT_GESTURE_BINDINGS",
    "GESTURE_ACTION_LABELS",
    "GESTURE_CONFIGURATION_FORMAT",
    "GESTURE_CONFIGURATION_VERSION",
    "LANDMARKS_PER_HAND",
    "MAX_CUSTOM_GESTURES",
    "MAX_SAMPLES_PER_GESTURE",
    "GestureAction",
    "GestureBinding",
    "GestureConfiguration",
    "GestureDefinition",
    "GestureLandmark",
    "GestureSample",
    "GestureSource",
    "LocalizedLabel",
    "default_gesture_definitions",
    "export_gesture_configuration",
    "import_gesture_configuration",
)
