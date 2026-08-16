"""Compatibility alias for infrastructure.wellbeing_reminder_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.wellbeing_reminder_store")
