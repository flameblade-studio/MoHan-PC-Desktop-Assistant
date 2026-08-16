"""Compatibility alias for infrastructure.memory_index."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.memory_index")
