"""Compatibility alias for integrations.azure_regions."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.azure_regions")
