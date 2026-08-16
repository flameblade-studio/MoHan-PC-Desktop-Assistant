"""Compatibility alias for :mod:`application.packaged_self_test`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.packaged_self_test")
