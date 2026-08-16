"""Compatibility alias for :mod:`application.companion_phrasebook`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.companion_phrasebook")
