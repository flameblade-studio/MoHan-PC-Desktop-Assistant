"""Compatibility alias for :mod:`application.proactive_companion_composition`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.proactive_companion_composition")
