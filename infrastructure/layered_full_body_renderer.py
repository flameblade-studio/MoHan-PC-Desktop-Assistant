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

lazy from PySide6.QtCore import QRect, QRectF, Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion

lazy from domain.constants import (
    FLOAT_COMPARISON_EPSILON,
    POSE_ATLAS_LAYERED_ROOT_NAME,
    POSE_ATLAS_ROOT_NAME,
)
lazy from domain.face_rig import EyeState, FaceMotionFrame, Viseme, eye_state_for_blink
lazy from infrastructure.layered_full_body_assets import (
    CompleteExpressionFrameSet,
    COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
    LayeredFullBodyManifest,
    LayeredFullBodyView,
    VIEW_IDS,
    load_layered_full_body_assets,
    snapshot_complete_expression_frames,
    snapshot_speech_frames,
)
lazy from infrastructure.mouth_geometry import paint_inward_lerped_u_layer
lazy from infrastructure.animated_appearance import AnimatedAppearance
lazy from infrastructure.full_body_blink_binding import bind_blink_source, snapshot_view_authority

MOUTH_APERTURE_THRESHOLD = 0.01
BLINK_VISIBLE_EPSILON = 1e-6
AUTHORED_SPEECH_VISIBLE_APERTURE = 0.16
# Iris translation scale: gaze_x/gaze_y are normalized to [-1, 1]; this maps
# them onto a small pixel offset so the eyes track the pointer while preserving the iris
# leaving the sclera.  The full-body layers are authored at 1024x1536, so a few
# pixels of travel reads as a natural glance rather than an eye-roll.
IRIS_GAZE_SCALE_X = 6.0
IRIS_GAZE_SCALE_Y = 4.0
# Breath lift scale: breath is normalized to [0, 1]; this maps the midpoint
# (0.5) to zero lift and the extremes to a small vertical body rise/fall.
BREATH_LIFT_SCALE = 6.0
# The authored body layer already contains the arms and hands, while each
# sleeve is available as a separate transparent physical layer.  Keep sleeve
# motion deliberately small so behavior reads while preserving the cuff connection
# from the underlying hand.
MAX_SLEEVE_LIFT = 4.0
MAX_GESTURE_SWAY = 3.0
GESTURE_ENERGY_THRESHOLD = 0.45
COMPLETE_EXPRESSION_NEUTRAL_POSE_ID = "front-crossed"

