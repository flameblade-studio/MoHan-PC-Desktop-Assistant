"""Compatibility alias for :mod:`domain.outfit_pack`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.outfit_pack")
