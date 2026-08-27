from __future__ import annotations

lazy import ctypes
lazy import os
lazy from ctypes import wintypes

lazy from PySide6.QtCore import QPoint, Qt, QTimer
lazy from PySide6.QtGui import QAction, QMouseEvent
lazy from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

lazy from application.proactive_companion_app_bridge import ProactiveAppDisposition
lazy from application.wellbeing_app_bridge import ReminderTrigger
lazy from application.wellbeing_app_bridge import SpeakRequest as ProactiveSpeakRequest
lazy from domain.app_profile import profile_setting, profile_window_title
lazy from domain.language_support import localized_reminder_line
lazy from domain.time_utils import local_wall_time
lazy from presentation.presentation_resources import LIGHT_MENU_STYLE, application_icon
lazy from presentation.ui_localization import ui_text

__all__ = (
    "REMINDER_LINES",
    "CompanionPlatformMixin",
    "reminder_line",
)

MIN_OVERLAP_AREA = 256

REMINDER_LINES = frozendict({
    "work": "主上，今日之局已開。若要開始，妾替你計時。",
    "lunch": "到吃飯時間了。工作可以稍候，主上的身體不能。",
    "dinner": "主上，先去用晚膳。空著腹談什麼長策。",
    "offwork": "你已經不需要向任何老闆證明自己肯加班了。",
    "overwork": "主上已連續工作太久。離席、飲水、伸展，十分鐘後再戰。",
})


def reminder_line(language: str, kind: str) -> str:
    return localized_reminder_line(
        language,
        kind,
        REMINDER_LINES[kind],
    )


