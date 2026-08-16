"""Compatibility alias for integrations.remote_control."""

from __future__ import annotations

lazy import importlib
lazy import sys

sys.modules[__name__] = importlib.import_module("integrations.remote_control")
