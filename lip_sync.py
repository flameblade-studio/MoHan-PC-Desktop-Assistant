"""Compatibility alias for :mod:`domain.lip_sync`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.lip_sync")
