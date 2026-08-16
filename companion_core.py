"""Compatibility alias for :mod:`presentation.companion_core`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.companion_core")
