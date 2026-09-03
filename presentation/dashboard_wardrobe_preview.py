"""Wardrobe Pavilion character preview: the composed look through the runtime path.

The preview no longer shows the raw pose-atlas PNG.  It composes the four
preview views (front, MoHan's left, her right, back) through the same
full-body renderer and active-outfit overlay the desktop companion uses, so
what the owner sees in the pavilion is what walks on the desktop: the
selected garment, hairstyle, headwear and makeup at the chosen intensity.

Composites are cached per (appearance signature, view) and rebuilt only when
the selection or makeup state changes.  A first composite takes a moment, so
it runs on a short timer once the preview is on screen instead of blocking
the UI thread; the bare base is shown meanwhile with an explicit "composing"
line.  A failed composite falls back to the bare base and, when a pack is
active, says so in the wardrobe status instead of staying silent.
"""

from __future__ import annotations

lazy from functools import partial

lazy from PySide6.QtCore import QTimer, Qt, Signal
lazy from PySide6.QtGui import QPixmap, QShowEvent
lazy from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
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

__all__ = (
    "PREVIEW_COMPOSE_DELAY_MS",
    "WARDROBE_PREVIEW_VIEWS",
    "DashboardWardrobePreviewMixin",
    "WardrobePreviewLabel",
)

# Side labels follow MoHan's OWN left/right (owner ruling 2026-08-28):
# yaw+090 presents her LEFT side to the camera, yaw-090 her right.
WARDROBE_PREVIEW_VIEWS = (
    ("wardrobe_view_front", "正面", "yaw+000-pitch+00"),
    ("wardrobe_view_left", "左側", "yaw+090-pitch+00"),
    ("wardrobe_view_right", "右側", "yaw-090-pitch+00"),
    ("wardrobe_view_back", "背面", "yaw-180-pitch+00"),
)
PREVIEW_WIDTH = 300
PREVIEW_HEIGHT = 400
PREVIEW_MIN_HEIGHT = 410
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


class WardrobePreviewLabel(QLabel):
    """Preview surface that announces when it becomes visible (its tab was shown)."""

    shown = Signal()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.shown.emit()


class DashboardWardrobePreviewMixin:
    """The preview card of the Wardrobe Pavilion and its composited, cached views."""

    def _wardrobe_preview_card(self) -> QFrame:
        preview_card = QFrame()
        preview_card.setProperty("mohanRole", "portraitCard")
        preview = QVBoxLayout(preview_card)
        preview.setContentsMargins(14, 14, 14, 14)
        preview.setSpacing(8)
        preview_title = QLabel(self._t("wardrobe_character_preview", "墨寒造型預覽"))
        preview_title.setAlignment(Qt.AlignCenter)
        preview_title.setProperty("mohanRole", "cardTitle")
        self.wardrobe_character_preview = WardrobePreviewLabel()
        self.wardrobe_character_preview.setObjectName("wardrobeCharacterPreview")
        self.wardrobe_character_preview.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        self.wardrobe_character_preview.setMinimumSize(PREVIEW_WIDTH, PREVIEW_MIN_HEIGHT)
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
        self.wardrobe_pose_buttons: list[QPushButton] = []
        pose_actions = QHBoxLayout()
        pose_actions.setSpacing(5)
        for key, fallback, view_id in WARDROBE_PREVIEW_VIEWS:
            button = QPushButton(self._t(key, fallback))
            button.setCheckable(True)
            button.setProperty("mohanAction", "pose")
            button.clicked.connect(partial(self._show_wardrobe_pose, view_id, button))
            self.wardrobe_pose_buttons.append(button)
            pose_actions.addWidget(button)
        self.wardrobe_character_preview.shown.connect(self._schedule_wardrobe_preview_compose)
        self._show_wardrobe_pose(WARDROBE_PREVIEW_VIEWS[0][2], self.wardrobe_pose_buttons[0])
        self.wardrobe_preview_name = QLabel(self._t("wardrobe_default_outfit", "內建預設服裝"))
        self.wardrobe_preview_name.setAlignment(Qt.AlignCenter)
        self.wardrobe_preview_name.setWordWrap(True)
        self.wardrobe_preview_name.setProperty("mohanRole", "statusPill")
        preview.addWidget(preview_title)
        preview.addWidget(self.wardrobe_character_preview, 1)
        preview.addWidget(self.wardrobe_preview_state_label)
        preview.addLayout(pose_actions)
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
        """Selection or makeup changed: re-show the checked view under the new signature."""
        buttons = getattr(self, "wardrobe_pose_buttons", None)
        if not buttons:
            return
        checked = next((button for button in buttons if button.isChecked()), buttons[0])
        self._show_wardrobe_pose(self._wardrobe_pose_view, checked)

    def _show_wardrobe_pose(self, view_id: str, active: QPushButton) -> None:
        self._wardrobe_pose_view = view_id
        for button in self.wardrobe_pose_buttons:
            button.setChecked(button is active)
        cached = self._wardrobe_preview_cache.get(self._wardrobe_preview_key(view_id))
        if cached is not None:
            self._present_wardrobe_preview(cached)
            self._set_wardrobe_preview_state(STATE_COMPOSITED)
            return
        if self._wardrobe_full_body_renderer is None:
            # No compositor was injected (offline dashboards): base plus overlay is cheap.
            self._compose_wardrobe_preview()
            return
        base = self._wardrobe_base_pixmap(view_id)
        if not base.isNull():
            self._present_wardrobe_preview(base)
        self._set_wardrobe_preview_state(STATE_COMPOSING)
        self._schedule_wardrobe_preview_compose()

    def _schedule_wardrobe_preview_compose(self) -> None:
        # Only a pending composite (state "composing") is scheduled; the offline
        # fallback is synchronous and a shown tab must not re-run a failed one.
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
                # One signature at a time: a selection change never keeps stale looks around.
                for stale in [entry for entry in self._wardrobe_preview_cache if entry[1:] != key[1:]]:
                    del self._wardrobe_preview_cache[stale]
                self._wardrobe_preview_cache[key] = pixmap
        self._present_wardrobe_preview(pixmap)
        self._set_wardrobe_preview_state(state)

    def _composited_wardrobe_view(self, view_id: str) -> tuple[QPixmap, str]:
        """Compose one view through the runtime path; fall back to the bare base fail-closed."""
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
        self.wardrobe_character_preview.setPixmap(
            pixmap.scaled(PREVIEW_WIDTH, PREVIEW_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _set_wardrobe_preview_state(self, state: str) -> None:
        self._wardrobe_preview_state = state
        fallback = self._t(
            "wardrobe_preview_fallback",
            "造型預覽暫時無法合成，目前顯示素體；桌面伴侶不受影響。",
        )
        label = getattr(self, "wardrobe_preview_state_label", None)
        if label is not None:
            if state == STATE_COMPOSING:
                label.setText(self._t("wardrobe_preview_composing", "正在以執行期合成造型預覽……"))
            elif state == STATE_FALLBACK:
                label.setText(fallback)
            else:
                label.setText("")
        # The wardrobe status line carries the fallback too, but never over the
        # feedback of an action the owner just took (apply, import, makeup).
        status = getattr(self, "wardrobe_status", None)
        ready = self._t("wardrobe_status_ready", "雲裳系統已就緒")
        if state == STATE_FALLBACK and status is not None and status.text() in {ready, fallback}:
            status.setText(fallback)
