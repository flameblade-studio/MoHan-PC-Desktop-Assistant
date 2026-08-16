"""Compatibility alias for :mod:`application.wellbeing_runtime`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.wellbeing_runtime")
