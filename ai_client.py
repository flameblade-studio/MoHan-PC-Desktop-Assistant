"""Compatibility alias for integrations.ai_client."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.ai_client")
