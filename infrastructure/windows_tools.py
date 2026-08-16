from __future__ import annotations

lazy import ctypes
lazy import os
lazy from ctypes import wintypes
lazy from functools import lru_cache
lazy from typing import Any

lazy from domain.flagship_action_models import ActionRequest, ActionResult


@lru_cache(maxsize=1)
def _user32():
    if os.name != "nt" or not hasattr(ctypes, "windll"):
        return None
    return ctypes.windll.user32


def visible_windows() -> list[dict[str, Any]]:
    user32 = _user32()
    if user32 is None:
        return []
    rows: list[dict[str, Any]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        rows.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "rect": [
                    int(rect.left),
                    int(rect.top),
                    int(rect.right),
                    int(rect.bottom),
                ],
            }
        )
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return rows


class WindowTools:
    def register_with(self, executor) -> None:
        if _user32() is None:
            return
        executor.register("window_list", self.action_list)
        executor.register(
            "window_activate",
            self.action_activate,
            self.verify_activate,
        )

    @staticmethod
    def action_list(request: ActionRequest) -> ActionResult:
        rows = visible_windows()
        return ActionResult(
            request.request_id,
            True,
            f"目前有 {len(rows)} 個可見視窗",
            {"windows": rows},
        )

    @staticmethod
    def action_activate(request: ActionRequest) -> ActionResult:
        user32 = _user32()
        if user32 is None:
            raise OSError("此平台不提供 Windows 視窗切換功能。")
        target = str(request.arguments.get("title", "")).strip()
        if not target:
            raise ValueError("請提供完整視窗標題")
        matches = [
            row for row in visible_windows() if row["title"] == target
        ]
        if len(matches) != 1:
            raise ValueError("視窗標題必須完整且只能符合一個視窗")
        hwnd = int(matches[0]["hwnd"])
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        if not user32.SetForegroundWindow(hwnd):
            raise RuntimeError("Windows 拒絕切換前景視窗")
        return ActionResult(
            request.request_id,
            True,
            f"已切換至：{target}",
            {"hwnd": hwnd, "title": target},
        )

    @staticmethod
    def verify_activate(
        _request: ActionRequest,
        result: ActionResult,
    ) -> bool:
        user32 = _user32()
        if user32 is None:
            return False
        return int(user32.GetForegroundWindow()) == int(result.data.get("hwnd", 0))
