"""Compatibility alias for :mod:`application.behavior_director`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.behavior_director")
