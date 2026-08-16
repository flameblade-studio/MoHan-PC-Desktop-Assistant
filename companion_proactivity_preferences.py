"""Compatibility alias for :mod:`domain.companion_proactivity_preferences`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.companion_proactivity_preferences")
