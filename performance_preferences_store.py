"""Compatibility alias for infrastructure.performance_preferences_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.performance_preferences_store")
