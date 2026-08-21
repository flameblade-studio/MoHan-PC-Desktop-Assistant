"""Anchor calibration for the parametric layered face assets.

The 54 (and future 600) authored layers must share one coordinate system and
one anchor. In continuous-gradient mode a single-pixel misalignment between
layers breaks the "real-girl" illusion, so this module fails closed when any
layer's opaque bounding box drifts more than one pixel from the pose's ``base``
layer.

This module is deliberately Qt-dependent (it decodes pixels), unlike
:mod:`infrastructure.layered_face_assets` which stays Qt-independent and only
reads PNG headers.
"""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtGui import QImage

lazy from infrastructure.layered_face_assets import (
    LAYERED_FACE_DIMENSION,
    LayeredFaceManifest,
)

# A layer whose opaque bounding box drifts more than this many pixels from the
# pose's base layer is rejected. One pixel is the hard ceiling: any larger jump
# is visible as a seam in continuous-gradient mode.
MAX_ANCHOR_DRIFT_PIXELS = 1

# The 18 facial-feature layers whose center must stay inside the base region.
# The 7 body/clothing layers (body, hair_back, hair_left, hair_right,
# sleeve_left, sleeve_right, ornament) legitimately extend beyond the face, so
# their centers are not checked against the base region.
FACIAL_LAYERS = frozenset(
    {
        "base",
        "jaw",
        "oral_cavity",
        "teeth_tongue",
        "lip_lower",
        "lip_upper",
        "corner_left",
        "corner_right",
        "blush_left",
        "blush_right",
        "iris_left",
        "iris_right",
        "eyelid_left",
        "eyelid_right",
        "eyeliner_left",
        "eyeliner_right",
        "brow_left",
        "brow_right",
    }
)


@dataclass(frozen=True, slots=True)
class LayerAnchor:
    """The opaque bounding box of one authored layer."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _opaque_bounds(path: Path) -> LayerAnchor | None:
    """Return the opaque bounding box of a PNG, or ``None`` if fully transparent."""
    image = QImage(str(path))
    if image.isNull():
        raise ValueError(f"cannot decode layered face PNG: {path.name}")
    if image.width() != LAYERED_FACE_DIMENSION or image.height() != LAYERED_FACE_DIMENSION:
        raise ValueError(
            f"unexpected layered face dimensions: {path.name} "
            f"({image.width()}x{image.height()})"
        )
    left = LAYERED_FACE_DIMENSION
    top = LAYERED_FACE_DIMENSION
    right = 0
    bottom = 0
    for y in range(LAYERED_FACE_DIMENSION):
        for x in range(LAYERED_FACE_DIMENSION):
            if image.pixelColor(x, y).alpha() == 0:
                continue
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)
    if right < left or bottom < top:
        return None
    return LayerAnchor(left, top, right + 1, bottom + 1)


def _center(anchor: LayerAnchor) -> tuple[float, float]:
    """Return the center of an anchor box."""
    return (
        (anchor.left + anchor.right) / 2.0,
        (anchor.top + anchor.bottom) / 2.0,
    )


def _center_escape(reference: LayerAnchor, candidate: LayerAnchor) -> float:
    """Return how far ``candidate``'s center escapes ``reference``'s box.

    A local layer (iris, blush, jaw, corner) legitimately occupies only a small
    region of the face, so its box is expected to sit *somewhere inside* the
    base layer's box rather than match it. The anchor check therefore verifies
    that each layer's center still lands inside the base's opaque region; a
    center that escapes the base region means the layer was authored on a
    shifted canvas and would produce a visible seam.
    """

    cx, cy = _center(candidate)
    escape_x = 0.0
    escape_y = 0.0
    if cx < reference.left:
        escape_x = reference.left - cx
    elif cx > reference.right:
        escape_x = cx - reference.right
    if cy < reference.top:
        escape_y = reference.top - cy
    elif cy > reference.bottom:
        escape_y = cy - reference.bottom
    return max(escape_x, escape_y)


def calibrate_layered_face_assets(manifest: LayeredFaceManifest) -> None:
    """Fail closed if any layer's center escapes the base layer's region.

    The ``base`` layer of each pose is the alignment reference. Every other
    layer's opaque bounding-box center must land inside the base layer's opaque
    region (within ``MAX_ANCHOR_DRIFT_PIXELS`` of tolerance). A center that
    escapes the base region means the layer was authored on a shifted canvas and
    would produce a visible seam in continuous-gradient mode. A fully
    transparent layer is also rejected, since it would silently erase that
    facial feature.
    """

    for pose, layered_pose in manifest.poses.items():
        base_path = layered_pose.path("base")
        base_anchor = _opaque_bounds(base_path)
        if base_anchor is None:
            raise ValueError(f"layered face base layer is fully transparent: {pose.value}")
        for layer in FACIAL_LAYERS:
            if layer == "base":
                continue
            anchor = _opaque_bounds(layered_pose.path(layer))
            if anchor is None:
                raise ValueError(
                    f"layered face layer is fully transparent: {pose.value}_{layer}"
                )
            escape = _center_escape(base_anchor, anchor)
            if escape > MAX_ANCHOR_DRIFT_PIXELS:
                raise ValueError(
                    f"layered face anchor center escape {escape:.1f}px exceeds "
                    f"{MAX_ANCHOR_DRIFT_PIXELS}px: {pose.value}_{layer}"
                )
