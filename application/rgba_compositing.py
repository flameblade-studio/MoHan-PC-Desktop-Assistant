"""Explicit rendering port for bit-exact RGBA composition."""

from __future__ import annotations

lazy from collections.abc import Sequence
lazy from typing import Protocol

lazy from application.native_rgba_acceleration import NativeRgbaAcceleration


class RgbaCompositorPort(Protocol):
    """Pure byte-buffer operations shared by the 2.5D renderers."""

    def alpha_over_rgba(self, target: bytes, source: bytes) -> bytes: ...

    def crossfade_rgba(
        self,
        first: bytes,
        second: bytes,
        second_weight: int,
    ) -> bytes: ...

    def composite_region_rgba(  # noqa: PLR0913, PLR0917 -- pixel-buffer contract
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
        occlusion_masks: Sequence[bytes] = (),
    ) -> bytes: ...


def create_rgba_compositor() -> RgbaCompositorPort:
    """Create one fault-isolated native adapter for one rendering runtime."""
    return NativeRgbaAcceleration()


__all__ = ("RgbaCompositorPort", "create_rgba_compositor")
