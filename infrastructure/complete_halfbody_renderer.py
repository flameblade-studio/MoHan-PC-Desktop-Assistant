"""Render coordinated half-body expressions and preserve displayed mouth state."""
from __future__ import annotations

lazy from collections import OrderedDict
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from application.appearance_ports import AppearanceRenderOptions
lazy from application.appearance_ports import MakeupOverlayPort
lazy from domain.character_runtime import character_rig_manifest
lazy from domain.face_rig import FaceMotionFrame
lazy from domain.qt_image_io import image_from_png, load_pixmap_png
lazy from infrastructure.animated_appearance import AnimatedAppearance
lazy from infrastructure.blink_makeup_composition import paint_blink_makeup
lazy from infrastructure.complete_halfbody_expressions import (
    COMPLETE_CHEEK_POSES, COMPLETE_FRONT_POSES, COMPLETE_POSES,
    EYES, FAMILIES, REQUIRED_COMPLETE_POSES, CompleteHalfbodyFrames,
    load_complete_halfbody_frames,
)

# Keep a full set of current and queued endpoints across all complete poses.
# These entries hold only cache keys and labels, not image buffers.
MAX_FRAME_CONTEXTS = 2 * len(COMPLETE_POSES) * len(FAMILIES) * len(EYES)
MAX_DECODED_FRAMES = 24
CLOSED_APERTURE = 0.01
_CHEEK_SILHOUETTE = character_rig_manifest().pose_silhouettes["cheek"]
_FRONT_SILHOUETTE = character_rig_manifest().pose_silhouettes["front"]


