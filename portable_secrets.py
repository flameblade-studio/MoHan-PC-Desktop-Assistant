"""Compatibility alias for infrastructure.portable_secrets."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("infrastructure.portable_secrets")
