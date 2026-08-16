from __future__ import annotations

lazy import hashlib
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Protocol

lazy from application.rgba_compositing import (
    RgbaCompositorPort,
    create_rgba_compositor,
)
lazy from domain.appearance_dynamics import (
    IDENTITY_TRANSFORM,
    AppearanceDynamics,
    DynamicsFrame,
    DynamicsInput,
    MotionTransform,
    motion_group_for_slot,
)


class AppearanceRenderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PixelMask:
    width: int
    height: int
    values: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Mask dimensions must be positive.")
        if len(self.values) != self.width * self.height:
            raise ValueError("Mask size does not match its dimensions.")
        if any(value not in (0, 1) for value in self.values):
            raise ValueError("Mask values must be binary.")


@dataclass(frozen=True, slots=True)
class CoreAppearanceManifest:
    width: int
    height: int
    core_rgba: bytes
    immutable_identity: PixelMask
    approved_regions: Mapping[str, PixelMask]
    occlusion_masks: Mapping[str, PixelMask]
    silhouettes: tuple[str, ...] = ("front-crossed",)


@dataclass(frozen=True, slots=True)
class ResolvedLayerAsset:
    path: str
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True, slots=True)
class AppearanceLayer:
    slot: str
    path: str
    sha256: str
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    z_order: int
    approved_region: str
    occlusion_masks: tuple[str, ...] = ()

    def replace(self, **changes: object) -> AppearanceLayer:
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class CompositingResult:
    width: int
    height: int
    rgba: bytes
    silhouette: str
    applied_slots: tuple[str, ...]
    layer_transforms: tuple[LayerTransformDescription, ...] = ()


@dataclass(frozen=True, slots=True)
class LayerTransformDescription:
    slot: str
    z_order: int
    transform: MotionTransform


class LayerAssetResolver(Protocol):
    def resolve(self, path: str) -> ResolvedLayerAsset | None: ...


class FramePublisher(Protocol):
    def publish(self, frame: bytes) -> None: ...


