"""Parametric 18-layer 2.5D face renderer.

Composes the 54 authored transparent layers (three poses × 18 facial layers)
into a continuously controlled face from a single :class:`FaceMotionFrame`.
This replaces whole-expression image switching with independent, sub-frame
deformation of eyelids, brows, irises, blush, lips, mouth corners, oral cavity,
teeth/tongue, and jaw.

The legacy :class:`~infrastructure.face_renderer.ParametricFaceRenderer` remains
the rollback path; this renderer is the new default once every gate passes.
"""

from __future__ import annotations

lazy from collections import OrderedDict
lazy from dataclasses import replace
lazy from pathlib import Path

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion, QTransform

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_rig import FaceMotionFrame, Viseme
lazy from infrastructure.layered_face_assets import (
    LayeredFaceManifest,
    LayeredFacePose,
    load_layered_face_assets,
)

MOUTH_APERTURE_THRESHOLD = 0.01
SCALE_EPSILON = 1e-4

# The authored 54-layer asset set lives under the project root, mirroring the
# ``RESOURCE_BASE`` resolution used by the presentation layer. The renderer
# resolves it itself so the composition boundary stays a no-arg factory.
LAYERED_FACE_ASSET_DIR = Path("assets") / "expressions" / "layered"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CACHED_LAYER_PIXMAPS = 30
MAX_CACHED_NEUTRAL_POSES = 3


