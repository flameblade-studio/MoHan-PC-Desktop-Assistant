"""Compatibility alias for :mod:`application.visual_context_fusion`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.visual_context_fusion")
