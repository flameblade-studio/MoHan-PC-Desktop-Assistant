"""Compatibility alias for infrastructure.openai_vision_preferences_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.openai_vision_preferences_store")
