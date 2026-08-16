"""Compatibility alias for :mod:`application.visual_perception`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.visual_perception")
