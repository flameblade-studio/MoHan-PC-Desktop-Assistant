"""Half-body face renderer with complete and layered source routes.

Installed complete-expression sources select coordinated mouth and blink
frames through explicit expression bindings. Other expressions retain the
existing native or parametric layer routes. Appearance remains separately
composed; source approval and formal installation are independent gates.
"""

from __future__ import annotations

lazy from collections import OrderedDict
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QPainter, QPixmap, QRegion

lazy from application.appearance_ports import OutfitOverlayPort
lazy from domain.companion_animation_contract import (
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    gesture_portrait_expression,
    outfit_silhouette,
)
lazy from domain.face_rig import FaceMotionFrame, Viseme
lazy from domain.qt_image_io import optional_pixmap, require_pixmap
# Eager because this function is re-exported for direct ``from ... import`` callers.
from domain.legacy_makeup import select_legacy_makeup_view_id
lazy from infrastructure.blink_makeup_composition import paint_blink_makeup
lazy from infrastructure.complete_halfbody_renderer import CompleteHalfbodyRenderer
lazy from infrastructure.detachable_halfbody_assets import load_detachable_halfbody_assets
lazy from infrastructure.exasperated_candidate_assets import (
    ExasperatedAppearanceOverlay,
    ExasperatedCandidateAssets,
)
lazy from infrastructure.layered_face_assets import (
    LayeredFaceManifest,
    LayeredFacePose,
    load_layered_face_assets,
)
# Public compatibility re-export retained after the painting helper split.
from infrastructure.layered_face_painting import MAX_CACHED_MASK_BOUNDS as MAX_CACHED_MASK_BOUNDS
lazy from infrastructure.layered_face_painting import LayeredFacePaintingMixin

MOUTH_APERTURE_THRESHOLD = 0.01

# The authored 54-layer asset set lives under the project root, mirroring the
# ``RESOURCE_BASE`` resolution used by the presentation layer. The renderer
# resolves it itself so the composition boundary stays a no-arg factory.
LAYERED_FACE_ASSET_DIR = Path("assets") / "expressions" / "layered"
DETACHABLE_HALFBODY_ASSET_DIR = Path("assets") / "expressions" / "detachable"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CACHED_LAYER_PIXMAPS = 30
MAX_CACHED_NEUTRAL_POSES = 3
SEAM_HEAL_RADIUS = 7
FACE_AUTHORITY_FILES = frozendict({
    "cheek": "idle.png",
    "lean": "idle_lean.png",
    "front": "idle_front.png",
})
REGISTERED_COMPOSITE_LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right", "hair_left", "hair_right",
    "sleeve_left", "sleeve_right", "ornament",
)
FACE_AUTHORITY_REGION_LAYERS = (
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right",
)


lazy from infrastructure.exasperated_face_rendering import ExasperatedFaceRenderingMixin


