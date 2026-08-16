"""Compatibility alias for :mod:`application.multisensory_interaction`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.multisensory_interaction")
