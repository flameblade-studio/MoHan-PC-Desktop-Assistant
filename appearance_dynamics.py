"""Compatibility alias for :mod:`domain.appearance_dynamics`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.appearance_dynamics")
