from __future__ import annotations

lazy import os
lazy import subprocess
lazy from collections.abc import Mapping
lazy from pathlib import Path, PurePosixPath

lazy from infrastructure.platform_contracts import (
    PlatformCapabilities,
    PlatformPaths,
    UnsupportedPlatformFeature,
)


class LinuxPlatformServices:
    """XDG-compliant paths and desktop opening for the Linux foundation."""

    capabilities = PlatformCapabilities(
        platform_id="linux",
        display_name="Linux",
        system_local_speech=False,
        verified_female_voice_catalog=False,
        offline_speech_recognition=False,
        secure_secret_storage=False,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=(),
    )

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
    ):
        values = os.environ if environ is None else environ
        user_home = Path.home() if home is None else Path(home)
        suffix = Path("YanJianStudio") / "MoHan"
        data_root = self._xdg_root(
            values,
            "XDG_DATA_HOME",
            user_home / ".local" / "share",
        )
        config_root = self._xdg_root(
            values,
            "XDG_CONFIG_HOME",
            user_home / ".config",
        )
        cache_root = self._xdg_root(
            values,
            "XDG_CACHE_HOME",
            user_home / ".cache",
        )
        self.paths = PlatformPaths(
            data=data_root / suffix,
            config=config_root / suffix,
            cache=cache_root / suffix,
        )

    @staticmethod
    def _xdg_root(
        values: Mapping[str, str],
        name: str,
        fallback: Path,
    ) -> Path:
        raw = str(values.get(name, "")).strip()
        # XDG base directories must be absolute.  A relative value would make
        # private data depend on the process working directory, so ignore it.
        if raw and PurePosixPath(raw).is_absolute():
            return Path(raw)
        return fallback

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        del application_id, command
        if not enabled:
            return
        raise UnsupportedPlatformFeature(
            "Linux 自動啟動尚未進入已驗證的安全實作階段。"
        )

    def open_path(self, path: Path) -> None:
        subprocess.Popen(
            ["xdg-open", str(path)],
            close_fds=True,
            start_new_session=True,
        )