class CompanionPlatformMixin:
    """Own the companion window's desktop shell and shutdown lifecycle."""

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(application_icon(), self)
        self.tray.setToolTip(profile_window_title(self.db))
        # Parent the menu to the window so it is destroyed with it instead of
        # surviving as a parentless top-level widget after shutdown.
        menu = QMenu(self)
        # The tray menu is a system-level popup that does not inherit the
        # dashboard's flagship theme.  Apply the shared light palette so its
        # items stay readable instead of falling back to the OS dark theme
        # (black background with grey text).
        menu.setStyleSheet(LIGHT_MENU_STYLE)
        self.tray_menu = menu
        language = profile_setting(self.db, "ui_language")
        open_action = QAction(
            ui_text(
                language,
                "tray_open_today",
                "開啟今日卷冊",
            ),
            self,
        )
        quit_action = QAction(
            ui_text(language, "tray_quit", "讓寒歸劍"),
            self,
        )
        open_action.triggered.connect(self.open_dashboard)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                self.open_dashboard() if reason == QSystemTrayIcon.Trigger else None
            )
        )
        self.tray.show()

    def open_dashboard(self) -> None:
        self.dashboard.refresh_all()
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _dashboard_visibility_changed(self, active: bool) -> None:
        self._topmost_policy_tick()
        if active:
            QTimer.singleShot(0, self.dashboard.bring_to_front)

    def _external_foreground_window(self) -> int:
        if os.name != "nt":
            return 0
        user32 = ctypes.windll.user32
        foreground = int(user32.GetForegroundWindow() or 0)
        if not foreground:
            return 0
        foreground = int(user32.GetAncestor(foreground, 2) or foreground)

        class GUIThreadInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        thread_id = user32.GetWindowThreadProcessId(foreground, None)
        gui_info = GUIThreadInfo()
        gui_info.cbSize = ctypes.sizeof(GUIThreadInfo)
        if thread_id and user32.GetGUIThreadInfo(
            thread_id,
            ctypes.byref(gui_info),
        ):
            moving = int(gui_info.hwndMoveSize or 0)
            if moving:
                foreground = int(user32.GetAncestor(moving, 2) or moving)
        own_windows = {
            int(self.winId()),
            int(self.dashboard.winId()),
        }
        if foreground in own_windows:
            return 0
        if not user32.IsWindowVisible(foreground) or user32.IsIconic(foreground):
            return 0
        class_name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(foreground, class_name, len(class_name))
        if class_name.value in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
        }:
            return 0
        return foreground

    @staticmethod
    def _rectangles_overlap_or_near(
        external: tuple[int, int, int, int],
        character: tuple[int, int, int, int],
        margin: int = 18,
    ) -> bool:
        ext_left, ext_top, ext_right, ext_bottom = external
        char_left, char_top, char_right, char_bottom = character
        char_left -= margin
        char_top -= margin
        char_right += margin
        char_bottom += margin
        overlap_width = max(
            0,
            min(ext_right, char_right) - max(ext_left, char_left),
        )
        overlap_height = max(
            0,
            min(ext_bottom, char_bottom) - max(ext_top, char_top),
        )
        return overlap_width * overlap_height >= MIN_OVERLAP_AREA

    def _external_foreground_overlaps_character(self) -> bool:
        self._smart_overlap_hwnd = 0
        if os.name != "nt":
            return False
        user32 = ctypes.windll.user32
        foreground = self._external_foreground_window()
        if not foreground:
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(foreground, ctypes.byref(rect)):
            return False
        character_rect = wintypes.RECT()
        if not user32.GetWindowRect(
            int(self.winId()),
            ctypes.byref(character_rect),
        ):
            return False
        overlaps = self._rectangles_overlap_or_near(
            (rect.left, rect.top, rect.right, rect.bottom),
            (
                character_rect.left,
                character_rect.top,
                character_rect.right,
                character_rect.bottom,
            ),
        )
        if overlaps:
            self._smart_overlap_hwnd = foreground
        return overlaps

    def _set_windows_character_z_order(
        self,
        enabled: bool,
        behind_hwnd: int = 0,
        user32=None,
        hwnd: int | None = None,
    ) -> None:
        user32 = user32 or ctypes.windll.user32
        hwnd = int(self.winId()) if hwnd is None else int(hwnd)
        flags = 0x0001 | 0x0002 | 0x0010
        if enabled:
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)
            return
        # HWND_NOTOPMOST only removes the topmost style and may still leave
        # the character above every normal window. Explicitly insert it
        # behind the foreground/moving window afterwards.
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)
        if behind_hwnd and user32.IsWindow(behind_hwnd):
            user32.SetWindowPos(
                hwnd,
                int(behind_hwnd),
                0,
                0,
                0,
                0,
                flags,
            )

    def _set_character_topmost(
        self,
        enabled: bool,
        behind_hwnd: int = 0,
    ) -> None:
        enabled = bool(enabled)
        behind_hwnd = 0 if enabled else int(behind_hwnd or 0)
        if self.character_topmost_active == enabled and (
            enabled or self.character_behind_hwnd == behind_hwnd
        ):
            return
        self.character_topmost_active = enabled
        self.character_behind_hwnd = behind_hwnd
        if os.name == "nt":
            self._set_windows_character_z_order(
                enabled,
                behind_hwnd,
            )
            return
        position = self.pos()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enabled)
        self.move(position)
        self.show()

    def _topmost_policy_tick(self) -> None:
        dashboard_active = (
            self.dashboard.isVisible() and not self.dashboard.isMinimized()
        )
        mode = str(
            self.db.setting(
                "topmost_mode",
                "智慧置頂（推薦）",
            )
        )
        if dashboard_active or mode == "不置頂":
            should_stay_on_top = False
            behind_hwnd = (
                int(self.dashboard.winId())
                if dashboard_active
                else self._external_foreground_window()
            )
        elif mode == "永遠置頂":
            should_stay_on_top = True
            behind_hwnd = 0
        else:
            should_stay_on_top = not self._external_foreground_overlaps_character()
            behind_hwnd = self._smart_overlap_hwnd
        self._set_character_topmost(
            should_stay_on_top,
            behind_hwnd,
        )

    def check_reminders(self) -> None:
        now = local_wall_time()
        for row in self.db.due_reminders(now):
            kind = str(row["kind"])
            result = self._dispatch_proactive_companion(
                timer_trigger=(
                    ReminderTrigger(kind) if kind in {"lunch", "dinner"} else None
                ),
                scheduled_request=(
                    None
                    if kind in {"lunch", "dinner"}
                    else ProactiveSpeakRequest(
                        str(
                            self.db.setting(
                                f"reminder_message_{kind}",
                                reminder_line(
                                    profile_setting(self.db, "ui_language"),
                                    kind,
                                ),
                            )
                        ),
                        "scheduled",
                        f"scheduled:{kind}:{now.date().isoformat()}",
                    )
                ),
            )
            if (
                result is not None
                and result.disposition is ProactiveAppDisposition.SUBMITTED
            ):
                self.db.mark_reminder_fired(kind, now.date().isoformat())
                self.dashboard.show()
                self.dashboard.raise_()

        active = self.db.active_session_seconds()
        threshold = int(self.db.setting("break_minutes", 90)) * 60
        bucket = active // threshold if threshold else 0
        notice_key = f"{now.date().isoformat()}-{bucket}"
        if active >= threshold and bucket and notice_key != self.last_overwork_notice:
            result = self._dispatch_proactive_companion(
                timer_trigger=ReminderTrigger.OVERWORK
            )
            if (
                result is not None
                and result.disposition is ProactiveAppDisposition.SUBMITTED
            ):
                self.last_overwork_notice = notice_key
                self.dashboard.show()
                self.dashboard.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._begin_character_drag(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_offset and event.buttons() & Qt.LeftButton:
            self._move_character_drag(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._finish_character_drag()
        super().mouseReleaseEvent(event)

    def _begin_character_drag(self, global_position: QPoint) -> None:
        self.drag_offset = global_position - self.frameGeometry().topLeft()

    def _move_character_drag(self, global_position: QPoint) -> None:
        if self.drag_offset is not None:
            self.move(global_position - self.drag_offset)

    def _finish_character_drag(self) -> None:
        self.drag_offset = None

    def _stop_window_timers(self) -> None:
        for timer_name in (
            "idle_timer",
            "pose_timer",
            "blink_timer",
            "gaze_timer",
            "ambient_timer",
            "mouth_timer",
            "mouth_visual_timer",
            "speech_finish_timer",
            "realtime_finish_timer",
            "expression_return_timer",
            "physics_timer",
            "motion_timer",
            "attention_timer",
            "saccade_timer",
            "reminder_timer",
            "clock_timer",
            "topmost_timer",
            "background_agent_timer",
            "proactive_presence_timer",
        ):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()

    def _close_runtime_services(self) -> None:
        outfit_generation = getattr(self, "_autonomous_outfit_generation", None)
        if outfit_generation is not None:
            outfit_generation.stop()
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is not None:
            scheduler.close()
            self.background_scheduler = None
        self.blink_generation = getattr(self, "blink_generation", 0) + 1
        self._cancel_expression_transition()
        self._cancel_pose_transition()
        for animation_name in ("state_animation",):
            animation = getattr(self, animation_name, None)
            if animation is not None:
                animation.stop()
        self._stop_realtime_output()
        self._stop_window_timers()
        for dashboard_timer_name in ("timer", "front_raise_timer"):
            dashboard_timer = getattr(
                self.dashboard,
                dashboard_timer_name,
                None,
            )
            if dashboard_timer is not None:
                dashboard_timer.stop()
        flagship_center = getattr(self.dashboard, "flagship_center", None)
        if flagship_center is not None:
            flagship_center.close_services()
        for engine in {self.azure_tts, self.azure_hd_tts}:
            close = getattr(engine, "close", None)
            if close is not None:
                close()

    def closeEvent(self, event) -> None:
        self._closing = True
        self._close_proactive_companion_app_bridge()
        self._cancel_adaptive_character_composition()
        self._close_runtime_services()
        self.dashboard.close()
        self.db.close()
        tray = getattr(self, "tray", None)
        if tray is not None:
            tray.hide()
        event.accept()