# The layered pack and the static authority it was cut from MUST move
# together: the seam-heal and face-restore passes below repaint authority
# pixels over the composed layers, so a mismatched pair paints one
# generation's face over the other's body.
FULL_BODY_ASSET_DIR = Path("assets") / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
FULL_BODY_AUTHORITY_DIR = Path("assets") / "pose-atlas" / POSE_ATLAS_ROOT_NAME
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CACHED_LAYER_PIXMAPS = 50
# One static base composite (body..authority face) per recently used view;
# four covers the two adjacent views of a turn plus hysteresis.
MAX_CACHED_STATIC_COMPOSITES = 4
MAX_CACHED_MASK_REGIONS = 256
SEAM_HEAL_RADIUS = 7
REGISTERED_COMPOSITE_LAYERS = (
    # oral_cavity / teeth_tongue are clean speech overlays rebuilt by
    # tools/rebuild_pose_atlas_mouth_layers.py; unlike the legacy skin
    # replacement cut-outs, their authored edges remain visible.
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
        *,
        authority_root: Path | None = None,
    ) -> None:
        self._manifest = manifest
        self._outfit_overlay = outfit_overlay
        self._animated_appearance = AnimatedAppearance(outfit_overlay)
        self._authority_root = (
            Path(authority_root).resolve() if authority_root is not None
            else PROJECT_ROOT / FULL_BODY_AUTHORITY_DIR
        )
        self._strict_authority = authority_root is not None
        self._bound_png_bytes: dict[str, bytes] = {}
        if manifest is not None:
            self._bind_manifest_blinks(manifest)
        # Two adjacent 25-layer views are sufficient for one interpolated
        # frame. Keeping all 600 decoded 1024x1536 RGBA layers retained roughly
        # 3.5 GiB before Qt/GPU copies and triggered Windows RADAR pre-leak
        # detection in the packaged runtime.
        self._pixmap_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._seam_region_cache: dict[str, QRegion] = {}
        self._static_composite_cache: OrderedDict[tuple, QPixmap] = OrderedDict()
        self._mask_region_cache: dict[int, QRegion] = {}
        self._face_region_cache: dict[str, QRegion] = {}

    def _mask_region(self, source: QPixmap) -> QRegion:
        """Return the opaque region of a decoded layer, cached per pixmap.

        ``QPixmap.mask()`` scans the full canvas on every call; the layer
        pixmaps are immutable once decoded, so the region is derived once per
        ``cacheKey`` and reused on the 50 Hz path.
        """
        key = source.cacheKey()
        region = self._mask_region_cache.get(key)
        if region is None:
            region = QRegion(source.mask())
            if len(self._mask_region_cache) > MAX_CACHED_MASK_REGIONS:
                self._mask_region_cache.clear()
            self._mask_region_cache[key] = region
        return region

    def _bind_manifest_blinks(self, manifest: LayeredFullBodyManifest) -> None:
        """Freeze candidate authority and authored motion before rendering."""
        snapshots: dict[str, bytes] = {}
        # Legacy view providers need only expose view(); explicit candidate
        # manifests expose all views so their source bytes can be frozen eagerly.
        views = manifest.views if self._strict_authority else getattr(manifest, "views", {})
        for view in views.values():
            if self._strict_authority:
                if view.blink_frames:
                    bound = bind_blink_source(self._authority_root, view.view_id, view.blink_frames)
                else:
                    bound = snapshot_view_authority(self._authority_root, view.view_id)
                snapshots.update(bound)
            snapshots.update(snapshot_speech_frames(view))
            snapshots.update(snapshot_complete_expression_frames(view))
        self._bound_png_bytes = snapshots

    def _manifest_or_load(self) -> LayeredFullBodyManifest:
        if self._manifest is None:
            manifest = load_layered_full_body_assets(
                PROJECT_ROOT / FULL_BODY_ASSET_DIR
            )
            self._bind_manifest_blinks(manifest)
            self._manifest = manifest
        return self._manifest

    def _cached_pixmap(self, path, *, required: bool = True) -> QPixmap:
        """Return a decoded layer pixmap, caching it across frames."""
        if path is None:
            return QPixmap()
        key = str(path)
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            if cached.isNull() and (required or Path(key).exists()):
                raise ValueError(f"Cannot decode full-body layer PNG: {key}")
            self._pixmap_cache.move_to_end(key)
            return cached
        snapshot = self._bound_png_bytes.get(key)
        if snapshot is None:
            pixmap = QPixmap(key)
        else:
            pixmap = QPixmap()
            if not pixmap.loadFromData(snapshot, "PNG"):
                raise ValueError(f"Cannot decode bound blink PNG: {key}")
        if pixmap.isNull() and (required or Path(key).exists()):
            raise ValueError(f"Cannot decode full-body layer PNG: {key}")
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
        bounded_energy = max(0.0, min(1.0, float(body_energy)))
        complete_paths = self._complete_expression_paths(
            view,
            motion,
            pose_id=pose_id,
            left_hand=left_hand,
            right_hand=right_hand,
            body_energy=bounded_energy,
            gesture_beat=gesture_beat,
        )
        deferred_body = (
            complete_paths is not None
            and self._animated_appearance.supports_body_replacement
        )
        if complete_paths is None or deferred_body:
            static = self._static_base_composite(
                view, pose_id, left_hand, right_hand, bounded_energy
            )
        else:
            static = self._complete_expression_base(
                view,
                complete_paths,
                pose_id=pose_id,
                left_hand=left_hand,
                right_hand=right_hand,
                body_energy=bounded_energy,
            )
        if static.isNull():
            return QPixmap()
        oral_mask = self._authored_oral_mask(view, motion, complete_paths)
        oral_bounds = (
            self._mask_region(oral_mask).boundingRect().adjusted(-1, -1, 1, 1)
            if oral_mask is not None else QRect()
        )
        protected_skin = (
            static.copy(oral_bounds)
            if complete_paths is not None and oral_mask is not None
            else QPixmap()
        )

        def paint_motion(frame: QPixmap) -> None:
            nonlocal protected_skin
            if complete_paths is not None:
                if oral_mask is not None:
                    protected_skin = frame.copy(oral_bounds)
                return
            # Motion is replayable on the bare frame if either outfit phase fails.
            self._paint_dynamic_eye_layers(frame, view, motion)
            if getattr(view, "speech_frames", None):
                self._paint_authored_speech(frame, view, motion)
                if oral_mask is not None:
                    protected_skin = frame.copy(oral_bounds)
                return
            self._paint_u_lip_layers(frame, view, motion.mouth.u_inward)
            if (
                motion.viseme is not Viseme.CLOSED
                or motion.mouth.aperture > MOUTH_APERTURE_THRESHOLD
            ):
                self._paint_visible_cavity(frame, view, motion.mouth)

        def restore_oral_skin(frame: QPixmap) -> None:
            # Preserve the already blended skin-motion pixels, including partial
            # apertures, while allowing lipstick outside the oral opening.
            if oral_mask is None or protected_skin.isNull():
                return
            protected = QPixmap(protected_skin)
            painter = QPainter(protected)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, oral_mask.copy(oral_bounds))
            painter.end()
            painter = QPainter(frame)
            painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            painter.drawPixmap(oral_bounds.topLeft(), protected)
            painter.end()

        eye_state = eye_state_for_blink(motion.expression_shape.blink)
        def replace_body(frame: QPixmap) -> QPixmap:
            if complete_paths is None:
                return frame
            path, _oral, mask = complete_paths
            if mask is None:
                return QPixmap(self._cached_pixmap(path))
            return self._replace_complete_expression_region(frame, path, mask)

        # Preserve legacy half-blink makeup for a base-only authored contract.
        suppressed = (
            frozenset({"eyes"})
            if (
                eye_state is EyeState.CLOSED
                or eye_state in view.blink_frames
                or (complete_paths is not None and eye_state is EyeState.HALF)
            )
            else frozenset()
        )
        result = self._animated_appearance.compose(
            static, view_id, paint_motion,
            suppress_makeup_slots=suppressed, eye_state=eye_state.value,
            paint_after_makeup=restore_oral_skin if oral_mask is not None else None,
            replace_body=replace_body if deferred_body else None,
        )

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

    def _authored_oral_mask(
        self,
        view: LayeredFullBodyView,
        motion: FaceMotionFrame,
        complete_paths: tuple[Path, Path | None, Path | None] | None = None,
    ) -> QPixmap | None:
        if complete_paths is not None:
            path = complete_paths[1]
            return self._cached_pixmap(path) if path is not None else None
        masks = getattr(view, "speech_oral_masks", {})
        if not masks or motion.mouth.aperture <= MOUTH_APERTURE_THRESHOLD:
            return None
        viseme = Viseme.CONSONANT if motion.viseme is Viseme.CLOSED else motion.viseme
        path = masks.get(viseme)
        if path is None:
            raise ValueError(f"Missing native speech oral mask: {view.view_id}/{viseme.value}")
        return self._cached_pixmap(path)

    def _complete_expression_paths(
        self,
        view: LayeredFullBodyView,
        motion: FaceMotionFrame,
        *,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        body_energy: float,
        gesture_beat: bool,
    ) -> tuple[Path, Path | None, Path | None] | None:
        """Resolve one complete face/body frame before detachable appearance."""

        group = getattr(view, "complete_expression_frames", None)
        if group is None:
            return None
        if not isinstance(group, CompleteExpressionFrameSet):
            raise ValueError("Complete expression frame group has an invalid type")
        eye_state = eye_state_for_blink(motion.expression_shape.blink)
        aperture = max(0.0, min(1.0, float(motion.mouth.aperture)))
        selected: tuple[Path, Path | None] | None = None
        if group.neutral_frames and aperture <= MOUTH_APERTURE_THRESHOLD:
            try:
                selected = group.neutral_frames[eye_state], None
            except KeyError as error:
                raise ValueError(
                    "Missing complete expression neutral state: "
                    f"{view.view_id}/{eye_state.value}"
                ) from error
        elif aperture <= MOUTH_APERTURE_THRESHOLD:
            return None
        else:
            viseme = Viseme.CONSONANT if motion.viseme is Viseme.CLOSED else motion.viseme
            try:
                frame = group.frame(viseme, eye_state)
                oral_mask = group.oral_mask(viseme, eye_state)
            except KeyError as error:
                raise ValueError(
                    "Missing complete expression state: "
                    f"{view.view_id}/{viseme.value}/{eye_state.value}"
                ) from error
            selected = frame, oral_mask
        self._ensure_complete_expression_body_motion(
            view,
            motion_policy=group.motion_policy,
            pose_id=pose_id,
            left_hand=left_hand,
            right_hand=right_hand,
            body_energy=body_energy,
            gesture_beat=gesture_beat,
        )
        frame, oral_mask = selected
        replacement_mask = (
            group.replacement_mask
            if group.motion_policy == COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY
            else None
        )
        return frame, oral_mask, replacement_mask

    def _complete_expression_base(
        self,
        view: LayeredFullBodyView,
        selection: tuple[Path, Path | None, Path | None],
        *,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        body_energy: float,
    ) -> QPixmap:
        """Compose body motion, then replace only a source-bound head region."""

        frame_path, _oral_mask, replacement_mask = selection
        if replacement_mask is None:
            return self._cached_pixmap(frame_path)
        base = self._static_base_composite(
            view, pose_id, left_hand, right_hand, body_energy
        )
        if base.isNull():
            return QPixmap()
        return self._replace_complete_expression_region(
            base, frame_path, replacement_mask,
        )

    def _replace_complete_expression_region(
        self,
        base: QPixmap,
        frame_path: Path,
        mask_path: Path,
    ) -> QPixmap:
        """Replace a hashed head region while clearing its old silhouette first."""

        source = self._cached_pixmap(frame_path)
        mask = self._cached_pixmap(mask_path)
        if source.isNull() or mask.isNull():
            return QPixmap()
        if source.size() != base.size() or mask.size() != base.size():
            raise ValueError(
                "Complete expression replacement requires same-canvas frame and mask"
            )

        masked_source = QPixmap(source.size())
        masked_source.fill(Qt.transparent)
        painter = QPainter(masked_source)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()

        # A fully opaque RGB body can decode as RGB32.  Copy it onto an alpha
        # capable canvas before clearing the declared region; otherwise Qt
        # cannot remove old hair pixels at the replacement boundary.
        result = QPixmap(base.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, base)
        painter.end()
        painter = QPainter(result)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        painter.drawPixmap(0, 0, mask)
        # The cleared destination and the masked source are both premultiplied.
        # Adding them implements base * (1 - mask) + source * mask while
        # keeping alpha opaque when both inputs are opaque.  SourceOver here
        # would multiply the destination alpha a second time at soft edges.
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.drawPixmap(0, 0, masked_source)
        painter.end()
        return result

    @staticmethod
    def _ensure_complete_expression_body_motion(
        view: LayeredFullBodyView,
        *,
        motion_policy: str,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        body_energy: float,
        gesture_beat: bool,
    ) -> None:
        """Reject motion only for the atomic neutral-body expression policy."""

        if motion_policy == COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY:
            return

        normalized_pose = str(pose_id).strip().lower()
        neutral_hands = all(
            LayeredFullBodyRenderer._is_neutral_hand(hand)
            for hand in (left_hand, right_hand)
        )
        if (
            normalized_pose == COMPLETE_EXPRESSION_NEUTRAL_POSE_ID
            and neutral_hands
            and body_energy <= FLOAT_COMPARISON_EPSILON
            and not gesture_beat
        ):
            return
        raise ValueError(
            "Complete expression frames support only neutral_body_only motion; "
            f"{view.view_id} requires pose/hand/energy-compatible frames for "
            f"pose_id={pose_id!r}, left_hand={left_hand!r}, "
            f"right_hand={right_hand!r}, body_energy={body_energy!r}, "
            f"gesture_beat={gesture_beat!r}"
        )

    @staticmethod
    def _is_neutral_hand(hand: str) -> bool:
        normalized = str(hand).strip().lower()
        return not normalized or normalized.startswith(("relaxed", "neutral"))

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

    def _static_base_composite(
        self,
        view: LayeredFullBodyView,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        bounded_energy: float,
    ) -> QPixmap:
        """Compose and cache every motion-independent layer of one view.

        Everything from the body up to and including the authority-face
        restoration is identical for every animation frame of a given view,
        pose and hand state: the neutral face cutouts painted here are fully
        covered again by ``_restore_authority_face``.  Rebuilding this stack
        on the 50 Hz viseme path dominated the frame budget, so it is cached
        and only the dynamic eye/mouth layers are painted per frame.
        """

        key = (
            view.view_id,
            pose_id,
            left_hand,
            right_hand,
            round(bounded_energy, 3),
        )
        cached = self._static_composite_cache.get(key)
        if cached is not None:
            self._static_composite_cache.move_to_end(key)
            return cached
        body = self._cached_pixmap(view.path("body"))
        if body.isNull():
            return QPixmap()
        if self._strict_authority:
            self._view_authority(view, body)
        result = QPixmap(body)
        self._paint_opacity(result, view.path("hair_back"), 1.0)
        self._paint_opacity(result, view.path("base"), 1.0)
        self._paint_neutral_face_layers(result, view)

        # Front hair, sleeves, ornament.
        self._paint_opacity(result, view.path("hair_left"), 1.0)
        self._paint_opacity(result, view.path("hair_right"), 1.0)
        left_lift = self._sleeve_lift(left_hand, pose_id, bounded_energy)
        right_lift = self._sleeve_lift(right_hand, pose_id, bounded_energy)
        self._paint_translated(result, view.path("sleeve_left"), dy=left_lift)
        self._paint_translated(result, view.path("sleeve_right"), dy=right_lift)
        self._paint_opacity(result, view.path("ornament"), 1.0)
        self._heal_registered_seams(result, view)
        self._restore_authority_face(result, view)
        self._static_composite_cache[key] = result
        self._static_composite_cache.move_to_end(key)
        while len(self._static_composite_cache) > MAX_CACHED_STATIC_COMPOSITES:
            self._static_composite_cache.popitem(last=False)
        return result

    def _paint_neutral_face_layers(
        self,
        result: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Paint the registered neutral facial cutouts (with parameter motion applied later).

        The authored facial layers are neutral registered cutouts, not
        effect-only overlays: painting them fills the transparent holes in
        ``base``.  Every pixel painted here sits inside the authority-face
        region and is replaced by ``_restore_authority_face``, so parameter
        motion (corner smile, gaze) is intentionally not applied — dynamic
        eye and mouth motion is re-applied after restoration instead.
        """

        for layer_name in (
            "jaw", "lip_lower", "lip_upper", "corner_left", "corner_right",
            "blush_left", "blush_right", "iris_left", "iris_right",
            "eyelid_left", "eyelid_right", "eyeliner_left", "eyeliner_right",
            "brow_left", "brow_right",
        ):
            self._paint_opacity(result, view.path(layer_name), 1.0)

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
                source_region = self._mask_region(source)
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
        authority = self._view_authority(view, target)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _restore_authority_face(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Remove broad skin-cutout artefacts while preserving body layers."""
        region = self._face_region_cache.get(view.view_id)
        if region is None:
            region = QRegion()
            for layer_name in FACE_AUTHORITY_REGION_LAYERS:
                path = view.path(layer_name)
                if path is None:
                    continue
                source = self._cached_pixmap(path)
                if not source.isNull():
                    region = region.united(self._mask_region(source))
            self._face_region_cache[view.view_id] = region
        if region.isEmpty():
            return
        authority = self._view_authority(view, target)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _view_authority(self, view: LayeredFullBodyView, target: QPixmap) -> QPixmap:
        """Bind seam/face restoration to this renderer's immutable source set."""
        path = self._authority_root / f"{view.view_id}.png"
        authority = self._cached_pixmap(path, required=self._strict_authority)
        if self._strict_authority:
            if authority.isNull():
                raise ValueError(f"Missing or invalid view authority: {path}")
            if authority.size() != target.size():
                raise ValueError(f"View authority canvas mismatch: {path}")
        return authority

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
        """Render a view blended toward its next neighbour by ``blend`` in [0, 1].

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
        if bounded == 1.0:
            return following
        # Add weighted premultiplied pixels instead of SourceOver. The old
        # silhouette must fade where the next view is transparent, while
        # overlapping opaque pixels retain total alpha (1-b) + b == 1.
        result = QPixmap(current.size())
        result.setDevicePixelRatio(current.devicePixelRatio())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setOpacity(1.0 - bounded)
        painter.drawPixmap(0, 0, current)
        # Bake opacity before addition: Qt applies painter opacity to the
        # saturated Plus result, which would fade the overlap a second time.
        weighted_next = QPixmap(following.size())
        weighted_next.setDevicePixelRatio(following.devicePixelRatio())
        weighted_next.fill(Qt.transparent)
        next_painter = QPainter(weighted_next)
        next_painter.setOpacity(bounded)
        next_painter.drawPixmap(0, 0, following)
        next_painter.end()
        painter.setOpacity(1.0)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.drawPixmap(0, 0, weighted_next)
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
        eye_state = eye_state_for_blink(expression.blink)
        authored_path = view.blink_frames.get(eye_state)
        if view.blink_frames and eye_state is not EyeState.REST and authored_path is None:
            raise ValueError(f"Incomplete authored eyelid states: {view.view_id}")
        if authored_path is not None:
            authored = self._cached_pixmap(authored_path)
            if authored.isNull():
                raise ValueError(f"Unreadable authored eyelid frame: {authored_path.name}")
            painter = QPainter(target)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.drawPixmap(0, 0, authored)
            painter.end()
            return
        gaze_dx = round(float(motion.gaze_x) * IRIS_GAZE_SCALE_X)
        gaze_dy = round(float(motion.gaze_y) * IRIS_GAZE_SCALE_Y)
        if gaze_dx or gaze_dy:
            gaze_layers = ("iris_left", "iris_right")
            gaze_region = QRegion()
            for layer_name in gaze_layers:
                source = self._cached_pixmap(view.path(layer_name))
                if not source.isNull():
                    gaze_region = gaze_region.united(self._mask_region(source))
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
                    blink_region = blink_region.united(self._mask_region(source))
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

    def _paint_authored_speech(
        self, target: QPixmap, view: LayeredFullBodyView, motion: FaceMotionFrame,
    ) -> None:
        """Reveal a registered mouth frame without stretching its teeth or lips."""
        aperture = max(0.0, min(1.0, float(motion.mouth.aperture)))
        if aperture <= MOUTH_APERTURE_THRESHOLD:
            return
        viseme = Viseme.CONSONANT if motion.viseme is Viseme.CLOSED else motion.viseme
        path = view.speech_frames.get(viseme)
        if path is None:
            raise ValueError(f"Missing native speech frame: {view.view_id}/{viseme.value}")
        source = self._cached_pixmap(path)
        if source.size() != target.size():
            raise ValueError(f"Native speech canvas mismatch: {path.name}")
        painter = QPainter(target)
        painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        painter.setOpacity(min(1.0, aperture / AUTHORED_SPEECH_VISIBLE_APERTURE))
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _paint_visible_cavity(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
        mouth,
    ) -> None:
        """Fade in the accepted registered speech mouth while preserving skin motion."""
        cavity_path = view.path("oral_cavity")
        if cavity_path is None:
            return
        cavity_source = self._cached_pixmap(cavity_path)
        if cavity_source.isNull():
            return
        bounds = self._mask_region(cavity_source).boundingRect()
        if bounds.isEmpty():
            # Back-side views intentionally use the body-only face authority.
            return
        aperture = max(0.0, min(1.0, float(mouth.aperture)))
        # This layer is a tightly cropped, softly feathered copy of the
        # matching yaw view's own authority mouth.  Some accepted packs keep
        # identical RGB at rest, so opacity alone leaves the authored speech state unchanged. Apply
        # a small, mouth-centred vertical aperture to this semantic cut-out;
        # the transparent full-canvas registration keeps the deformation away
        # from the chin and surrounding skin.
        aperture_scale = 1.0 + aperture * 0.22
        target_height = float(bounds.height()) * aperture_scale
        target_rect = QRectF(
            float(bounds.x()),
            float(bounds.y()) + (float(bounds.height()) - target_height) / 2.0,
            float(bounds.width()),
            target_height,
        )
        source_rect = QRectF(bounds)
        # Native face cutouts can end at different neck heights. A percentage
        # of that bounding box can cross the lips and erase the speech state.
        # The authored lip footprint owns the permitted movement; a single
        # pixel around it accommodates filtered edges without moving the chin.
        lip_region = QRegion()
        for name in ("lip_upper", "lip_lower", "corner_left", "corner_right"):
            path = view.path(name)
            if path is not None:
                lip_region = lip_region.united(self._mask_region(self._cached_pixmap(path)))
        if lip_region.isEmpty():
            return
        mouth_clip = QRectF(lip_region.boundingRect().adjusted(-1, -1, 1, 1))
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
            # inward_lerped_u_layer semantics, painted straight onto the
            # composition target (see paint_inward_lerped_u_layer).
            paint_inward_lerped_u_layer(
                target,
                source,
                view.mouth_center_x,
                u_inward,
            )
