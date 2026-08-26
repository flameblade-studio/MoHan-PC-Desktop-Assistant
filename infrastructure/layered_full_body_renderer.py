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

lazy from PySide6.QtCore import QRectF, Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_rig import FaceMotionFrame, Viseme
lazy from infrastructure.layered_full_body_assets import (
    LayeredFullBodyManifest,
    LayeredFullBodyView,
    VIEW_IDS,
    load_layered_full_body_assets,
)
lazy from infrastructure.mouth_geometry import inward_lerped_u_layer

MOUTH_APERTURE_THRESHOLD = 0.01
BLINK_VISIBLE_EPSILON = 1e-6
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
GESTURE_ENERGY_THRESHOLD = 0.45

FULL_BODY_ASSET_DIR = Path("assets") / "pose-atlas" / "v4-layered"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CACHED_LAYER_PIXMAPS = 50
SEAM_HEAL_RADIUS = 7
REGISTERED_COMPOSITE_LAYERS = (
    # oral_cavity / teeth_tongue are clean speech overlays rebuilt by
    # tools/rebuild_pose_atlas_mouth_layers.py; unlike the legacy skin
    # replacement cut-outs, their edges must not be healed back to neutral.
    "body", "hair_back", "base", "jaw", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right", "hair_left", "hair_right",
    "sleeve_left", "sleeve_right", "ornament",
)
FACE_AUTHORITY_REGION_LAYERS = (
    "base", "jaw", "lip_lower", "lip_upper", "corner_left", "corner_right",
    "blush_left", "blush_right", "iris_left", "iris_right", "eyelid_left",
    "eyelid_right", "eyeliner_left", "eyeliner_right", "brow_left",
    "brow_right",
)


