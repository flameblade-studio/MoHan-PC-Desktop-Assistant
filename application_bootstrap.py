"""Compatibility alias for :mod:`application.application_bootstrap`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.application_bootstrap")
