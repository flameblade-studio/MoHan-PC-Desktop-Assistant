from __future__ import annotations

lazy import os
lazy import sys
lazy from collections.abc import Mapping
lazy from functools import lru_cache
lazy from pathlib import Path

lazy from infrastructure.platform_contracts import PlatformServicePort
lazy from infrastructure.platform_linux import LinuxPlatformServices
lazy from infrastructure.platform_macos import MacOSPlatformServices
lazy from infrastructure.platform_windows import WindowsPlatformServices


def normalized_platform_id(value: str | None = None) -> str:
    candidate = str(value or sys.platform).strip().lower()
    if candidate.startswith("win") or candidate == "nt":
        return "windows"
    if candidate.startswith("darwin") or candidate in {"mac", "macos"}:
        return "macos"
    if candidate.startswith("linux"):
        return "linux"
    raise RuntimeError(f"MoHan 尚未定義此作業系統平台：{candidate}")


def create_platform_services(
    platform_id: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> PlatformServicePort:
    normalized = normalized_platform_id(platform_id)
    implementations = {
        "windows": WindowsPlatformServices,
        "macos": MacOSPlatformServices,
        "linux": LinuxPlatformServices,
    }
    return implementations[normalized](environ=environ, home=home)


@lru_cache(maxsize=1)
def current_platform_services() -> PlatformServicePort:
    return create_platform_services()


def resolved_data_dir(
    platform: PlatformServicePort | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    override = str(values.get("MOHAN_DATA_DIR", "")).strip()
    if override:
        return Path(override).expanduser()
    return (platform or current_platform_services()).paths.data
