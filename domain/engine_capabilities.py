"""The running engine's own compatibility facts for character-pack checks."""

from __future__ import annotations

lazy import json
lazy import sys
lazy import tomllib
lazy from dataclasses import dataclass
lazy from pathlib import Path

ENGINE_API_VERSION = 1
SUPPORTED_ENGINE_FEATURES: frozenset[str] = frozenset()
UNKNOWN_ENGINE_VERSION = "0.0.0"


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """What this build can actually run; never derived from the pack being checked."""

    version: str
    api_version: int
    features: frozenset[str]


def current_engine_capabilities() -> EngineCapabilities:
    return EngineCapabilities(
        _runtime_engine_version(),
        ENGINE_API_VERSION,
        SUPPORTED_ENGINE_FEATURES,
    )


def _runtime_engine_version() -> str:
    """Read this runtime's build metadata without importing a product shell."""

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    build_info_path = root / "build-info.json"
    try:
        payload = json.loads(build_info_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()

    project_path = root / "pyproject.toml"
    try:
        project_payload = tomllib.loads(project_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, tomllib.TOMLDecodeError):
        return UNKNOWN_ENGINE_VERSION
    project = project_payload.get("project")
    if not isinstance(project, dict):
        return UNKNOWN_ENGINE_VERSION
    version = project.get("version")
    return (
        version.strip()
        if isinstance(version, str) and version.strip()
        else UNKNOWN_ENGINE_VERSION
    )
