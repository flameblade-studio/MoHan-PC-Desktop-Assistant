from __future__ import annotations

lazy import os
lazy import winreg
lazy from collections.abc import Mapping
lazy from contextlib import suppress
lazy from pathlib import Path

lazy from platform_contracts import (
    PlatformCapabilities,
    PlatformPaths,
    UnsupportedPlatformFeature,
)


class WindowsPlatformServices:
    """Windows desktop integration with imports kept behind runtime guards."""

    capabilities = PlatformCapabilities(
        platform_id="windows",
        display_name="Windows",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=True,
        native_window_management=True,
        published_installers=("portable-zip", "exe", "msi"),
    )

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
    ):
        values = os.environ if environ is None else environ
        user_home = Path.home() if home is None else Path(home)
        local_root = Path(values.get("LOCALAPPDATA") or user_home)
        # This is the exact path used by every existing public Windows build.
        # Moving it would silently create a new profile and appear to lose data.
        application_root = local_root / "YanJianStudio" / "MoHan"
        self.paths = PlatformPaths(
            data=application_root,
            config=application_root,
            cache=application_root / "cache",
        )

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        if os.name != "nt":
            raise UnsupportedPlatformFeature(
                "Windows 登入自動啟動只能在 Windows 上設定。"
            )
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    application_id,
                    0,
                    winreg.REG_SZ,
                    command,
                )
                return
            with suppress(FileNotFoundError):
                winreg.DeleteValue(key, application_id)

    def open_path(self, path: Path) -> None:
        if os.name != "nt":
            raise UnsupportedPlatformFeature(
                "Windows 路徑開啟功能只能在 Windows 上使用。"
            )
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            raise UnsupportedPlatformFeature("目前 Python 不提供 os.startfile。")
        startfile(str(path))
