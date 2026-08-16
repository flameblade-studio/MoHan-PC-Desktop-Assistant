"""Compatibility alias for :mod:`domain.version_info`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.version_info")
