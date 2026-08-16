"""Compatibility alias for infrastructure.portable_secret_binding."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.portable_secret_binding")
