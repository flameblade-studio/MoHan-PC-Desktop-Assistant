"""Compatibility alias for :mod:`application.background_agents`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.background_agents")
