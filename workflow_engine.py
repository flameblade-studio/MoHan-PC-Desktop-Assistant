"""Compatibility alias for :mod:`application.workflow_engine`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.workflow_engine")
