"""Compatibility alias for :mod:`application.local_visual_intelligence`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.local_visual_intelligence")
