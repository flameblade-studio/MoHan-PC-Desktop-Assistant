"""Parametric 24-view × 25-layer full-body renderer.

Composes the 600 authored transparent layers (24 yaw views × 25 layers) into a
continuously controlled full-body portrait. This replaces the legacy PoseAtlas
static photo + procedural mouth with independent, sub-frame deformation of the
mouth, eyelids, brows, irises, blush, lips, and jaw across every yaw view.

Adjacent views are blended with a clamped linear interpolation so the character
turns smoothly, and the view ring wraps around (yaw+165 → yaw-180).
"""

from __future__ import annotations

lazy from collections import OrderedDict
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QPainter, QPixmap, QRegion

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_rig import FaceMotionFrame, Viseme
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
    VIEW_IDS,
    load_layered_full_body_assets,
)

MOUTH_APERTURE_THRESHOLD = 0.01
# Iris translation scale: gaze_x/gaze_y are normalized to [-1, 1]; this maps
# them onto a small pixel offset so the eyes track the pointer without the iris
# leaving the sclera.  The full-body layers are authored at 1024x1536, so a few
# pixels of travel reads as a natural glance rather than an eye-roll.
IRIS_GAZE_SCALE_X = 6.0
IRIS_GAZE_SCALE_Y = 4.0
# Breath lift scale: breath is normalized to [0, 1]; this maps the midpoint
# (0.5) to zero lift and the extremes to a small vertical body rise/fall.
BREATH_LIFT_SCALE = 6.0
# The authored body layer already contains the arms and hands, while each
# sleeve is available as a separate transparent physical layer.  Keep sleeve
# motion deliberately small so behavior reads without disconnecting the cuff
# from the underlying hand.
MAX_SLEEVE_LIFT = 4.0
MAX_GESTURE_SWAY = 3.0

FULL_BODY_ASSET_DIR = Path("assets") / "pose-atlas" / "v4-layered"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CACHED_LAYER_PIXMAPS = 50


