"""Compatibility alias for :mod:`application.cloud_vision_runtime`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.cloud_vision_runtime")
