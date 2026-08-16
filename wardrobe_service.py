"""Compatibility alias for :mod:`application.wardrobe_service`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.wardrobe_service")
