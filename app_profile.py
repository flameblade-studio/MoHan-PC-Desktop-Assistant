"""Compatibility alias for :mod:`domain.app_profile`."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("domain.app_profile")
