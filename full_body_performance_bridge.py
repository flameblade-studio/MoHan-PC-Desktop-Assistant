"""Compatibility alias for :mod:`application.full_body_performance_bridge`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.full_body_performance_bridge")
