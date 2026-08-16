"""Compatibility alias for infrastructure.special_occasion_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.special_occasion_store")
