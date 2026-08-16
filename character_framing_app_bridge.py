"""Compatibility alias for :mod:`application.character_framing_app_bridge`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.character_framing_app_bridge")
