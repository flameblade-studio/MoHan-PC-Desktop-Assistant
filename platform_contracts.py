"""Compatibility alias for infrastructure.platform_contracts."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.platform_contracts")