class LayeredParametricFaceRenderer:
    """Compose the 18 authored layers from continuous face parameters.

    This renderer satisfies :class:`FaceRendererPort` so it can replace
    :class:`~infrastructure.face_renderer.ParametricFaceRenderer` at the
    composition boundary. The ``render(base, motion, layers, *, aperture)``
    entry point ignores ``base``/``layers`` (whole-expression inputs) and
    composes from the 18 authored layers instead, keyed by ``motion.pose``.
    """

    def __init__(self, manifest: LayeredFaceManifest | None = None) -> None:
        self._manifest = manifest
        # One 25-layer pose plus a transition margin is sufficient. The former
        # unbounded cache retained every full-canvas pose layer for the entire
        # process lifetime after pose changes.
        self._pixmap_cache: OrderedDict[str, QPixmap] = OrderedDict()
        # A neutral pose is the immutable result of compositing all 25 authored
        # layers.  Speech changes only the small dynamic feature cut-outs, so
        # rebuilding the same 1254px body, hair, clothing and neutral face for
        # both endpoints of every phoneme transition wastes most of the 20ms
        # frame budget.  Keep at most the three authored poses; returned
        # QPixmaps detach on first paint and cannot mutate these authorities.
        self._neutral_pose_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._top_pose_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._layer_center_cache: dict[str, tuple[float, float]] = {}
        self._mask_bounds_cache: dict[int, QRect] = {}

    def _manifest_or_load(self) -> LayeredFaceManifest:
        """Return the injected manifest, or lazily load the authored assets."""
        if self._manifest is None:
            self._manifest = load_layered_face_assets(
                PROJECT_ROOT / LAYERED_FACE_ASSET_DIR
            )
        return self._manifest

    def _pose(self, motion: FaceMotionFrame) -> LayeredFacePose:
        return self._manifest_or_load().pose(motion.pose)

    def _cached_pixmap(self, path) -> QPixmap:
        """Return a decoded layer pixmap, caching it across frames."""
        key = str(path)
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            self._pixmap_cache.move_to_end(key)
            return cached
        pixmap = QPixmap(key)
        self._pixmap_cache[key] = pixmap
        self._pixmap_cache.move_to_end(key)
        while len(self._pixmap_cache) > MAX_CACHED_LAYER_PIXMAPS:
            self._pixmap_cache.popitem(last=False)
        return pixmap

    # -- FaceRendererPort-compatible entry points ---------------------------

    def render(
        self,
        base: QPixmap,
        motion: FaceMotionFrame,
        layers: object,
        *,
        aperture: float | None = None,
    ) -> QPixmap:
        """Compose the 25 authored layers for ``motion.pose``.

        ``base`` and ``layers`` are accepted for interface compatibility with
        :class:`FaceRendererPort` but are ignored: the layered renderer draws
        from its own authored assets instead of a whole-expression image. The
        mouth opening is driven by ``motion.mouth.aperture`` (already smoothed
        by the face-motion controller), unless the caller supplies an explicit
        ``aperture`` override (the legacy speech path passes a discrete 0.0/1.0
        target during mouth transitions). The composed frame is scaled to
        ``base``'s size so the caller's canvas dimensions are preserved.
        """

        if aperture is not None:
            motion = replace(
                motion,
                mouth=replace(
                    motion.mouth,
                    aperture=max(0.0, min(1.0, float(aperture))),
                ),
            )
        composed = self.render_pose(self._pose(motion), motion)
        if composed.isNull() or base.isNull():
            return composed
        result = (
            composed
            if composed.size() == base.size()
            else composed.scaled(
                base.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        actual_aperture = (
            motion.mouth.aperture if aperture is None else float(aperture)
        )
        mouth_source = getattr(layers, "mouth_source", None)
        mouth_mask = getattr(layers, "mouth_mask", None)
        if actual_aperture > MOUTH_APERTURE_THRESHOLD:
            self._paint_masked(
                result,
                mouth_source,
                mouth_mask,
                max(0.0, min(1.0, actual_aperture / 0.18)),
            )
        return result

    def render_overlay(
        self,
        base: QPixmap,
        source: QPixmap,
        *,
        mask: QPixmap | None = None,
        opacity: float = 1.0,
    ) -> QPixmap:
        """Compose one registered expression layer without owning its policy."""

        result = QPixmap(base)
        if mask is None:
            if not source.isNull():
                painter = QPainter(result)
                painter.setOpacity(max(0.0, min(1.0, float(opacity))))
                painter.drawPixmap(0, 0, source)
                painter.end()
            return result
        self._paint_masked(result, source, mask, opacity)
        return result

    # -- core layered composition -------------------------------------------

    def render_pose(
        self,
        pose: LayeredFacePose,
        motion: FaceMotionFrame,
    ) -> QPixmap:
        """Render one complete half-body frame for the given pose and motion."""

        neutral = self._neutral_pose(pose)
        if neutral.isNull():
            return QPixmap()
        # QPixmap uses implicit sharing.  Dynamic painting detaches this frame
        # while the cached neutral authority remains unchanged.
        result = QPixmap(neutral)
        expression = motion.expression_shape
        mouth = motion.mouth

        # Every authored facial PNG is a registered cutout from the authority
        # portrait.  The base deliberately has transparent feature holes, so
        # each neutral cutout must be painted even when its control is zero.
        # Motion is then layered over that stable reconstruction.  Treating
        # these as effect-only overlays produced the reported black eye/cheek
        # holes as soon as speech handed the canvas to this renderer.
        # ``jaw`` is a registered skin replacement, not a detached sprite.
        # Repainting it after translation duplicates the chin and creates a
        # floating skin fragment.  Keep the neutral cutout registered; the
        # lip/cavity controls below provide the visible articulation.

        if motion.viseme is not Viseme.CLOSED or mouth.aperture > MOUTH_APERTURE_THRESHOLD:
            self._paint_mouth_opening(result, pose, mouth)

        self._paint_mouth_lips(result, pose, mouth)

        corner = mouth.corner_smile
        if abs(corner) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, pose.path("corner_left"), dx=-corner * 2.0, dy=-corner * 1.0)
            self._paint_translated(result, pose.path("corner_right"), dx=corner * 2.0, dy=-corner * 1.0)

        if expression.blush > 0.0:
            self._paint_opacity(result, pose.path("blush_left"), expression.blush)
            self._paint_opacity(result, pose.path("blush_right"), expression.blush)

        if expression.blink > 0.0:
            self._paint_opacity(result, pose.path("eyelid_left"), expression.blink)
            self._paint_opacity(result, pose.path("eyelid_right"), expression.blink)
            self._paint_opacity(result, pose.path("eyeliner_left"), expression.blink)
            self._paint_opacity(result, pose.path("eyeliner_right"), expression.blink)

        brow_dy = -expression.brow_lift * 3.0 + expression.brow_tension * 1.5
        if abs(brow_dy) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, pose.path("brow_left"), dy=brow_dy)
            self._paint_translated(result, pose.path("brow_right"), dy=brow_dy)

        # Restore the authored topmost occlusion after dynamic facial layers;
        # bangs, sleeves and ornaments must stay in front of the face.
        self._paint_top_pose(result, pose)
        return result

    def _neutral_pose(self, pose: LayeredFacePose) -> QPixmap:
        """Return the cached exact 25-layer neutral composite for one pose."""

        key = pose.pose.value
        cached = self._neutral_pose_cache.get(key)
        if cached is not None:
            self._neutral_pose_cache.move_to_end(key)
            return cached
        body = self._cached_pixmap(pose.path("body"))
        if body.isNull():
            return QPixmap()
        neutral = QPixmap(body)
        # Preserve the authoritative shared half/full-body Z-order.  This is a
        # layered-renderer cache, not a fallback to a legacy whole portrait.
        for layer_name in (
            "hair_back",
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
        ):
            self._paint_opacity(neutral, pose.path(layer_name), 1.0)
        self._neutral_pose_cache[key] = neutral
        self._neutral_pose_cache.move_to_end(key)
        while len(self._neutral_pose_cache) > MAX_CACHED_NEUTRAL_POSES:
            self._neutral_pose_cache.popitem(last=False)
        return neutral

    def _paint_top_pose(self, target: QPixmap, pose: LayeredFacePose) -> None:
        """Paint one cached transparent top-layer composite in canonical order."""

        key = pose.pose.value
        top = self._top_pose_cache.get(key)
        if top is None:
            body = self._cached_pixmap(pose.path("body"))
            if body.isNull():
                return
            top = QPixmap(body.size())
            top.fill(Qt.transparent)
            for layer_name in (
                "hair_left",
                "hair_right",
                "sleeve_left",
                "sleeve_right",
                "ornament",
            ):
                self._paint_opacity(top, pose.path(layer_name), 1.0)
            self._top_pose_cache[key] = top
            self._top_pose_cache.move_to_end(key)
            while len(self._top_pose_cache) > MAX_CACHED_NEUTRAL_POSES:
                self._top_pose_cache.popitem(last=False)
        else:
            self._top_pose_cache.move_to_end(key)
        painter = QPainter(target)
        painter.drawPixmap(0, 0, top)
        painter.end()

    # -- painting helpers ---------------------------------------------------

    def _paint_opacity(self, target: QPixmap, path, opacity: float) -> None:
        source = self._cached_pixmap(path)
        if source.isNull() or opacity <= 0.0:
            return
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _paint_translated(self, target: QPixmap, path, *, dx: float = 0.0, dy: float = 0.0) -> None:
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(round(dx), round(dy), source)
        painter.end()

    def _paint_masked(
        self,
        target: QPixmap,
        source: QPixmap | None,
        mask: QPixmap | None,
        opacity: float,
    ) -> None:
        if source is None or mask is None or source.isNull() or mask.isNull():
            return
        mask_key = int(mask.cacheKey())
        bounds = self._mask_bounds_cache.get(mask_key)
        if bounds is None:
            bounds = QRegion(mask.mask()).boundingRect()
            self._mask_bounds_cache[mask_key] = bounds
        if bounds.isEmpty():
            return
        # The speech mask occupies only a small mouth rectangle. Allocating and
        # alpha-compositing a full 1254x1254 portrait for every 50 Hz viseme was
        # the dominant Windows p95 cost. Preserve the same DestinationIn blend
        # while restricting the temporary surface to the authored mask bounds.
        layer = QPixmap(bounds.size())
        layer.fill(Qt.transparent)
        mask_painter = QPainter(layer)
        mask_painter.drawPixmap(
            0,
            0,
            source,
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(
            0,
            0,
            mask,
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )
        mask_painter.end()
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(bounds.topLeft(), layer)
        painter.end()

    def _paint_mouth_lips(self, target: QPixmap, pose: LayeredFacePose, mouth) -> None:
        """Scale the upper/lower lips around the mouth center for articulation."""

        width_scale = 1.0 + (mouth.width - 0.5) * 0.08 - mouth.rounding * 0.02
        height_scale = 1.0 + mouth.aperture * 0.12
        if (
            abs(width_scale - 1.0) < SCALE_EPSILON
            and abs(height_scale - 1.0) < SCALE_EPSILON
        ):
            return
        for layer in ("lip_upper", "lip_lower"):
            path = pose.path(layer)
            dy = mouth.aperture * (-2.0 if layer == "lip_upper" else 8.0)
            self._paint_transformed(
                target,
                path,
                scale_x=width_scale,
                scale_y=height_scale,
                dy=dy,
            )

    def _paint_mouth_opening(
        self,
        target: QPixmap,
        pose: LayeredFacePose,
        mouth,
    ) -> None:
        """Open a visible cavity before placing the articulated lip layers."""
        aperture = max(0.0, min(1.0, float(mouth.aperture)))
        self._paint_transformed(
            target,
            pose.path("oral_cavity"),
            scale_x=1.0 + mouth.rounding * 0.08,
            scale_y=1.0 + aperture * 1.4,
            dy=aperture * 3.0,
        )
        self._paint_transformed(
            target,
            pose.path("teeth_tongue"),
            scale_y=1.0 + aperture * 0.45,
            dy=aperture * 2.0,
        )

    def _paint_transformed(
        self,
        target: QPixmap,
        path,
        *,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        dx: float = 0.0,
        dy: float = 0.0,
    ) -> None:
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        center_x, center_y = self._layer_center(path, source)
        transform = QTransform()
        transform.translate(center_x + dx, center_y + dy)
        transform.scale(scale_x, scale_y)
        transform.translate(-center_x, -center_y)
        # Paint the transformed layer directly into the destination. The old
        # path allocated a full-canvas temporary for every lip/cavity layer on
        # every viseme, then copied that canvas a second time. Direct painting
        # is pixel-equivalent and removes four large allocations per frame.
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _layer_center(self, path, source: QPixmap) -> tuple[float, float]:
        """Return one alpha-bounds pivot without rescanning it at 50 Hz."""
        key = str(path)
        cached = self._layer_center_cache.get(key)
        if cached is not None:
            return cached
        bounds = QRegion(source.mask()).boundingRect()
        center = (float(bounds.center().x()), float(bounds.center().y()))
        self._layer_center_cache[key] = center
        return center
