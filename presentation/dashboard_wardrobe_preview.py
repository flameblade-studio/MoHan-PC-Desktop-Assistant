"""Wardrobe Pavilion character preview: the composed look through the runtime path.

The preview composes all 24 views of a draggable full-circle turntable through the same
full-body renderer and active-outfit overlay the desktop companion uses, so
what the owner sees in the pavilion is what walks on the desktop: the
selected garment, hairstyle, headwear and makeup at the chosen intensity.

Composites are cached per (appearance signature, view) and rebuilt only when
the selection or makeup state changes.  A first composite takes a moment, so
it runs on a short timer once the preview is on screen. During rotation the
previous frame remains visible with an explicit "composing" line; only the
first composition starts from the bare base. A failed composite falls back
to the bare base and, when a pack is
active, says so in the wardrobe status instead of staying silent.
"""

from __future__ import annotations

lazy from PySide6.QtCore import QTimer, Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
)

lazy from domain.constants import POSE_ATLAS_RELATIVE_ROOT
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from presentation.presentation_resources import resource_path
lazy from presentation.dashboard_artwork import CelestialFrame, SCENE_GROUND_RATIO
lazy from presentation.wardrobe_turntable import WardrobeTurntableLabel

__all__ = (
    "PREVIEW_COMPOSE_DELAY_MS",
    "WARDROBE_PREVIEW_VIEWS",
    "DashboardWardrobePreviewMixin",
)

# Side labels follow MoHan's OWN left/right (owner ruling 2026-08-28):
# yaw+090 presents her LEFT side to the camera, yaw-090 her right.
WARDROBE_PREVIEW_VIEWS = (
    ("wardrobe_view_front", "正面", "yaw+000-pitch+00"),
    ("wardrobe_view_left", "左側", "yaw+090-pitch+00"),
    ("wardrobe_view_right", "右側", "yaw-090-pitch+00"),
    ("wardrobe_view_back", "背面", "yaw-180-pitch+00"),
)
PREVIEW_WIDTH = 220
PREVIEW_MIN_HEIGHT = 220
# Lets the tab paint before the first (slow) full-body composite starts.
PREVIEW_COMPOSE_DELAY_MS = 30
STATE_IDLE = "idle"
STATE_COMPOSING = "composing"
STATE_COMPOSITED = "composited"
STATE_FALLBACK = "fallback"
# Neutral closed-mouth frame; breath 0.5 is zero lift in the full-body renderer.
PREVIEW_MOTION = FaceMotionFrame(
    FacePose.FRONT, "idle", Viseme.CLOSED, MouthShape(), ExpressionShape(), breath=0.5,
)


