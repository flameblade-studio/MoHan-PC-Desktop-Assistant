"""Compatibility alias for integrations.cloud_connectors."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.cloud_connectors")
