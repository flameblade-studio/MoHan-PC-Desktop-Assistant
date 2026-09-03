from __future__ import annotations

lazy from collections.abc import Iterable

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

lazy from domain.companion_animation_contract import (
    BLUSH_PRESERVING_BLINK_EXPRESSIONS,
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    EXPRESSION_BLINK_FRAMES,
    EXPRESSION_DERIVED_VISEME_FRAMES,
    EXPRESSION_EYE_OFFSETS,
    EXPRESSION_FACE_OFFSETS,
    EXPRESSION_MOUTH_OFFSETS,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_EXPRESSIONS,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_SPEECH_MOUTH_RECTS,
    EYES_CLOSED_EXPRESSIONS,
    HAPPY_SPEECH_CLOSED_EXPRESSION,
    SPEAKING_BLINK_PREFIXES,
)
lazy from domain.expression_system import FaceAnchorProfile
lazy from domain.face_rig import EyeState, eye_state_for_blink
lazy from presentation.presentation_resources import resource_path

__all__ = ("CompanionFaceAssetMethods",)

IMPROVEMENT_THRESHOLD = 0.018
MIN_OPAQUE_ALPHA = 180


class CompanionFaceAssetMethods:
    def _render_masked_blink_frame(self, opacity: float) -> QPixmap:
        """Stamp exactly one eyelid authority inside its identity mask."""

        # While speaking, compose over the archived clean speech frame — the
        # exact mouth currently on screen — not a recomposition at the
        # target aperture.  The old recomposition made the mouth jump to
        # its target the instant a blink stamped, then snap back on the
        # next transition tick.
        archived = (
            getattr(self, "speech_visual_pixmap", None)
            if self.state == "speaking"
            else None
        )
        frame = (
            QPixmap(archived)
            if archived is not None and not archived.isNull()
            else self._render_half_body_frame()
        )
        if eye_state_for_blink(opacity) is EyeState.REST:
            return frame
        expression = self.current_expression
        if self.state == "speaking":
            expression = (
                self.speech_gesture_expression
                or getattr(self, "speech_current_expression", None)
                or expression
            )
        return self._blink_composite(frame, str(expression), opacity)

    def _idle_expression(self) -> str:
        if self.idle_pose == "lean":
            return "idle_lean"
        if self.idle_pose == "front":
            return "idle_front"
        return "idle"

    def _speaking_expression(self) -> str:
        if self.idle_pose == "lean":
            return "speaking_lean"
        if self.idle_pose == "front":
            return "speaking_front"
        return "speaking"

    def _mouth_mid_expression(self) -> str:
        if self.idle_pose == "lean":
            return "mouth_mid_lean"
        if self.idle_pose == "front":
            return "mouth_mid_front"
        return "mouth_mid"

    def _closed_speech_expression(self) -> str:
        if self.idle_pose == "cheek":
            return CHEEK_SPEECH_CLOSED_EXPRESSION
        return self._idle_expression()

    def _build_mouth_frames(self) -> None:
        self.presentation_ports.validate_face_assets(
            resource_path("assets/expressions")
        )
        mouth_clips = self._mouth_clip_regions()
        self.mouth_clips = mouth_clips
        self._build_speech_mouth_masks(mouth_clips)
        self._build_cheek_neutral_speech_frame()
        self._build_gesture_mouth_masks()
        blink_regions = self._blink_regions()
        self._build_blink_masks(blink_regions)
        self._build_face_parallax_cutouts(
            blink_regions,
            mouth_clips,
        )
        self._normalize_base_speech_frames()
        self._build_pose_viseme_frames(mouth_clips)
        self._build_happy_neutral_speech_frames()
        self._build_derived_expression_visemes()
        self._build_expression_anchor_profiles()
        self._build_expression_eye_layers()

    @staticmethod
    def _mouth_clip_regions() -> frozendict[str, QRect]:
        return frozendict({
            "": QRect(168, 195, 64, 40),
            "_lean": QRect(158, 194, 62, 42),
            "_front": QRect(206, 199, 54, 35),
        })

    @staticmethod
    def _soft_rounded_mask(
        regions: Iterable[QRect],
        alpha_steps: tuple[tuple[int, int], ...],
        radius: int,
    ) -> QPixmap:
        mask = QPixmap(465, 465)
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        for region in regions:
            for inset, alpha in alpha_steps:
                painter.setBrush(QColor(255, 255, 255, alpha))
                painter.drawRoundedRect(
                    region.adjusted(inset, inset, -inset, -inset),
                    radius,
                    radius,
                )
        painter.end()
        return mask

    def _build_speech_mouth_masks(
        self,
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        alpha_steps = (
            (0, 52),
            (1, 82),
            (2, 128),
            (3, 255),
        )
        self.mouth_masks = {
            suffix: self._soft_rounded_mask(
                (mouth_clip,),
                alpha_steps,
                9,
            )
            for suffix, mouth_clip in mouth_clips.items()
        }
        self.viseme_mouth_masks = dict(self.mouth_masks)

    def _build_cheek_neutral_speech_frame(self) -> None:
        cheek_idle = self.expression_pixmaps["idle"]
        cheek_neutral = QPixmap(cheek_idle)
        self.expression_pixmaps[CHEEK_SPEECH_CLOSED_EXPRESSION] = cheek_neutral
        self.physics_expression_poses[CHEEK_SPEECH_CLOSED_EXPRESSION] = "cheek"

    def _build_gesture_mouth_masks(self) -> None:
        alpha_steps = (
            (0, 48),
            (1, 80),
            (2, 132),
            (3, 210),
            (4, 255),
        )
        self.gesture_mouth_masks = {
            expression: self._soft_rounded_mask(
                (mouth_rect,),
                alpha_steps,
                9,
            )
            for expression, mouth_rect in (EXPRESSION_SPEECH_MOUTH_RECTS.items())
        }

    def _build_derived_expression_visemes(self) -> None:
        for expression in EXPRESSION_SPEECH_EXPRESSIONS:
            closed = self.expression_pixmaps[
                HAPPY_SPEECH_CLOSED_EXPRESSION if expression == "happy" else expression
            ]
            source_frames = EXPRESSION_SPEECH_FRAMES[expression]
            for vowel, source_key, opacity in (
                ("I", "mid", 0.68),
                ("U", "round", 0.64),
            ):
                derived = QPixmap(closed)
                painter = QPainter(derived)
                painter.setOpacity(opacity)
                painter.drawPixmap(
                    0,
                    0,
                    self._masked_region(
                        self.expression_pixmaps[source_frames[source_key]],
                        self.gesture_mouth_masks[expression],
                    ),
                )
                painter.end()
                derived_name = EXPRESSION_DERIVED_VISEME_FRAMES[expression][vowel]
                self.expression_pixmaps[derived_name] = derived

    @staticmethod
    def _blink_regions() -> frozendict[str, tuple[QRect, QRect]]:
        return frozendict({
            "cheek": (
                QRect(160, 153, 55, 34),
                QRect(198, 153, 61, 34),
            ),
            "lean": (
                QRect(153, 153, 55, 34),
                QRect(191, 153, 61, 34),
            ),
            "front": (
                QRect(180, 153, 53, 34),
                QRect(220, 153, 56, 34),
            ),
        })

    def _build_blink_masks(
        self,
        blink_regions: frozendict[str, tuple[QRect, QRect]],
    ) -> None:
        alpha_steps = (
            (0, 42),
            (1, 76),
            (2, 132),
            (3, 255),
        )
        self.blink_masks = {
            pose: self._soft_rounded_mask(
                regions,
                alpha_steps,
                10,
            )
            for pose, regions in blink_regions.items()
        }
        self.blush_blink_masks = {
            pose: self._soft_rounded_mask(
                tuple(region.adjusted(0, 0, 0, -12) for region in regions),
                alpha_steps,
                8,
            )
            for pose, regions in blink_regions.items()
        }
        self.wink_masks = {
            pose: self._soft_rounded_mask(
                (regions[1].adjusted(0, 0, 0, -12),),
                alpha_steps,
                8,
            )
            for pose, regions in blink_regions.items()
        }
        self.dedicated_blink_regions = blink_regions
        self.dedicated_blink_masks = self.blink_masks

    def _build_face_parallax_cutouts(
        self,
        blink_regions: frozendict[str, tuple[QRect, QRect]],
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        self.face_parallax_cutouts = {}
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            left_eye, right_eye = blink_regions[pose]
            cutouts = (
                left_eye.adjusted(-5, -4, 5, 4),
                right_eye.adjusted(-5, -4, 5, 4),
                mouth_clips[suffix].adjusted(-7, -6, 7, 6),
            )
            source = QPixmap(465, 465)
            source.fill(Qt.transparent)
            painter = QPainter(source)
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.drawPixmap(0, 0, self.face_sources[pose])
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.transparent)
            for region in cutouts:
                painter.drawRoundedRect(region, 11, 11)
            painter.end()
            self.face_sources[pose] = source
            self.face_parallax_cutouts[pose] = cutouts

    def _normalize_base_speech_frames(self) -> None:
        for closed_name, open_name, mid_name in (
            ("idle", "speaking", "mouth_mid"),
            ("idle_lean", "speaking_lean", "mouth_mid_lean"),
            ("idle_front", "speaking_front", "mouth_mid_front"),
        ):
            closed = self.expression_pixmaps[
                CHEEK_SPEECH_CLOSED_EXPRESSION if closed_name == "idle" else closed_name
            ]
            suffix = closed_name.removeprefix("idle")
            self.expression_pixmaps[open_name] = self._compose_mouth_only(
                closed,
                self.expression_pixmaps[open_name],
                suffix,
            )
            mid_source = self.expression_pixmaps[
                "viseme_mid_front" if suffix == "_front" else f"viseme_i{suffix}"
            ]
            self.expression_pixmaps[mid_name] = self._compose_mouth_only(
                closed,
                mid_source,
                suffix,
            )

    def _compose_mouth_only(
        self,
        closed: QPixmap,
        source: QPixmap,
        suffix: str,
    ) -> QPixmap:
        normalized = QPixmap(closed)
        painter = QPainter(normalized)
        painter.drawPixmap(
            0,
            0,
            self._masked_region(
                source,
                self.viseme_mouth_masks[suffix],
            ),
        )
        painter.end()
        return normalized

    def _build_pose_viseme_frames(
        self,
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        for suffix in mouth_clips:
            closed = self.expression_pixmaps[
                CHEEK_SPEECH_CLOSED_EXPRESSION if suffix == "" else f"idle{suffix}"
            ]
            opened = self.expression_pixmaps[f"speaking{suffix}"]
            source_frames = (
                (
                    "mouth_wide",
                    self.expression_pixmaps.get(
                        f"viseme_wide{suffix}",
                        opened,
                    ),
                ),
                (
                    "mouth_round",
                    self.expression_pixmaps[f"viseme_round{suffix}"],
                ),
                ("mouth_i", self.expression_pixmaps[f"viseme_i{suffix}"]),
                ("mouth_o", self.expression_pixmaps[f"viseme_o{suffix}"]),
            )
            if suffix == "_front":
                self.expression_pixmaps["mouth_mid_front"] = self._compose_mouth_only(
                    closed,
                    self.expression_pixmaps["viseme_mid_front"],
                    suffix,
                )
            for frame_prefix, source in source_frames:
                self.expression_pixmaps[f"{frame_prefix}{suffix}"] = (
                    self._compose_mouth_only(
                        closed,
                        source,
                        suffix,
                    )
                )
            self._build_blink_viseme_frames(suffix)

    def _build_happy_neutral_speech_frames(self) -> None:
        """Keep smiling eyes while every speaking mouth returns to neutral."""
        expression = "happy"
        mouth_mask = self.gesture_mouth_masks[expression]
        neutral_closed = self.expression_pixmaps[CHEEK_SPEECH_CLOSED_EXPRESSION]
        happy_closed = QPixmap(self.expression_pixmaps[expression])
        painter = QPainter(happy_closed)
        painter.drawPixmap(
            0,
            0,
            self._masked_region(neutral_closed, mouth_mask),
        )
        painter.end()
        self.expression_pixmaps[HAPPY_SPEECH_CLOSED_EXPRESSION] = happy_closed
        self.physics_expression_poses[HAPPY_SPEECH_CLOSED_EXPRESSION] = "cheek"

        neutral_sources = {
            "mid": self.expression_pixmaps["mouth_mid"],
            "open": self.expression_pixmaps["speaking"],
            "round": self.expression_pixmaps["mouth_round"],
        }
        for frame, source in neutral_sources.items():
            speech_frame = QPixmap(happy_closed)
            painter = QPainter(speech_frame)
            painter.drawPixmap(
                0,
                0,
                self._masked_region(source, mouth_mask),
            )
            painter.end()
            self.expression_pixmaps[EXPRESSION_SPEECH_FRAMES[expression][frame]] = (
                speech_frame
            )

    def _build_blink_viseme_frames(self, suffix: str) -> None:
        blink = self.expression_pixmaps[f"blink{suffix}"]
        frame_names = (
            (f"mouth_mid{suffix}", f"blink_mid{suffix}"),
            (f"speaking{suffix}", f"blink_open{suffix}"),
            (f"mouth_wide{suffix}", f"blink_wide{suffix}"),
            (f"mouth_round{suffix}", f"blink_round{suffix}"),
            (f"mouth_i{suffix}", f"blink_i{suffix}"),
            (f"mouth_o{suffix}", f"blink_o{suffix}"),
        )
        for mouth_name, result_name in frame_names:
            combined = QPixmap(blink.size())
            combined.fill(Qt.transparent)
            painter = QPainter(combined)
            painter.drawPixmap(0, 0, blink)
            painter.drawPixmap(
                0,
                0,
                self._masked_mouth_patch(
                    self.expression_pixmaps[mouth_name],
                    suffix,
                ),
            )
            painter.end()
            self.expression_pixmaps[result_name] = combined

    def _masked_mouth_patch(
        self,
        source: QPixmap,
        suffix: str,
        target_expression: str | None = None,
        source_already_aligned: bool = False,
    ) -> QPixmap:
        offset_x, offset_y = self._expression_mouth_offset(target_expression)
        mask = self.mouth_masks[suffix]
        if source_already_aligned and (offset_x or offset_y):
            mask = self._translated_pixmap(mask, offset_x, offset_y)
        patch = QPixmap(source.size())
        patch.fill(Qt.transparent)
        painter = QPainter(patch)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        if (
            not source_already_aligned
            and target_expression is not None
            and (offset_x or offset_y)
        ):
            patch = self._translated_pixmap(
                patch,
                offset_x,
                offset_y,
            )
        return patch

    def _build_expression_anchor_profiles(self) -> None:
        """Register a measured facial alignment profile for every expression."""
        base_expressions = {
            "cheek": "idle",
            "lean": "idle_lean",
            "front": "idle_front",
        }
        face_regions = {
            "cheek": QRect(125, 92, 165, 165),
            "lean": QRect(120, 92, 165, 165),
            "front": QRect(150, 88, 165, 170),
        }
        profiles: dict[str, FaceAnchorProfile] = {}
        for expression, pose in self.physics_expression_poses.items():
            if expression not in self.expression_pixmaps:
                continue
            if expression == base_expressions[pose] or expression.startswith((
                "speaking",
                "mouth_",
                "blink",
                "viseme_",
            )):
                profiles[expression] = FaceAnchorProfile(
                    pose,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    1.0,
                    0.0,
                )
                continue
            offset_x, offset_y = EXPRESSION_FACE_OFFSETS.get(
                expression,
                (0, 0),
            )
            profiles[expression] = FaceAnchorProfile(
                pose,
                offset_x,
                offset_y,
                *EXPRESSION_EYE_OFFSETS.get(expression, (offset_x, offset_y)),
                *EXPRESSION_MOUTH_OFFSETS.get(
                    expression,
                    (offset_x, offset_y),
                ),
                1.0 if expression in EXPRESSION_FACE_OFFSETS else 0.0,
                0.0,
            )
        self.expression_anchor_profiles = profiles
        self.expression_anchor_base_expressions = base_expressions
        self.expression_anchor_face_regions = face_regions

    @staticmethod
    def _estimate_face_offset(
        base: QPixmap,
        target: QPixmap,
        region: QRect,
    ) -> tuple[int, int, float, float]:
        base_image = base.toImage()
        target_image = target.toImage()
        zero_score = CompanionFaceAssetMethods._face_offset_candidate_score(
            base_image,
            target_image,
            region,
            0,
            0,
        )
        best_x = 0
        best_y = 0
        best_score = zero_score
        for offset_y in range(-6, 7):
            for offset_x in range(-6, 7):
                score = CompanionFaceAssetMethods._face_offset_candidate_score(
                    base_image,
                    target_image,
                    region,
                    offset_x,
                    offset_y,
                )
                if score < best_score:
                    best_x = offset_x
                    best_y = offset_y
                    best_score = score
        improvement = (
            0.0
            if zero_score <= 0.0
            else max(0.0, (zero_score - best_score) / zero_score)
        )
        if improvement < IMPROVEMENT_THRESHOLD:
            best_x = 0
            best_y = 0
        confidence = min(1.0, improvement / 0.16)
        return best_x, best_y, confidence, best_score

    @staticmethod
    def _face_offset_candidate_score(
        base: QImage,
        target: QImage,
        region: QRect,
        offset_x: int,
        offset_y: int,
    ) -> float:
        difference = 0
        samples = 0
        for y in range(region.top(), region.bottom() + 1, 5):
            target_y = y + offset_y
            if target_y < 0 or target_y >= target.height():
                continue
            for x in range(region.left(), region.right() + 1, 5):
                target_x = x + offset_x
                if target_x < 0 or target_x >= target.width():
                    continue
                pixel_difference = CompanionFaceAssetMethods._opaque_pixel_difference(
                    base.pixel(x, y),
                    target.pixel(target_x, target_y),
                )
                if pixel_difference is None:
                    continue
                difference += pixel_difference
                samples += 1
        return difference / max(1, samples)

    @staticmethod
    def _opaque_pixel_difference(
        first: int,
        second: int,
    ) -> int | None:
        alpha_first = (first >> 24) & 0xFF
        alpha_second = (second >> 24) & 0xFF
        if alpha_first < MIN_OPAQUE_ALPHA or alpha_second < MIN_OPAQUE_ALPHA:
            return None
        return (
            abs(((first >> 16) & 0xFF) - ((second >> 16) & 0xFF))
            + abs(((first >> 8) & 0xFF) - ((second >> 8) & 0xFF))
            + abs((first & 0xFF) - (second & 0xFF))
        )

    def _expression_face_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(expression or "")
        if profile is None:
            return 0, 0
        return profile.offset_x, profile.offset_y

    def _expression_eye_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(expression or "")
        if profile is None:
            return 0, 0
        return profile.eye_offset_x, profile.eye_offset_y

    def _expression_mouth_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(expression or "")
        if profile is None:
            return 0, 0
        return profile.mouth_offset_x, profile.mouth_offset_y

    @staticmethod
    def _translated_pixmap(
        source: QPixmap,
        offset_x: int,
        offset_y: int,
    ) -> QPixmap:
        translated = QPixmap(source.size())
        translated.fill(Qt.transparent)
        painter = QPainter(translated)
        painter.drawPixmap(offset_x, offset_y, source)
        painter.end()
        return translated

    def _build_expression_eye_layers(self) -> None:
        """Match the tracking layer to every mouth frame.

        The cheek speaking frame has slightly different eye registration from
        its idle frame. Reusing an idle eye patch over rapidly changing mouth
        frames makes the whole eye area appear to wobble intermittently.
        """
        self.expression_eye_sources = {}
        self.expression_face_sources = {}
        self.expression_physics_sources = {}
        for expression, pose in self.physics_expression_poses.items():
            expression_source = self.expression_pixmaps.get(expression)
            if expression_source is None:
                continue
            offset_x, offset_y = self._expression_eye_offset(expression)
            eye_alpha = self._translated_pixmap(
                self.eye_sources[pose],
                offset_x,
                offset_y,
            )
            face_offset_x, face_offset_y = self._expression_face_offset(expression)
            face_alpha = self._translated_pixmap(
                self.face_sources[pose],
                face_offset_x,
                face_offset_y,
            )
            self.expression_eye_sources[expression] = self._masked_region(
                expression_source,
                eye_alpha,
            )
            self.expression_face_sources[expression] = self._masked_region(
                expression_source,
                face_alpha,
            )
            self.expression_physics_sources[expression] = {
                "ornament": QPixmap(self.physics_sources[pose]),
                "hair_left": QPixmap(self.hair_sources[pose]["left"]),
                "hair_right": QPixmap(self.hair_sources[pose]["right"]),
                "sleeve_left": QPixmap(self.sleeve_sources[pose]["left"]),
                "sleeve_right": QPixmap(self.sleeve_sources[pose]["right"]),
            }

    @staticmethod
    def _masked_region(source: QPixmap, alpha_source: QPixmap) -> QPixmap:
        """Extract a matching local layer from the expression itself."""
        layer = QPixmap(source.size())
        layer.fill(Qt.transparent)
        painter = QPainter(layer)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, alpha_source)
        painter.end()
        return layer

    def _render_base_expression(self) -> str:
        """Return the emotional base currently visible under transient layers."""
        if (
            self.state == "speaking"
            and self.speech_gesture_expression in self.expression_pixmaps
        ):
            return self.speech_gesture_expression
        if (
            self.state == "speaking"
            and self.speech_closed_expression in self.expression_pixmaps
        ):
            return self.speech_closed_expression
        return self.current_expression

    def _local_physics_source(
        self,
        part: str,
        fallback: QPixmap,
    ) -> QPixmap:
        return self.expression_physics_sources.get(
            self._render_base_expression(),
            {},
        ).get(part, fallback)

    def _blink_expression(self) -> str:
        if self.idle_pose == "lean":
            return "blink_lean"
        if self.idle_pose == "front":
            return "blink_front"
        return "blink"

    def _speaking_blink_expression(self) -> str:
        suffix = self._active_speech_pose_suffix()
        current = self.speech_current_expression
        blink_prefix = next(
            (
                blink
                for mouth, blink in SPEAKING_BLINK_PREFIXES
                if current.startswith(mouth)
            ),
            "blink",
        )
        return f"{blink_prefix}{suffix}"

    @staticmethod
    def _pose_suffix(pose: str) -> str:
        return "_lean" if pose == "lean" else "_front" if pose == "front" else ""

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
        if base_expression in EXPRESSION_POSES and not is_expression_speech:
            return QPixmap(base_pixmap)
        pose = self.physics_expression_poses.get(
            base_expression,
            getattr(self, "active_physics_pose", "front"),
        )
        suffix = self._pose_suffix(pose)
        offset_x, offset_y = self._expression_eye_offset(base_expression)
        dedicated_blink = EXPRESSION_BLINK_FRAMES.get(base_expression)
        if eye_state is EyeState.HALF:
            # A semantic HALF state is not permission to blend REST and CLOSED
            # authority portraits. Use a dedicated registered half-eye source
            # when one is authored. If it is absent, keep the REST authority
            # untouched: the visual acceptance contract forbids substituting
            # CLOSED for a partial value, which reads as a premature blink.
            half_key = (
                f"{dedicated_blink}_half"
                if dedicated_blink is not None
                else f"blink_half{suffix}"
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
            blink_patch = self._masked_region(
                blink_source,
                self.blush_blink_masks[pose]
                if base_expression in BLUSH_PRESERVING_BLINK_EXPRESSIONS
                else self.blink_masks[pose],
            )
        if dedicated_blink is None and (offset_x or offset_y):
            blink_patch = self._translated_pixmap(
                blink_patch,
                offset_x,
                offset_y,
            )
        return self.face_renderer.render_overlay(
            base_pixmap,
            blink_patch,
            # Never alpha-crossfade two eye authorities.
            opacity=1.0,
        )

    def _wink_composite(
        self,
        base_pixmap: QPixmap,
        base_expression: str,
        opacity: float = 1.0,
    ) -> QPixmap:
        """Close one eye without replacing the surrounding expression."""
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

    def _masked_eye_patch(self, source: QPixmap, pose: str) -> QPixmap:
        return self._masked_region(source, self.blink_masks[pose])

    def _active_speech_pose_suffix(self) -> str:
        if self.state == "speaking":
            if self.speech_closed_expression.endswith("_lean"):
                return "_lean"
            if self.speech_closed_expression.endswith("_front"):
                return "_front"
            if self.speech_closed_expression == "idle":
                return ""
            return self.speech_pose_suffix
        return (
            "_lean"
            if self.idle_pose == "lean"
            else "_front"
            if self.idle_pose == "front"
            else ""
        )
