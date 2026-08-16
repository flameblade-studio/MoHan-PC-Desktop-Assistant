"""Compatibility alias for :mod:`domain.feature_registry`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.feature_registry")