class DashboardWardrobePreviewMixin:
    """The preview card of the Wardrobe Pavilion and its composited, cached views."""

    def _wardrobe_preview_card(self) -> QFrame:
        preview_card = QFrame()
        preview_card.setProperty("mohanRole", "portraitCard")
        preview = QVBoxLayout(preview_card)
        preview.setContentsMargins(0, 0, 0, 0)
        preview.setSpacing(8)
        scene = CelestialFrame(kind="scene")
        scene_layout = QVBoxLayout(scene)
        scene_layout.setContentsMargins(14, 20, 14, 0)
        preview_title = QLabel(self._t("wardrobe_character_preview", "墨寒造型預覽"))
        preview_title.setAlignment(Qt.AlignCenter)
        preview_title.setProperty("mohanRole", "cardTitle")
        self.wardrobe_character_preview = WardrobeTurntableLabel(scene)
        self.wardrobe_character_preview.attach_to_scene(SCENE_GROUND_RATIO)
        self.wardrobe_character_preview.setObjectName("wardrobeCharacterPreview")
        self.wardrobe_character_preview.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        scene.setMinimumSize(PREVIEW_WIDTH, PREVIEW_MIN_HEIGHT)
        self.wardrobe_character_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.wardrobe_character_preview.setAccessibleName(
            self._t("wardrobe_character_preview", "墨寒造型預覽")
        )
        ports = self.presentation_ports
        self._wardrobe_outfit_overlay = ports.outfit_overlay_factory(
            on_stale_body_profile=lambda: self.set_outfit_generation_status("body-profile-outdated")
        )
        self._wardrobe_full_body_renderer = ports.full_body_renderer_factory(
            outfit_overlay=self._wardrobe_outfit_overlay
        )
        self._wardrobe_preview_cache: dict[tuple[object, ...], QPixmap] = {}
        self._wardrobe_preview_pending = False
        self._wardrobe_preview_state = STATE_IDLE
        self._wardrobe_pose_source = QPixmap()
        self._wardrobe_pose_view = WARDROBE_PREVIEW_VIEWS[0][2]
        self.wardrobe_preview_state_label = QLabel("")
        self.wardrobe_preview_state_label.setAlignment(Qt.AlignCenter)
        self.wardrobe_preview_state_label.setWordWrap(True)
        self.wardrobe_preview_state_label.setProperty("mohanRole", "muted")
        rotation_hint = self._t(
            "wardrobe_rotation_hint",
            "拖曳人物可環繞 360°；也可用方向鍵旋轉，Home 回正面。",
        )
        self.wardrobe_character_preview.setAccessibleDescription(rotation_hint)
        self.wardrobe_character_preview.setToolTip(rotation_hint)
        self.wardrobe_rotation_hint = QLabel(rotation_hint)
        self.wardrobe_rotation_hint.setWordWrap(True)
        self.wardrobe_rotation_hint.setAlignment(Qt.AlignCenter)
        self.wardrobe_rotation_hint.setProperty("mohanRole", "rotationHint")
        self.wardrobe_character_preview.view_changed.connect(self._show_wardrobe_pose)
        self.wardrobe_character_preview.shown.connect(self._schedule_wardrobe_preview_compose)
        self._show_wardrobe_pose(self.wardrobe_character_preview.view_id)
        self.wardrobe_preview_name = QLabel(self._t("wardrobe_default_outfit", "內建預設服裝"))
        self.wardrobe_preview_name.setAlignment(Qt.AlignCenter)
        self.wardrobe_preview_name.setWordWrap(True)
        self.wardrobe_preview_name.setProperty("mohanRole", "statusPill")
        scene_layout.addWidget(preview_title)
        scene_layout.addStretch(1)
        preview.addWidget(scene, 1)
        preview.addWidget(self.wardrobe_preview_state_label)
        preview.addWidget(self.wardrobe_rotation_hint)
        preview.addWidget(self.wardrobe_preview_name)
        return preview_card

    def _update_wardrobe_preview_name(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        self.wardrobe_preview_name.setText(current.text())

    def _refresh_wardrobe_preview(self) -> None:
        """Selection or makeup changed: preserve the current turntable angle."""
        preview = getattr(self, "wardrobe_character_preview", None)
        if preview is None:
            return
        self._show_wardrobe_pose(preview.view_id)

    def _show_wardrobe_pose(self, view_id: str) -> None:
        self._wardrobe_pose_view = view_id
        cached = self._wardrobe_preview_cache.get(self._wardrobe_preview_key(view_id))
        if cached is not None:
            self._present_wardrobe_preview(cached)
            self._set_wardrobe_preview_state(STATE_COMPOSITED)
            return
        if self._wardrobe_full_body_renderer is None:
            # The offline dashboard uses its local compositor slot (offline dashboards): base plus overlay is cheap.
            self._compose_wardrobe_preview()
            return
        base = self._wardrobe_base_pixmap(view_id)
        if self._wardrobe_pose_source.isNull() and not base.isNull():
            self._present_wardrobe_preview(base)
        self._set_wardrobe_preview_state(STATE_COMPOSING)
        self._schedule_wardrobe_preview_compose()

    def _schedule_wardrobe_preview_compose(self) -> None:
        # Only a pending composite (state "composing") is scheduled; the offline
        # fallback is synchronous and a shown tab keeps each failed preview to one run.
        if (
            self._wardrobe_preview_pending
            or self._wardrobe_preview_state != STATE_COMPOSING
            or self._wardrobe_full_body_renderer is None
            or not self.wardrobe_character_preview.isVisible()
        ):
            return
        if self._wardrobe_preview_key(self._wardrobe_pose_view) in self._wardrobe_preview_cache:
            return
        self._wardrobe_preview_pending = True
        QTimer.singleShot(PREVIEW_COMPOSE_DELAY_MS, self._compose_wardrobe_preview)

    def _compose_wardrobe_preview(self) -> None:
        self._wardrobe_preview_pending = False
        view_id = self._wardrobe_pose_view
        key = self._wardrobe_preview_key(view_id)
        pixmap = self._wardrobe_preview_cache.get(key)
        state = STATE_COMPOSITED
        if pixmap is None:
            pixmap, state = self._composited_wardrobe_view(view_id)
            if pixmap.isNull():
                self._set_wardrobe_preview_state(STATE_FALLBACK)
                return
            if state == STATE_COMPOSITED:
                # One signature at a time: a selection change keeps each selection's look current.
                for stale in [entry for entry in self._wardrobe_preview_cache if entry[1:] != key[1:]]:
                    del self._wardrobe_preview_cache[stale]
                self._wardrobe_preview_cache[key] = pixmap
        self._present_wardrobe_preview(pixmap)
        self._set_wardrobe_preview_state(state)

    def _composited_wardrobe_view(self, view_id: str) -> tuple[QPixmap, str]:
        """Compose one view through the runtime path; fall back to the bare base protective."""
        renderer = self._wardrobe_full_body_renderer
        composed = QPixmap()
        if renderer is not None:
            try:
                composed = QPixmap(renderer.render_view(view_id, PREVIEW_MOTION))
            except (KeyError, OSError, RuntimeError, TypeError, ValueError):
                composed = QPixmap()
        if composed.isNull():
            base = self._wardrobe_base_pixmap(view_id)
            if base.isNull():
                return base, STATE_FALLBACK
            composed = self._wardrobe_outfit_overlay.apply(base, view_id)
        dressed = self._wardrobe_outfit_overlay.layer_count(view_id) > 0
        if not dressed and self.wardrobe_service.appearance_active():
            return composed, STATE_FALLBACK
        return composed, STATE_COMPOSITED

    def _wardrobe_preview_key(self, view_id: str) -> tuple[object, ...]:
        return (view_id, *self.wardrobe_service.appearance_signature())

    @staticmethod
    def _wardrobe_base_pixmap(view_id: str) -> QPixmap:
        return QPixmap(str(resource_path(POSE_ATLAS_RELATIVE_ROOT) / f"{view_id}.png"))

    def _present_wardrobe_preview(self, pixmap: QPixmap) -> None:
        self._wardrobe_pose_source = pixmap
        self.wardrobe_character_preview.set_rendered_pixmap(pixmap)

    def _set_wardrobe_preview_state(self, state: str) -> None:
        self._wardrobe_preview_state = state
        fallback = self._t(
            "wardrobe_preview_fallback",
            '外觀合成需要處理，預覽目前顯示素體；桌面角色維持目前外觀。',
        )
        label = getattr(self, "wardrobe_preview_state_label", None)
        if label is not None:
            label.setVisible(state == STATE_COMPOSING)
            if state == STATE_COMPOSING:
                label.setText(self._t("wardrobe_preview_composing", "正在以執行期合成造型預覽……"))
            elif state == STATE_FALLBACK:
                label.setText(fallback)
            else:
                label.setText("")
        # The wardrobe status line carries the fallback too, but stays below the
        # feedback of an action the owner just took (apply, import, makeup).
        status = getattr(self, "wardrobe_status", None)
        ready = self._t("wardrobe_status_ready", "雲裳系統已就緒")
        if state == STATE_FALLBACK and status is not None and status.text() in {ready, fallback}:
            status.setText(fallback)