class LayeredParametricFaceRenderer(
    ExasperatedFaceRenderingMixin,
    LayeredFacePaintingMixin,
):
    """Select complete expressions or compose existing authored face layers.

    This renderer satisfies :class:`FaceRendererPort` so it can replace
    :class:`~infrastructure.face_renderer.ParametricFaceRenderer` at the
    composition boundary. Complete sources use explicit expression bindings;
    existing native and parametric routes handle expressions without them.
    """

    def __init__(
        self,
        manifest: LayeredFaceManifest | None = None,
        outfit_overlay: OutfitOverlayPort | None = None,
        authority_dir: Path | None = None,
        detachable_dir: Path | None = None,
        use_detachable: bool = True,
        exasperated_candidate_dir: Path | None = None,
        candidate_appearance_overlay: ExasperatedAppearanceOverlay | None = None,
    ) -> None:
        self._manifest = manifest
        self._outfit_overlay = outfit_overlay
        # The idle authority portraits (seam healing, face restoration) and
        # the speaking/viseme patches are read from this directory.  Tests
        # pass a staging directory to validate a candidate rig against its
        # own authorities while preserving assets/expressions.
        self._authority_dir = (
            Path(authority_dir).resolve()
            if authority_dir is not None
            else PROJECT_ROOT / "assets" / "expressions"
        )
        self._detachable_dir = (
            Path(detachable_dir).resolve()
            if detachable_dir is not None
            else PROJECT_ROOT / DETACHABLE_HALFBODY_ASSET_DIR
        )
        self._use_detachable = use_detachable
        self._exasperated_candidate_dir = (
            Path(exasperated_candidate_dir).resolve()
            if exasperated_candidate_dir is not None
            else None
        )
        self._candidate_appearance_overlay = candidate_appearance_overlay
        # An explicitly injected detachable candidate must not be shadowed by
        # the repository's installed complete-expression pack. Callers that
        # want both sources can bind both directories explicitly.
        complete_root = (
            self._authority_dir / "complete-expressions"
            if authority_dir is not None or detachable_dir is None
            else self._detachable_dir / "complete-expressions"
        )
        self._complete_halfbody = CompleteHalfbodyRenderer(complete_root, outfit_overlay)
        self._exasperated_candidate_assets: ExasperatedCandidateAssets | None = None
        self._exasperated_candidate_rest: QPixmap | None = None
        self._exasperated_candidate_patches: dict[str, QPixmap] = {}
        self._detachable_assets = None
        self._detachable_loaded = False
        self._detachable_cache: OrderedDict[str, QPixmap] = OrderedDict()
        # One 25-layer pose plus a transition margin is sufficient. The former
        # unbounded cache retained every full-canvas pose layer for the entire
        # process lifetime after pose changes.
        self._pixmap_cache: OrderedDict[str, QPixmap] = OrderedDict()
        # A neutral pose is the immutable result of compositing all 25 authored
        # layers.  Speech changes only the small dynamic feature cut-outs, so
        # rebuilding the same 1254px body, hair, clothing and neutral face for
        # both endpoints of every phoneme transition wastes most of the 20ms
        # frame budget.  Keep at most the three authored poses; returned
        # QPixmaps detach on first paint and preserve these authorities.
        self._neutral_pose_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._top_pose_cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._layer_center_cache: dict[str, tuple[float, float]] = {}
        # Speech masks may be regenerated as transient QPixmaps for the whole
        # lifetime of the application, so their cache keys are not a finite
        # authored-asset set. Retain only the recent working set.
        self._mask_bounds_cache: OrderedDict[int, QRect] = OrderedDict()
        self._seam_region_cache: dict[str, QRegion] = {}
        self._face_region_cache: dict[str, QRegion] = {}
        self._mouth_mask_cache: dict[str, QPixmap] = {}

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
        """Render a source-bound expression when installed, otherwise the legacy rig."""

        if aperture is not None:
            motion = replace(
                motion,
                mouth=replace(
                    motion.mouth,
                    aperture=max(0.0, min(1.0, float(aperture))),
                ),
            )
        # The presentation path already supplies the authored viseme frame and
        # its pose-specific soft mouth mask.  Start from a clean 25-layer
        # neutral composite here, then apply that one registered mouth patch
        # exactly once below.  Deforming the neutral lip/cavity cut-outs first
        # and painting the viseme a second time was the source of the doubled,
        # fragmented mouth seen in packaged builds.
        # The four gesture expressions (and their speech/blink frames) are the
        # exception: their body differs from the neutral pose, so the authored
        # gesture portrait is the frame and the appearance pack dresses it with
        # the layers cut on that very portrait (its gesture silhouette).
        gesture = gesture_portrait_expression(motion.expression)
        silhouette = outfit_silhouette(motion.expression, motion.pose.value)
        if gesture == "exasperated_front" and self._exasperated_candidate_dir is not None:
            return self._render_exasperated_candidate(base, motion, layers, aperture)
        complete = self._complete_halfbody.render(base, motion, layers)
        if complete is not None:
            return complete
        native_state = getattr(self._outfit_overlay, "render_native_state", None)
        if callable(native_state):
            amount = motion.mouth.aperture if aperture is None else float(aperture)
            native = optional_pixmap(
                native_state(
                    silhouette,
                    speaking=amount > MOUTH_APERTURE_THRESHOLD,
                )
            )
            if native is not None:
                return native if base.isNull() or native.size() == base.size() else native.scaled(
                    base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
        native_neutral = getattr(self._outfit_overlay, "native_neutral", None)
        composed = (
            optional_pixmap(native_neutral(silhouette))
            if callable(native_neutral)
            else None
        )
        # Both sources below can supply a legacy (pre-V5-rebind) authored
        # face that makeup_declares_view() may redirect makeup away from:
        # native_neutral() returns the reviewed-garment "native identity"
        # image pinned to this pose (assets/expressions/reviewed-garments/) --
        # traced empirically (2026-09-29, trace_glance_branch.py) to be what
        # actually supplies glance/caught/happy/worried/reminder (none of
        # them reach _gesture_portrait: gesture_portrait_expression() only
        # returns non-None for the 4 front-pose GESTURE_OUTFIT_SILHOUETTES,
        # not these cheek/lean EXPRESSION_POSES entries) -- and
        # _gesture_portrait() itself for the front gestures that DO have a
        # dedicated legacy silhouette some day.  Every other source (
        # complete_halfbody, render_native_state, _detachable_portrait,
        # render_pose) is a new-face composite and never sets this flag.
        may_need_legacy_makeup = composed is not None and not composed.isNull()
        if composed is None:
            composed = self._detachable_portrait(silhouette)
        if composed.isNull() and gesture is not None:
            composed = self._gesture_portrait(gesture)
            may_need_legacy_makeup = not composed.isNull()
        if composed.isNull():
            composed = self.render_pose(
                self._pose(motion),
                motion,
                animate_mouth=False,
            )
        if composed.isNull() or base.isNull():
            return composed
        # Apply the outfit overlay on the FULL authored canvas, before any
        # scaling: the outfit assets and their anchor bounds live in the
        # authority canvas coordinates (1254px for the half-body poses).
        # Applying after the scale-down to the caller's canvas made every
        # anchor check requiring attention (or draw ~2.7x off), so installed outfits stay outside
        # appeared on the half-body poses at all.
        if self._outfit_overlay is not None:
            # This frame still contains REST eyes. Select state pigment only
            # after a registered eyelid patch is available in render_overlay;
            # HALF source selection stays separate from makeup on the REST fallback.
            # A legacy gesture portrait (the old, pre-V5-rebind authored
            # illustration, e.g. glance.png/caught.png) is geometrically a
            # different face from the new-face makeup layers authored for
            # `silhouette`; when the active makeup pack declares a matching
            # legacy silhouette (see LEGACY_MAKEUP_SILHOUETTES,
            # domain/outfit_pack.py), makeup resolves against that instead,
            # leaving garment/silhouette-clip on the unchanged `silhouette`.
            # Every other composed source (new-face native/detachable/render_pose)
            # is completely unaffected: makeup_view_id stays None for them,
            # byte-identical to before this addition.
            #
            makeup_view_id = None
            if may_need_legacy_makeup:
                declares = getattr(self._outfit_overlay, "makeup_declares_view", None)
                makeup_view_id = select_legacy_makeup_view_id(declares, silhouette)
            composed = require_pixmap(
                self._outfit_overlay.apply(
                    composed,
                    silhouette,
                    makeup_view_id=makeup_view_id,
                )
            )
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
                result, mouth_source, mouth_mask,
                max(0.0, min(1.0, actual_aperture / 0.18)),
            )
        return result

    def _gesture_portrait(self, expression: str) -> QPixmap:
        """The authored full-canvas portrait of one gesture expression (null when absent)."""
        return QPixmap(self._cached_pixmap(self._authority_dir / f"{expression}.png"))

    def supports_discrete_speech(self, expression: str) -> bool:
        """Tell the presentation timer when complete mouth endpoints are authoritative."""
        if self._complete_halfbody.supports(expression):
            return True
        if expression == CHEEK_SPEECH_CLOSED_EXPRESSION:
            capability = getattr(self._outfit_overlay, "has_native_motion", None)
            return bool(callable(capability) and capability("cheek-rest"))
        return (
            self._exasperated_candidate_dir is not None
            and gesture_portrait_expression(expression) == "exasperated_front"
        )

    def _detachable_portrait(self, silhouette: str) -> QPixmap:
        """Use the installed seven-part rig; missing installation uses legacy assets."""
        if not self._use_detachable:
            return QPixmap()
        if not self._detachable_loaded:
            self._detachable_assets = load_detachable_halfbody_assets(self._detachable_dir)
            self._detachable_loaded = True
        if self._detachable_assets is None:
            return QPixmap()
        cached = self._detachable_cache.get(silhouette)
        if cached is None:
            cached = self._detachable_assets.compose(silhouette)
            self._detachable_cache[silhouette] = cached
            self._detachable_cache.move_to_end(silhouette)
            while len(self._detachable_cache) > MAX_CACHED_NEUTRAL_POSES:
                self._detachable_cache.popitem(last=False)
        else:
            self._detachable_cache.move_to_end(silhouette)
        return QPixmap(cached)

    def render_overlay(
        self,
        base: QPixmap,
        source: QPixmap,
        *,
        mask: QPixmap | None = None,
        opacity: float = 1.0,
        eye_state: str = "rest",
        view_id: str | None = None,
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        """Compose one registered expression layer without owning its policy."""
        if eye_state != "rest":
            makeup_context = makeup_view_id if makeup_view_id is not None else view_id
            complete = self._complete_halfbody.blink(
                base, eye_state, source, makeup_context
            )
            if complete is not None:
                return complete
        native_blink = getattr(self._outfit_overlay, "render_native_blink", None)
        if view_id is not None and eye_state != "rest" and callable(native_blink):
            native = optional_pixmap(
                native_blink(base, view_id, eye_state=eye_state)
            )
            if native is not None:
                return native
        result = QPixmap(base)
        if mask is None:
            if not source.isNull():
                painter = QPainter(result)
                if eye_state != "rest":
                    # A registered eyelid replaces face colour while the
                    # existing body retains its matte, including fine alpha
                    # around extracted highlights and hair-edge pixels.
                    painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                painter.setOpacity(max(0.0, min(1.0, float(opacity))))
                painter.drawPixmap(0, 0, source)
                painter.end()
                makeup_context = makeup_view_id if makeup_view_id is not None else view_id
                if makeup_context is not None and eye_state != "rest" and self._outfit_overlay is not None:
                    paint_blink_makeup(result, source, self._outfit_overlay, makeup_context, eye_state)
            return result
        self._paint_masked(result, source, mask, opacity)
        return result
    # -- core layered composition -------------------------------------------

    def render_pose(
        self,
        pose: LayeredFacePose,
        motion: FaceMotionFrame,
        *,
        animate_mouth: bool = True,
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

        # The authored eyelid/brow/blush PNGs are registered replacement
        # cut-outs from the authority portrait, not independent effect sprites.
        # They are already present exactly once in ``neutral``. Painting those
        # semi-transparent cut-outs a second time exposes their extraction
        # boundaries as the reported forehead arc, cheek circles, eye bars and
        # chin seam. Keep them atomic until a future asset revision supplies
        # genuine alternate-state layers; mouth articulation below remains
        # fully parametric and is confined to the mouth region.
        _ = expression

        # Restore the authored topmost occlusion after dynamic facial layers;
        # bangs, sleeves and ornaments must stay in front of the face.
        self._paint_top_pose(result, pose)
        # Every supplied layer is a full-canvas registered cut-out.  Heal only
        # their extraction boundary after the final top occlusion is present;
        # healing earlier allowed hair/sleeve/ornament seams to be painted back
        # over the repaired face on the very next operation.
        self._heal_registered_seams(result, pose)
        # The first-generation face cut-outs contain broad skin-coloured
        # interiors, not merely antialiased feature pixels.  Restore the exact
        # authority face inside the union of those registered face layers so
        # their rectangles/circles remain outside visible output.  This is a facial
        # identity sanitation pass only: body, hair, sleeves, ornaments and
        # their physics remain the 25-layer composition above.
        self._restore_authority_face(result, pose)
        if (
            animate_mouth
            and (
                motion.viseme is not Viseme.CLOSED
                or mouth.aperture > MOUTH_APERTURE_THRESHOLD
            )
        ):
            self._paint_registered_mouth(result, pose, motion)
        return result

    def _restore_authority_face(
        self,
        target: QPixmap,
        pose: LayeredFacePose,
    ) -> None:
        """Replace defective skin-filled cut-out interiors with clean identity."""

        key = pose.pose.value
        region = self._face_region_cache.get(key)
        if region is None:
            region = QRegion()
            for layer_name in FACE_AUTHORITY_REGION_LAYERS:
                source = self._cached_pixmap(pose.path(layer_name))
                if not source.isNull():
                    region = region.united(QRegion(source.mask()))
            self._face_region_cache[key] = region
        authority_name = FACE_AUTHORITY_FILES.get(key)
        if not authority_name or region.isEmpty():
            return
        authority = self._cached_pixmap(self._authority_dir / authority_name)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _paint_registered_mouth(
        self,
        target: QPixmap,
        pose: LayeredFacePose,
        motion: FaceMotionFrame,
    ) -> None:
        """Apply one identity-preserving authored mouth inside a soft mask.

        The supplied lip/cavity PNGs are neutral registered cut-outs. Scaling
        those cut-outs also scales their anti-aliased skin boundary, which
        tears the face.  MoHan already has authority-aligned speech/viseme
        portraits for all three half-body poses.  Use only the small mouth
        region from the best matching authority while the remaining 25-layer
        frame stays fully parametric.
        """

        key = pose.pose.value
        suffix = "" if key == "cheek" else f"_{key}"
        names = {
            Viseme.A: f"speaking{suffix}",
            Viseme.I: f"viseme_i{suffix}",
            Viseme.U: f"viseme_round{suffix}",
            Viseme.E: f"viseme_i{suffix}",
            Viseme.O: f"viseme_o{suffix}",
            Viseme.CONSONANT: f"speaking{suffix}",
        }
        requested = str(motion.expression).strip()
        candidates = (
            requested,
            names.get(motion.viseme, f"speaking{suffix}"),
            f"speaking{suffix}",
        )
        source = QPixmap()
        for name in candidates:
            path = self._authority_dir / f"{name}.png"
            if path.is_file():
                source = self._cached_pixmap(path)
                if not source.isNull():
                    break
        if source.isNull():
            return
        mask = self._mouth_mask(pose)
        opacity = max(
            0.0,
            min(1.0, float(motion.mouth.aperture) / 0.16),
        )
        self._paint_masked(target, source, mask, opacity)

    def _mouth_mask(self, pose: LayeredFacePose) -> QPixmap:
        key = pose.pose.value
        cached = self._mouth_mask_cache.get(key)
        if cached is not None:
            return cached
        region = QRegion()
        for layer_name in (
            "oral_cavity",
            "teeth_tongue",
            "lip_lower",
            "lip_upper",
            "corner_left",
            "corner_right",
        ):
            source = self._cached_pixmap(pose.path(layer_name))
            if not source.isNull():
                region = region.united(QRegion(source.mask()))
        bounds = region.boundingRect().adjusted(-12, -9, 12, 9)
        body = self._cached_pixmap(pose.path("body"))
        mask = QPixmap(body.size())
        mask.fill(Qt.transparent)
        if not bounds.isEmpty():
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            for inset, alpha in ((0, 46), (2, 86), (4, 150), (6, 255)):
                rect = bounds.adjusted(inset, inset, -inset, -inset)
                if not rect.isEmpty():
                    painter.setBrush(QColor(255, 255, 255, alpha))
                    painter.drawRoundedRect(rect, 10, 10)
            painter.end()
        self._mouth_mask_cache[key] = mask
        return mask

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

    def _heal_registered_seams(
        self,
        target: QPixmap,
        pose: LayeredFacePose,
    ) -> None:
        """Restore only extraction-edge pixels from the authority portrait.

        The supplied feature PNGs are full-canvas registered cut-outs. Their
        anti-aliased extraction edges carry slightly different premultiplied
        skin colours, which form visible circles and the chin arc when stacked.
        This is not a legacy portrait fallback: all 25 layers remain the frame
        source and only a three-pixel boundary band is colour-registered to the
        authority image before continuous controls are applied.
        """

        key = pose.pose.value
        region = self._seam_region_cache.get(key)
        if region is None:
            region = QRegion()
            offsets = tuple(
                (dx, dy)
                for dx in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                for dy in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                if abs(dx) + abs(dy) <= SEAM_HEAL_RADIUS
            )
            for layer_name in REGISTERED_COMPOSITE_LAYERS:
                source = self._cached_pixmap(pose.path(layer_name))
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
            self._seam_region_cache[key] = region
        authority_name = FACE_AUTHORITY_FILES.get(key)
        if not authority_name or region.isEmpty():
            return
        authority = self._cached_pixmap(self._authority_dir / authority_name)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.drawPixmap(0, 0, authority)
        painter.end()

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
