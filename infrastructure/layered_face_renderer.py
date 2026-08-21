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

lazy from dataclasses import replace
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QTransform

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
        # Cache decoded layer pixmaps so the 50 Hz render loop never re-reads
        # the 25 authored PNGs from disk on every frame.
        self._pixmap_cache: dict[str, QPixmap] = {}

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
            return cached
        pixmap = QPixmap(key)
        self._pixmap_cache[key] = pixmap
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
        if composed.size() == base.size():
            return composed
        return composed.scaled(
            base.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

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

        # Body + back hair sit below the face base layer.
        body = self._cached_pixmap(pose.path("body"))
        if body.isNull():
            return QPixmap()
        result = QPixmap(body)
        self._paint_opacity(result, pose.path("hair_back"), 1.0)

        base = self._cached_pixmap(pose.path("base"))
        if base.isNull():
            return QPixmap()
        self._paint_opacity(result, pose.path("base"), 1.0)
        expression = motion.expression_shape
        mouth = motion.mouth

        # Jaw: translate the jaw influence region downward with jaw opening.
        self._paint_translated(
            result,
            pose.path("jaw"),
            dy=mouth.jaw * 3.0,
        )

        # Oral cavity + teeth/tongue appear only while the mouth is open.
        if motion.viseme is not Viseme.CLOSED or mouth.aperture > MOUTH_APERTURE_THRESHOLD:
            aperture_opacity = max(0.0, min(1.0, mouth.aperture / 0.18))
            self._paint_opacity(result, pose.path("oral_cavity"), aperture_opacity)
            self._paint_opacity(result, pose.path("teeth_tongue"), aperture_opacity)

        # Lips: scale width/rounding around the mouth center for articulation.
        self._paint_mouth_lips(result, pose, mouth)

        # Mouth corners: smile pulls the corners outward/upward.
        corner = mouth.corner_smile
        if abs(corner) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, pose.path("corner_left"), dx=-corner * 2.0, dy=-corner * 1.0)
            self._paint_translated(result, pose.path("corner_right"), dx=corner * 2.0, dy=-corner * 1.0)

        # Blush: opacity follows the blush control.
        if expression.blush > 0.0:
            self._paint_opacity(result, pose.path("blush_left"), expression.blush)
            self._paint_opacity(result, pose.path("blush_right"), expression.blush)

        # Irises: gaze is applied by the caller via translation; here we only
        # ensure the iris layers are present (opacity 1.0 by default).
        self._paint_opacity(result, pose.path("iris_left"), 1.0)
        self._paint_opacity(result, pose.path("iris_right"), 1.0)

        # Eyelids + eyeliner: blink closes them with opacity.
        if expression.blink > 0.0:
            self._paint_opacity(result, pose.path("eyelid_left"), expression.blink)
            self._paint_opacity(result, pose.path("eyelid_right"), expression.blink)
            self._paint_opacity(result, pose.path("eyeliner_left"), expression.blink)
            self._paint_opacity(result, pose.path("eyeliner_right"), expression.blink)

        # Brows: lift/tension translate the brow layers.
        brow_dy = -expression.brow_lift * 3.0 + expression.brow_tension * 1.5
        if abs(brow_dy) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, pose.path("brow_left"), dy=brow_dy)
            self._paint_translated(result, pose.path("brow_right"), dy=brow_dy)

        # Front hair, sleeves and ornament sit above the face (topmost layers).
        self._paint_opacity(result, pose.path("hair_left"), 1.0)
        self._paint_opacity(result, pose.path("hair_right"), 1.0)
        self._paint_opacity(result, pose.path("sleeve_left"), 1.0)
        self._paint_opacity(result, pose.path("sleeve_right"), 1.0)
        self._paint_opacity(result, pose.path("ornament"), 1.0)

        return result

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

    @staticmethod
    def _paint_masked(
        target: QPixmap,
        source: QPixmap | None,
        mask: QPixmap | None,
        opacity: float,
    ) -> None:
        if source is None or mask is None or source.isNull() or mask.isNull():
            return
        layer = QPixmap(source.size())
        layer.fill(Qt.transparent)
        mask_painter = QPainter(layer)
        mask_painter.drawPixmap(0, 0, source)
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(0, 0, mask)
        mask_painter.end()
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(0, 0, layer)
        painter.end()

    def _paint_mouth_lips(self, target: QPixmap, pose: LayeredFacePose, mouth) -> None:
        """Scale the upper/lower lips around the mouth center for articulation."""

        width_scale = 1.0 + (mouth.width - 0.5) * 0.08 - mouth.rounding * 0.02
        height_scale = 1.0 + mouth.aperture * 0.04
        if abs(width_scale - 1.0) < SCALE_EPSILON and abs(height_scale - 1.0) < SCALE_EPSILON:
            self._paint_opacity(target, pose.path("lip_upper"), 1.0)
            self._paint_opacity(target, pose.path("lip_lower"), 1.0)
            return
        for layer in ("lip_upper", "lip_lower"):
            source = self._cached_pixmap(pose.path(layer))
            if source.isNull():
                continue
            center_x = source.width() / 2.0
            center_y = source.height() / 2.0
            transform = QTransform()
            transform.translate(center_x, center_y)
            transform.scale(width_scale, height_scale)
            transform.translate(-center_x, -center_y)
            transformed = QPixmap(source.size())
            transformed.fill(Qt.transparent)
            painter = QPainter(transformed)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setTransform(transform)
            painter.drawPixmap(0, 0, source)
            painter.end()
            painter = QPainter(target)
            painter.drawPixmap(0, 0, transformed)
            painter.end()
