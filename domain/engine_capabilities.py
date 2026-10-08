"""The running engine's own compatibility facts for character-pack checks."""

from __future__ import annotations

lazy from dataclasses import dataclass

lazy from domain.version_info import APP_VERSION

ENGINE_API_VERSION = 1
SUPPORTED_ENGINE_FEATURES: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """What this build can actually run; never derived from the pack being checked."""

    version: str
    api_version: int
    features: frozenset[str]


def current_engine_capabilities() -> EngineCapabilities:
    return EngineCapabilities(APP_VERSION, ENGINE_API_VERSION, SUPPORTED_ENGINE_FEATURES)
