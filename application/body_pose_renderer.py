from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from application.rgba_compositing import (
    RgbaCompositorPort,
    create_rgba_compositor,
)
lazy from domain.character_pose import CharacterPose, ViewBlend

LAYER_DEPTHS = frozendict(
    {
        "background": 0,
        "hair-back": 10,
        "body": 20,
        "authored-full-body": 20,
        "leg-left": 21,
        "leg-right": 22,
        "foot-left": 23,
        "foot-right": 24,
        "sole-left": 25,
        "sole-right": 26,
        "garment-back": 30,
        "arm-left": 40,
        "arm-right": 50,
        "garment-front": 60,
        "hand-left": 70,
        "hand-right": 80,
        "weapon": 90,
        "face-alignment": 91,
        "hair-alignment": 92,
        "garment-alignment": 93,
        "accessory-alignment": 94,
        "hair-front": 100,
        "face": 110,
        "mouth": 115,
        "foreground": 120,
    }
)
REQUIRED_BODY_LAYERS = frozenset(
    {
        "body",
        "arm-left",
        "arm-right",
        "hand-left",
        "hand-right",
    }
)


@dataclass(frozen=True, slots=True)
class BodyPoseLayer:
    name: str
    depth: int
    rgba: bytes


@dataclass(frozen=True, slots=True)
class PoseAssetSet:
    view_id: str
    silhouette: str
    width: int
    height: int
    layers: tuple[BodyPoseLayer, ...]
    available_corrections: frozenset[str]
    outfit_compatible: bool
    face_visible: bool
    articulation_safe: bool


@dataclass(frozen=True, slots=True)
class BodyPoseFrame:
    width: int
    height: int
    rgba: bytes
    generation: int
    view_ids: tuple[str, ...]
    layer_order: tuple[str, ...]
    articulation_active: bool
    contract: str = "legacy-v3"
    body_profile_id: str = ""
    rig_id: str | None = None
    geometry_signature: tuple[float, ...] = ()
    crop: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    static_revision: str = ""


class PoseAssetSource(Protocol):
    def resolve(self, view_id: str) -> PoseAssetSet | None: ...


class PoseFramePublisher(Protocol):
    def publish(self, frame: BodyPoseFrame) -> None: ...


class ArticulationOverlayPort(Protocol):
    def continue_overlay(
        self,
        frame: bytes,
        view_id: str,
        generation: int,
    ) -> bytes: ...

    def pause(self, generation: int) -> None: ...


class BodyPoseRenderer:
    """Atomically compose complete authored views and safe crossfades."""

    def __init__(  # noqa: PLR0913 -- renderer ports are explicit dependencies
        self,
        width: int,
        height: int,
        source: PoseAssetSource,
        publisher: PoseFramePublisher,
        articulation: ArticulationOverlayPort,
        *,
        rgba_compositor: RgbaCompositorPort | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Pose canvas dimensions must be positive.")
        self.width = width
        self.height = height
        self._source = source
        self._publisher = publisher
        self._articulation = articulation
        self._rgba = rgba_compositor or create_rgba_compositor()
        self._generation = 0
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

    def begin_transition(self) -> int:
        self._generation += 1
        return self._generation

    def render(
        self,
        generation: int,
        blend: ViewBlend,
        first_pose: CharacterPose | None,
        second_pose: CharacterPose | None,
    ) -> BodyPoseFrame:
        if generation != self._generation or not self._crossfade_is_safe(
            blend,
            first_pose,
            second_pose,
        ):
            return self._current_frame
        first_assets = self._source.resolve(blend.first.view_id)
        second_assets = self._source.resolve(blend.second.view_id)
        if first_assets is None or second_assets is None:
            return self._current_frame
        first_frame = self._compose_view(first_assets, first_pose)
        second_frame = self._compose_view(second_assets, second_pose)
        if first_frame is None or second_frame is None:
            return self._current_frame
        first_rgba, first_order = first_frame
        second_rgba, second_order = second_frame
        if first_order != second_order:
            return self._current_frame
        mixed = self._rgba.crossfade_rgba(
            first_rgba,
            second_rgba,
            round(blend.second_weight * 65_535),
        )
        articulation_active = bool(
            first_assets.face_visible
            and second_assets.face_visible
            and first_assets.articulation_safe
            and second_assets.articulation_safe
            and first_pose.speech_safe
            and second_pose.speech_safe
        )
        view_identity = f"{first_assets.view_id}|{second_assets.view_id}"
        if articulation_active:
            mixed = self._articulation.continue_overlay(
                mixed,
                view_identity,
                generation,
            )
        else:
            self._articulation.pause(generation)
        if (
            len(mixed) != self.width * self.height * 4
            or generation != self._generation
        ):
            return self._current_frame
        candidate = BodyPoseFrame(
            self.width,
            self.height,
            mixed,
            generation,
            (first_assets.view_id, second_assets.view_id),
            first_order,
            articulation_active,
        )
        self._publish(candidate)
        if generation == self._generation:
            self._current_frame = candidate
        return self._current_frame

    def _crossfade_is_safe(
        self,
        blend: ViewBlend,
        first_pose: CharacterPose | None,
        second_pose: CharacterPose | None,
    ) -> bool:
        return bool(
            blend.interpolated
            and blend.reason == "adjacent_crossfade"
            and 0.0 <= blend.second_weight <= 1.0
            and first_pose is not None
            and second_pose is not None
            and first_pose.view_id == blend.first.view_id
            and second_pose.view_id == blend.second.view_id
        )

    def _compose_view(
        self,
        assets: PoseAssetSet,
        pose: CharacterPose,
    ) -> tuple[bytes, tuple[str, ...]] | None:
        if (
            assets.view_id != pose.view_id
            or assets.silhouette != pose.silhouette
            or assets.width != self.width
            or assets.height != self.height
            or not assets.outfit_compatible
            or not pose.required_corrections.issubset(
                assets.available_corrections
            )
        ):
            return None
        names = tuple(layer.name for layer in assets.layers)
        if len(set(names)) != len(names) or not set(names) >= REQUIRED_BODY_LAYERS:
            return None
        if not assets.face_visible and "face" in names:
            return None
        if any(
            layer.name not in LAYER_DEPTHS
            or layer.depth != LAYER_DEPTHS[layer.name]
            or len(layer.rgba) != self.width * self.height * 4
            for layer in assets.layers
        ):
            return None
        ordered = tuple(sorted(assets.layers, key=lambda layer: layer.depth))
        if len({layer.depth for layer in ordered}) != len(ordered):
            return None
        frame = bytes(self.width * self.height * 4)
        for layer in ordered:
            frame = self._rgba.alpha_over_rgba(frame, layer.rgba)
        return frame, tuple(layer.name for layer in ordered)

    def _publish(self, candidate: BodyPoseFrame) -> None:
        previous = self._current_frame
        try:
            self._publisher.publish(candidate)
        except Exception:
            self._publisher.publish(previous)
            raise
