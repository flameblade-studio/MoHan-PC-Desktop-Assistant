"""Complete-expression frame selection and source-bound head replacement.

Split out of ``layered_full_body_renderer`` so the parametric renderer stays
inside the layer-module line ratchet.  ``LayeredFullBodyRenderer`` mixes these
methods back in unchanged; they rely on its ``_cached_pixmap`` and
``_static_base_composite`` helpers.
"""

from __future__ import annotations

lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_rig import FaceMotionFrame, Viseme, eye_state_for_blink
lazy from infrastructure.layered_full_body_assets import (
    COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
    CompleteExpressionFrameSet,
    LayeredFullBodyView,
)

MOUTH_APERTURE_THRESHOLD = 0.01
COMPLETE_EXPRESSION_NEUTRAL_POSE_ID = "front-crossed"


class CompleteExpressionRendering:
    """Resolve and composite authored complete-expression frames."""

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
            CompleteExpressionRendering._is_neutral_hand(hand)
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
