"""Load and validate the 25-layer parametric 2.5D face assets.

Codex authored 75 transparent PNG layers (three poses × 25 layers) under
``assets/expressions/layered/``: the original 18 facial layers plus 7 body
layers (body, hair_back, hair_left, hair_right, sleeve_left, sleeve_right,
ornament). This module loads them into an immutable, Qt-independent manifest so
the parametric renderer can compose a continuously controlled half-body
portrait without whole-expression image switching.

Layer naming follows the *screen* left/right convention used by the authored
assets. The renderer is responsible for any character-local mirroring.
"""

from __future__ import annotations

lazy import struct
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.constants import FULL_BODY_LAYER_Z_ORDER
lazy from domain.face_rig import FacePose

LAYERED_FACE_DIMENSION = 1254
PNG_HEADER_LENGTH = 24

# The 25 authored layers, in paint order (bottom to top). This is the same
# Z-order as ``FULL_BODY_LAYER_Z_ORDER`` so the half-body and full-body
# renderers share one authoritative ordering.
LAYER_NAMES = FULL_BODY_LAYER_Z_ORDER

# Layers that must be present for every pose.
REQUIRED_LAYERS = frozenset(LAYER_NAMES)


@dataclass(frozen=True, slots=True)
class LayeredFacePose:
    """One pose's complete set of 18 transparent layers."""

    pose: FacePose
    layers: frozendict[str, Path]

    def path(self, layer: str) -> Path:
        return self.layers[layer]


@dataclass(frozen=True, slots=True)
class LayeredFaceManifest:
    """The complete three-pose layered face asset set."""

    poses: frozendict[FacePose, LayeredFacePose]

    def pose(self, pose: FacePose) -> LayeredFacePose:
        return self.poses[pose]


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(PNG_HEADER_LENGTH)
    if len(header) != PNG_HEADER_LENGTH or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid layered face PNG: {path.name}")
    return struct.unpack(">II", header[16:24])


def load_layered_face_assets(root: Path) -> LayeredFaceManifest:
    """Load and validate all 54 layered face assets, failing closed on gaps."""

    poses: dict[FacePose, LayeredFacePose] = {}
    for pose in FacePose:
        layers: dict[str, Path] = {}
        for layer in LAYER_NAMES:
            path = root / f"{pose.value}_{layer}.png"
            if not path.is_file():
                raise FileNotFoundError(
                    f"missing layered face asset: {pose.value}_{layer}.png"
                )
            if _png_dimensions(path) != (LAYERED_FACE_DIMENSION, LAYERED_FACE_DIMENSION):
                raise ValueError(
                    f"unexpected layered face dimensions: {pose.value}_{layer}.png"
                )
            layers[layer] = path
        poses[pose] = LayeredFacePose(pose, frozendict(layers))
    return LayeredFaceManifest(frozendict(poses))