class LayeredFullBodyRenderer:
    """Compose the 25 authored layers across 24 yaw views."""

    def __init__(self, manifest: LayeredFullBodyManifest | None = None) -> None:
        self._manifest = manifest
        # Two adjacent 25-layer views are sufficient for one interpolated
        # frame. Keeping all 600 decoded 1024x1536 RGBA layers retained roughly
        # 3.5 GiB before Qt/GPU copies and triggered Windows RADAR pre-leak
        # detection in the packaged runtime.
        self._pixmap_cache: OrderedDict[str, QPixmap] = OrderedDict()

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
            self._pixmap_cache.move_to_end(key)
            return cached
        pixmap = QPixmap(key)
        self._pixmap_cache[key] = pixmap
        self._pixmap_cache.move_to_end(key)
        while len(self._pixmap_cache) > MAX_CACHED_LAYER_PIXMAPS:
            self._pixmap_cache.popitem(last=False)
        return pixmap

    def render_view(
        self,
        view_id: str,
        motion: FaceMotionFrame,
        *,
        pose_id: str = "front-crossed",
        left_hand: str = "relaxed",
        right_hand: str = "relaxed",
        body_energy: float = 0.0,
        gesture_beat: bool = False,
    ) -> QPixmap:
        """Render one complete full-body frame for the given view and motion."""
        view = self._manifest_or_load().view(view_id)
        body = self._cached_pixmap(view.path("body"))
        if body.isNull():
            return QPixmap()
        result = QPixmap(body)
        self._paint_opacity(result, view.path("hair_back"), 1.0)
        self._paint_opacity(result, view.path("base"), 1.0)
        self._paint_face_layers(result, view, motion)

        # Front hair, sleeves, ornament.
        self._paint_opacity(result, view.path("hair_left"), 1.0)
        self._paint_opacity(result, view.path("hair_right"), 1.0)
        bounded_energy = max(0.0, min(1.0, float(body_energy)))
        left_lift = self._sleeve_lift(left_hand, pose_id, bounded_energy)
        right_lift = self._sleeve_lift(right_hand, pose_id, bounded_energy)
        self._paint_translated(result, view.path("sleeve_left"), dy=left_lift)
        self._paint_translated(result, view.path("sleeve_right"), dy=right_lift)
        self._paint_opacity(result, view.path("ornament"), 1.0)

        # Breathing moves the atomically composed character. Moving only the
        # body below stationary hair and face layers creates visible seams.
        breath_dy = (motion.breath - 0.5) * BREATH_LIFT_SCALE
        gesture_dx = self._gesture_sway(
            pose_id,
            left_hand,
            right_hand,
            bounded_energy,
            gesture_beat,
        )
        return self._translated_frame(result, breath_dy, gesture_dx)

    @staticmethod
    def _sleeve_lift(
        hand: str,
        pose_id: str,
        body_energy: float,
    ) -> float:
        normalized_hand = str(hand).strip().lower()
        active_hand = bool(normalized_hand) and not normalized_hand.startswith(
            ("relaxed", "neutral")
        )
        active_pose = any(
            token in str(pose_id).lower()
            for token in ("wave", "greet", "present", "cheek", "touch")
        )
        if not active_hand and not active_pose:
            return 0.0
        return -MAX_SLEEVE_LIFT * max(0.35, body_energy)

    @staticmethod
    def _gesture_sway(
        pose_id: str,
        left_hand: str,
        right_hand: str,
        body_energy: float,
        gesture_beat: bool,
    ) -> float:
        if not gesture_beat and body_energy < 0.45:
            return 0.0
        seed = f"{pose_id}:{left_hand}:{right_hand}"
        direction = -1.0 if sum(map(ord, seed)) % 2 else 1.0
        return direction * MAX_GESTURE_SWAY * max(0.4, body_energy)

    def _paint_face_layers(
        self,
        result: QPixmap,
        view: LayeredFullBodyView,
        motion: FaceMotionFrame,
    ) -> None:
        """Paint registered neutral cutouts and their parameter motion."""

        expression = motion.expression_shape
        mouth = motion.mouth

        # The authored facial layers are neutral registered cutouts, not
        # effect-only overlays. Paint every cutout first so the transparent
        # holes in ``base`` are always filled, then add parameter motion.
        self._paint_opacity(result, view.path("jaw"), 1.0)
        # ``jaw`` is a registered replacement cutout. Translating and painting
        # a second copy produces the floating chin fragment seen at runtime.

        self._paint_opacity(result, view.path("oral_cavity"), 1.0)
        self._paint_opacity(result, view.path("teeth_tongue"), 1.0)
        self._paint_opacity(result, view.path("lip_lower"), 1.0)
        self._paint_opacity(result, view.path("lip_upper"), 1.0)
        if motion.viseme is not Viseme.CLOSED or mouth.aperture > MOUTH_APERTURE_THRESHOLD:
            self._paint_visible_cavity(result, view, mouth)

        self._paint_opacity(result, view.path("corner_left"), 1.0)
        self._paint_opacity(result, view.path("corner_right"), 1.0)
        corner = mouth.corner_smile
        if abs(corner) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, view.path("corner_left"), dx=-corner * 2.0, dy=-corner * 1.0)
            self._paint_translated(result, view.path("corner_right"), dx=corner * 2.0, dy=-corner * 1.0)

        self._paint_opacity(result, view.path("blush_left"), 1.0)
        self._paint_opacity(result, view.path("blush_right"), 1.0)
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

        self._paint_opacity(result, view.path("eyelid_left"), 1.0)
        self._paint_opacity(result, view.path("eyelid_right"), 1.0)
        self._paint_opacity(result, view.path("eyeliner_left"), 1.0)
        self._paint_opacity(result, view.path("eyeliner_right"), 1.0)
        if expression.blink > 0.0:
            self._paint_opacity(result, view.path("eyelid_left"), expression.blink)
            self._paint_opacity(result, view.path("eyelid_right"), expression.blink)
            self._paint_opacity(result, view.path("eyeliner_left"), expression.blink)
            self._paint_opacity(result, view.path("eyeliner_right"), expression.blink)

        self._paint_opacity(result, view.path("brow_left"), 1.0)
        self._paint_opacity(result, view.path("brow_right"), 1.0)
        brow_dy = -expression.brow_lift * 3.0 + expression.brow_tension * 1.5
        if abs(brow_dy) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, view.path("brow_left"), dy=brow_dy)
            self._paint_translated(result, view.path("brow_right"), dy=brow_dy)

    @staticmethod
    def _translated_frame(source: QPixmap, dy: float, dx: float = 0.0) -> QPixmap:
        if (
            abs(dy) < FLOAT_COMPARISON_EPSILON
            and abs(dx) < FLOAT_COMPARISON_EPSILON
        ):
            return source
        translated = QPixmap(source.size())
        translated.fill(Qt.transparent)
        painter = QPainter(translated)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(round(dx), round(dy), source)
        painter.end()
        return translated

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

    def _paint_visible_cavity(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
        mouth,
    ) -> None:
        """Reveal a compact natural cavity inside the registered lip texture.

        The authored full-body mouth cutouts contain neutral skin/lip colour
        and some are registered over the chin rather than the visible mouth.
        Use the per-view face-base bounds to locate the actual mouth and paint
        only its inner opening, preserving the surrounding layered portrait.
        """
        path = view.path("base")
        if path is None:
            return
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        bounds = QRegion(source.mask()).boundingRect()
        aperture = max(0.0, min(1.0, float(mouth.aperture)))
        width = max(2.0, bounds.width() * (0.16 + mouth.width * 0.08))
        height = max(1.5, bounds.height() * (0.003 + aperture * 0.024))
        center_x = bounds.center().x()
        center_y = bounds.y() + bounds.height() * 0.57
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(75, 26, 36, 220))
        painter.drawEllipse(
            round(center_x - width / 2.0),
            round(center_y - height / 2.0),
            max(1, round(width)),
            max(1, round(height)),
        )
        painter.end()
