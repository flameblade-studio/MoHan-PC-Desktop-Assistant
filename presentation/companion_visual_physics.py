from __future__ import annotations

lazy import math

lazy from PySide6.QtCore import QPoint, QRect, Qt, QTimer
lazy from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
lazy from PySide6.QtWidgets import QLabel, QWidget

lazy from domain.companion_animation_contract import (
    EXPRESSION_BLINK_FRAMES,
    EXPRESSION_DERIVED_VISEME_FRAMES,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_FRAMES,
    PHYSICS_POSE_SUFFIXES,
    PHYSICS_SPEECH_FRAME_PREFIXES,
)
lazy from presentation.presentation_resources import resource_path

__all__ = ("CompanionVisualPhysicsMethods",)


class CompanionVisualPhysicsMethods:
    def _build_physics_overlay_widgets(self, root: QWidget) -> None:
        self.sleeve_left_overlay = QLabel(root)
        self.sleeve_right_overlay = QLabel(root)
        self.hair_left_overlay = QLabel(root)
        self.hair_right_overlay = QLabel(root)
        for overlay in (
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
        ):
            self._configure_character_overlay(overlay)
        self.physics_overlay = QLabel(root)
        self._configure_character_overlay(self.physics_overlay)

    def _initialize_physics_animation(self) -> None:
        self._reset_physics_dynamics()
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self._physics_tick)
        self.physics_timer.start(33)

    def _physics_enabled(self, key: str) -> bool:
        return bool(self.physics_features.get(key, True))

    def _reload_physics_settings(self) -> None:
        for key in tuple(self.physics_features):
            self.physics_features[key] = bool(self.db.setting(key, True))
        self._apply_physics_visibility()
        self._render_attention_layers(force=True)

    def _apply_physics_visibility(self, expression: str | None = None) -> None:
        if not hasattr(self, "physics_overlay"):
            return
        if getattr(self, "_adaptive_full_body_active", False):
            # A published v4 full-body frame already includes sleeves, hair and
            # ornament.  Keep these legacy layers hidden until legacy rendering
            # takes the canvas back over.
            self.sleeve_left_overlay.hide()
            self.sleeve_right_overlay.hide()
            self.hair_left_overlay.hide()
            self.hair_right_overlay.hide()
            self.physics_overlay.hide()
            return
        pose_supported = (
            expression
            if expression is not None
            else getattr(self, "current_expression", "")
        ) in getattr(self, "physics_expression_poses", {})
        self.sleeve_left_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_sleeves")
        )
        self.sleeve_right_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_sleeves")
        )
        self.hair_left_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_hair")
        )
        self.hair_right_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_hair")
        )
        self.physics_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_ornament")
        )

    def _build_physics_layers(self) -> None:
        self._reset_physics_dynamics()
        self.active_physics_pose = "front"
        self.physics_anchors = self._ornament_anchors()
        self.hair_anchors = self._hair_anchors()
        self.sleeve_anchors = self._sleeve_anchors()
        self.physics_sources: dict[str, QPixmap] = {}
        self.hair_sources: dict[str, dict[str, QPixmap]] = {}
        self.sleeve_sources: dict[str, dict[str, QPixmap]] = {}
        self._load_physics_sources()
        self.physics_expression_poses = self._physics_expression_pose_map()

    def _reset_physics_dynamics(self) -> None:
        self.physics_phase = 0
        self.ornament_angle = 0.0
        self.ornament_velocity = 0.0
        self.hair_left_angle = 0.0
        self.hair_right_angle = 0.0
        self.hair_left_velocity = 0.0
        self.hair_right_velocity = 0.0
        self.sleeve_left_angle = 0.0
        self.sleeve_right_angle = 0.0
        self.sleeve_left_velocity = 0.0
        self.sleeve_right_velocity = 0.0
        self.current_breath = 0.0
        self.last_rendered_ornament_angle = 99.0
        self.last_rendered_hair_angles = (99.0, 99.0)
        self.last_rendered_sleeves = (99.0, 99.0, 99.0)

    @staticmethod
    def _ornament_anchors() -> frozendict:
        return frozendict({
            "cheek": QPoint(315, 96),
            "lean": QPoint(306, 96),
            "front": QPoint(293, 72),
        })

    @staticmethod
    def _hair_anchors() -> frozendict:
        return frozendict({
            "cheek": frozendict({
                "left": QPoint(187, 178),
                "right": QPoint(268, 168),
            }),
            "lean": frozendict({
                "left": QPoint(177, 174),
                "right": QPoint(254, 162),
            }),
            "front": frozendict({
                "left": QPoint(183, 171),
                "right": QPoint(278, 168),
            }),
        })

    @staticmethod
    def _sleeve_anchors() -> frozendict:
        return frozendict({
            "cheek": frozendict({
                "left": QPoint(132, 253),
                "right": QPoint(330, 239),
            }),
            "lean": frozendict({
                "left": QPoint(130, 252),
                "right": QPoint(326, 239),
            }),
            "front": frozendict({
                "left": QPoint(131, 253),
                "right": QPoint(333, 253),
            }),
        })

    def _load_physics_sources(self) -> None:
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            self.physics_sources[pose] = self._scaled_expression_asset(
                f"v120_ornament{suffix}.png"
            )
            self.hair_sources[pose] = {}
            self.sleeve_sources[pose] = {}
            for side in ("left", "right"):
                hair = self._scaled_expression_asset(f"v120_hair_{side}{suffix}.png")
                self.hair_sources[pose][side] = self._hair_texture_only(hair)
                sleeve = self._scaled_expression_asset(
                    f"v120_sleeve_{side}{suffix}.png"
                )
                self.sleeve_sources[pose][side] = self._sleeve_texture_only(
                    sleeve, side
                )

    @staticmethod
    def _scaled_expression_asset(filename: str) -> QPixmap:
        source = QPixmap(str(resource_path(f"assets/expressions/{filename}")))
        return source.scaled(
            465,
            465,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def _physics_expression_pose_map(self) -> dict[str, str]:
        pose_map = {
            **{f"{prefix}{suffix}": pose for prefix in PHYSICS_SPEECH_FRAME_PREFIXES}
            for suffix, pose in PHYSICS_POSE_SUFFIXES
        }
        for expression, pose in EXPRESSION_POSES.items():
            self._register_expression_pose_frames(
                pose_map,
                expression,
                pose,
            )
        return pose_map

    def _register_expression_pose_frames(
        self,
        pose_map: dict[str, str],
        expression: str,
        pose: str,
    ) -> None:
        if expression in self.expression_pixmaps:
            pose_map[expression] = pose
        for frame in EXPRESSION_SPEECH_FRAMES[expression].values():
            if frame in self.expression_pixmaps:
                pose_map[frame] = pose
        for frame in EXPRESSION_DERIVED_VISEME_FRAMES[expression].values():
            pose_map[frame] = pose
        blink_frame = EXPRESSION_BLINK_FRAMES.get(expression)
        if blink_frame is not None and blink_frame in self.expression_pixmaps:
            pose_map[blink_frame] = pose

    @staticmethod
    def _hair_texture_only(source: QPixmap) -> QPixmap:
        """Remove skin and clothing accidentally carried by a hair cutout.

        Rotating a complete cutout that contains cheek, neck or sleeve pixels
        produces dark seams across the face. Hair physics only needs the dark,
        low-chroma strands; all other opaque pixels are made transparent.
        """
        safe = QPixmap(source)
        mask = QPixmap(source.size())
        mask.fill(Qt.transparent)
        gradient = QLinearGradient(0, 278, 0, 318)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 255))
        painter = QPainter(mask)
        painter.fillRect(
            QRect(0, 278, source.width(), source.height() - 278),
            gradient,
        )
        painter.end()
        painter = QPainter(safe)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        return safe

    @staticmethod
    def _sleeve_texture_only(source: QPixmap, side: str) -> QPixmap:
        """Keep only outer blue fabric so hands and hair never ghost."""
        safe = QPixmap(source)
        mask = QPixmap(source.size())
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        if side == "left":
            gradient = QLinearGradient(145, 0, 175, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRect(0, 0, 175, source.height()), gradient)
        else:
            gradient = QLinearGradient(290, 0, 320, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 255))
            painter.fillRect(
                QRect(290, 0, source.width() - 290, source.height()),
                gradient,
            )
        painter.end()
        painter = QPainter(safe)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        return safe

    def _update_physics_pose(self, expression: str) -> None:
        pose = self.physics_expression_poses.get(expression)
        if pose is None:
            if hasattr(self, "physics_overlay"):
                self.physics_overlay.hide()
                self.hair_left_overlay.hide()
                self.hair_right_overlay.hide()
                self.sleeve_left_overlay.hide()
                self.sleeve_right_overlay.hide()
            return
        pose_changed = getattr(self, "active_physics_pose", None) != pose
        self.active_physics_pose = pose
        if hasattr(self, "physics_overlay"):
            self._apply_physics_visibility(expression)
            if pose_changed:
                self.ornament_velocity += (
                    0.45 if pose == "lean" else -0.35 if pose == "front" else 0.25
                )
                self.hair_left_velocity += 0.12 if pose == "lean" else -0.09
                self.hair_right_velocity += -0.1 if pose == "lean" else 0.08
                self.sleeve_left_velocity += 0.035 if pose == "lean" else -0.025
                self.sleeve_right_velocity += -0.03 if pose == "lean" else 0.022
            self._render_sleeve_layers(force=True)
            self._render_hair_layers(force=True)
            self._render_physics_layer(force=True)

    def _physics_tick(self) -> None:
        if not hasattr(self, "physics_overlay"):
            return
        if not any(
            self._physics_enabled(key)
            for key in (
                "physics_sleeves",
                "physics_hair",
                "physics_ornament",
            )
        ):
            return
        self.physics_phase = (self.physics_phase + 1) % 3600
        ambient = math.sin(self.physics_phase * math.tau / 190.0) * 0.38
        voice_motion = (
            (self.viseme_dynamics.smoothed_level - 0.18) * 0.75
            if self.state == "speaking"
            else 0.0
        )
        target = ambient + voice_motion
        acceleration = (
            target - self.ornament_angle
        ) * 0.085 - self.ornament_velocity * 0.16
        self.ornament_velocity += acceleration
        self.ornament_angle = max(
            -1.15,
            min(1.15, self.ornament_angle + self.ornament_velocity),
        )
        left_target = ambient * 0.42 + voice_motion * 0.20
        right_target = -ambient * 0.35 + voice_motion * 0.16
        left_acceleration = (
            left_target - self.hair_left_angle
        ) * 0.032 - self.hair_left_velocity * 0.105
        right_acceleration = (
            right_target - self.hair_right_angle
        ) * 0.038 - self.hair_right_velocity * 0.115
        self.hair_left_velocity += left_acceleration
        self.hair_right_velocity += right_acceleration
        self.hair_left_angle = max(
            -0.34,
            min(0.34, self.hair_left_angle + self.hair_left_velocity),
        )
        self.hair_right_angle = max(
            -0.32,
            min(0.32, self.hair_right_angle + self.hair_right_velocity),
        )
        breath_wave = math.sin(self.physics_phase * math.tau / 145.0)
        if self.state == "speaking":
            self.current_breath = max(
                0.0,
                min(
                    1.0,
                    self.viseme_dynamics.smoothed_level * 0.72 + 0.18,
                ),
            )
        sleeve_voice = voice_motion * 0.055
        sleeve_left_target = breath_wave * 0.075 + sleeve_voice
        sleeve_right_target = -breath_wave * 0.065 - sleeve_voice * 0.82
        self.sleeve_left_velocity += (
            sleeve_left_target - self.sleeve_left_angle
        ) * 0.020 - self.sleeve_left_velocity * 0.12
        self.sleeve_right_velocity += (
            sleeve_right_target - self.sleeve_right_angle
        ) * 0.022 - self.sleeve_right_velocity * 0.125
        self.sleeve_left_angle = max(
            -0.16,
            min(0.16, self.sleeve_left_angle + self.sleeve_left_velocity),
        )
        self.sleeve_right_angle = max(
            -0.15,
            min(0.15, self.sleeve_right_angle + self.sleeve_right_velocity),
        )
        self._render_sleeve_layers()
        self._render_hair_layers()
        self._render_physics_layer()

    def _render_sleeve_layers(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_sleeves"):
            self.sleeve_left_overlay.hide()
            self.sleeve_right_overlay.hide()
            return
        breath_lift = max(0.0, min(1.0, self.current_breath)) * 0.65 + (
            self.viseme_dynamics.smoothed_level * 0.35
            if self.state == "speaking"
            else 0.0
        )
        current = (
            self.sleeve_left_angle,
            self.sleeve_right_angle,
            breath_lift,
        )
        previous = self.last_rendered_sleeves
        if (
            not force
            and abs(current[0] - previous[0]) < 0.012
            and abs(current[1] - previous[1]) < 0.012
            and abs(current[2] - previous[2]) < 0.08
        ):
            return
        pose = getattr(self, "active_physics_pose", "front")
        for side, angle, overlay in (
            ("left", self.sleeve_left_angle, self.sleeve_left_overlay),
            ("right", self.sleeve_right_angle, self.sleeve_right_overlay),
        ):
            source = self._local_physics_source(
                f"sleeve_{side}",
                self.sleeve_sources[pose][side],
            )
            anchor = self.sleeve_anchors[pose][side]
            rendered = QPixmap(source.size())
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.translate(0.0, -breath_lift)
            painter.translate(anchor)
            painter.rotate(angle)
            painter.translate(-anchor)
            painter.drawPixmap(0, 0, source)
            painter.end()
            overlay.setPixmap(rendered)
            overlay.raise_()
        self.hair_left_overlay.raise_()
        self.hair_right_overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_sleeves = current

    def _render_hair_layers(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_hair"):
            self.hair_left_overlay.hide()
            self.hair_right_overlay.hide()
            return
        current = (self.hair_left_angle, self.hair_right_angle)
        previous = self.last_rendered_hair_angles
        if (
            not force
            and abs(current[0] - previous[0]) < 0.025
            and abs(current[1] - previous[1]) < 0.025
        ):
            return
        pose = getattr(self, "active_physics_pose", "front")
        for side, angle, overlay in (
            ("left", self.hair_left_angle, self.hair_left_overlay),
            ("right", self.hair_right_angle, self.hair_right_overlay),
        ):
            source = self._local_physics_source(
                f"hair_{side}",
                self.hair_sources[pose][side],
            )
            anchor = self.hair_anchors[pose][side]
            rendered = QPixmap(source.size())
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.translate(anchor)
            painter.rotate(angle)
            painter.translate(-anchor)
            painter.drawPixmap(0, 0, source)
            painter.end()
            overlay.setPixmap(rendered)
            overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_hair_angles = current

    def _render_physics_layer(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_ornament"):
            self.physics_overlay.hide()
            return
        pose = getattr(self, "active_physics_pose", "front")
        if (
            not force
            and abs(self.ornament_angle - self.last_rendered_ornament_angle) < 0.04
        ):
            return
        source = self._local_physics_source(
            "ornament",
            self.physics_sources[pose],
        )
        anchor = self.physics_anchors[pose]
        rendered = QPixmap(source.size())
        rendered.fill(Qt.transparent)
        painter = QPainter(rendered)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(anchor)
        painter.rotate(self.ornament_angle)
        painter.translate(-anchor)
        painter.drawPixmap(0, 0, source)
        painter.end()
        self.physics_overlay.setPixmap(rendered)
        self.hair_left_overlay.raise_()
        self.hair_right_overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_ornament_angle = self.ornament_angle
