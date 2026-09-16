"""Render coordinated half-body expressions and preserve displayed mouth state."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from domain.face_rig import FaceMotionFrame
from infrastructure.animated_appearance import AnimatedAppearance
from infrastructure.complete_halfbody_expressions import (
    EYES, FAMILIES, CompleteHalfbodyFrames, load_complete_halfbody_frames,
)
from infrastructure.detachable_halfbody_assets import POSES

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

    def blink(self, base: QPixmap, eye_state: str) -> QPixmap | None:
        if eye_state not in EYES:
            raise ValueError(f"Unsupported complete half-body eye state: {eye_state}")
        binding = self._contexts.get(base.cacheKey())
        if binding is None:
            return None
        return self._compose(base, *binding, eye_state)

    def _compose(
        self, base: QPixmap, pose: str, family: str, eye: str,
    ) -> QPixmap:
        key = pose, family, eye
        if self._assets is None:
            raise RuntimeError("Complete half-body sources have not been loaded")
        if key not in self._pixmaps:
            frame = QPixmap()
            if not frame.loadFromData(self._assets.frames[pose][family][eye], "PNG"):
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
        self._contexts[frame.cacheKey()] = (pose, family)
        self._contexts.move_to_end(frame.cacheKey())
        while len(self._contexts) > MAX_FRAME_CONTEXTS:
            self._contexts.popitem(last=False)
        return frame