class CompleteHalfbodyRenderer:
    """Optional whole-frame sources with appearance composed separately.

    Pixmap cache keys identify the displayed endpoint during a speech transition.
    A blink therefore follows that endpoint, even if the next mouth is queued.
    """

    def __init__(
        self, root: Path, overlay: object = None,
        supplement: tuple[Path, Path] | None = None,
        *, complete_root: Path | None = None, require_complete: bool = False,
    ) -> None:
        self._root = root if complete_root is None else complete_root
        self._explicit_complete = complete_root is not None
        self._require_complete = require_complete
        self._loaded = False
        self._assets: CompleteHalfbodyFrames | None = None
        self._appearance = AnimatedAppearance(overlay)
        self._overlay = overlay
        self._supplement = supplement
        self._contexts: OrderedDict[int, tuple[str, str]] = OrderedDict()
        self._pixmaps: OrderedDict[tuple[str, str, str], QPixmap] = OrderedDict()
        self._oral_pixmaps: dict[tuple[str, str], QPixmap] = {}
        if self._explicit_complete:
            self._load()

    def _load(self) -> CompleteHalfbodyFrames | None:
        if not self._loaded:
            self._assets = load_complete_halfbody_frames(self._root)
            if self._explicit_complete and self._assets is None:
                raise FileNotFoundError(f"Missing declared complete half-body manifest: {self._root / 'manifest.json'}")
            if self._require_complete and self._assets is not None:
                missing = REQUIRED_COMPLETE_POSES - set(self._assets.frames)
                if missing:
                    raise ValueError(f"Missing complete half-body poses: {', '.join(sorted(missing))}")
                missing_blinks = REQUIRED_COMPLETE_POSES - self._assets.whole_frame_blinks
                if missing_blinks:
                    raise ValueError(f"Native half-body requires whole-frame blinks: {', '.join(sorted(missing_blinks))}")
            if self._supplement is not None and not self._explicit_complete:
                root, manifest = self._supplement
                additional = load_complete_halfbody_frames(root, manifest_path=manifest)
                if additional is None:
                    raise ValueError("Declared complete half-body supplement is unavailable")
                existing = self._assets
                if existing is None:
                    self._assets = additional
                else:
                    if set(existing.frames) & set(additional.frames):
                        raise ValueError("Complete half-body supplement repeats an existing pose")
                    if set(existing.expressions) & set(additional.expressions):
                        raise ValueError("Complete half-body supplement repeats an existing binding")
                    self._assets = CompleteHalfbodyFrames(
                        frozendict({**existing.frames, **additional.frames}),
                        frozendict({**existing.expressions, **additional.expressions}),
                        frozendict({**existing.oral_masks, **additional.oral_masks}),
                        existing.whole_frame_blinks | additional.whole_frame_blinks,
                    )
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
        emotional_binding = assets.expressions.get(motion.expression)
        if emotional_binding is not None and emotional_binding[0] in COMPLETE_FRONT_POSES:
            # Generic speech mouth names choose only a mouth family. The live
            # emotional expression still owns the brows, eyes and face canvas.
            family = binding[1] if binding is not None else emotional_binding[1]
            binding = emotional_binding[0], family
        if binding is None:
            if self._require_complete:
                raise ValueError(f"Missing native half-body expression: {expression}")
            self._set_active_mouth_state(None, None)
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
        assets = self._load()
        if assets is not None and binding[0] in assets.whole_frame_blinks:
            return endpoint
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

    def has_whole_frame_blink(self, frame: QPixmap) -> bool:
        """Whether this displayed endpoint owns the entire blink frame."""

        binding = self._contexts.get(frame.cacheKey())
        assets = self._load()
        return (
            binding is not None
            and assets is not None
            and binding[0] in assets.whole_frame_blinks
        )

    def _set_active_mouth_state(self, viseme: str | None, oral_mask: QPixmap | None) -> None:
        setter = getattr(self._overlay, "set_active_mouth_state", None)
        if callable(setter):
            setter(viseme, oral_mask)

    def _oral_mask(self, pose: str, family: str) -> QPixmap | None:
        if self._assets is None or family == "neutral":
            return None
        data = self._assets.oral_masks.get(pose, {}).get(family)
        if data is None:
            return None
        key = (pose, family)
        if key not in self._oral_pixmaps:
            image = image_from_png(data)
            if image.isNull():
                raise ValueError(f"Cannot decode complete half-body oral mask: {key}")
            self._oral_pixmaps[key] = QPixmap.fromImage(image)
        return QPixmap(self._oral_pixmaps[key])

    @staticmethod
    def _makeup_view_id(pose: str, eye: str) -> str | None:
        if pose in COMPLETE_FRONT_POSES:
            return pose
        if pose not in COMPLETE_CHEEK_POSES:
            return None
        return pose if eye == "rest" else f"{pose}-{eye}"

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
        if pose in COMPLETE_CHEEK_POSES or pose in COMPLETE_FRONT_POSES:
            viseme = {"neutral": None, "small": "I", "a": "A", "o": "O"}[family]
            self._set_active_mouth_state(viseme, self._oral_mask(pose, family))
        else:
            self._set_active_mouth_state(None, None)
        appearance_view_id = pose
        appearance_declares = getattr(
            self._overlay, "appearance_declares_view", None,
        )
        if pose in COMPLETE_FRONT_POSES:
            appearance_view_id = _FRONT_SILHOUETTE
        elif (
            pose in COMPLETE_CHEEK_POSES
            and callable(appearance_declares)
            and not appearance_declares(pose)
        ):
            appearance_view_id = _CHEEK_SILHOUETTE
        makeup_view_id = self._makeup_view_id(pose, eye)
        declares = getattr(self._overlay, "makeup_declares_view", None)
        if makeup_view_id is not None and (
            not callable(declares) or not declares(makeup_view_id)
        ):
            makeup_view_id = None
        frame = self._appearance.compose(
            self._pixmaps[key], appearance_view_id, lambda _frame: None,
            AppearanceRenderOptions(
                suppress_makeup_slots=frozenset({"eyes"}) if eye != "rest" else frozenset(),
                eye_state=eye,
                makeup_view_id=makeup_view_id,
            ),
        )
        if not base.isNull() and frame.size() != base.size():
            frame = frame.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._remember_context(frame, (pose, family))
        return frame
