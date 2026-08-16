from __future__ import annotations

lazy import hashlib
lazy from dataclasses import dataclass

lazy from application.appearance_renderer import (
    AppearanceLayer,
    AppearanceRenderer,
    CoreAppearanceManifest,
    PixelMask,
    ResolvedLayerAsset,
)
lazy from application.native_rgba_acceleration import (
    alpha_over_rgba_python,
    composite_region_rgba_python,
    crossfade_rgba_python,
)


@dataclass
class RecordingRgbaCompositor:
    region_calls: int = 0

    def alpha_over_rgba(self, target: bytes, source: bytes) -> bytes:
        return alpha_over_rgba_python(target, source)

    def crossfade_rgba(
        self,
        first: bytes,
        second: bytes,
        second_weight: int,
    ) -> bytes:
        return crossfade_rgba_python(first, second, second_weight)

    def composite_region_rgba(
        self,
        target: bytes,
        target_width: int,
        target_height: int,
        source: bytes,
        source_width: int,
        source_height: int,
        anchor_x: int,
        anchor_y: int,
        approved_region: bytes,
        immutable_identity: bytes,
        occlusion_masks: tuple[bytes, ...] = (),
    ) -> bytes:
        self.region_calls += 1
        return composite_region_rgba_python(
            target,
            target_width,
            target_height,
            source,
            source_width,
            source_height,
            anchor_x,
            anchor_y,
            approved_region,
            immutable_identity,
            occlusion_masks,
        )


class Resolver:
    def __init__(self, asset: ResolvedLayerAsset) -> None:
        self._asset = asset

    def resolve(self, _path: str) -> ResolvedLayerAsset:
        return self._asset


def test_appearance_renderer_routes_safe_region_composition_through_port() -> None:
    core_rgba = bytes(4 * 4 * 4)
    binary_canvas = bytes((1,) * 16)
    empty_canvas = bytes(16)
    core = CoreAppearanceManifest(
        4,
        4,
        core_rgba,
        PixelMask(4, 4, empty_canvas),
        {"garment": PixelMask(4, 4, binary_canvas)},
        {},
    )
    layer_rgba = b"\x00" * 16 + bytes((40, 80, 120, 255)) + b"\x00" * 16
    asset = ResolvedLayerAsset("layer", 3, 3, layer_rgba)
    layer = AppearanceLayer(
        "garment",
        "layer",
        hashlib.sha256(layer_rgba).hexdigest(),
        3,
        3,
        0,
        0,
        1,
        "garment",
    )
    compositor = RecordingRgbaCompositor()
    result = AppearanceRenderer(
        core,
        Resolver(asset),
        rgba_compositor=compositor,
    ).render("front-crossed", (layer,))

    assert compositor.region_calls == 1
    assert result.rgba[20:24] == bytes((40, 80, 120, 255))
