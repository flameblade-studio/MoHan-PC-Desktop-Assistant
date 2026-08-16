"""Compatibility alias for :mod:`application.visual_social_cues`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.visual_social_cues")
