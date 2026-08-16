"""Compatibility alias for :mod:`application.service_container`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("application.service_container")
