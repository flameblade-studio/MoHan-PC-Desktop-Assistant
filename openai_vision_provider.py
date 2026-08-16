"""Compatibility alias for integrations.openai_vision_provider."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.openai_vision_provider")
