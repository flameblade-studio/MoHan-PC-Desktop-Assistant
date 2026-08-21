"""Parametric 24-view × 25-layer full-body renderer.

Composes the 600 authored transparent layers (24 yaw views × 25 layers) into a
continuously controlled full-body portrait. This replaces the legacy PoseAtlas
static photo + procedural mouth with independent, sub-frame deformation of the
mouth, eyelids, brows, irises, blush, lips, and jaw across every yaw view.

Adjacent views are blended with a clamped linear interpolation so the character
turns smoothly, and the view ring wraps around (yaw+165 → yaw-180).
"""

from __future__ import annotations

lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QTransform

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_rig import FaceMotionFrame, Viseme
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
    VIEW_IDS,
    load_layered_full_body_assets,
)

MOUTH_APERTURE_THRESHOLD = 0.01
SCALE_EPSILON = 1e-4
# Iris translation scale: gaze_x/gaze_y are normalized to [-1, 1]; this maps
# them onto a small pixel offset so the eyes track the pointer without the iris
# leaving the sclera.  The full-body layers are authored at 1024x1536, so a few
# pixels of travel reads as a natural glance rather than an eye-roll.
IRIS_GAZE_SCALE_X = 6.0
IRIS_GAZE_SCALE_Y = 4.0
# Breath lift scale: breath is normalized to [0, 1]; this maps the midpoint
# (0.5) to zero lift and the extremes to a small vertical body rise/fall.
BREATH_LIFT_SCALE = 6.0

