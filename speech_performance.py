"""Compatibility alias for :mod:`application.speech_performance`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.speech_performance")
