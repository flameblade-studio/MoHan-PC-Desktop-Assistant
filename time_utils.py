"""Compatibility alias for :mod:`domain.time_utils`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.time_utils")
