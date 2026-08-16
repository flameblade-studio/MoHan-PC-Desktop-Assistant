"""Compatibility alias for :mod:`application.camera_presence`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.camera_presence")
