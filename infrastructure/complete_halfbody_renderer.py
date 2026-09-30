"""Render coordinated half-body expressions and preserve displayed mouth state."""
from __future__ import annotations

lazy from collections import OrderedDict
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from application.appearance_ports import MakeupOverlayPort
lazy from domain.face_rig import FaceMotionFrame
lazy from domain.qt_image_io import load_pixmap_png
lazy from infrastructure.animated_appearance import AnimatedAppearance
lazy from infrastructure.blink_makeup_composition import paint_blink_makeup
lazy from infrastructure.complete_halfbody_expressions import (
    EYES, FAMILIES, CompleteHalfbodyFrames, load_complete_halfbody_frames,
)
lazy from infrastructure.detachable_halfbody_assets import POSES

# Keep a full set of current and queued endpoints across all seven poses.
# These entries hold only cache keys and labels, not image buffers.
MAX_FRAME_CONTEXTS = 2 * len(POSES) * len(FAMILIES) * len(EYES)
MAX_DECODED_FRAMES = 24
CLOSED_APERTURE = 0.01


class CompleteHalfbodyRenderer:
    """Optional whole-frame sources with appearance composed separately.

    Pixmap cache keys identify the displayed endpoint during a speech transition.
    A blink therefore follows that endpoint, even if the next mouth is queued.
    """

    def __init__(self, root: Path, overlay: object = None) -> None:
        self._root = root
        self._loaded = False
        self._assets: CompleteHalfbodyFrames | None = None
        self._appearance = AnimatedAppearance(overlay)
        self._overlay = overlay
        self._contexts: OrderedDict[int, tuple[str, str]] = OrderedDict()
        self._pixmaps: OrderedDict[tuple[str, str, str], QPixmap] = OrderedDict()

    def _load(self) -> CompleteHalfbodyFrames | None:
        if not self._loaded:
            self._assets = load_complete_halfbody_frames(self._root)
            self._loaded = True
        return self._assets

    def supports(self, expression: str) -> bool:
        assets = self._load()
        return assets is not None and expression in assets.expressions

    def render(
        self, base: QPixmap, motion: FaceMotionFrame, layers: object,
    ) -> QPixmap | None:
        assets = self._load()
        if assets is None:
            return None
        expression = getattr(layers, "mouth_expression", None) or motion.expression
        binding = assets.expressions.get(expression)
        if binding is None:
            return None
        pose, family = binding
        if motion.mouth.aperture <= CLOSED_APERTURE:
            family = "neutral"
        # Half-body timers keep a clean open-eye endpoint and stamp blinking
        # separately. This also preserves the endpoint during mouth transitions.
        return self._compose(base, pose, family, "rest")

    def blink(
        self,
        base: QPixmap,
        eye_state: str,
        eye_patch: QPixmap | None = None,
        makeup_context: str | None = None,
    ) -> QPixmap | None:
        if eye_state not in EYES:
            raise ValueError(f"Unsupported complete half-body eye state: {eye_state}")
        binding = self._contexts.get(base.cacheKey())
        if binding is None:
            return None
        endpoint = self._compose(base, *binding, eye_state)
        if eye_patch is None or eye_patch.isNull():
            return endpoint
        # Complete endpoints own the eyelid pixels, not the displayed mouth,
        # gesture, hair or body.  The caller supplies the already registered
        # eye patch, whose alpha is the exact authority boundary for this
        # expression and eye state.
        layer = QPixmap(endpoint.size())
        layer.fill(Qt.transparent)
        painter = QPainter(layer)
        painter.drawPixmap(0, 0, endpoint)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, eye_patch)
        painter.end()
        result = QPixmap(base)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, layer)
        painter.end()
        if (
            makeup_context is not None
            and isinstance(self._overlay, MakeupOverlayPort)
            and callable(self._overlay.apply_makeup)
        ):
            paint_blink_makeup(
                result, eye_patch, self._overlay, makeup_context, eye_state
            )
        self._remember_context(result, binding)
        return result

    def _remember_context(self, frame: QPixmap, binding: tuple[str, str]) -> None:
        self._contexts[frame.cacheKey()] = binding
        self._contexts.move_to_end(frame.cacheKey())
        while len(self._contexts) > MAX_FRAME_CONTEXTS:
            self._contexts.popitem(last=False)

    def _compose(
        self, base: QPixmap, pose: str, family: str, eye: str,
    ) -> QPixmap:
        key = pose, family, eye
        if self._assets is None:
            raise RuntimeError("Complete half-body sources have not been loaded")
        if key not in self._pixmaps:
            frame = QPixmap()
            if not load_pixmap_png(frame, self._assets.frames[pose][family][eye]):
                raise ValueError(f"Cannot decode complete half-body frame: {key}")
            self._pixmaps[key] = frame
        self._pixmaps.move_to_end(key)
        while len(self._pixmaps) > MAX_DECODED_FRAMES:
            self._pixmaps.popitem(last=False)
        frame = self._appearance.compose(
            self._pixmaps[key], pose, lambda _frame: None,
            eye_state=eye,
            suppress_makeup_slots=frozenset({"eyes"}) if eye != "rest" else frozenset(),
        )
        if not base.isNull() and frame.size() != base.size():
            frame = frame.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember_context(frame, (pose, family))
        return frame
