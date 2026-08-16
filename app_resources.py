"""Compatibility alias for infrastructure.app_resources."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.app_resources")
