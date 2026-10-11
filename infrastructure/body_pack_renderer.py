"""Render declared body frames and character layers without a shared asset route."""
from __future__ import annotations

lazy import hashlib
lazy import logging
lazy from collections import OrderedDict
lazy from collections.abc import Callable, Mapping
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap, QRegion
lazy from domain.body_pack import BodyPackMismatchError
lazy from domain.character_layer_plan import CharacterLayerPlan, CharacterLayerAsset, CharacterLayerMask
lazy from domain.face_rig import FaceMotionFrame, Viseme, eye_state_for_blink
lazy from domain.qt_image_io import load_pixmap_png
lazy from infrastructure.body_pack_reader import BodyPackReader
lazy from infrastructure.body_pack_compositor import compose_body_pack_frame, body_pack_alpha_region


LOGGER = logging.getLogger(__name__)
CLOSED_APERTURE = 0.01
MAX_FRAME_CONTEXTS = 48


class BodyPackRenderer:
    """Own both renderer ports for a declared dependency.

    Expression, mouth and blink pixels come exclusively from verified body
    frames. Character layers are composed after that core state is selected.
    Missing views or states raise; this route never requests product assets.
    """

    def __init__(
        self, body: BodyPackReader, views: Mapping[str, CharacterLayerPlan],
        load_layer: Callable[[CharacterLayerAsset | CharacterLayerMask], bytes],
    ) -> None:
        self._body = body
        self._views = views
        self._load_layer = load_layer
        self._contexts: OrderedDict[int, tuple[str, str]] = OrderedDict()
        self._pixmaps: OrderedDict[str, QPixmap] = OrderedDict()
        self._core_regions: OrderedDict[str, QRegion] = OrderedDict()

    def _pixmap(self, data: bytes) -> QPixmap:
        digest = hashlib.sha256(data).hexdigest()
        cached = self._pixmaps.get(digest)
        if cached is not None:
            self._pixmaps.move_to_end(digest)
            return QPixmap(cached)
        pixmap = QPixmap()
        if not load_pixmap_png(pixmap, data):
            raise BodyPackMismatchError("invalid_image", "Cannot decode a declared body or character frame")
        self._pixmaps[digest] = pixmap
        while len(self._pixmaps) > MAX_FRAME_CONTEXTS:
            self._pixmaps.popitem(last=False)
        return QPixmap(pixmap)

    def _core_region(self, data: bytes) -> QRegion:
        digest = hashlib.sha256(data).hexdigest()
        cached = self._core_regions.get(digest)
        if cached is None:
            cached = body_pack_alpha_region(self._pixmap(data))
            self._core_regions[digest] = cached
            while len(self._core_regions) > MAX_FRAME_CONTEXTS:
                self._core_regions.popitem(last=False)
        self._core_regions.move_to_end(digest)
        return QRegion(cached)

    def _compose(self, view: str, state: str, *, halfbody: bool = False) -> QPixmap:
        base = self._pixmap(self._body.load_frame(view, state, halfbody=halfbody))
        mask = self._body.load_face_core(view)
        core = None if mask is None else self._core_region(mask)
        plan = self._views.get(view)
        if plan is None:
            return base
        if mask is None and (plan.layers or plan.base_hide is not None):
            error = BodyPackMismatchError(
                "face_core_required",
                "Provide a body-owned face-core mask for a view with character layers; "
                "an empty mask declares a view without a visible face", view,
            )
            LOGGER.error("Body-pack composition rejected [%s]: %s", error.code, error)
            raise error

        def image(record: CharacterLayerAsset | CharacterLayerMask) -> QPixmap:
            data = self._load_layer(record)
            if hashlib.sha256(data).hexdigest() != record.sha256:
                raise BodyPackMismatchError("file_hash_mismatch", f"Character layer changed: {record.path}")
            return self._pixmap(data)

        return compose_body_pack_frame(base, plan, image, face_core=core)

    @staticmethod
    def _family(motion: FaceMotionFrame, aperture: float | None = None) -> str:
        amount = motion.mouth.aperture if aperture is None else aperture
        if motion.viseme is Viseme.CLOSED or amount <= CLOSED_APERTURE:
            return "neutral"
        return {Viseme.A: "a", Viseme.O: "o", Viseme.U: "o"}.get(motion.viseme, "small")

    def render_view(self, view_id: str, motion: FaceMotionFrame, **options: object) -> QPixmap:
        """Select the body's authored blink and mouth endpoint for this view."""
        eye = eye_state_for_blink(motion.expression_shape.blink).value
        family = self._family(motion)
        state = eye if family == "neutral" else f"{family}-{eye}"
        keys = self._body.frame_keys(view_id)
        if family == "neutral" and keys == ("rest",):
            state = "rest"
        return self._compose(view_id, state)

    def render(
        self, base: QPixmap, motion: FaceMotionFrame, layers: object,
        *, aperture: float | None = None,
    ) -> QPixmap:
        """Render an authored half-body pose and remember its blink endpoint."""
        poses = {item.view_id for item in self._body.manifest.half_body}
        view = motion.expression if motion.expression in poses else motion.pose.value
        family = self._family(motion, aperture)
        result = self._compose(view, f"{family}-rest", halfbody=True)
        if not base.isNull() and result.size() != base.size():
            result = result.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember(result, view, family)
        return result

    def _remember(self, frame: QPixmap, view: str, family: str) -> None:
        self._contexts[frame.cacheKey()] = view, family
        while len(self._contexts) > MAX_FRAME_CONTEXTS:
            self._contexts.popitem(last=False)

    def render_complete_blink(self, base: QPixmap, eye_state: str) -> QPixmap:
        """Keep the displayed body mouth endpoint during a whole-frame blink."""
        context = self._contexts.get(base.cacheKey())
        if context is None:
            error = BodyPackMismatchError(
                "missing_frame_context", "Render a body-owned endpoint before blinking",
            )
            LOGGER.error("Body-pack blink rejected [%s]: %s", error.code, error)
            raise error
        view, family = context
        result = self._compose(view, f"{family}-{eye_state}", halfbody=True)
        if result.size() != base.size():
            result = result.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember(result, view, family)
        return result

    def render_overlay(
        self, base: QPixmap, source: QPixmap, *, mask: QPixmap | None = None,
        opacity: float = 1.0, eye_state: str = "rest", view_id: str | None = None,
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        """Resolve blinking from body-owned endpoints supplied by render()."""
        if eye_state == "rest":
            return QPixmap(base)
        return self.render_complete_blink(base, eye_state)
