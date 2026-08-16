"""Compatibility alias for infrastructure.secret_store."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.secret_store")