class AppearanceRenderer:
    """Validate and atomically composite generic appearance layers."""

    def __init__(
        self,
        core: CoreAppearanceManifest,
        resolver: LayerAssetResolver,
        publisher: FramePublisher | None = None,
        dynamics: AppearanceDynamics | None = None,
        rgba_compositor: RgbaCompositorPort | None = None,
    ) -> None:
        self._validate_core(core)
        self._core = core
        self._resolver = resolver
        self._publisher = publisher
        self._dynamics = dynamics or AppearanceDynamics()
        self._rgba = rgba_compositor or create_rgba_compositor()
        self._current_frame = CompositingResult(
            core.width,
            core.height,
            core.core_rgba,
            core.silhouettes[0],
            (),
        )

    @property
    def current_frame(self) -> CompositingResult:
        return self._current_frame

    def render(
        self,
        silhouette: str,
        layers: tuple[AppearanceLayer, ...],
        dynamics_input: DynamicsInput | None = None,
    ) -> CompositingResult:
        if silhouette not in self._core.silhouettes:
            raise AppearanceRenderError("Unknown or missing silhouette.")
        ordered = tuple(sorted(layers, key=lambda layer: layer.z_order))
        if len({layer.z_order for layer in ordered}) != len(ordered):
            raise AppearanceRenderError("Layer z-order must be unique.")
        resolved = tuple(
            (layer, self._resolve_and_validate(layer)) for layer in ordered
        )
        frame = self._core.core_rgba
        for declaration, asset in resolved:
            frame = self._composite(frame, declaration, asset)
        dynamics_snapshot = self._dynamics.snapshot()
        dynamics_frame = (
            self._dynamics.current_frame
            if dynamics_input is None
            else self._dynamics.advance(dynamics_input)
        )
        result = CompositingResult(
            self._core.width,
            self._core.height,
            frame,
            silhouette,
            tuple(layer.slot for layer in ordered),
            self._layer_transforms(ordered, dynamics_frame),
        )
        try:
            self._publish(result)
        except Exception:
            self._dynamics.restore(dynamics_snapshot)
            raise
        self._current_frame = result
        return result

    @staticmethod
    def _layer_transforms(
        layers: tuple[AppearanceLayer, ...],
        frame: DynamicsFrame,
    ) -> tuple[LayerTransformDescription, ...]:
        if frame.static_fallback:
            return ()
        return tuple(
            LayerTransformDescription(
                layer.slot,
                layer.z_order,
                frame.for_slot(layer.slot),
            )
            for layer in layers
            if motion_group_for_slot(layer.slot) is not None
            and frame.for_slot(layer.slot) != IDENTITY_TRANSFORM
        )

    def _resolve_and_validate(
        self,
        layer: AppearanceLayer,
    ) -> ResolvedLayerAsset:
        if layer.approved_region not in self._core.approved_regions:
            raise AppearanceRenderError("Layer region is not approved.")
        if any(name not in self._core.occlusion_masks for name in layer.occlusion_masks):
            raise AppearanceRenderError("Occlusion mask is not allowlisted.")
        asset = self._resolver.resolve(layer.path)
        if asset is None or asset.path != layer.path:
            raise AppearanceRenderError("Layer asset is missing.")
        if (
            asset.width != layer.width
            or asset.height != layer.height
            or asset.width <= 0
            or asset.height <= 0
            or asset.width > self._core.width
            or asset.height > self._core.height
            or len(asset.rgba) != asset.width * asset.height * 4
        ):
            raise AppearanceRenderError("Layer dimensions are invalid.")
        if hashlib.sha256(asset.rgba).hexdigest() != layer.sha256:
            raise AppearanceRenderError("Layer hash does not match.")
        if not self._alpha_edges_are_safe(asset):
            raise AppearanceRenderError("Layer alpha edge is unsafe.")
        return asset

    def _composite(
        self,
        frame: bytes,
        layer: AppearanceLayer,
        asset: ResolvedLayerAsset,
    ) -> bytes:
        region = self._core.approved_regions[layer.approved_region]
        occlusions = tuple(
            self._core.occlusion_masks[name] for name in layer.occlusion_masks
        )
        try:
            return self._rgba.composite_region_rgba(
                frame,
                self._core.width,
                self._core.height,
                asset.rgba,
                asset.width,
                asset.height,
                layer.anchor_x,
                layer.anchor_y,
                region.values,
                self._core.immutable_identity.values,
                tuple(mask.values for mask in occlusions),
            )
        except ValueError as error:
            raise AppearanceRenderError(str(error)) from error

    def _publish(self, result: CompositingResult) -> None:
        if self._publisher is None:
            return
        previous = self._current_frame
        try:
            self._publisher.publish(result.rgba)
        except Exception:
            self._publisher.publish(previous.rgba)
            raise

    @staticmethod
    def _alpha_edges_are_safe(asset: ResolvedLayerAsset) -> bool:
        for y in range(asset.height):
            for x in range(asset.width):
                index = (y * asset.width + x) * 4
                red, green, blue, alpha = asset.rgba[index : index + 4]
                if alpha == 0 and (red or green or blue):
                    return False
                if (
                    alpha != 0
                    and (x == 0 or y == 0 or x == asset.width - 1 or y == asset.height - 1)
                ):
                    return False
        return True

    @staticmethod
    def _validate_core(core: CoreAppearanceManifest) -> None:
        if core.width <= 0 or core.height <= 0 or not core.silhouettes:
            raise AppearanceRenderError("Core canvas is invalid.")
        if len(core.core_rgba) != core.width * core.height * 4:
            raise AppearanceRenderError("Core frame size is invalid.")
        masks = (
            core.immutable_identity,
            *core.approved_regions.values(),
            *core.occlusion_masks.values(),
        )
        if any(mask.width != core.width or mask.height != core.height for mask in masks):
            raise AppearanceRenderError("Core mask size is invalid.")
