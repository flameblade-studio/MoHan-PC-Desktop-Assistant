"""Compatibility alias for :mod:`presentation.first_run_wizard`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.first_run_wizard")
