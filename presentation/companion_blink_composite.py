"""Blink and wink compositing for the companion face.

Split out of ``companion_face_assets`` so that module stays inside the
layer-module line ratchet.  ``CompanionFaceAssetMethods`` inherits these
methods unchanged; they rely on its mask, offset and pixmap helpers.
"""

from __future__ import annotations

lazy from PySide6.QtGui import QPixmap

lazy from domain.companion_animation_contract import (
    BLUSH_PRESERVING_BLINK_EXPRESSIONS,
    EXPRESSION_BLINK_FRAMES,
    EXPRESSION_HALF_BLINK_FRAME_SOURCES,
    EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_EXPRESSIONS,
    EYES_CLOSED_EXPRESSIONS,
    outfit_silhouette,
)
lazy from domain.face_rig import EyeState, eye_state_for_blink
lazy from presentation.companion_blink_brow_guard import GUARDED_EXPRESSIONS, preserve_gesture_brows

__all__ = ("CompanionBlinkCompositeMethods",)


class CompanionBlinkCompositeMethods:
    """Compose blink, half-blink and wink endpoints onto a base portrait."""

    def _native_eye_authority_active(self, view_id: str) -> bool:
        """Allow native eye endpoints only for the selected source-bound pose."""
        renderer = getattr(self, "face_renderer", None)
        overlay = getattr(renderer, "_outfit_overlay", None)
        has_native_motion = getattr(overlay, "has_native_motion", None)
        if not callable(has_native_motion):
            return False
        return bool(has_native_motion(view_id))

    def _native_eye_composite(
        self,
        base_pixmap: QPixmap,
        base_expression: str,
        pose: str,
        eye_state: EyeState,
        view_id: str,
    ) -> QPixmap | None:
        """Compose a native eye endpoint only for a source-bound base."""
        if not CompanionBlinkCompositeMethods._native_eye_authority_active(self, view_id):
            return None
        overlay = getattr(self.face_renderer, "_outfit_overlay", None)
        source_key = (
            EXPRESSION_HALF_BLINK_FRAME_SOURCES if eye_state is EyeState.HALF
            else EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES
        ).get(base_expression)
        source = self.expression_pixmaps.get(source_key)
        has_source = source is not None and not source.isNull()
        native_blink = getattr(overlay, "render_native_blink", None)
        if not has_source and not callable(native_blink):
            return QPixmap(base_pixmap)
        if not has_source and base_expression in EXPRESSION_POSES:
            # A complete expression portrait keeps its own features: merely
            # sharing this pose's silhouette is not source authority over it.
            return None
        patch = QPixmap()
        if has_source:
            patch = self._masked_region(source, self.blink_masks[pose])
        return self.face_renderer.render_overlay(
            base_pixmap,
            patch,
            eye_state=eye_state.value,
            view_id=view_id,
            opacity=1.0,
        )

    def _blink_composite(
        self,
        base_pixmap: QPixmap,
        base_expression: str,
        opacity: float = 1.0,
    ) -> QPixmap:
        eye_state = eye_state_for_blink(opacity)
        if eye_state is EyeState.REST:
            return QPixmap(base_pixmap)
        # Emotional portraits are complete, identity-locked illustrations.
        # A neutral eye patch changes their eyelids, brows and face contour,
        # so they stay intact until a dedicated matching blink asset exists.
        if base_expression in EYES_CLOSED_EXPRESSIONS:
            return QPixmap(base_pixmap)
        is_expression_speech = (
            self.state == "speaking"
            and base_expression in EXPRESSION_SPEECH_EXPRESSIONS
        )
        pose = self.physics_expression_poses.get(
            base_expression,
            getattr(self, "active_physics_pose", "front"),
        )
        view_id = outfit_silhouette(base_expression, pose)
        native_result = CompanionBlinkCompositeMethods._native_eye_composite(
            self,
            base_pixmap,
            base_expression,
            pose,
            eye_state,
            view_id,
        )
        if native_result is not None:
            return native_result
        appearance_view_id = view_id
        if base_expression in EXPRESSION_POSES:
            # Its own registered patch is the only eye authority it may stamp.
            # Only the native-eye gate is suppressed; the appearance context is
            # kept so blink makeup still composes (see makeup_view_id).
            view_id = None
            if not is_expression_speech:
                return QPixmap(base_pixmap)
        suffix = self._pose_suffix(pose)
        offset_x, offset_y = self._expression_eye_offset(base_expression)
        dedicated_blink = EXPRESSION_BLINK_FRAMES.get(base_expression)
        bound_source = (
            EXPRESSION_HALF_BLINK_FRAME_SOURCES if eye_state is EyeState.HALF
            else EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES
        ).get(base_expression)
        if (
            dedicated_blink is None
            and bound_source is None
            and base_expression in EXPRESSION_POSES
        ):
            # Contract B: no blink endpoint is bound to THIS expression, so keep
            # the incoming frame; the neutral pose donor is not authority here.
            return QPixmap(base_pixmap)
        if eye_state is EyeState.HALF:
            # A semantic HALF state is not permission to blend REST and CLOSED
            # authority portraits. Use a dedicated registered half-eye source
            # when one is authored. If it is absent, keep the REST authority
            # untouched: the visual acceptance contract forbids substituting
            # CLOSED for a partial value, which reads as a premature blink.
            half_key = (
                f"{dedicated_blink}_half"
                if dedicated_blink is not None
                else (
                    bound_source
                    if bound_source is not None
                    else f"blink_half{suffix}"
                )
            )
            half_source = self.expression_pixmaps.get(half_key)
            if half_source is None or half_source.isNull():
                return QPixmap(base_pixmap)
            if half_source is not None and not half_source.isNull():
                eye_mask = self.blink_masks[pose]
                if offset_x or offset_y:
                    eye_mask = self._translated_pixmap(
                        eye_mask,
                        offset_x,
                        offset_y,
                    )
                half_patch = self._masked_region(half_source, eye_mask)
                return self.face_renderer.render_overlay(
                    base_pixmap,
                    half_patch,
                    eye_state=eye_state.value, view_id=view_id,
                    makeup_view_id=appearance_view_id,
                    opacity=1.0,
                )
        if dedicated_blink is not None:
            blink_source = self.expression_pixmaps[dedicated_blink]
            eye_mask = self.blink_masks[pose]
            if offset_x or offset_y:
                eye_mask = self._translated_pixmap(
                    eye_mask,
                    offset_x,
                    offset_y,
                )
            blink_patch = self._masked_region(blink_source, eye_mask)
        else:
            blink_source = self.expression_pixmaps[f"blink{suffix}"]
            blink_mask = (
                self.blush_blink_masks[pose]
                if base_expression in BLUSH_PRESERVING_BLINK_EXPRESSIONS
                else self.blink_masks[pose]
            )
            blink_patch = self._masked_region(blink_source, blink_mask)
        if dedicated_blink is None and (offset_x or offset_y):
            blink_patch = self._translated_pixmap(
                blink_patch,
                offset_x,
                offset_y,
            )
        if dedicated_blink is None and base_expression in GUARDED_EXPRESSIONS:
            blink_patch = preserve_gesture_brows(
                base_pixmap, blink_patch, blink_patch, expression=base_expression,
            )
        return self.face_renderer.render_overlay(
            base_pixmap,
            blink_patch,
            eye_state=eye_state.value, view_id=view_id,
            makeup_view_id=appearance_view_id,
            # Keep one eye authority active throughout each alpha crossfade.
            opacity=1.0,
        )

    def _wink_composite(
        self,
        base_pixmap: QPixmap,
        base_expression: str,
        opacity: float = 1.0,
    ) -> QPixmap:
        """Close one eye while preserving the surrounding expression."""
        if eye_state_for_blink(opacity) is EyeState.REST:
            return QPixmap(base_pixmap)
        pose = self.physics_expression_poses.get(
            base_expression,
            getattr(self, "active_physics_pose", "front"),
        )
        suffix = self._pose_suffix(pose)
        offset_x, offset_y = self._expression_eye_offset(base_expression)
        mask = self.wink_masks[pose]
        if offset_x or offset_y:
            mask = self._translated_pixmap(mask, offset_x, offset_y)
        patch = self._masked_region(
            self.expression_pixmaps[f"blink{suffix}"],
            mask,
        )
        if offset_x or offset_y:
            patch = self._translated_pixmap(patch, offset_x, offset_y)
        return self.face_renderer.render_overlay(
            base_pixmap,
            patch,
            opacity=1.0,
        )
