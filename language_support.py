"""Compatibility alias for :mod:`domain.language_support`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.language_support")
