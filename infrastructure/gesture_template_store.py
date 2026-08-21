from __future__ import annotations

lazy import json
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass, replace
lazy from typing import Final

lazy from domain.contracts import SecretStorePort
lazy from domain.gesture_configuration import (
    LANDMARKS_PER_HAND,
    MAX_CUSTOM_GESTURES,
    MAX_SAMPLES_PER_GESTURE,
    GestureConfiguration,
    GestureLandmark,
    GestureSample,
    GestureSource,
)

GESTURE_TEMPLATES_FORMAT: Final = "mohan-protected-gesture-templates"
GESTURE_TEMPLATES_VERSION: Final = 1
MAX_GESTURE_TEMPLATES_BYTES: Final = 2 * 1024 * 1024
MAX_GESTURE_ID_LENGTH = 80
LANDMARK_COORDINATE_DIMENSIONS = 3
_PAYLOAD_KEYS: Final = frozenset({"format", "version", "templates"})
_BOUNDARY_ERRORS: Final = (Exception,)


class GestureTemplateStoreError(RuntimeError):
    """A fixed-detail error that never exposes protected template content."""


GestureTemplates = dict[str, tuple[GestureSample, ...]]


@dataclass(slots=True)
class ProtectedGestureTemplateStore:
    """Persist normalized hand skeletons behind the operating-system vault."""

    secret_store: SecretStorePort

    def __post_init__(self) -> None:
        try:
            valid = all(
                callable(getattr(self.secret_store, method, None))
                for method in ("load", "save", "clear")
            )
        except _BOUNDARY_ERRORS:
            valid = False
        if not valid:
            raise GestureTemplateStoreError(
                "Protected gesture-template storage is unavailable."
            )

    def load(self) -> GestureTemplates:
        raw = self.snapshot()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            raise GestureTemplateStoreError(
                "Protected gesture templates are invalid."
            ) from None
        return _decode_templates(payload)

    def save(self, configuration: GestureConfiguration) -> None:
        if not isinstance(configuration, GestureConfiguration):
            raise GestureTemplateStoreError(
                "Protected gesture templates are invalid."
            )
        templates = {
            definition.gesture_id: definition.samples
            for definition in configuration.definitions
            if definition.source is GestureSource.CUSTOM and definition.samples
        }
        if not templates:
            self._clear()
            return
        raw = _encode_templates(templates)
        try:
            self.secret_store.save(raw)
        except _BOUNDARY_ERRORS:
            raise GestureTemplateStoreError(
                "Protected gesture templates could not be saved."
            ) from None

    def snapshot(self) -> str:
        try:
            raw = self.secret_store.load()
        except _BOUNDARY_ERRORS:
            raise GestureTemplateStoreError(
                "Protected gesture templates could not be read."
            ) from None
        _validate_raw(raw)
        return raw

    def restore(self, raw: str) -> None:
        _validate_raw(raw)
        if not raw:
            self._clear()
            return
        try:
            self.secret_store.save(raw)
        except _BOUNDARY_ERRORS:
            raise GestureTemplateStoreError(
                "Protected gesture templates could not be restored."
            ) from None

    def _clear(self) -> None:
        try:
            self.secret_store.clear()
        except _BOUNDARY_ERRORS:
            raise GestureTemplateStoreError(
                "Protected gesture templates could not be cleared."
            ) from None


def merge_protected_templates(
    configuration: GestureConfiguration,
    templates: Mapping[str, tuple[GestureSample, ...]],
) -> GestureConfiguration:
    """Attach only templates whose custom definition still exists."""

    if not isinstance(configuration, GestureConfiguration):
        raise GestureTemplateStoreError("Gesture configuration is invalid.")
    definitions = tuple(
        replace(
            definition,
            samples=templates.get(definition.gesture_id, ()),
        )
        if definition.source is GestureSource.CUSTOM
        else definition
        for definition in configuration.definitions
    )
    return replace(configuration, definitions=definitions)


def _encode_templates(
    templates: Mapping[str, tuple[GestureSample, ...]],
) -> str:
    payload = {
        "format": GESTURE_TEMPLATES_FORMAT,
        "version": GESTURE_TEMPLATES_VERSION,
        "templates": {
            gesture_id: [
                [[point.x, point.y, point.z] for point in sample.landmarks]
                for sample in samples
            ]
            for gesture_id, samples in sorted(templates.items())
        },
    }
    try:
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, UnicodeError):
        raise GestureTemplateStoreError(
            "Protected gesture templates are invalid."
        ) from None
    _validate_raw(raw)
    return raw


def _decode_templates(payload: object) -> GestureTemplates:
    if not isinstance(payload, Mapping) or set(payload) != _PAYLOAD_KEYS:
        raise GestureTemplateStoreError("Protected gesture templates are invalid.")
    if payload.get("format") != GESTURE_TEMPLATES_FORMAT:
        raise GestureTemplateStoreError(
            "Protected gesture-template format is unsupported."
        )
    version = payload.get("version")
    if isinstance(version, bool) or version != GESTURE_TEMPLATES_VERSION:
        raise GestureTemplateStoreError(
            "Protected gesture-template version is unsupported."
        )
    raw_templates = payload.get("templates")
    if not isinstance(raw_templates, Mapping):
        raise GestureTemplateStoreError("Protected gesture templates are invalid.")
    if len(raw_templates) > MAX_CUSTOM_GESTURES:
        raise GestureTemplateStoreError("Too many protected gesture templates exist.")
    templates: GestureTemplates = {}
    for gesture_id, raw_samples in raw_templates.items():
        if (
            not isinstance(gesture_id, str)
            or not gesture_id.startswith("custom:")
            or len(gesture_id) > MAX_GESTURE_ID_LENGTH
        ):
            raise GestureTemplateStoreError(
                "A protected gesture-template identifier is invalid."
            )
        templates[gesture_id] = _decode_samples(raw_samples)
    return templates


def _decode_samples(payload: object) -> tuple[GestureSample, ...]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise GestureTemplateStoreError("Protected gesture samples are invalid.")
    if len(payload) > MAX_SAMPLES_PER_GESTURE:
        raise GestureTemplateStoreError("A protected gesture has too many samples.")
    return tuple(_decode_sample(sample) for sample in payload)


def _decode_sample(payload: object) -> GestureSample:
    if (
        not isinstance(payload, Sequence)
        or isinstance(payload, (str, bytes))
        or len(payload) != LANDMARKS_PER_HAND
    ):
        raise GestureTemplateStoreError("A protected gesture sample is invalid.")
    landmarks: list[GestureLandmark] = []
    try:
        for coordinates in payload:
            if (
                not isinstance(coordinates, Sequence)
                or isinstance(coordinates, (str, bytes))
                or len(coordinates) != LANDMARK_COORDINATE_DIMENSIONS
                or not all(type(value) in {int, float} for value in coordinates)
            ):
                raise GestureTemplateStoreError(
                    "Protected gesture landmark coordinates are invalid."
                )
            x, y, z = coordinates
            landmarks.append(GestureLandmark(float(x), float(y), float(z)))
        return GestureSample(tuple(landmarks))
    except (TypeError, ValueError, OverflowError):
        raise GestureTemplateStoreError(
            "Protected gesture landmark coordinates are invalid."
        ) from None


def _validate_raw(raw: object) -> None:
    if not isinstance(raw, str):
        raise GestureTemplateStoreError("Protected gesture templates are invalid.")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError:
        raise GestureTemplateStoreError("Protected gesture templates are invalid.") from None
    if size > MAX_GESTURE_TEMPLATES_BYTES:
        raise GestureTemplateStoreError("Protected gesture templates are too large.")
