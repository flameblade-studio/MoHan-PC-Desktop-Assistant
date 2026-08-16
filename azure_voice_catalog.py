"""Compatibility alias for integrations.azure_voice_catalog."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.azure_voice_catalog")
