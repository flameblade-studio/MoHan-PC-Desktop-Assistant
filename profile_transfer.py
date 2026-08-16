"""Compatibility alias for infrastructure.profile_transfer."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.profile_transfer")
