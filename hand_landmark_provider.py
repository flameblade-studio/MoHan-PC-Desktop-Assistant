"""Compatibility alias for infrastructure.hand_landmark_provider."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.hand_landmark_provider")
