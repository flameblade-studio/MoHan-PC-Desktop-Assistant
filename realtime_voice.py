"""Compatibility alias for integrations.realtime_voice."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.realtime_voice")