class LayeredFullBodyRenderer:
    """Compose the 25 authored layers across 24 yaw views."""

    def __init__(
        self,
        manifest: LayeredFullBodyManifest | None = None,
        outfit_overlay=None,
    ) -> None:
        self._manifest = manifest
        self._outfit_overlay = outfit_overlay
        # Two adjacent 25-layer views are sufficient for one interpolated
        # frame. Keeping all 600 decoded 1024x1536 RGBA layers retained roughly
        # 3.5 GiB before Qt/GPU copies and triggered Windows RADAR pre-leak
        # detection in the packaged runtime.
        self._pixmap_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._seam_region_cache: dict[str, QRegion] = {}
        self._face_region_cache: dict[str, QRegion] = {}

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
        self._heal_registered_seams(result, view)
        self._restore_authority_face(result, view)
        # Authority restoration removes seam-healing artefacts, but also
        # restores the neutral eye pixels. Re-apply only bounded eye motion
        # afterwards so dynamic pixels cannot escape their authored masks.
        self._paint_dynamic_eye_layers(result, view, motion)
        self._paint_u_lip_layers(result, view, motion.mouth.u_inward)
        if (
            motion.viseme is not Viseme.CLOSED
            or motion.mouth.aperture > MOUTH_APERTURE_THRESHOLD
        ):
            self._paint_visible_cavity(result, view, motion.mouth)
        if self._outfit_overlay is not None:
            result = self._outfit_overlay.apply(result, view_id)

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
        if not gesture_beat and body_energy < GESTURE_ENERGY_THRESHOLD:
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

        # The rebuilt oral-cavity layer is an accepted authority speech mouth,
        # not a neutral skin replacement. Keep it absent while closed;
        # registered lip/corner cut-outs below reconstruct the authority mouth.
        self._paint_opacity(result, view.path("lip_lower"), 1.0)
        self._paint_opacity(result, view.path("lip_upper"), 1.0)
        self._paint_opacity(result, view.path("corner_left"), 1.0)
        self._paint_opacity(result, view.path("corner_right"), 1.0)
        corner = mouth.corner_smile
        if abs(corner) >= FLOAT_COMPARISON_EPSILON:
            self._paint_translated(result, view.path("corner_left"), dx=-corner * 2.0, dy=-corner * 1.0)
            self._paint_translated(result, view.path("corner_right"), dx=corner * 2.0, dy=-corner * 1.0)

        self._paint_opacity(result, view.path("blush_left"), 1.0)
        self._paint_opacity(result, view.path("blush_right"), 1.0)

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

        self._paint_opacity(result, view.path("brow_left"), 1.0)
        self._paint_opacity(result, view.path("brow_right"), 1.0)

        # Eyelid, brow and blush assets are neutral registered replacements.
        # Repainting them for a control value alpha-composites the same skin
        # cut-out twice and reveals its circular/oval calibration boundary at
        # runtime.  Keep each replacement atomic; only the mouth cavity is a
        # safe deformable full-body feature in the current authored set.
        _ = expression

    def _heal_registered_seams(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Colour-register only authored cut-out boundaries to the view authority."""

        region = self._seam_region_cache.get(view.view_id)
        if region is None:
            region = QRegion()
            offsets = tuple(
                (dx, dy)
                for dx in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                for dy in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                if abs(dx) + abs(dy) <= SEAM_HEAL_RADIUS
            )
            for layer_name in REGISTERED_COMPOSITE_LAYERS:
                path = view.path(layer_name)
                if path is None:
                    continue
                source = self._cached_pixmap(path)
                if source.isNull():
                    continue
                source_region = QRegion(source.mask())
                if source_region.isEmpty():
                    continue
                outer = QRegion(source_region)
                inner = QRegion(source_region)
                for dx, dy in offsets:
                    outer = outer.united(source_region.translated(dx, dy))
                    inner = inner.intersected(source_region.translated(dx, dy))
                region = region.united(outer.subtracted(inner))
            self._seam_region_cache[view.view_id] = region
        if region.isEmpty():
            return
        authority = self._cached_pixmap(
            PROJECT_ROOT / "assets" / "pose-atlas" / "v4" / f"{view.view_id}.png"
        )
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _restore_authority_face(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Remove broad skin-cutout artefacts without replacing body layers."""

        region = self._face_region_cache.get(view.view_id)
        if region is None:
            region = QRegion()
            for layer_name in FACE_AUTHORITY_REGION_LAYERS:
                path = view.path(layer_name)
                if path is None:
                    continue
                source = self._cached_pixmap(path)
                if not source.isNull():
                    region = region.united(QRegion(source.mask()))
            self._face_region_cache[view.view_id] = region
        if region.isEmpty():
            return
        authority = self._cached_pixmap(
            PROJECT_ROOT / "assets" / "pose-atlas" / "v4" / f"{view.view_id}.png"
        )
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.drawPixmap(0, 0, authority)
        painter.end()

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

    def _paint_dynamic_eye_layers(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
        motion: FaceMotionFrame,
    ) -> None:
        """Re-apply blink and gaze after authority restoration, mask-confined."""

        expression = motion.expression_shape
        gaze_dx = round(float(motion.gaze_x) * IRIS_GAZE_SCALE_X)
        gaze_dy = round(float(motion.gaze_y) * IRIS_GAZE_SCALE_Y)
        if gaze_dx or gaze_dy:
            gaze_layers = ("iris_left", "iris_right")
            gaze_region = QRegion()
            for layer_name in gaze_layers:
                source = self._cached_pixmap(view.path(layer_name))
                if not source.isNull():
                    gaze_region = gaze_region.united(QRegion(source.mask()))
            if not gaze_region.isEmpty():
                painter = QPainter(target)
                painter.setClipRegion(gaze_region)
                for layer_name in gaze_layers:
                    source = self._cached_pixmap(view.path(layer_name))
                    if not source.isNull():
                        painter.drawPixmap(gaze_dx, gaze_dy, source)
                painter.end()

        blink = min(1.0, max(0.0, float(expression.blink)))
        if blink > BLINK_VISIBLE_EPSILON:
            blink_layers = (
                "eyelid_left",
                "eyelid_right",
                "eyeliner_left",
                "eyeliner_right",
            )
            blink_region = QRegion()
            for layer_name in blink_layers:
                source = self._cached_pixmap(view.path(layer_name))
                if not source.isNull():
                    blink_region = blink_region.united(QRegion(source.mask()))
            if not blink_region.isEmpty():
                blink_dy = max(1, round(blink * 4.0))
                painter = QPainter(target)
                painter.setClipRegion(blink_region)
                for layer_name in blink_layers:
                    source = self._cached_pixmap(view.path(layer_name))
                    if not source.isNull():
                        painter.drawPixmap(0, blink_dy, source)
                painter.end()

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
        """Fade in the accepted registered speech mouth without skin motion."""
        cavity_path = view.path("oral_cavity")
        if cavity_path is None:
            return
        cavity_source = self._cached_pixmap(cavity_path)
        if cavity_source.isNull():
            return
        bounds = QRegion(cavity_source.mask()).boundingRect()
        if bounds.isEmpty():
            # Back-side views intentionally contain no visible mouth.
            return
        aperture = max(0.0, min(1.0, float(mouth.aperture)))
        # This layer is a tightly cropped, softly feathered copy of the
        # matching yaw view's own authority mouth.  Some accepted packs keep
        # identical RGB at rest, so opacity alone cannot create speech. Apply
        # a small, mouth-centred vertical aperture to this semantic cut-out;
        # the transparent full-canvas registration keeps the deformation away
        # from the chin and surrounding skin.
        aperture_scale = 1.0 + aperture * 0.22
        target_height = float(bounds.height()) * aperture_scale
        target_rect = QRectF(
            float(bounds.x()),
            float(bounds.center().y()) - target_height / 2.0,
            float(bounds.width()),
            target_height,
        )
        source_rect = QRectF(bounds)
        base_source = self._cached_pixmap(view.path("base"))
        face_bounds = QRegion(base_source.mask()).boundingRect()
        protected_chin_y = round(
            face_bounds.y() + face_bounds.height() * 0.76
        )
        mouth_clip = QRectF(
            float(bounds.x()),
            target_rect.y(),
            float(bounds.width()),
            max(0.0, float(protected_chin_y) - target_rect.y()),
        )
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setClipRect(mouth_clip)
        painter.setOpacity(min(1.0, aperture / 0.24))
        painter.drawPixmap(target_rect, cavity_source, source_rect)
        painter.end()

    def _paint_u_lip_layers(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
        u_inward: float,
    ) -> None:
        """Apply U inward motion only to canonical semantic lip pixels."""

        if view.mouth_center_x is None or u_inward <= 0.0:
            return
        for layer_name in (
            "lip_upper",
            "lip_lower",
            "corner_left",
            "corner_right",
        ):
            path = view.path(layer_name)
            if path is None:
                continue
            source = self._cached_pixmap(path)
            if source.isNull():
                continue
            transformed = inward_lerped_u_layer(
                source,
                view.mouth_center_x,
                u_inward,
            )
            painter = QPainter(target)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(0, 0, transformed)
            painter.end()
