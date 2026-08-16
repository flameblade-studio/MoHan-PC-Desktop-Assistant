"""Compatibility alias for integrations.home_assistant."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.home_assistant")
