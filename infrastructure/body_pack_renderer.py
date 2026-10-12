"""Render declared body frames and character layers without a shared asset route."""
from __future__ import annotations

lazy import hashlib
lazy import logging
lazy from collections import OrderedDict
lazy from collections.abc import Callable, Mapping
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap, QRegion
lazy from domain.body_pack import BodyPackMismatchError, BodyPackSource
lazy from domain.character_layer_plan import CharacterLayerPlan, CharacterLayerAsset, CharacterLayerMask
lazy from domain.face_rig import FaceMotionFrame, Viseme, eye_state_for_blink
lazy from domain.qt_image_io import load_pixmap_png
lazy from infrastructure.body_pack_compositor import compose_body_pack_frame, body_pack_alpha_region


LOGGER = logging.getLogger(__name__)
CLOSED_APERTURE = 0.01
MAX_PIXMAP_CACHE_BYTES = 32 * 1024 * 1024
MAX_LAYER_BYTES_CACHE_BYTES = 8 * 1024 * 1024
REST_ONLY_FAMILY = "rest-only"


class BodyPackRenderer:
    """Own both renderer ports for a declared dependency.

    Expression, mouth and blink pixels come exclusively from verified body
    frames. Character layers are composed after that core state is selected.
    Missing views or states raise; this route never requests product assets.

    The reader may retain 16 MiB of source bytes. This renderer separately
    retains at most 8 MiB of verified layer bytes, 32 MiB of decoded and
    composed pixmaps, and 8 MiB of alpha regions (64 MiB total). All Qt image
    decoding, pixmap, mask, and region work must stay on the GUI thread.
    """

    supports_wink = False

    def __init__(
        self, body: BodyPackSource, views: Mapping[str, CharacterLayerPlan],
        load_layer: Callable[[CharacterLayerAsset | CharacterLayerMask], bytes],
    ) -> None:
        self._body = body
        self._views = views
        self._load_layer = load_layer
        self._last_context: tuple[str, str] | None = None
        self._pixmaps: OrderedDict[tuple[object, ...], tuple[QPixmap, int]] = OrderedDict()
        self._pixmap_cache_bytes = 0
        self._layer_bytes: OrderedDict[str, bytes] = OrderedDict()
        self._layer_bytes_cache_bytes = 0

    @staticmethod
    def _pixmap_weight(pixmap: QPixmap) -> int:
        bytes_per_line = ((pixmap.width() * pixmap.depth() + 31) // 32) * 4
        return bytes_per_line * pixmap.height()

    def _cached_pixmap(self, key: tuple[object, ...]) -> QPixmap | None:
        cached = self._pixmaps.get(key)
        if cached is not None:
            self._pixmaps.move_to_end(key)
            return QPixmap(cached[0])
        return None

    def _cache_pixmap(self, key: tuple[object, ...], pixmap: QPixmap) -> None:
        weight = self._pixmap_weight(pixmap)
        if weight <= 0 or weight > MAX_PIXMAP_CACHE_BYTES:
            return
        previous = self._pixmaps.pop(key, None)
        if previous is not None:
            self._pixmap_cache_bytes -= previous[1]
        self._pixmaps[key] = (QPixmap(pixmap), weight)
        self._pixmap_cache_bytes += weight
        while self._pixmap_cache_bytes > MAX_PIXMAP_CACHE_BYTES:
            _, (_, removed_weight) = self._pixmaps.popitem(last=False)
            self._pixmap_cache_bytes -= removed_weight

    def _pixmap(self, data: bytes, digest: str | None = None) -> QPixmap:
        digest = hashlib.sha256(data).hexdigest() if digest is None else digest
        key = ("image", digest)
        cached = self._cached_pixmap(key)
        if cached is not None:
            return cached
        pixmap = QPixmap()
        if not load_pixmap_png(pixmap, data):
            raise BodyPackMismatchError(
                "invalid_image", "Cannot decode a declared body or character frame",
            )
        self._cache_pixmap(key, pixmap)
        return QPixmap(pixmap)

    def _core_region(self, data: bytes) -> QRegion:
        digest = hashlib.sha256(data).hexdigest()
        return body_pack_alpha_region(self._pixmap(data, digest), digest)

    def _layer_data(self, record: CharacterLayerAsset | CharacterLayerMask) -> bytes:
        cached = self._layer_bytes.get(record.sha256)
        if cached is not None:
            self._layer_bytes.move_to_end(record.sha256)
            return cached
        data = self._load_layer(record)
        if hashlib.sha256(data).hexdigest() != record.sha256:
            raise BodyPackMismatchError(
                "file_hash_mismatch", f"Character layer changed: {record.path}",
            )
        weight = len(data)
        if weight <= MAX_LAYER_BYTES_CACHE_BYTES:
            previous = self._layer_bytes.pop(record.sha256, None)
            if previous is not None:
                self._layer_bytes_cache_bytes -= len(previous)
            self._layer_bytes[record.sha256] = data
            self._layer_bytes_cache_bytes += weight
            while self._layer_bytes_cache_bytes > MAX_LAYER_BYTES_CACHE_BYTES:
                _, removed = self._layer_bytes.popitem(last=False)
                self._layer_bytes_cache_bytes -= len(removed)
        return data

    def _compose(self, view: str, state: str, *, halfbody: bool = False) -> QPixmap:
        cache_key = ("composed", view, state, halfbody)
        cached = self._cached_pixmap(cache_key)
        if cached is not None:
            return cached
        base_data = self._body.load_frame(view, state, halfbody=halfbody)
        base = self._pixmap(base_data)
        mask = self._body.load_face_core(view)
        core = None if mask is None else self._core_region(mask)
        plan = self._views.get(view)
        if plan is None:
            self._cache_pixmap(cache_key, base)
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
            return self._pixmap(self._layer_data(record), record.sha256)

        result = compose_body_pack_frame(base, plan, image, face_core=core)
        self._cache_pixmap(cache_key, result)
        return result

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
        if keys == ("rest",):
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
        keys = self._body.frame_keys(view, halfbody=True)
        if keys == ("rest",):
            family = REST_ONLY_FAMILY
            state = "rest"
        else:
            state = f"{family}-rest"
        result = self._compose(view, state, halfbody=True)
        if not base.isNull() and result.size() != base.size():
            result = result.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember(view, family)
        return result

    def _remember(self, view: str, family: str) -> None:
        self._last_context = (view, family)

    def render_complete_blink(self, base: QPixmap, eye_state: str) -> QPixmap:
        """Use the latest view/family for a blink, including copied or scaled frames."""
        context = self._last_context
        if context is None:
            error = BodyPackMismatchError(
                "missing_frame_context", "Render a body-owned endpoint before blinking",
            )
            LOGGER.error("Body-pack blink rejected [%s]: %s", error.code, error)
            raise error
        view, family = context
        if family == REST_ONLY_FAMILY:
            return QPixmap(base)
        result = self._compose(view, f"{family}-{eye_state}", halfbody=True)
        if result.size() != base.size():
            result = result.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember(view, family)
        return result

    def render_overlay(
        self, base: QPixmap, source: QPixmap, *, mask: QPixmap | None = None,
        opacity: float = 1.0, eye_state: str = "rest", view_id: str | None = None,
        makeup_view_id: str | None = None,
    ) -> QPixmap:
        """Resolve supported eye endpoints from the most recent body frame.

        Wink frames are not declared by the body-pack contract yet and are
        explicitly rejected before any legacy asset can be requested.
        """
        if eye_state.startswith("wink"):
            error = BodyPackMismatchError(
                "unsupported_wink", "Wink is not authored by this body-pack renderer",
            )
            LOGGER.error("Body-pack wink rejected [%s]: %s", error.code, error)
            raise error
        if eye_state == "rest":
            return QPixmap(base)
        return self.render_complete_blink(base, eye_state)


def create_body_pack_renderer(
    body: BodyPackSource | None, views: Mapping[str, CharacterLayerPlan],
    load_layer: Callable[[CharacterLayerAsset | CharacterLayerMask], bytes],
) -> BodyPackRenderer:
    """Build a renderer from a structurally compatible body-pack source."""
    if body is None:
        raise TypeError("A resolved body-pack source is required.")
    return BodyPackRenderer(body, views, load_layer)
