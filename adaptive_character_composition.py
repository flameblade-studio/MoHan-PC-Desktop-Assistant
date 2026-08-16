"""Compatibility alias for :mod:`application.adaptive_character_composition`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.adaptive_character_composition")
