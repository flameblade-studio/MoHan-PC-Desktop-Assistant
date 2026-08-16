"""Compatibility alias for :mod:`application.framing_orchestrator`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.framing_orchestrator")
