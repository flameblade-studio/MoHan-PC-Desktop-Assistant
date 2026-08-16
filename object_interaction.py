"""Compatibility alias for :mod:`application.object_interaction`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.object_interaction")
