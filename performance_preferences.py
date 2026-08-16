"""Compatibility alias for :mod:`domain.performance_preferences`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.performance_preferences")
