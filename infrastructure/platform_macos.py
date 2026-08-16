from __future__ import annotations

lazy import subprocess
lazy from collections.abc import Mapping
lazy from pathlib import Path

lazy from infrastructure.platform_contracts import (
    PlatformCapabilities,
    PlatformPaths,
    UnsupportedPlatformFeature,
)


class MacOSPlatformServices:
    """Safe macOS paths and desktop opening for the compatibility foundation."""

    capabilities = PlatformCapabilities(
        platform_id="macos",
        display_name="macOS",
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
        del environ
        user_home = Path.home() if home is None else Path(home)
        application_support = (
            user_home / "Library" / "Application Support" / "YanJianStudio" / "MoHan"
        )
        self.paths = PlatformPaths(
            data=application_support,
            config=application_support,
            cache=user_home / "Library" / "Caches" / "YanJianStudio" / "MoHan",
        )

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
            "macOS 登入項目尚未進入已驗證的安全實作階段。"
        )

    def open_path(self, path: Path) -> None:
        subprocess.Popen(
            ["open", str(path)],
            close_fds=True,
            start_new_session=True,
        )
