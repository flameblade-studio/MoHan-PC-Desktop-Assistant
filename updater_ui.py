"""Compatibility alias for :mod:`presentation.updater_ui`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.updater_ui")