FULL_BODY_ASSET_DIR = Path("assets") / "pose-atlas" / "v4-layered"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LayeredFullBodyRenderer:
    """Compose the 25 authored layers across 24 yaw views."""

    def __init__(self, manifest: LayeredFullBodyManifest | None = None) -> None:
        self._manifest = manifest
        # Cache decoded layer pixmaps so the 50 Hz render loop never re-reads
        # the 600 authored PNGs from disk on every frame.
        self._pixmap_cache: dict[str, QPixmap] = {}

    def _manifest_or_load(self) -> LayeredFullBodyManifest:
        if self._manifest is None:
            self._manifest = load_layered_full_body_assets(
                PROJECT_ROOT / FULL_BODY_ASSET_DIR
            )
        return self._manifest

    def _cached_pixmap(self, path) -> QPixmap:
        """Return a decoded layer pixmap, caching it across frames."""
        if path is None:
            return QPixmap()
        key = str(path)
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            return cached
        pixmap = QPixmap(key)
        self._pixmap_cache[key] = pixmap
        return pixmap

    def render_view(
        self,
        view_id: str,
        motion: FaceMotionFrame,
    ) -> QPixmap:
        """Render one complete full-body frame for the given view and motion."""
        view = self._manifest_or_load().view(view_id)
        body = self._cached_pixmap(view.path("body"))
        if body.isNull():
            return QPixmap()
        result = QPixmap(body)
        # Breathing: a gentle vertical lift of the whole body so the chest and
        # shoulders rise and fall with the idle breath.  The offset is small and
        # bounded so it reads as a natural breath, never a bounce.
        breath_dy = (motion.breath - 0.5) * BREATH_LIFT_SCALE
        if abs(breath_dy) >= FLOAT_COMPARISON_EPSILON:
            lifted = QPixmap(body.size())
            lifted.fill(Qt.transparent)
            painter = QPainter(lifted)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(0, round(breath_dy), body)
            painter.end()
            result = lifted
        self._paint_opacity(result, view.path("hair_back"), 1.0)
        self._paint_opacity(result, view.path("base"), 1.0)

        expression = motion.expression_shape
        mouth = motion.mouth

        # Jaw translation.
        self._paint_translated(result, view.path("jaw"), dy=mouth.jaw * 3.0)

        # Oral cavity + teeth/tongue appear only while the mouth is open.
        if motion.viseme is not Viseme.CLOSED or mouth.aperture > MOUTH_APERTURE_THRESHOLD:
            aperture_opacity = max(0.0, min(1.0, mouth.aperture / 0.18))
            self._paint_opacity(result, view.path("oral_cavity"), aperture_opacity)
            self._paint_opacity(result, view.path("teeth_tongue"), aperture_opacity)

        # Lips.
        self._paint_mouth_lips(result, view, mouth)

        # Mouth corners.
        corner = mouth.corner_smile
        if abs(corner) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, view.path("corner_left"), dx=-corner * 2.0, dy=-corner * 1.0)
            self._paint_translated(result, view.path("corner_right"), dx=corner * 2.0, dy=-corner * 1.0)

        # Blush.
        if expression.blush > 0.0:
            self._paint_opacity(result, view.path("blush_left"), expression.blush)
            self._paint_opacity(result, view.path("blush_right"), expression.blush)

        # Irises: translate by the gaze vector so the eyes track the pointer,
        # the shy look-away, and the natural saccade.  The offset is small and
        # bounded so the iris never leaves the sclera.
        gaze_dx = motion.gaze_x * IRIS_GAZE_SCALE_X
        gaze_dy = motion.gaze_y * IRIS_GAZE_SCALE_Y
        if abs(gaze_dx) >= FLOAT_COMPARISON_EPSILON or abs(gaze_dy) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(
                result, view.path("iris_left"), dx=gaze_dx, dy=gaze_dy
            )
            self._paint_translated(
                result, view.path("iris_right"), dx=gaze_dx, dy=gaze_dy
            )
        else:
            self._paint_opacity(result, view.path("iris_left"), 1.0)
            self._paint_opacity(result, view.path("iris_right"), 1.0)

        # Eyelids + eyeliner.
        if expression.blink > 0.0:
            self._paint_opacity(result, view.path("eyelid_left"), expression.blink)
            self._paint_opacity(result, view.path("eyelid_right"), expression.blink)
            self._paint_opacity(result, view.path("eyeliner_left"), expression.blink)
            self._paint_opacity(result, view.path("eyeliner_right"), expression.blink)

        # Brows.
        brow_dy = -expression.brow_lift * 3.0 + expression.brow_tension * 1.5
        if abs(brow_dy) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, view.path("brow_left"), dy=brow_dy)
            self._paint_translated(result, view.path("brow_right"), dy=brow_dy)

        # Front hair, sleeves, ornament.
        self._paint_opacity(result, view.path("hair_left"), 1.0)
        self._paint_opacity(result, view.path("hair_right"), 1.0)
        self._paint_opacity(result, view.path("sleeve_left"), 1.0)
        self._paint_opacity(result, view.path("sleeve_right"), 1.0)
        self._paint_opacity(result, view.path("ornament"), 1.0)

        return result

    def render_blended(
        self,
        view_id: str,
        motion: FaceMotionFrame,
        *,
        blend: float = 0.0,
    ) -> QPixmap:
        """Render a view blended toward its next neighbour by ``blend`` in [0, 1).

        ``blend == 0`` returns the exact view; ``blend`` approaching 1 blends
        toward the next view in the ring (wrapping from yaw+165 to yaw-180).
        """
        bounded = max(0.0, min(1.0, float(blend)))
        if bounded < FLOAT_COMPARISON_EPSILON:
            return self.render_view(view_id, motion)
        current = self.render_view(view_id, motion)
        next_view = self._next_view(view_id)
        following = self.render_view(next_view, motion)
        if current.isNull() or following.isNull():
            return current
        result = QPixmap(current.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setOpacity(1.0 - bounded)
        painter.drawPixmap(0, 0, current)
        painter.setOpacity(bounded)
        painter.drawPixmap(0, 0, following)
        painter.end()
        return result

    @staticmethod
    def _next_view(view_id: str) -> str:
        index = VIEW_IDS.index(view_id)
        return VIEW_IDS[(index + 1) % len(VIEW_IDS)]

    # -- painting helpers ---------------------------------------------------

    def _paint_opacity(self, target: QPixmap, path, opacity: float) -> None:
        if path is None:
            return
        source = self._cached_pixmap(path)
        if source.isNull() or opacity <= 0.0:
            return
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _paint_translated(self, target: QPixmap, path, *, dx: float = 0.0, dy: float = 0.0) -> None:
        if path is None:
            return
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(round(dx), round(dy), source)
        painter.end()

    def _paint_mouth_lips(self, target: QPixmap, view: LayeredFullBodyView, mouth) -> None:
        width_scale = 1.0 + (mouth.width - 0.5) * 0.08 - mouth.rounding * 0.02
        height_scale = 1.0 + mouth.aperture * 0.04
        if abs(width_scale - 1.0) < SCALE_EPSILON and abs(height_scale - 1.0) < SCALE_EPSILON:
            self._paint_opacity(target, view.path("lip_upper"), 1.0)
            self._paint_opacity(target, view.path("lip_lower"), 1.0)
            return
        for layer in ("lip_upper", "lip_lower"):
            path = view.path(layer)
            if path is None:
                continue
            source = self._cached_pixmap(path)
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
