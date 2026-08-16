"""Compatibility alias for infrastructure.platform_macos."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.platform_macos")
