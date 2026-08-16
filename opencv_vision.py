"""Compatibility alias for infrastructure.opencv_vision."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.opencv_vision")
