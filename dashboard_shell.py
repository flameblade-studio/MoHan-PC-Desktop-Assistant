"""Compatibility alias for :mod:`presentation.dashboard_shell`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.dashboard_shell")
