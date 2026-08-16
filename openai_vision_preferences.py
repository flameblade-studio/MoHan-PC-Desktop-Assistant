"""Compatibility alias for :mod:`domain.openai_vision_preferences`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.openai_vision_preferences")
