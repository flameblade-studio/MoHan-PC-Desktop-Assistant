from __future__ import annotations

lazy import ctypes
lazy import sys
lazy from ctypes import wintypes


class _LastInputInfo(ctypes.Structure):
    _fields_ = (("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD))


def seconds_since_local_input() -> float | None:
    """Return local desktop idle time while keeping keys and pointer data private."""

    if sys.platform != "win32":
        return None
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    get_tick_count64 = ctypes.windll.kernel32.GetTickCount64
    get_tick_count64.restype = ctypes.c_ulonglong
    tick_count = get_tick_count64()
    elapsed_ms = ((tick_count & 0xFFFFFFFF) - info.dwTime) & 0xFFFFFFFF
    return elapsed_ms / 1000.0
