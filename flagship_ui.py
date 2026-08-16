"""Compatibility alias for :mod:`presentation.flagship_ui`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.flagship_ui")
