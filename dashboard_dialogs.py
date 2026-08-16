"""Compatibility alias for :mod:`presentation.dashboard_dialogs`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("presentation.dashboard_dialogs")
