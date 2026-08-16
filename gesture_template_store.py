"""Compatibility alias for infrastructure.gesture_template_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.gesture_template_store")
