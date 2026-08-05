from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class UnsupportedPlatformFeature(OSError):
    """Raised when a platform adapter deliberately has no safe implementation."""


@dataclass(frozen=True)
class PlatformPaths:
    """Per-user paths selected without changing existing Windows storage."""

    data: Path
    config: Path
    cache: Path


@dataclass(frozen=True)
class PlatformCapabilities:
    """Capabilities proven by the concrete desktop-platform adapter."""

    platform_id: str
    display_name: str
    system_local_speech: bool
    verified_female_voice_catalog: bool
    offline_speech_recognition: bool
    secure_secret_storage: bool
    desktop_autostart: bool
    native_window_management: bool
    published_installers: tuple[str, ...]


class PlatformServicePort(Protocol):
    paths: PlatformPaths
    capabilities: PlatformCapabilities

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None: ...

    def open_path(self, path: Path) -> None: ...
