from __future__ import annotations

lazy import ctypes
lazy import sys
lazy from ctypes import wintypes


class _LastInputInfo(ctypes.Structure):
    _fields_ = (("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD))


def seconds_since_local_input() -> float | None:
    """Return local desktop idle time without recording keys or pointer data."""

    if sys.platform != "win32":
        return None
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    tick_count = ctypes.windll.kernel32.GetTickCount64()
    return max(0.0, (tick_count - info.dwTime) / 1000.0)
