"""Compatibility alias for :mod:`domain.expression_system`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.expression_system")
