"""Compatibility alias for :mod:`application.runtime_bootstrap`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.runtime_bootstrap")
