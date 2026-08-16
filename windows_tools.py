"""Compatibility alias for infrastructure.windows_tools."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.windows_tools")
