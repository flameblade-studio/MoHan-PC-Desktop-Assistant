from __future__ import annotations

lazy import hashlib
lazy import math
lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from application.body_pose_renderer import (
    LAYER_DEPTHS,
    BodyPoseFrame,
    BodyPoseLayer,
    PoseFramePublisher,
)
lazy from application.rgba_compositing import (
    RgbaCompositorPort,
    create_rgba_compositor,
)
lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_full_body_rig import FULL_BODY_RIG_SCHEMA_VERSION

FULL_BODY_CONTRACT = "full-body-v4"
FULL_BODY_RIG_ID = "mohan-full-body-v1"
AUTHORED_FULL_BODY_SLOT = "authored-full-body"
V4_STATIC_LAYER_SLOTS = frozenset(
    {
        "body",
        "arm-left",
        "arm-right",
        "hand-left",
        "hand-right",
        "leg-left",
        "leg-right",
        "foot-left",
        "foot-right",
        "sole-left",
        "sole-right",
        "face-alignment",
        "hair-alignment",
        "garment-alignment",
        "accessory-alignment",
    }
)
SPEECH_LAYER_SLOTS = frozenset({"face", "mouth"})


@dataclass(frozen=True, slots=True)
class NormalizedCrop:
    """Crop-only framing; it cannot prescribe a stretched output size."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Crop values must be finite.")
        if (
            self.x < 0.0
            or self.y < 0.0
            or self.width <= 0.0
            or self.height <= 0.0
            or self.x + self.width > 1.0
            or self.y + self.height > 1.0
        ):
            raise ValueError("Crop must remain inside normalized frame bounds.")

    @property
    def tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)


@dataclass(frozen=True, slots=True)
class FullBodyLayerEvidence:
    slot: str
    sha256: str
    evidence: str

    def __post_init__(self) -> None:
        if (
            not self.slot.strip()
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
            or not self.evidence.strip()
        ):
            raise ValueError("Layer evidence must be complete and verifiable.")


@dataclass(frozen=True, slots=True)
class FullBodyRenderLayer:
    layer: BodyPoseLayer
    evidence: FullBodyLayerEvidence

    def __post_init__(self) -> None:
        if self.layer.name != self.evidence.slot:
            raise ValueError("Layer evidence identifies a different slot.")
        if hashlib.sha256(self.layer.rgba).hexdigest() != self.evidence.sha256:
            raise ValueError("Layer pixels do not match their evidence hash.")


@dataclass(frozen=True, slots=True)
class FullBodyRenderSpec:
    view_id: str
    width: int
    height: int
    body_profile_id: str
    body_profile_version_range: tuple[int, int]
    rig_id: str
    rig_version_range: tuple[int, int]
    geometry_signature: tuple[float, ...]
    crop: NormalizedCrop
    static_layers: tuple[FullBodyRenderLayer, ...]
    source_evidence: str


class FullBodyFramePublisher(Protocol):
    def publish(self, frame: BodyPoseFrame) -> None: ...


class FullBodyRenderAdapter:
    """Compose v4 bodies atomically while speech only replaces face layers."""

    def __init__(
        self,
        width: int,
        height: int,
        publisher: PoseFramePublisher | FullBodyFramePublisher,
        rgba_compositor: RgbaCompositorPort | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Full-body canvas dimensions must be positive.")
        self.width = width
        self.height = height
        self._publisher = publisher
        self._rgba = rgba_compositor or create_rgba_compositor()
        self._generation = 0
        self._static_compositions = 0
        self._static_rgba: bytes | None = None
        self._static_layer_order: tuple[str, ...] = ()
        self._current_frame = BodyPoseFrame(
            width,
            height,
            bytes(width * height * 4),
            0,
            (),
            (),
            False,
        )

    @property
    def current_frame(self) -> BodyPoseFrame:
        return self._current_frame

    @property
    def static_compositions(self) -> int:
        return self._static_compositions

    def begin_transition(self) -> int:
        self._generation += 1
        return self._generation

    def render_full_body(
        self,
        generation: int,
        specification: FullBodyRenderSpec,
    ) -> BodyPoseFrame:
        if generation != self._generation:
            return self._current_frame
        composed = self._compose_static(specification)
        if composed is None or generation != self._generation:
            return self._current_frame
        static_rgba, layer_order, revision = composed
        candidate = BodyPoseFrame(
            self.width,
            self.height,
            static_rgba,
            generation,
            (specification.view_id,),
            layer_order,
            False,
            FULL_BODY_CONTRACT,
            specification.body_profile_id,
            specification.rig_id,
            specification.geometry_signature,
            specification.crop.tuple,
            revision,
        )
        if not self._publish_if_current(generation, candidate):
            return self._current_frame
        self._static_rgba = static_rgba
        self._static_layer_order = layer_order
        self._static_compositions += 1
        self._current_frame = candidate
        return candidate

    def crossfade_full_body(
        self,
        generation: int,
        first: FullBodyRenderSpec,
        second: FullBodyRenderSpec,
        second_weight: float,
    ) -> BodyPoseFrame:
        if generation != self._generation or not 0.0 <= second_weight <= 1.0:
            return self._current_frame
        if (
            first.geometry_signature != second.geometry_signature
            or first.crop != second.crop
            or first.body_profile_id != second.body_profile_id
            or first.rig_id != second.rig_id
        ):
            return self._current_frame
        first_composed = self._compose_static(first)
        second_composed = self._compose_static(second)
        if first_composed is None or second_composed is None:
            return self._current_frame
        first_rgba, first_order, first_revision = first_composed
        second_rgba, second_order, second_revision = second_composed
        if first_order != second_order or generation != self._generation:
            return self._current_frame
        mixed = self._rgba.crossfade_rgba(
            first_rgba,
            second_rgba,
            round(second_weight * 65_535),
        )
        revision = hashlib.sha256(
            f"{first_revision}:{second_revision}:{second_weight:.9f}".encode("ascii")
        ).hexdigest()
        candidate = BodyPoseFrame(
            self.width,
            self.height,
            mixed,
            generation,
            (first.view_id, second.view_id),
            first_order,
            False,
            FULL_BODY_CONTRACT,
            first.body_profile_id,
            first.rig_id,
            first.geometry_signature,
            first.crop.tuple,
            revision,
        )
        if not self._publish_if_current(generation, candidate):
            return self._current_frame
        self._static_rgba = mixed
        self._static_layer_order = first_order
        self._static_compositions += 2
        self._current_frame = candidate
        return candidate

    def update_speech_layers(
        self,
        generation: int,
        layers: tuple[FullBodyRenderLayer, ...],
    ) -> BodyPoseFrame:
        if (
            generation != self._generation
            or self._static_rgba is None
            or self._current_frame.contract != FULL_BODY_CONTRACT
        ):
            return self._current_frame
        validated = self._validate_layers(layers, SPEECH_LAYER_SLOTS, exact=False)
        if validated is None or not layers:
            return self._current_frame
        frame = self._static_rgba
        for item in validated:
            frame = self._rgba.alpha_over_rgba(frame, item.layer.rgba)
        if generation != self._generation:
            return self._current_frame
        dynamic_order = tuple(item.layer.name for item in validated)
        candidate = BodyPoseFrame(
            self.width,
            self.height,
            frame,
            generation,
            self._current_frame.view_ids,
            (*self._static_layer_order, *dynamic_order),
            True,
            self._current_frame.contract,
            self._current_frame.body_profile_id,
            self._current_frame.rig_id,
            self._current_frame.geometry_signature,
            self._current_frame.crop,
            self._current_frame.static_revision,
        )
        if self._publish_if_current(generation, candidate):
            self._current_frame = candidate
        return self._current_frame

    def _compose_static(
        self,
        specification: FullBodyRenderSpec,
    ) -> tuple[bytes, tuple[str, ...], str] | None:
        if not self._valid_spec(specification):
            return None
        names = {item.layer.name for item in specification.static_layers}
        allowed = (
            frozenset({AUTHORED_FULL_BODY_SLOT})
            if names == {AUTHORED_FULL_BODY_SLOT}
            else V4_STATIC_LAYER_SLOTS
        )
        layers = self._validate_layers(
            specification.static_layers,
            allowed,
            exact=True,
        )
        if layers is None:
            return None
        frame = bytes(self.width * self.height * 4)
        for item in layers:
            frame = self._rgba.alpha_over_rgba(frame, item.layer.rgba)
        revision = hashlib.sha256(
            "|".join(item.evidence.sha256 for item in layers).encode("ascii")
        ).hexdigest()
        return frame, tuple(item.layer.name for item in layers), revision

    def _valid_spec(self, specification: FullBodyRenderSpec) -> bool:
        return bool(
            specification.view_id.strip()
            and specification.width == self.width
            and specification.height == self.height
            and specification.body_profile_id == MOHAN_BODY_PROFILE.profile_id
            and self._range_contains(
                specification.body_profile_version_range,
                MOHAN_BODY_PROFILE.version,
            )
            and specification.rig_id == FULL_BODY_RIG_ID
            and self._range_contains(
                specification.rig_version_range,
                FULL_BODY_RIG_SCHEMA_VERSION,
            )
            and specification.geometry_signature
            and all(math.isfinite(value) for value in specification.geometry_signature)
            and specification.source_evidence.strip()
        )

    def _validate_layers(
        self,
        layers: tuple[FullBodyRenderLayer, ...],
        allowed: frozenset[str],
        *,
        exact: bool,
    ) -> tuple[FullBodyRenderLayer, ...] | None:
        names = tuple(item.layer.name for item in layers)
        if len(set(names)) != len(names):
            return None
        if (exact and set(names) != allowed) or (not exact and not set(names) <= allowed):
            return None
        if any(
            item.layer.name not in LAYER_DEPTHS
            or item.layer.depth != LAYER_DEPTHS[item.layer.name]
            or len(item.layer.rgba) != self.width * self.height * 4
            for item in layers
        ):
            return None
        ordered = tuple(sorted(layers, key=lambda item: item.layer.depth))
        if len({item.layer.depth for item in ordered}) != len(ordered):
            return None
        return ordered

    def _publish_if_current(
        self,
        generation: int,
        candidate: BodyPoseFrame,
    ) -> bool:
        if generation != self._generation:
            return False
        previous = self._current_frame
        try:
            self._publisher.publish(candidate)
        except Exception:
            self._publisher.publish(previous)
            raise
        if generation != self._generation:
            self._publisher.publish(previous)
            return False
        return True

    @staticmethod
    def _range_contains(value: tuple[int, int], version: int) -> bool:
        return bool(
            len(value) == 2
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
            and value[0] <= version < value[1]
        )
